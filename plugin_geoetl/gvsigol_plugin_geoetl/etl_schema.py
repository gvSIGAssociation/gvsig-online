# -*- coding: utf-8 -*-

import pandas as pd
import tempfile
import shutil
from osgeo import ogr, osr
import psycopg2

def get_sheets_excel(excel):
    xl = pd.ExcelFile(excel)
    return xl.sheet_names

def get_schema_excel(excel, dicc):
    xl = pd.read_excel(excel, sheet_name=dicc["sheet-name"], header=dicc["header"], usecols=dicc["usecols"])

    return list(xl.columns)

def get_schema_shape(listF):
    for i in listF:

        ext = i.name[-4:]
        shpName = i.name[:-4]

        if ext =='.dbf':
            dbfTemp = tempfile.NamedTemporaryFile(delete=False)
            dbfTemp.write(i.read())
            dbfTemp.close()
            shutil.copy(dbfTemp.name, '/tmp/'+shpName+'.dbf')
        
        elif ext == '.prj':
            prjTemp = tempfile.NamedTemporaryFile(delete=False)
            prjTemp.write(i.read())
            prjTemp.close()
            shutil.copy(prjTemp.name, '/tmp/'+shpName+'.prj')
        
        elif ext == '.shp':
            shpTemp = tempfile.NamedTemporaryFile(delete=False)
            shpTemp.write(i.read())
            shpTemp.close()
            shutil.copy(shpTemp.name, '/tmp/'+shpName+'.shp')
        
        elif ext == '.shx':
            shxTemp = tempfile.NamedTemporaryFile(delete=False)
            shxTemp.write(i.read())
            shxTemp.close()
            shutil.copy(shxTemp.name, '/tmp/'+shpName+'.shx')
  
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open('/tmp/'+shpName+'.shp', 0)
            
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

