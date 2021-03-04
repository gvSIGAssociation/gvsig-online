# -*- coding: utf-8 -*-

import pandas as pd
import tempfile
import shutil
from osgeo import ogr, osr
import psycopg2

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
