# -*- coding: utf-8 -*-

import pandas as pd
import psycopg2
import cx_Oracle
#import base64
import requests
import json
import re
#from datetime import date
from django.contrib.gis.gdal import DataSource
from .models import database_connections
import os
import shutil
from zipfile import ZipFile
from gvsigol import settings
from psycopg2 import sql
from datetime import datetime
from hashlib import sha256
import base64
import pymssql
import xmltodict
from .settings import GEOETL_DB

def get_sheets_excel(excel, r):
    import warnings

    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

    if r == 'single':
    
        xl = pd.ExcelFile(excel)
        return xl.sheet_names
    else:
        sheets_array = []
        for file in os.listdir(excel):
            if file.endswith(".xls") or file.endswith(".xlsx"):
                xl = pd.ExcelFile(excel+'//'+file)
                for sh in list(xl.sheet_names):
                    if sh not in sheets_array:
                        sheets_array.append(sh)
        return sheets_array
        

def get_schema_excel(dicc):
    import warnings

    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

    if dicc['reading'] == 'single':
    
        xl = pd.read_excel(dicc["excel-file"], sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
        return list(xl.columns)
    
    else:
        column_array = []
        for file in os.listdir(dicc["excel-file"]):
            if file.endswith(".xls") or file.endswith(".xlsx"):
                xl = pd.read_excel(dicc["excel-file"]+'//'+file, sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
                for col in list(xl.columns):
                    if col not in column_array:
                        column_array.append(col)
        column_array.append('_filename')
        return column_array

def get_schema_kml(file):

    from .etl_tasks import get_temp_dir
    temp_dir = get_temp_dir()

    if file.endswith('.kmz'):
        kmz_file = file[7:]

        filename = kmz_file.split('/')[-1].split('.')[0]

        kmz_zip = '/'+os.path.join(temp_dir, filename+'.zip')

        shutil.copy(kmz_file, kmz_zip)

        with ZipFile(kmz_zip) as zf:
            zf.extractall('/'+os.path.join(temp_dir, filename))

        kml_file = '/'+os.path.join(temp_dir, filename, 'doc.kml')

    elif file.endswith('.kml'):
        kml_file = file[7:]
        
    dataSource = DataSource(kml_file)
            
    layer = dataSource[0]

    schema = ['ogc_fid']
    for x in layer.fields:
        schema.append(x.lower())

    if file.endswith('.kmz'):
        
        shutil.rmtree(temp_dir)

    return schema

def get_schema_shape(file):

    shp = file[7:]

    dataSource = DataSource(shp)
            
    layer = dataSource[0]

    schema = [x.lower() for x in layer.fields] 

    return schema

#test if connection postgres is valid
def test_oracle(dicc):
    try:
        conn = cx_Oracle.connect(
            dicc['username'],
            dicc['password'],
            dicc['dsn']
        )
        conn.close()
        return {"result": True}
    except Exception as e:
        print('Connection Oracle: ' + str(e))
        return {"result": False}

def test_postgres(dicc):
    try:
        conn = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
        cur = conn.cursor()
        
        sql = "SELECT schema_name FROM information_schema.schemata"
        cur.execute(sql)
        conn.commit()
        
        conn.close()

        return {"result": True}
    except Exception as e:
        print ('Connection postgres: ' + str(e))
        return {"result": False}
    
def test_sqlserver(dicc):
    try:
        conn = pymssql.connect(dicc['server-sql-server'], dicc['username-sql-server'], dicc['password-sql-server'], dicc['db-sql-server'], tds_version = dicc["tds-version-sql-server"])
        conn.close()
        return {"result": True}
    except Exception as e:
        print('Connection SQL Server Failed: ' + str(e))
        return {"result": False}

def get_schema_csv(dicc):
    # Determine header parameter for pandas
    skiprows = int(dicc.get("header", 0))  # Always respect skip header value
    if dicc.get('schema-option') == 'no-schema':
        header_param = None  # No schema row - pandas will use integer indices
    else:
        header_param = 0  # First row after skipped rows contains schema
    
    if dicc.get('reading') == 'multiple':
        column_array = []
        for file in os.listdir(dicc["csv-file"]):
            if file.endswith((".csv", ".txt")):
                csvdata = pd.read_csv(dicc["csv-file"]+'/'+file, sep=dicc["separator"], 
                                    header=header_param, skiprows=skiprows)
                
                # Generate automatic column names if no schema
                if dicc.get('schema-option') == 'no-schema':
                    import string
                    num_cols = len(csvdata.columns)
                    csvdata.columns = [string.ascii_uppercase[i] if i < 26 else f"Column{i+1}" for i in range(num_cols)]
                
                for col in list(csvdata.columns):
                    if col not in column_array:
                        column_array.append(col)
        column_array.append('_filename')
        return column_array
    else:
        csvdata = pd.read_csv(dicc["csv-file"], sep=dicc["separator"], 
                            header=header_param, skiprows=skiprows)
        
        # Generate automatic column names if no schema
        if dicc.get('schema-option') == 'no-schema':
            import string
            num_cols = len(csvdata.columns)
            csvdata.columns = [string.ascii_uppercase[i] if i < 26 else f"Column{i+1}" for i in range(num_cols)]
        
    return list(csvdata.columns)

def get_owners_oracle(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = cx_Oracle.connect(
        params['username'],
        params['password'],
        params['dsn']
    )

    c = conn.cursor()
    c.execute("select username as schema_name from sys.all_users order by username")

    owners = []
    for own in c:
        owners.append(own[0])

    conn.close()

    return owners

def get_tables_oracle(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = cx_Oracle.connect(
        params['username'],
        params['password'],
        params['dsn']
    )

    c = conn.cursor()
    c.execute("SELECT table_name FROM all_tables WHERE owner = '"+dicc['owner-name']+"' ORDER BY table_name ")

    tables = []
    for tbl in c:
        tables.append(tbl[0])

    conn.close()

    return tables

def get_schema_oracle(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = cx_Oracle.connect(
        params['username'],
        params['password'],
        params['dsn']
    )
    
    c = conn.cursor()

    if dicc['checkbox'] == "true":
        try:   
            create_type = "create type cols_name as table of varchar2(32767)"

            c.execute(create_type)
        except:
            print ('Existe el type cols_name')
        try:
            create_function = "CREATE OR REPLACE FUNCTION GET_COLUMNS_NAME(p_selectQuery IN VARCHAR2) RETURN cols_name PIPELINED IS "
            create_function+= "v_cursor_id integer; v_col_cnt integer; v_columns dbms_sql.desc_tab; "
            create_function+= "begin v_cursor_id := dbms_sql.open_cursor; dbms_sql.parse(v_cursor_id, p_selectQuery, dbms_sql.native); "
            create_function+= "dbms_sql.describe_columns(v_cursor_id, v_col_cnt, v_columns); "
            create_function+= "for i in 1 .. v_columns.count loop pipe row(v_columns(i).col_name); end loop; "
            create_function+= "dbms_sql.close_cursor(v_cursor_id); return; exception when others then "
            create_function+= "dbms_sql.close_cursor(v_cursor_id); raise; end;"
            
            c.execute(create_function)
        except:
            print ('Existe la función get_columns_name')
        
        raw_sql = dicc['sql']

        # Divide la SQL en SELECT ... FROM ...
        parts = re.split(r'\bFROM\b', raw_sql, maxsplit=1, flags=re.IGNORECASE)

        if len(parts) == 2:
            select_part, rest_of_query = parts
            # Eliminar variables con arrobas del SELECT, junto con comas opcionales alrededor
            select_cleaned = re.sub(r'(,\s*)?@@.*?@@(,\s*)?', lambda m: ',' if m.group(1) and m.group(2) else '', select_part)

            # Reemplazar variables en la parte restante (FROM y más allá) por 1
            rest_cleaned = re.sub(r"@@.*?@@", "1", rest_of_query)

            sanitized_sql = f"{select_cleaned.strip()} FROM {rest_cleaned.strip()}"
        else:
            # Fallback: no hay FROM → solo reemplazo genérico por 1
            sanitized_sql = re.sub(r"@@.*?@@", "1", raw_sql)

        # Escapar comillas simples
        sql_w = sanitized_sql.replace("'", "''")
            
        sql = "select * from TABLE(GET_COLUMNS_NAME('"+sql_w+"'))"
        
    else:
        sql = "SELECT column_name FROM ALL_TAB_COLUMNS WHERE table_name = '"+dicc['table-name']+"' AND owner = '"+dicc['owner-name']+"'"

    c.execute(sql)

    attrnames =[]
    for attr in c:
        attrnames.append(attr[0].lower())

    """if dicc['check'] == True:
        try:
            drop_type = "DROP TYPE cols_name FORCE"
            c.execute(drop_type)
        except:
            print("No se ha borrado el type cols_name")

        try:
            drop_func = "DROP FUNCTION GET_COLUMNS_NAME"
            c.execute(drop_func)
        except:
            print("No se ha borrado la función get_columns_name")"""

    conn.close()

    return attrnames

def get_proced_indenova(dicc):

    api  = database_connections.objects.get(name = dicc['api'])

    params_str = api.connection_params
    params = json.loads(params_str)

    domain = params['domain']
    api_key = params['api-key']

    url_list = domain + "//api/rest/process/v1/process/list?idsection=27"

    headers_list = {'esigna-auth-api-key': api_key}

    r_list = requests.get(url_list, headers = headers_list)
    
    listProd = []
    for i in json.loads(r_list.content.decode('utf8')):
        listProd.append([i['id'], i['name']])
    
    return listProd

def get_schema_postgres(dicc):
    
    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)
   
    table_name = dicc['tablename']
    
    #postgres connection
    conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
    cur = conn.cursor()

    sql_ = sql.SQL("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = %s AND table_name   = %s;")

    cur.execute(sql_,[dicc['schema-name'], table_name])
    listSchema = []

    if "query" in dicc:
        attr_query = re.search('SELECT(.*)FROM', dicc['query'])
        attr_query = attr_query.group(1).replace(' ', '')
        list_attr_query = attr_query.split(',')
        for attr in list_attr_query:
            if attr == '*':
                
                for col in cur:
                    if col[1] == 'USER-DEFINED' or col[1] == 'geometry':
                        pass
                    else:
                        listSchema.append(col[0])

            elif attr[0] =='"' and attr[-1] == '"':
                listSchema.append(attr[1:-1])

            elif attr[0] =='"' and '"AS' in attr:

                at = attr.split('"AS')[-1]

                if at[0] =='"' and at[-1] == '"':
                    listSchema.append(at[1:-1])
                else:
                    listSchema.append(at)

            elif ')AS' in attr:

                at = attr.split(')AS')[-1]

                if at[0] =='"' and at[-1] == '"':
                    listSchema.append(at[1:-1])
                else:
                    listSchema.append(at)

            else:
                listSchema.append(attr)

    else:
        for col in cur:
            if col[1] == 'USER-DEFINED' or col[1] == 'geometry':
                pass
            else:
                listSchema.append(col[0])

    conn.commit()
    conn.close()
    cur.close()

    return listSchema


def get_schema_name_postgres(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)

    conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
    cur = conn.cursor()
    
    sql = "SELECT schema_name FROM information_schema.schemata"
    cur.execute(sql)
    conn.commit()
    listSchema = []
    for row in cur:
        listSchema.append(row[0])
    
    conn.close()

    return listSchema

def get_table_name_postgres(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)

    conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
    cur = conn.cursor()
    
    sql_ = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
    cur.execute(sql_, [dicc['schema-name']])
    conn.commit()
    listSchema = []
    for row in cur:
        listSchema.append(row[0])
    
    conn.close()

    return listSchema

def getwsSegPass(psw):

    utc = datetime.utcnow()
    
    utcText = utc.strftime('%Y%m%d%H%M%S')

    hashInputString = utcText+psw

    hashInputBytes = hashInputString.encode('utf-8')

    hashBytes = sha256(hashInputBytes).digest()

    hashBase64 = base64.b64encode(hashBytes)

    wsSegPass = utcText+hashBase64.decode()

    return wsSegPass

def get_entities_segex(dicc):

    if dicc['domain'] == 'PRE':
        url = 'https://pre-02000.sedipualba.es/apisegex/'
    else:
        url = 'https://02000.sedipualba.es/apisegex/'

    listEntidades = 'Georef/ListEntidades'

    r = requests.get(url+listEntidades)

    print('listEntidades: ' + str(r.status_code))

    if r.status_code == 200:

        listEntities = []

        for i in r.json():
            listEntities.append([i['Id'], i['Descripcion']])
        
        return listEntities
    else:
        return []

def get_types_segex (dicc):

    api  = database_connections.objects.get(name = dicc['api'])

    params_str = api.connection_params
    params = json.loads(params_str)

    entity = params['entities-list'][0]

    if params['domain'] == 'PRE':
        url = 'https://pre-%s.sedipualba.es/apisegex/' % (entity)
    else:
        url = 'https://%s.sedipualba.es/apisegex/' % (entity)

    wsSegUser = params['user']

    wsSegPass = getwsSegPass(params['password'])

    listTipos = 'Georef/ListTiposGeoref?wsSegUser=%s&wsSegPass=%s&idEntidad=%s' % (wsSegUser, wsSegPass, entity)

    r = requests.get(url+listTipos)

    print('listTipos: '+str(r.status_code))

    if r.status_code == 200:

        listTypes = []

        for i in r.json():
            listTypes.append([i['Id'], i['Descripcion']])
        
        return listTypes
    else:
        return []


def get_schema_json(dicc):
    
    if dicc['api-rest'] == 'true':
        """if dicc['is-pag'] == 'true':
            start = dicc['init-pag']
            jsondata = pd.read_json(dicc['url']+'&'+dicc['pag-par']+'='+str(start))
        else:"""
        jsondata = pd.read_json(dicc['url'])
    else:
        jsondata = pd.read_json(dicc['json-file'])
    
    return list(jsondata.columns)


def get_schema_padron_alba(dicc):
    
    if dicc['service'] == 'PRE':
        url = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pre_estadisticas_padron&u=fPqq2xHVQkix&pag=1"
    elif dicc['service'] == 'PRO':
        url = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pro_estadisticas_padron&u=fPqq2xHVQkix&pag=1"

    jsondata = pd.read_json(url)
    
    return list(jsondata.columns)


def perf_func(dicc, level=0):
    if dicc:
        if isinstance(dicc, dict):
            for key in dicc.keys():
                tagList.append([level, key])
                perf_func(dicc[key], level+1)
        elif isinstance(dicc, list):
            for i in dicc:
                for key in i.keys():
                    tagList.append([level, key])
                    perf_func(i[key], level+1)

def get_xml_tags(f, r):

    tagList_cleaned = []
    
    if r == 'single':
        listXmlFile = [f.split('//')[1]]

    else:
        listXmlFile = []
        for file in os.listdir(f):
            if file.endswith(".xml"):
                listXmlFile.append(f +'//'+ file)

    
    for xmlFile in listXmlFile:

        xmlStr = open(xmlFile).read()

        xmlDict = xmltodict.parse(xmlStr)

        global tagList

        tagList = []

        perf_func(xmlDict, 0)

        count = 0
        for i in tagList:
            level = i[0]
            for j in tagList[count:]:
                if i == j:
                    pass
                elif j[0] == level+1:
                    j.append(i[1])
                elif j[0] == level:
                    break
            count+=1

        for k in tagList:
            if len(k) == 3:
                item = [str(k[0])+'-'+k[2], k[1]]
            else:
                item = [str(k[0]), k[1]]

            if item not in tagList_cleaned:

                pos = 0
                addItem = True

                for l in reversed(tagList_cleaned):
                    pos += -1
                    if item[0] == '0':
                        break
                    elif l[0] == item[0]:
                        tagList_cleaned.insert(pos, item)
                        addItem = False
                        break
                    elif item[0].split('-')[1] == l[1]:
                        tagList_cleaned.insert(pos, item)
                        addItem = False
                        break
                    
                if addItem:

                    tagList_cleaned.append(item)

    return tagList_cleaned[::-1]


def get_schemas_sqlserver(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = pymssql.connect(params['server-sql-server'], params['username-sql-server'], params['password-sql-server'], params['db-sql-server'], tds_version = params["tds-version-sql-server"])
    
    cursor = conn.cursor(as_dict=True)
    
    cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA  WHERE CATALOG_NAME  = '%s'" % (params['db-sql-server']) )

    schemas = []
    for row in cursor:
        schemas.append(row['SCHEMA_NAME'])

    conn.close()

    return schemas


def get_tables_sqlserver(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = pymssql.connect(params['server-sql-server'], params['username-sql-server'], params['password-sql-server'], params['db-sql-server'], params['db-sql-server'], tds_version = '7.0')
    cursor = conn.cursor(as_dict=True)
    
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_CATALOG = '%s' AND TABLE_SCHEMA  = '%s' ORDER BY TABLE_NAME" % (params['db-sql-server'], dicc['schema-name']) )

    tables = []
    for row in cursor:
        tables.append(row['TABLE_NAME'])

    conn.close()

    return tables

def get_data_schemas_sqlserver(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = pymssql.connect(params['server-sql-server'], params['username-sql-server'], params['password-sql-server'], params['db-sql-server'], tds_version = params["tds-version-sql-server"])    
    
    cursor = conn.cursor(as_dict=True)

    if dicc['checkbox'] == 'true':
        _sql = "SELECT name AS COLUMN_NAME, system_type_name AS DATA_TYPE FROM sys.dm_exec_describe_first_result_set ('%s', NULL, 0) ;" % (dicc['sql'].replace("'", "''"))

    else:
        _sql = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '%s' AND TABLE_NAME  = '%s'" % (dicc['schema-name'], dicc['table-name']) 
    
    cursor.execute(_sql)

    columns = []
    for row in cursor:
        if row['DATA_TYPE'] != 'geometry' and row['DATA_TYPE'] != 'geography':
            columns.append(row['COLUMN_NAME'])

    conn.close()

    return columns


def get_schema_padron_atm(dicc):
    
    try:
        api = database_connections.objects.get(name=dicc['api'])
        credenciales = json.loads(api.connection_params)
    except Exception as e:
        print(f"Error al obtener credenciales de la API: {e}")
        return None
    
    url_auth = "https://pmcloudserver.atm-maggioli.es/api/auth/login" 
    first = True

    # Autenticación
    try:
        response = requests.post(url_auth, json=credenciales)
        response.raise_for_status()  # Lanza una excepción si el código no es 200
        data = response.json()
        token = data.get("accesstoken", {}).get("token")

        if not token:
            print("Error: No se obtuvo el token de autenticación.")
            return None
    except requests.RequestException as e:
        print(f"Error en la solicitud de autenticación: {e}")
        return None

    
    start = 0
    length = 20
        
    while length == 20:
        params = {
            "id": 1,
            "start": start,
            "length": 20,
            "sort": None,
            "order": None,
            "gettotal": True,
            "filtro": None,
            "columns": [
                {
                "name": None,
                "data": None
                }
            ]
            }
    
        headers = {"Authorization": f"Bearer {token}"}
        url_list = f"https://pmcloudserver.atm-maggioli.es/padron/api/habitante/GetList/"
        
        
        try:
            response_list = requests.post(url_list, headers=headers, json=params)
            response_list.raise_for_status()  
            habitantes = response_list.json()

            if "data" not in habitantes:
                print("Advertencia: No se encontró 'data' en la respuesta.")
                break

        except requests.RequestException as e:
            print(f"Error al obtener la lista de habitantes: {e}")
            break 
        
        for hab in habitantes['data']:
            
            if hab["bfechabaja"] == False:
                
                if hab['tipodocu'] == '1':
                    documento = hab.get('dni', '') + hab.get('nif', '')
                    
                elif hab['tipodocu'] == '2':
                    documento = hab.get('pasaporte', '')
                    
                elif hab['tipodocu'] == '3':
                    documento = hab.get('lextr', '') + hab.get('dni', '') + hab.get('nif', '')
                else:
                    documento = None

                # Consulta de datos del habitante
                try:
                    
                    if documento:
                        url_modelos = f"https://pmcloudserver.atm-maggioli.es/padron/api/habitante/GetPorDocumento/{documento}"
                        response_modelos = requests.get(url_modelos, headers=headers)
                        response_modelos.raise_for_status()

                        data = response_modelos.json()

                        habitante = data.get('habitante', {})
                        lastmovimiento = data.get('lastmovimiento', {})
                        vivienda = data.get('vivienda', {})
                        domicilio = data.get('domicilio', {})
                        
                        habitante.pop("tabla", None)
                        lastmovimiento.pop("tabla", None)
                        vivienda.pop("tabla", None)
                        domicilio.pop("tabla", None)

                        habitante_keys = list(habitante.keys()) 
                        lastmovimiento_keys = list(lastmovimiento.keys()) 
                        vivienda_keys = list(vivienda.keys()) 
                        domicilio_keys = list(domicilio.keys())
                        
                        all_keys = list(habitante.keys()) + list(lastmovimiento.keys()) + list(vivienda.keys()) + list(domicilio.keys())
                        duplicated_keys = {k for k in all_keys if all_keys.count(k) > 1 and not k.startswith("id")}

                        def agregar_sufijo_lista(keys, sufijo):
                            return [f"{k}{sufijo}" if k in duplicated_keys else k for k in keys]
                        
                        columns = habitante_keys + agregar_sufijo_lista(lastmovimiento_keys, "_lastmovimiento") + agregar_sufijo_lista(vivienda_keys, "_vivienda") + agregar_sufijo_lista(domicilio_keys, "_domicilio")
                        
                        return columns
                    
                except requests.RequestException as e:
                    print(f"Error al obtener datos del habitante: {e}")
        
        length = len(habitantes['data'])
        start += 20

