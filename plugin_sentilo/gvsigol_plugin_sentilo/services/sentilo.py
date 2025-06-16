

from collections import defaultdict
from django.shortcuts import get_object_or_404
import pandas as pd
import requests
from gvsigol_plugin_sentilo.models import SentiloConfiguration
from sqlalchemy import Column, String, Float, Integer, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, Table

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from gvsigol_plugin_sentilo.settings import SENTILO_DB, MUNICIPALITY
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

def fetch_sentilo_api(url, identity_key, db_table, sensors):
    conn_string = 'postgresql://'+SENTILO_DB['user']+':'+SENTILO_DB['password']+'@'+SENTILO_DB['host']+':'+SENTILO_DB['port']+'/'+SENTILO_DB['database']
    db = create_engine(conn_string)
    conn = db.connect()
    entities = sentilo_http_request(url, sensors, identity_key)
    output, db_columns = format_sentilo_data_etl(entities)
    db_table = db_table
    Base = declarative_base()

    # Definir el modelo de la tabla
    class SentiloData(Base):
        __tablename__ = db_table
        id = Column(Integer, primary_key=True, autoincrement=True)
        component = Column(String)
        lat = Column(Float)
        lng = Column(Float)
        observation_time = Column(TIMESTAMP)
        end_observation_time = Column(TIMESTAMP)
        tipo = Column(String)

    # Crear la tabla si no existe
    Base.metadata.create_all(db)

    metadata = MetaData(bind=db)

    # Cargar la definición de la tabla vía reflexión
    tabla = Table(db_table, metadata, autoload_with=db)

    # Obtener e imprimir los nombres de las columnas
    nombres_de_columnas = [column.name for column in tabla.columns]
    for col in db_columns: 
        if col.lower() not in nombres_de_columnas:
            column = None
            if col.endswith("_value"):
                column = Column(col, Float)
            else:
                column = Column(col, String)
            tabla.append_column(column)
            with db.connect() as alter_conn:
                alter_conn.execute(f'ALTER TABLE {tabla.name} ADD COLUMN {col} {column.type.compile(db.dialect)}')
                
    conn.execute(f'ALTER TABLE {tabla.name} ADD COLUMN IF NOT EXISTS end_observation_time timestamp')

    conn.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{db_table}_unique_constraint'
            ) THEN
                ALTER TABLE {db_table}
                ADD CONSTRAINT {db_table}_unique_constraint
                UNIQUE (component, lat, lng, observation_time);
            END IF;
        END$$;
    """)
    
    df = pd.json_normalize(output)

    df_obj = df.select_dtypes(['object'])
    df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
    # Prepare insert statement
    stmt = insert(tabla).values(df.to_dict(orient='records'))

    # Add on conflict do nothing
    stmt = stmt.on_conflict_do_nothing(index_elements=['component', 'lat', 'lng', 'observation_time'])

    # Execute
    conn.execute(stmt)
    
    update_sql = f"""
        WITH ranked AS (
        SELECT 
            id,
            observation_time::timestamp AS obs_time,
            component,
            intensity_uom,
            LEAD(observation_time::timestamp) OVER (
            PARTITION BY component, intensity_uom
            ORDER BY observation_time::timestamp
            ) AS next_obs
        FROM {db_table}
        )
        UPDATE {db_table} sp
        SET end_observation_time = COALESCE(r.next_obs, r.obs_time + INTERVAL '1 day')
        FROM ranked r
        WHERE sp.id = r.id;
        """
    
    with db.begin() as conn:
        conn.execute(update_sql)

    conn.close()
    db.dispose()
    


#etl_tasks
def format_sentilo_data_etl(entities):
    filteredEntities = filter(lambda entity: "council_data" in entity and "value" in entity["council_data"] and entity["council_data"]["value"]["municipality"] == MUNICIPALITY, entities)
    finalList = []
    list_tmp = {}
    for entity in filteredEntities:
        componentSubStringIndex =  entity['id'].find("CUA")
        componentSensor = entity['id'][componentSubStringIndex:-3]
        metadata = entity["description"]["value"]
        observation_time = entity[metadata]["metadata"]["samplingTime"]["value"]
        tipo = entity['type']
        uom = ""
        try: 
            uom = entity["_uom"]["value"]
            entity["uom"] = uom
        except Exception as e:
            print("Error getting uom")
        observation_value = 0
        try: 
            observation_value = float(entity[metadata]["value"])
        except Exception as e:
            observation_value = 0
        observation_string = str(entity[metadata]["value"])
        try:
            observation_string = observation_string + " " + uom
        except Exception as e:
            print("Error getting observation_string", e)
        try:
            lat = entity["location"]["value"].get("lat") or entity["location"]["value"].get("latitude")
            lng = entity["location"]["value"].get("lng") or entity["location"]["value"].get("longitude")
        except Exception:
            print(entity["location"]["value"])
            lat = None
            lng = None

        list_tmp = {
            "component": componentSensor,
            "observation_time": observation_time,
            "lat": lat,
            "lng": lng,
            "tipo": tipo,
            "metadata": metadata.lower(),
            metadata.lower() + "_string": observation_string,
            metadata.lower() + "_value": observation_value,
            metadata.lower() + "_uom": uom
        }
        finalList.append(list_tmp)


    grouped_data = defaultdict(lambda: {'metadata': set()})
    for item in finalList:
        key = (item['component'], item['observation_time'], item['lat'], item['lng'])

        if key not in grouped_data:
            grouped_data[key]['component'] = item['component']
            grouped_data[key]['observation_time'] = item['observation_time']
            grouped_data[key]['lat'] = item['lat']
            grouped_data[key]['lng'] = item['lng']
        grouped_data[key]['tipo'] = set()
        grouped_data[key]['metadata'] = set()
        
    for item in finalList:
        key = (item['component'], item['observation_time'], item['lat'], item['lng'])
        grouped_data[key]['tipo'].add(item['tipo'])
        grouped_data[key]['metadata'].add(item['metadata'])
        metas = filter(lambda key: key.startswith(item['metadata']), item.keys())
        for meta in metas:
            grouped_data[key][meta] = item[meta]
    

    output = []

    for key, value in grouped_data.items():
        value['tipo'] = ','.join(value['tipo'])   
        value['metadata'] = ','.join(value['metadata'])

        output.append(value)

    keys = set()
    for item in output:
        keys.update(item.keys())
    keys = list(keys)
    keys.sort()
    return output, keys

def sentilo_http_request(baseUrl, sensors, apikey):
    headers = {'Authorization': 'Bearer ' + apikey}
    entitiesRequest = requests.get(baseUrl, headers=headers)
    entities = []
    global_status_code = entitiesRequest.status_code
    if global_status_code == 200:
        entities = entitiesRequest.json()
    for sensor in sensors:
        urlEntities = baseUrl + "/" + sensor
        httpRequest = requests.get(urlEntities, headers=headers)
        status_code = httpRequest.status_code
        if status_code == 200:
            entities.append(httpRequest.json())
    return entities

def process_sentilo_request(form):
    # domain = models.CharField(max_length=200)
    # sentilo_identity_key = models.CharField(max_length=200)
    # tabla_de_datos = models.CharField(max_length=200)
    # sentilo_sensors = models.TextField()  # Assuming this can be a long list
    # intervalo_de_actualizacion = models.IntegerField()
    id = form.id
    db_table_name = form.tabla_de_datos
    urlEntities = form.domain
    identity_key = form.sentilo_identity_key
    interval = form.intervalo_de_actualizacion
    task = 'gvsigol_plugin_sentilo.tasks.fetch_sentilo_api_task'
    my_task_name = task + "." + str(id)
    if not PeriodicTask.objects.filter(name=my_task_name).exists():
        
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every = interval,
            period = IntervalSchedule.MINUTES,
        )
        PeriodicTask.objects.create(
            interval=schedule,
            name=my_task_name,
            task=task,
            args=json.dumps([urlEntities, identity_key, db_table_name, form.sentilo_sensors])
        )
    sensors_string = form.sentilo_sensors
    sensors = sensors_string.split(",")
    fetch_sentilo_api(urlEntities, identity_key, db_table_name, sensors)
    return


def delete_sentilo_request(config_id):
    task = 'gvsigol_plugin_sentilo.tasks.fetch_sentilo_api_task'
    my_task_name = task + "." + str(config_id)
    config = get_object_or_404(SentiloConfiguration, id=config_id)
    config.delete()
    # remove any pending celery task 
    tasks_to_delete = PeriodicTask.objects.filter(name=my_task_name)

    if tasks_to_delete.exists():
        tasks_to_delete.delete()
    return

def populate_sentilo_configs(configs):
    configs_to_return = []
    for config in configs:
        task = 'gvsigol_plugin_sentilo.tasks.fetch_sentilo_api_task'
        my_task_name = task + "." + str(config.id)
        task = PeriodicTask.objects.filter(name=my_task_name).first()
        if task: 
            last_run = task.last_run_at
            config.last_run = last_run
        else:
            config.last_run = "Never"
        configs_to_return.append(config)
    return configs_to_return
