# -*- coding: utf-8 -*-

import pandas as pd
import tempfile
import shutil
from osgeo import ogr, osr
import psycopg2
import cx_Oracle
import base64
import requests
import json

def get_sheets_excel(excel):
    
    xl = pd.ExcelFile(excel)
    return xl.sheet_names

def get_schema_excel(dicc):
    
    xl = pd.read_excel(dicc["excel-file"], sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
    return list(xl.columns)

def get_schema_shape(file):

    shp = file[7:]

    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(shp, 0)
            
    layer = dataSource.GetLayer()
    schema = []
    ldefn = layer.GetLayerDefn()
    for n in range(ldefn.GetFieldCount()):
        fdefn = ldefn.GetFieldDefn(n)
        schema.append(fdefn.name)

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
        conn.close()
        return {"result": True}
    except:
        return {"result": False}

def get_schema_csv(dicc):
    csvdata = pd.read_csv(dicc["csv-file"], sep=dicc["separator"])
    return list(csvdata.columns)

def get_owners_oracle(dicc):

    conn = cx_Oracle.connect(
        dicc['username'],
        dicc['password'],
        dicc['dsn']
    )

    c = conn.cursor()
    c.execute("select username as schema_name from sys.dba_users order by username")

    owners = []
    for own in c:
        owners.append(own[0])

    conn.close()

    return owners

def get_tables_oracle(dicc):

    conn = cx_Oracle.connect(
        dicc['username'],
        dicc['password'],
        dicc['dsn']
    )

    c = conn.cursor()
    c.execute("SELECT table_name FROM all_tables WHERE owner = '"+dicc['owner-name']+"' ORDER BY table_name ")

    tables = []
    for tbl in c:
        tables.append(tbl[0])

    conn.close()

    return tables

def get_schema_oracle(dicc):

    conn = cx_Oracle.connect(
        dicc['username'],
        dicc['password'],
        dicc['dsn']
    )
    c = conn.cursor()

    if dicc['check'] == True:
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

        sql = "select * from TABLE(GET_COLUMNS_NAME('"+dicc['sql']+"'))"

    else:
        sql = "SELECT column_name FROM ALL_TAB_COLUMNS WHERE table_name = '"+dicc['table-name']+"' AND owner = '"+dicc['owner-name']+"'"


    c.execute(sql)

    attrnames =[]
    for attr in c:
        attrnames.append(attr[0])

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

def get_schema_indenova(dicc):
    
    domain = dicc['domain']
    api_key = dicc['api-key']
    client_id = dicc['client-id']
    secret = dicc['secret']
