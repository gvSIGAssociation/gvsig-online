# -*- coding: utf-8 -*-

import pandas as pd
import tempfile
import shutil
from osgeo import ogr, osr
import psycopg2
import cx_Oracle

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
    c.execute("SELECT column_name FROM ALL_TAB_COLUMNS WHERE table_name = '"+dicc['table-name']+"' AND owner = '"+dicc['owner-name']+"'")

    attrnames =[]
    for attr in c:
        attrnames.append(attr[0])

    conn.close()

    return attrnames