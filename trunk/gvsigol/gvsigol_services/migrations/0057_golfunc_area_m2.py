# -*- coding: utf-8 -*-

from django.db import migrations
from gvsigol_services.triggers import drop_procedure
import json, psycopg2

TRIGGER_FUNCTION_SCHEMA = "public"
TRIGGER_FUNCTION_NAME = "gol_area_m2"
TRIGGER_FUNCTION_SIGNATURE = "public.gol_area_m2(text)"

TRIGGER_FUNCTION_DEF = """CREATE OR REPLACE FUNCTION public.gol_area_m2() RETURNS trigger AS $$
        try:
            column_name = TD["args"][0]
            plan = plpy.prepare("SELECT * FROM geometry_columns WHERE f_table_name = $1 AND f_table_schema = $2", ["text","text"])        
            rv = plpy.execute(plan,[TD["table_name"],TD["table_schema"]],1)
            geom_column = rv[0]["f_geometry_column"]
            
            plan = plpy.prepare("SELECT ST_Area($1) as aream2", ["text"])
            rv = plpy.execute(plan,[TD["new"][geom_column]],1)
            TD["new"][column_name] = rv[0]["aream2"]
        except plpy.SPIError as e:
            TD["new"][column_name] = ''
            plpy.log("ERROR gol_area_m2: " + str(e))
        except Exception as e:
            TD["new"][column_name] = ''
            plpy.log(str(e))
        finally:
            return "MODIFY"
    $$ LANGUAGE plpython3u;
    """
def get_db_connection(datastore):
    """
    Obtiene una conexión de introspección a la base de datos.
    Soporta tanto el modo legacy como el nuevo modelo de conexiones.
    """
    params = json.loads(datastore.connection_params) if datastore.connection_params else {}
    
    
    host = params.get('host', 'localhost')
    port = params.get('port', '5432')
    dbname = params.get('database', '')
    user = params.get('user', '')
    passwd = params.get('passwd', params.get('password', ''))
    
    conn = psycopg2.connect(database=dbname, user=user, password=passwd, host=host, port=port, connect_timeout=5)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def install_procedure(apps, definition):
    """
    Installs the procedure on the database referenced by the cursor.
    If cursor is not provided, the procedure is installed in the database
    of all the available datastores
    """
    Datastore = apps.get_model("gvsigol_services", "Datastore")
    for store in Datastore.objects.filter(type='v_PostGIS'):
        conn = get_db_connection(store)
        cursor = conn.cursor()
        cursor.execute(definition)
        conn.close()


def insert_def(apps, schema_editor):
    try:
        from django.utils.translation import gettext_noop as _
        TriggerProcedure = apps.get_model("gvsigol_services", "TriggerProcedure")
        procedure = TriggerProcedure()
        procedure.signature = TRIGGER_FUNCTION_SIGNATURE
        procedure.func_name = TRIGGER_FUNCTION_NAME
        procedure.func_schema = TRIGGER_FUNCTION_SCHEMA
        procedure.label = _('Area (m2)')
        procedure.definition_tpl = TRIGGER_FUNCTION_DEF
        procedure.activation = 'BEFORE'
        procedure.event = 'INSERT OR UPDATE'
        procedure.orientation = 'ROW'
        procedure.save()
        
        install_procedure(apps, procedure.definition_tpl)

    except Exception as error:
        print(error)

def remove_def(apps, schema_editor):
    try:
        drop_procedure(TRIGGER_FUNCTION_SIGNATURE)
        TriggerProcedure = apps.get_model("gvsigol_services", "TriggerProcedure")
        TriggerProcedure.objects.filter(signature=TRIGGER_FUNCTION_SIGNATURE).delete()
    except Exception as error:
        print(error)
        
class Migration(migrations.Migration):
    dependencies = [
        ('gvsigol_services', '0056_layerreadwriteroles'),
    ]

    operations = [
        migrations.RunPython(insert_def, reverse_code=remove_def),
    ]
