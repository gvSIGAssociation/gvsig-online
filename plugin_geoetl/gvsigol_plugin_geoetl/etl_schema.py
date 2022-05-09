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

    if file.endswith('.kmz'):
        kmz_file = file[7:]
        path_list = kmz_file.split('/')[:-1]
        filename = kmz_file.split('/')[-1].split('.')[0]

        kmz_zip = '//'+os.path.join(*path_list, filename+'.zip')

        shutil.copy(kmz_file, kmz_zip)

        with ZipFile(kmz_zip) as zf:
            zf.extractall('//'+os.path.join(*path_list, filename))

        kml_file = '//'+os.path.join(*path_list, filename, 'doc.kml')

    elif file.endswith('.kml'):
        kml_file = file[7:]
        
    dataSource = DataSource(kml_file)
            
    layer = dataSource[0]

    schema = [x.lower() for x in layer.fields]

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
    except:
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

def get_schema_csv(dicc):
    csvdata = pd.read_csv(dicc["csv-file"], sep=dicc["separator"])
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
        
        sql_w = dicc['sql'].replace("'", "''")
        
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

    domain = dicc['domain']

    api_key = dicc['api-key']

    url_list = domain + "//api/rest/process/v1/process/list?idsection=27"

    headers_list = {'esigna-auth-api-key': api_key}

    r_list = requests.get(url_list, headers = headers_list)
    
    listProd = []
    for i in json.loads(r_list.content.decode('utf8')):
        listProd.append([i['id'], i['name']])
    
    return listProd

"""def get_schema_indenova(dicc):
    
    domain = dicc['domain']
    api_key = dicc['api-key']
    client_id = dicc['client-id']
    secret = dicc['secret']
    auth = (client_id+':'+secret).encode()

    if dicc['checkbox-init'] is True:
        today = date.today()
        init_date = today.strftime("%d/%m/%Y")
    else:
        in_d_list = dicc['init-date'].split('-')
        init_date = in_d_list[2]+'/'+in_d_list[1]+'/'+in_d_list[0]
    
    if dicc['checkbox-end'] is True:
        today = date.today()
        end_date = today.strftime("%d/%m/%Y")
    else:
        end_d_list = dicc['end-date'].split('-')
        end_date = end_d_list[2]+'/'+end_d_list[1]+'/'+end_d_list[0]

    proced_list = dicc['proced-list']

    url_auth = domain + "//api/rest/security/v1/authentication/authenticate"
    headers_auth = {'esigna-auth-api-key': api_key, 'Authorization': "Basic ".encode()+ base64.b64encode(auth) }
    r_auth = requests.get(url_auth, headers = headers_auth)
    token = r_auth.content

    listSchema = []

    for i in proced_list:
        if i != 'all':
            if dicc['check'] is True:

                url_date = domain + '/api/rest/bpm/v1/search/'+i+'/getExpsByTramAndDates?dateIni='+init_date+'&dateEnd='+end_date
            else:
                url_date = domain + "/api/rest/bpm/v1/search/"+i+"/getOpenExpsByTramAndDateIni?dateIni="+init_date

            headers_token = {'esigna-auth-api-key': api_key, "Authorization": "Bearer "+token.decode()}
            r_date = requests.get(url_date, headers = headers_token)
            
            if r_date.status_code == 200:
                for j in json.loads(r_date.content.decode('utf8')):
                    
                    numExp = j['numExp']
            
                    url_cad = domain + '//api/rest/bpm/v1/search/getDataFileByNumber?numExp='+numExp+'&listMetadata=adirefcatt'
                    r_cad = requests.get(url_cad, headers = headers_token)
                    
                    expedient = json.loads(r_cad.content.decode('utf-8'))

                    for key in expedient.keys():
                        if isinstance(expedient[key], list):
                            if key != 'metadata':
                                for k in expedient[key]:
                                    for ke in k.keys():
                                        if ke not in listSchema:
                                            listSchema.append(ke)
                            else:
                                for k in expedient[key]:
                                    if k['varName'] not in listSchema:
                                        listSchema.append(k['varName'])
                        else:
                            if key not in listSchema:
                                listSchema.append(key)
    
    return [x.lower() for x in listSchema]"""

def get_schema_postgres(dicc):
    
    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)
   
    table_name = dicc['tablename']
    
    #postgres connection
    conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
    cur = conn.cursor()

    sql ="SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = '"+dicc['schema-name']+"' AND table_name   = '"+table_name+"';"

    cur.execute(sql)
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
    
    sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = '"+ dicc['schema-name']+"'"
    cur.execute(sql)
    conn.commit()
    listSchema = []
    for row in cur:
        listSchema.append(row[0])
    
    conn.close()

    return listSchema