# -*- coding: utf-8 -*-

from itertools import count
from . import settings

import pandas as pd
import psycopg2
import json
import math
import numpy as np
from collections import defaultdict
from osgeo import ogr, osr
import copy
from dateutil.parser import parse
import mgrs
import gdaltools
import tempfile
import cx_Oracle
from geomet import wkt
from . import etl_schema
import requests
import base64
from datetime import date, datetime
from sqlalchemy import create_engine


# Python class to print topological sorting of a DAG 
class Graph: 
	def __init__(self, vertices): 
        # dictionary containing adjacency List 
		self.graph = defaultdict(list) 
        # No. of vertices 
		self.V = vertices 

	# function to add an edge to graph 
	def addEdge(self, u, v): 
		self.graph[u].append(v) 

	# A recursive function used by topologicalSort 
	def topologicalSortUtil(self, v, visited, stack): 

		# Mark the current node as visited. 
		visited[v] = True

		# Recur for all the vertices adjacent to this vertex 
		for i in self.graph[v]: 
			if visited[i] == False: 
				self.topologicalSortUtil(i, visited, stack) 

		# Push current vertex to stack which stores result 
		stack.append(v) 

	# The function to do Topological Sort.
	def topologicalSort(self): 
		# Mark all the vertices as not visited 
		visited = [False]*self.V 
		stack = [] 

		# Call the recursive helper function to store Topological 
		# Sort starting from all vertices one by one 
		for i in range(self.V): 
			if visited[i] == False: 
				self.topologicalSortUtil(i, visited, stack) 

		# Print contents of the stack 
        # return list in reverse order
		return stack[::-1] 

#functions associated to tasks. 
#All of them receive a dictionary with the parameters for the task
#and the data -if task is not an input task-
#the output for each function must be a list of json. 
# list will be as longer as outputs has the task. e.g filter has two outputs True ans False
#so output list will be [jsonTrue, jsonFalse]

def input_Excel(dicc):

    df = pd.read_excel(dicc["excel-file"], sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
    table_name = dicc['id']

    conn_string = 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
  
    db = create_engine(conn_string)
    conn = db.connect()

    df.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
    
    return [table_name]

def input_Shp(dicc):

    table_name = dicc['id'].replace('-','_')

    shp = dicc['shp-file'][7:]
  
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(shp, 0)
            
    layer = dataSource.GetLayer()

    epsg = str(dicc['epsg'])
    
    if epsg == '':
        try:
            epsg = layer.GetSpatialRef().GetAuthorityCode(None)
        except:
            pass
    
    srs = "EPSG:"+str(epsg)
    schema = settings.GEOETL_DB['schema']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name+'"'
    cur.execute(sqlDrop)
    conn.commit()
    
    _ogr = gdaltools.ogr2ogr()
    _ogr.set_encoding('UTF-8')
    _ogr.set_input(shp, srs=srs)
    conn = gdaltools.PgConnectionString(host=settings.GEOETL_DB["host"], port=settings.GEOETL_DB["port"], dbname=settings.GEOETL_DB["database"], schema=schema, user=settings.GEOETL_DB["user"], password=settings.GEOETL_DB["password"])
    _ogr.set_output(conn, table_name=table_name)
    _ogr.set_output_mode(layer_mode=_ogr.MODE_DS_CREATE, data_source_mode=_ogr.MODE_DS_UPDATE)

    _ogr.layer_creation_options = {
        "LAUNDER": "YES",
        "precision": "NO"
    }
    _ogr.config_options = {
        "OGR_TRUNCATE": "NO"
    }
    _ogr.set_dim("2")
    _ogr.execute()

    return [table_name]
    

def trans_RemoveAttr(dicc):

    attrList = dicc['attr']
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlRemov = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'

    for attr in attrList:
        sqlRemov += ' DROP COLUMN "'+ attr + '",'

    cur.execute(sqlRemov[:-1])
    conn.commit()
    conn.close()
    cur.close()

    return [table_name_target]
    

def trans_KeepAttr(dicc):

    attrList = dicc['attr']
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDatetype = 'SELECT column_name from information_schema.columns '
    sqlDatetype += "where table_schema = '"+ settings.GEOETL_DB["schema"]+"' and table_name ='"+table_name_source+"' "
    cur.execute(sqlDatetype)
    conn.commit()
    for row in cur:
        if row[0] == 'wkb_geometry':
            attrList.append('wkb_geometry')
            break

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select '

    for attr in attrList:
        sqlDup += ' "'+ attr + '",'

    sqlDup = sqlDup[:-1]+' from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'

    cur.execute(sqlDup)
    conn.commit()
    conn.close()
    cur.close()

    return [table_name_target]

def trans_RenameAttr(dicc):

    oldAttr = dicc['old-attr']
    newAttr = dicc['new-attr'].split(" ")
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlRename_ = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'

    for x in range (0, len(oldAttr)):
        sqlRename = sqlRename_ + ' RENAME COLUMN "'+ oldAttr[x] + '" TO "'+newAttr[x]+'";'

        cur.execute(sqlRename)
        conn.commit()
    
    conn.close()
    cur.close()

    return [table_name_target]

def trans_Join(dicc):

    attr1 = dicc['attr1']
    attr2 = dicc['attr2']

    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]

    table_name_target_join = dicc['id']+'_0'
    table_name_target_0_not_used = dicc['id']+'_1'
    table_name_target_1_not_used = dicc['id']+'_2'

    output = [table_name_target_join, table_name_target_0_not_used, table_name_target_1_not_used]

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    schemas =[]

    for table_name in dicc['data']:
        sqlDatetype = 'SELECT column_name from information_schema.columns '
        sqlDatetype += "where table_schema = '"+ settings.GEOETL_DB["schema"]+"' and table_name ='"+table_name+"' "
        cur.execute(sqlDatetype)
        conn.commit()
        sc =[]
        for row in cur:
            sc.append(row[0])
        schemas.append(sc)

    for name in schemas[0]:
        if name in schemas[1]:
            schemas[1].remove(name)

    schema_0 = 'A0."' + '", A0."'.join(schemas[0]) + '"'
    schema_1 = 'A1."' + '", A1."'.join(schemas[1]) + '"'
    schema = schema_0 +' , ' + schema_1

    for out in output:

        sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+out+'"'
        cur.execute(sqlDrop)
        conn.commit()

    sqlJoin = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_join+'" as (select '+ schema+' from '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" AS A0'
    sqlJoin += ' INNER JOIN '+settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" AS A1 ON A0."'+attr1+'" = A1."'+attr2+'" );'
    cur.execute(sqlJoin)
    conn.commit()

    sqlNotJoin1 = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_0_not_used+'" as (select A0.* from '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" AS A0'
    sqlNotJoin1 += ' LEFT OUTER JOIN '+settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" AS A1 ON A0."'+attr1+'" = A1."'+attr2+'" WHERE '+schema_1.split(",")[0] +' IS NULL );'
    cur.execute(sqlNotJoin1)
    conn.commit()

    sqlNotJoin2 = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_1_not_used+'" as (select A1.* from '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" AS A0'
    sqlNotJoin2 += ' RIGHT OUTER JOIN '+settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" AS A1 ON A0."'+attr1+'" = A1."'+attr2+'" WHERE '+schema_0.split(",")[0] +' IS NULL );'
    cur.execute(sqlNotJoin2)
    conn.commit()

    return output

def trans_ModifyValue(dicc):
    
    attr = dicc['attr']
    
    value = dicc['value']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlDatetype = 'SELECT  data_type from information_schema.columns '
    sqlDatetype += "where table_schema = '"+ settings.GEOETL_DB["schema"]+"' and table_name ='"+table_name_target+"' and column_name = '" + attr + "'"

    cur.execute(sqlDatetype)
    conn.commit()

    for row in cur:
        data_type = row[0]

    sqlUpdate = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' SET "'+attr+'" = '
    
    if 'char' in data_type or data_type == 'text':
        sqlUpdate += "'"+value+"'"
    else:
        sqlUpdate += value

    cur.execute(sqlUpdate)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_CreateAttr(dicc):

    attr = dicc['attr']
    value = dicc['value']
    data_type = dicc['data-type']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' ADD COLUMN "'+attr+'" '+data_type

    cur.execute(sqlAdd)
    conn.commit()

    if value != '':
        
        sqlUpdate = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' SET "'+attr+'" = '
        
        if data_type == 'VARCHAR':
            sqlUpdate += "'"+value+"'"
        else:
            sqlUpdate += value

        cur.execute(sqlUpdate)
        conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_Filter(dicc):

    attr = '"'+dicc['attr']+'"'
    
    value=dicc['value']
    
    operator = dicc['operator']

    table_name_source = dicc['data'][0]
    table_name_target_passed = dicc['id']+'_0'
    table_name_target_failed = dicc['id']+'_1'

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop_ = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target_passed+'"'
    cur.execute(sqlDrop_)
    conn.commit()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target_failed+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDatetype = 'SELECT  data_type from information_schema.columns '
    sqlDatetype += "where table_schema = '"+ settings.GEOETL_DB["schema"]+"' and table_name ='"+table_name_source+"' and column_name = '" + attr[1:-1] + "'"
    cur.execute(sqlDatetype)
    conn.commit()

    for row in cur:
        data_type = row[0]

    if operator == 'starts-with':
        operator = 'LIKE'
        value = value + '%'
    elif operator == 'ends-with':
        operator = 'LIKE'
        value = '%' + value
    elif operator == 'contains':
        operator = 'LIKE'
        value = '%' + value + '%'

    if 'char' in data_type or data_type == 'text':
        value = "'"+value+"'"
    elif operator == 'LIKE':
        attr = attr + "::varchar"
        value = "'"+value+"'"
    else:
        value = str(value)

    sqlFilPassed = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_passed+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"'
    sqlFilPassed += ' WHERE '+attr+' '+ operator + ' ' + value+ ');'
    cur.execute(sqlFilPassed)
    conn.commit()

    sqlFilFailed = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_failed+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"'
    sqlFilFailed += ' WHERE NOT '+attr+' '+ operator + ' ' + value+ ');'
    cur.execute(sqlFilFailed)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target_passed, table_name_target_failed]

def executePostgres(dicc, sql):
    conn = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    conn.close()
    cur.close()


def output_Postgresql(dicc, geom_column_name = ''):

    conn_string_source = 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
    db_source = create_engine(conn_string_source)
    conn_source = db_source.connect()
    
    table_name_source = dicc['data'][0]

    if geom_column_name == '':
    
        df = pd.read_sql("SELECT * FROM "+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"', con = conn_source)
    else:
        df = pd.read_sql("SELECT *, ST_ASTEXT ("+geom_column_name+") AS _st_astext_temp FROM " + settings.GEOETL_DB["schema"]+'."'+table_name_source+'"', con = conn_source)


    schemaTable = dicc['tablename'].lower()

    if '.' in schemaTable:
        esq = schemaTable.split(".")[0]
        table_name = schemaTable.split(".")[1]
    else:
        esq = 'public'
        table_name = schemaTable

    conn_string_target= 'postgresql://'+dicc['user']+':'+dicc['password']+'@'+dicc['host']+':'+dicc['port']+'/'+dicc['database']
    db_target = create_engine(conn_string_target)
    conn_target = db_target.connect()

    if dicc['operation'] == 'CREATE':
        df.to_sql(table_name, con=conn_target, schema= esq, if_exists='fail', index=False)
    elif dicc['operation'] == 'APPEND':
        df.to_sql(table_name, con=conn_target, schema= esq, if_exists='append', index=False)
    elif dicc['operation'] == 'OVERWRITE':
        df.to_sql(table_name, con=conn_target, schema= esq, if_exists='replace', index=False)
    elif dicc['operation'] == 'UPDATE':
        
        attr_list = list(df.columns)
        
        for row in df.iterrows():
            sqlUpdate = 'UPDATE '+ esq+'."'+table_name+'" SET '
            row_list = list(row[1])
            for i in range (0, len(row_list)):
                sqlUpdate += '"'+attr_list[i]+'" = '+"'"+str(row_list[i]).replace("'","''")+"',"
            value = str(row[1][dicc['match']]).replace("'","''")
        
            sqlUpdate = sqlUpdate[:-1] + ' WHERE "'+dicc['match']+'" = '+"'"+value+"'"

            executePostgres(dicc, sqlUpdate)
    
    elif dicc['operation'] == 'DELETE':
        
        for row in df.iterrows():
            sqlDelete = 'DELETE FROM '+ esq+'."'+table_name+'" '
            value = str(row[1][dicc['match']]).replace("'","''")
            sqlDelete = sqlDelete + ' WHERE "'+dicc['match']+'" = '+"'"+value+"'"
            executePostgres(dicc, sqlDelete)

    return [table_name]


def output_Postgis(dicc):

    table_name_source = dicc['data'][0]
    schemaTable = dicc['tablename'].lower()

    if '.' in schemaTable:
        esq = schemaTable.split(".")[0]
        tab = schemaTable.split(".")[1]
    else:
        esq = 'public'
        tab = schemaTable

    con_source = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = con_source.cursor()

    """sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"  ADD COLUMN _st_astext_temp TEXT'
    cur.execute(sqlAlter)
    con_source.commit()

    sqlUpdate = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"  SET _st_astext_temp = ST_ASTEXT (wkb_geometry)'
    cur.execute(sqlUpdate)
    con_source.commit()"""

    sqlSrid = 'SELECT ST_SRID (wkb_geometry) FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" WHERE wkb_geometry IS NOT NULL LIMIT 1'
    cur.execute(sqlSrid)
    con_source.commit()
    for row in cur:
        srid = row[0]
        break

    sqlTypeGeom = 'SELECT ST_ASTEXT (wkb_geometry) FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" WHERE wkb_geometry IS NOT NULL LIMIT 1'
    cur.execute(sqlTypeGeom)
    con_source.commit()
    for row in cur:
        type_geom = row[0].split('(')[0]
        break

    if dicc['operation'] == 'CREATE':

        output_Postgresql(dicc,'wkb_geometry')

    else:

        sqlAlter = 'ALTER TABLE '+esq+'."'+tab+'"  ADD COLUMN _st_astext_temp TEXT'
        cur.execute(sqlAlter)
        con_source.commit()

        sqlUpdate = 'UPDATE '+esq+'."'+tab+'"  SET _st_astext_temp = ST_ASTEXT (wkb_geometry)'
        cur.execute(sqlUpdate)
        con_source.commit()

        output_Postgresql(dicc,'wkb_geometry')

    """sqlDrop = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"  DROP COLUMN _st_astext_temp '
    cur.execute(sqlDrop)
    con_source.commit()"""
    
    con_source.close()
    cur.close()

    con_target = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
    cur2 = con_target.cursor()

    sqlDrop2 = 'ALTER TABLE '+esq+'."'+tab+'"  DROP COLUMN "wkb_geometry"'
    cur2.execute(sqlDrop2)
    con_target.commit()

    sqlAlter2 = 'ALTER TABLE '+esq+'."'+tab+'"  ADD COLUMN wkb_geometry geometry('+type_geom+', '+str(srid)+')'
    cur2.execute(sqlAlter2)
    con_target.commit()

    sqlUpdate2 = 'UPDATE '+esq+'."'+tab+'"  SET wkb_geometry = ST_GeomFromText(_st_astext_temp,'+str(srid)+')'
    cur2.execute(sqlUpdate2)
    con_target.commit()

    sqlDrop2 = 'ALTER TABLE '+esq+'."'+tab+'"  DROP COLUMN _st_astext_temp'
    cur2.execute(sqlDrop2)
    con_target.commit()

    con_target.close()
    cur2.close()


def input_Csv(dicc):

    df = pd.read_csv(dicc["csv-file"], sep=dicc["separator"], encoding='utf8')
    table_name = dicc['id']

    conn_string = 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
  
    db = create_engine(conn_string)
    conn = db.connect()

    df.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
    
    return [table_name]

def trans_Reproject(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    sourceepsg = str(dicc['source-epsg'])
    targetepsg = str(dicc['target-epsg'])

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    if sourceepsg == '':
        pass
    else:
        sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+ '" ALTER COLUMN wkb_geometry TYPE geometry USING ST_SetSRID(wkb_geometry, '+sourceepsg+')'
        cur.execute(sqlAlter)
        conn.commit()

    sqlTransf = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+ '" ALTER COLUMN wkb_geometry TYPE geometry USING ST_Transform(wkb_geometry, '+targetepsg+')'
    cur.execute(sqlTransf)
    conn.commit()
    
    return[table_name_target]

def trans_Counter(dicc):

    attr = dicc['attr']
    
    gbAttr= dicc['group-by-attr']
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    if gbAttr == '':
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
        cur.execute(sqlDup)
        conn.commit()

        sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' ADD COLUMN "'+attr+'" SERIAL; '  
        cur.execute(sqlAdd)
        conn.commit()
    else:
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select *, row_number() OVER (PARTITION BY "'+gbAttr+'") from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" ORDER BY "'+gbAttr+'");'
        cur.execute(sqlDup)
        conn.commit()
        sqlRename = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" RENAME COLUMN "row_number" TO "'+attr+'";'
        cur.execute(sqlRename)
        conn.commit()

    conn.close()
    cur.close()
 
    return [table_name_target]

def trans_Calculator(dicc):

    table = dicc['data'][0]
    attr = dicc['attr']
    expression= dicc['expression']

    exp = expression.replace("[", "i['properties'][")

    for i in table['features']:
        i['properties'][attr] = eval(exp)

    return [table]

def trans_CadastralGeom(dicc):
    from gvsigol_plugin_catastro.views import get_rc_polygon
    
    attr = dicc['attr']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' ADD COLUMN "_id_temp" SERIAL, ADD COLUMN "wkb_geometry" geometry(MultiPolygon, 4326); '
    cur.execute(sqlAdd)
    conn.commit()

    sqlSel = 'SELECT "'+attr+'", "_id_temp" FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'";'
    cur.execute(sqlSel)
    
    for row in cur:
        cur2 = conn.cursor()
        features = get_rc_polygon(row[0])
        
        i ={}
        coordinates =[]
        
        for feature in features:
            edgeCoord = []
            
            coords = feature['coords'].split(" ")
            srs = feature['srs'].split(":")[1]
            
            pairCoord = []
            for j in range (0, len(coords)):
                pairCoord.insert(0, float(coords[j]))
                
                if j != 0 and j % 2!=0:
                    
                    edgeCoord.append(pairCoord)
                    pairCoord =[]
        
            coordinates.append(edgeCoord)

        if len(coordinates) >= 1:

            i['geometry'] = {"type": 'MultiPolygon',
                            'coordinates': [coordinates]
                            }
            insert = True


        if insert:
            
            sqlInsert = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" SET wkb_geometry = ST_SetSRID(ST_GeomFromGeoJSON(' +"'"+ str(json.dumps(i["geometry"])) +"'), "+ srs +') WHERE "_id_temp" = ' + str(row[1])
            cur2.execute(sqlInsert)
            conn.commit()
            insert = False
    
    sqlDropCol = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN _id_temp;'
    cur.execute(sqlDropCol)
    conn.commit()

    conn.close()
    cur.close()
    cur2.close()

    return [table_name_target]

def trans_MGRS(dicc):
    table = dicc['data'][0]
    select = dicc['select']

    m = mgrs.MGRS()
    
    if select == 'mgrstolatlon':
        grid = dicc['mgrs']
        
        for i in table['features']:
            try:
                lat, lon = m.toLatLon(i['properties'][grid].replace(" ", ""))
                i['properties']['_lat'] = lat
                i['properties']['_lon'] = lon
            except:
                i['properties']['_lat'] = 'NULL'
                i['properties']['_lon'] = 'NULL'

    else:
        lat = dicc['lat']
        lon = dicc['lon']
        
        for i in table['features']:
            try:
                grid = m.toMGRS(i['properties'][lat], i['properties'][lon])
                i['properties']['_mgrs_grid'] = grid
            except:
                i['properties']['_mgrs_grid'] = 'NULL'

    return [table]

def trans_TextToPoint(dicc):
    
    table = dicc['data'][0]
    lat = dicc['lat']
    lon = dicc['lon']
    epsg = dicc['epsg']
    table["type"] = "FeatureCollection"
    table["crs"] = {"type": "name", "properties":{"name":"EPSG:"+str(epsg)}}

    for i in table['features']:
        lat_ = i['properties'][lat]
        lon_ = i['properties'][lon]

        try:
            i["type"] = "Feature"
            i["geometry"] = {"type": "Point", "coordinates": [float(lon_), float(lat_)]}
        except:
            pass
    
    return[table]

def input_Oracle(dicc):
    
    conn = cx_Oracle.connect(
        dicc['username'],
        dicc['password'],
        dicc['dsn']
    )

    conn_string_source = 'oracle+cx_oracle://'+dicc['username']+':'+dicc['password']+'@'+dicc['dsn'].split('/')[0]+'/?service_name='+dicc['dsn'].split('/')[1]
    db_source = create_engine(conn_string_source)
    conn_source = db_source.connect()
    
    if dicc['checkbox'] == "true":
        sql = dicc['sql']
        df = pd.read_sql(sql, con = conn_source)
    else:
        df = pd.read_sql("SELECT * FROM "+dicc['owner-name']+"."+dicc['table-name'], con = conn_source)

    conn_string_target= 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
    db_target = create_engine(conn_string_target)
    conn_target = db_target.connect()
    table_name = dicc['id']
    df.to_sql(table_name, con=conn_target, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)

    return [table_name]

def trans_WktGeom(dicc):
    
    attr = dicc['attr']
    epsg = dicc['epsg']
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()
    if epsg =='':
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (SELECT *, ST_GeomFromText("'+attr+'") as wkb_geometry  FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
        cur.execute(sqlDup)
        conn.commit()
    else:
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (SELECT *, ST_SetSRID ( ST_GeomFromText("'+attr+'"), '+epsg+' ) as wkb_geometry  FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
        cur.execute(sqlDup)
        conn.commit()

    sqlRemov = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN "'+ attr + '"'
    cur.execute(sqlRemov)
    conn.commit()

    return [table_name_target]

    
def trans_SplitAttr(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    attr = dicc['attr']
    _list = dicc['list']
    _split = dicc['split']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select *, string_to_array("'+attr+'",'+"'"+_split+"'" + ') as "'+_list+'" from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlDropCol = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN "'+attr+'"; '
    cur.execute(sqlDropCol)
    conn.commit()

    conn.close()
    cur.close()
    
    return [table_name_target]

def trans_ExplodeList(dicc):
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    attr = dicc['attr']
    list_name = dicc['list']
    
    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlCreate = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (SELECT * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"); TRUNCATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlCreate)
    conn.commit()

    sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' ADD COLUMN "_id_temp" SERIAL, ADD COLUMN "'+attr+'" TEXT'
    cur.execute(sqlAdd)
    conn.commit()

    sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"'+' ADD COLUMN "_id_temp" SERIAL;'
    cur.execute(sqlAdd)
    conn.commit()

    sqlSel = 'SELECT "'+list_name+'", _id_temp FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'";'
    cur.execute(sqlSel)
    
    for row in cur:
        cur2 = conn.cursor()
        for i in range (0, len(row[0])):
            sqlInsert = 'INSERT INTO '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  SELECT *, ' +"'"+ row[0][i] +"'"+ ' FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" WHERE "_id_temp" = ' + str(row[1])
            cur2.execute(sqlInsert)
            conn.commit()

    sqlDropCol = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN _id_temp, DROP COLUMN "'+list_name+'"; '
    sqlDropCol += 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" DROP COLUMN _id_temp; '
    cur.execute(sqlDropCol)
    conn.commit()

    conn.close()
    cur.close()
    cur2.close()

    return [table_name_target]

def trans_Union(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    groupby = dicc['group-by-attr']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    if groupby == '':
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select ST_Union(wkb_geometry) as wkb_geometry from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
        cur.execute(sqlDup)
        conn.commit()
    else:
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select "'+groupby+'", ST_Union(wkb_geometry) as wkb_geometry from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" GROUP BY "'+groupby+'");'
        cur.execute(sqlDup)
        conn.commit()

    return [table_name_target]

def input_Indenova(dicc):
    
    domain = dicc['domain']
    api_key = dicc['api-key']
    client_id = dicc['client-id']
    secret = dicc['secret']
    auth = (client_id+':'+secret).encode()

    table_name = dicc['id']

    if dicc['checkbox-init'] == "true":
        today = date.today()
        init_date = today.strftime("%d/%m/%Y")
    else:
        in_d_list = dicc['init-date'].split('-')
        init_date = in_d_list[2]+'/'+in_d_list[1]+'/'+in_d_list[0]
    
    if dicc['date-indenova'] == "check-init-end-date":
        if dicc['checkbox-end'] == "true":
            today = date.today()
            end_date = today.strftime("%d/%m/%Y")
        else:
            end_d_list = dicc['end-date'].split('-')
            end_date = end_d_list[2]+'/'+end_d_list[1]+'/'+end_d_list[0]

    proced_list = dicc['proced-list']

    schema = dicc['schema']

    url_auth = domain + "//api/rest/security/v1/authentication/authenticate"
    headers_auth = {'esigna-auth-api-key': api_key, 'Authorization': "Basic ".encode()+ base64.b64encode(auth) }
    r_auth = requests.get(url_auth, headers = headers_auth)
    token = r_auth.content

    conn_string = 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
    db = create_engine(conn_string)
    conn = db.connect()

    first = True

    for i in proced_list:
        if i != 'all':
            if dicc['date-indenova'] == "check-init-end-date":

                url_date = domain + '//api/rest/bpm/v1/search//'+i+'//getExpsByTramAndDates?dateIni='+init_date+'&dateEnd='+end_date
            else:
                url_date = domain + "//api/rest/bpm/v1/search//"+i+"//getOpenExpsByTramAndDateIni?dateIni="+init_date

            headers_token = {'esigna-auth-api-key': api_key, "Authorization": "Bearer "+token.decode()}
            r_date = requests.get(url_date, headers = headers_token)

            if r_date.status_code == 200:
                for j in json.loads(r_date.content.decode('utf8')):
                    numExp = j['numExp']
            
                    url_cad = domain + '//api/rest/bpm/v1/search/getDataFileByNumber?numExp='+numExp+'&listMetadata=adirefcatt'
                    r_cad = requests.get(url_cad, headers = headers_token)
                    
                    expedient = json.loads(r_cad.content.decode('utf-8'))
                    
                    exp_copy = expedient.copy()

                    for key in expedient.keys():
                        if isinstance(expedient[key], list):
                            del exp_copy[key]
                            if key != 'metadata':
                                for k in expedient[key]:
                                    exp_copy.update(k)
                            else:
                                for k in expedient[key]:
                                    exp_copy[k['varName']] = k['varValue']
                        
                    list_keys = list(exp_copy.keys())

                    list_keys_low = [x.lower() for x in list_keys]
                    
                    for attr in schema:
                        if attr not in list_keys_low and attr != 'adirefcatt':
                            exp_copy[attr] =''
                        elif attr not in list_keys_low and attr == 'adirefcatt':
                            exp_copy[attr] ='00000000000000000000'
                    
                    if domain == 'https://devempleadopublico.alzira.es/PortalFuncionario':
                        exp_copy['url'] = "https://devempleadopublico.alzira.es/PortalFuncionario/accesoexp.do?formAction=openexp&idexp="+str(exp_copy["idExp"])
                        
                    exp_copy_low = {x.lower(): v for x, v in exp_copy.items()}

                    df = pd.json_normalize(exp_copy_low)

                    if first:
                        df.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
                        first = False
                    else:
                        df.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='append', index=False)

    return[table_name]

def input_Postgres(dicc, geom_column_name = ''):

    conn_string_source = 'postgresql://'+dicc['user']+':'+dicc['password']+'@'+dicc['host']+':'+dicc['port']+'/'+dicc['database']

    schemaTable = dicc['tablename'].lower()
    db_source = create_engine(conn_string_source)
    conn_source = db_source.connect()

    if geom_column_name == '':
        df = pd.read_sql("SELECT * FROM " + schemaTable, con = conn_source)
    else:
        df = pd.read_sql("SELECT *, ST_ASTEXT ("+geom_column_name+") AS _st_astext_temp FROM " + schemaTable, con = conn_source)

    table_name = dicc['id']

    conn_string_target= 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+'/'+settings.GEOETL_DB['database']
  
    db_target = create_engine(conn_string_target)
    conn_target = db_target.connect()

    df.to_sql(table_name, con=conn_target, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)

    return [table_name]

def input_Postgis(dicc):

    table_name = dicc['id']

    schemaTable = dicc['tablename'].lower()

    if '.' in schemaTable:
        esq = schemaTable.split(".")[0]
        tab = schemaTable.split(".")[1]
    else:
        esq = 'public'
        tab = schemaTable

    con_source = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
    cur = con_source.cursor()

    sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
    sqlDatetype += "where table_schema = '"+ esq+"' and table_name ='"+tab+"' "
    cur.execute(sqlDatetype)
    con_source.commit()

    for row in cur:
        if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
            geom_column_name = row[0]
            break

    """sqlAlter = 'ALTER TABLE '+esq+'."'+tab+'"  ADD COLUMN IF NOT EXISTS _st_astext_temp TEXT'
    cur.execute(sqlAlter)
    con_source.commit()

    sqlUpdate = 'UPDATE '+esq+'."'+tab+'"  SET _st_astext_temp = ST_ASTEXT ('+geom_column_name+')'
    cur.execute(sqlUpdate)
    con_source.commit()"""

    sqlSrid = 'SELECT ST_SRID ('+geom_column_name+') FROM '+esq+'."'+tab+'" WHERE '+geom_column_name+' IS NOT NULL LIMIT 1'
    cur.execute(sqlSrid)
    con_source.commit()
    for row in cur:
        srid = row[0]
        break

    sqlTypeGeom = 'SELECT ST_ASTEXT ('+geom_column_name+') FROM '+esq+'."'+tab+'" WHERE '+geom_column_name+' IS NOT NULL LIMIT 1'
    cur.execute(sqlTypeGeom)
    con_source.commit()
    for row in cur:
        type_geom = row[0].split('(')[0]
        break

    con_source.close()
    cur.close()

    input_Postgres(dicc, geom_column_name)

    """sqlDrop = 'ALTER TABLE '+esq+'."'+tab+'"  DROP COLUMN _st_astext_temp '
    cur.execute(sqlDrop)
    con_source.commit()"""


    con_target = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur2 = con_target.cursor()
    
    sqlDrop2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  DROP COLUMN "'+ geom_column_name+'"'
    cur2.execute(sqlDrop2)
    con_target.commit()

    sqlAlter2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  ADD COLUMN wkb_geometry geometry('+type_geom+', '+str(srid)+')'
    cur2.execute(sqlAlter2)
    con_target.commit()

    sqlUpdate2 = 'UPDATE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  SET wkb_geometry = ST_GeomFromText(_st_astext_temp,'+str(srid)+')'
    cur2.execute(sqlUpdate2)
    con_target.commit()

    sqlDrop2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  DROP COLUMN _st_astext_temp'
    cur2.execute(sqlDrop2)
    con_target.commit()

    con_target.close()
    cur2.close()

    return [table_name]

def trans_CompareRows(dicc):

    attr = dicc['attr']

    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]

    table_name_target_equals = dicc['id']+'_0'
    table_name_target_news = dicc['id']+'_1'
    table_name_target_changes = dicc['id']+'_2'
    table_name_target_1_not_used = dicc['id']+'_3'

    output = [table_name_target_equals, table_name_target_news,table_name_target_changes, table_name_target_1_not_used]

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    for out in output:
        sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+out+'"'
        cur.execute(sqlDrop)
        conn.commit()

    sqlEquals = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target_equals+'" as (SELECT * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'"); TRUNCATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target_equals+'"'
    cur.execute(sqlEquals)
    conn.commit()

    sqlNew = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_news+'" as (select A0.* from '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" AS A0'
    sqlNew += ' LEFT OUTER JOIN '+settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" AS A1 ON A0."'+attr+'" = A1."'+attr+'" WHERE A1."'+attr+'" IS NULL );'
    cur.execute(sqlNew)
    conn.commit()

    sqlNotJoin2 = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_1_not_used+'" as (select A1.* from '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" AS A0'
    sqlNotJoin2 += ' RIGHT OUTER JOIN '+settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" AS A1 ON A0."'+attr+'" = A1."'+attr+'" WHERE A0."'+attr+'" IS NULL );'
    cur.execute(sqlNotJoin2)
    conn.commit()

    sqlChanges = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target_changes+'" as (SELECT * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'"); TRUNCATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target_changes+'"'
    cur.execute(sqlChanges)
    conn.commit()

    sqlSelect0 = 'SELECT "'+attr+'", * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'"'
    cur.execute(sqlSelect0)
    
    for row in cur:
        cur2 = conn.cursor()
        sqlSelect1 = 'SELECT "'+attr+'", * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" WHERE "'+attr+'" = '+"'"+str(row[0])+"'"
        cur2.execute(sqlSelect1)
        
        for row2 in cur2:
            if row == row2:
                sqlInsert = 'INSERT INTO '+settings.GEOETL_DB["schema"]+'."'+table_name_target_equals+'" SELECT  * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" WHERE "'+attr+'" = '+"'"+str(row[0])+"'"
                cur2.execute(sqlInsert)
                conn.commit()
            else:
                sqlInsert = 'INSERT INTO '+settings.GEOETL_DB["schema"]+'."'+table_name_target_changes+'" SELECT  * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" WHERE "'+attr+'" = '+"'"+str(row[0])+"'"
                cur2.execute(sqlInsert)
                conn.commit()
            break
            
    conn.close()
    cur.close()


    return output


def trans_FilterGeom(dicc):
    table_name_source = dicc['data'][0]
    table_name_target_points = dicc['id']+'_0'
    table_name_target_multipoints = dicc['id']+'_1'
    table_name_target_lines = dicc['id']+'_2'
    table_name_target_multilines = dicc['id']+'_3'
    table_name_target_polygons = dicc['id']+'_4'
    table_name_target_multipolygons = dicc['id']+'_5'

    output = [table_name_target_points, table_name_target_multipoints, table_name_target_lines, table_name_target_multilines, table_name_target_polygons, table_name_target_multipolygons]
    
    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    for out in output:
        sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+out+'"'
        cur.execute(sqlDrop)
        conn.commit()

    typeGeom = ['POINT', 'MULTIPOINT', 'LINESTRING', 'MULTILINESTRING', 'POLYGON', 'MULTIPOLYGON']

    for i in range (0, len(typeGeom)):
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+output[i]+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"'+ "WHERE ST_ASTEXT(wkb_geometry) LIKE '"+typeGeom[i]+"%' );"
        cur.execute(sqlDup)
        conn.commit()

    conn.close()
    cur.close()

    return output

def trans_CalcArea(dicc):
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    attr = dicc['attr']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select *, ST_Area(wkb_geometry) as "'+attr+'"  from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    conn.close()
    cur.close()

    return[table_name_target]

def trans_CurrentDate(dicc):
    
    attr = dicc['attr']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' ADD COLUMN "'+attr+'" DATE;'
    sqlAdd += 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' SET "'+attr+'" = CURRENT_DATE;'
    cur.execute(sqlAdd)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_ExplodeGeom(dicc):
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select *, (st_dump(wkb_geometry)).geom from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlDropCol = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN wkb_geometry;'
    cur.execute(sqlDropCol)
    conn.commit()

    sqlRename = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" RENAME COLUMN geom TO wkb_geometry;'
    cur.execute(sqlRename)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]


def get_type_n_srid(table_name):

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    """sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name+'"  ADD COLUMN _st_astext_temp TEXT'
    cur.execute(sqlAlter)
    conn.commit()


    sqlUpdate = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name+'"  SET _st_astext_temp = ST_ASTEXT (wkb_geometry)'
    cur.execute(sqlUpdate)
    conn.commit()"""

    sqlTypeGeom = 'SELECT ST_ASTEXT (wkb_geometry) FROM '+settings.GEOETL_DB['schema']+'."'+table_name+'" WHERE wkb_geometry IS NOT NULL LIMIT 1'
    cur.execute(sqlTypeGeom)
    conn.commit()
    for row in cur:
        type_geom = row[0].split('(')[0]
        break

    sqlSrid = 'SELECT ST_SRID (wkb_geometry) FROM '+settings.GEOETL_DB['schema']+'."'+table_name+'" WHERE wkb_geometry IS NOT NULL LIMIT 1'
    cur.execute(sqlSrid)
    conn.commit()
    for row in cur:
        srid = row[0]
        break

    conn.close()
    cur.close()

    return srid, type_geom

def drop_geom_column(table_name,  srid=0, type_geom = ''):

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  DROP COLUMN "wkb_geometry"'
    cur.execute(sqlDrop2)
    conn.commit()

    sqlAlter2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  ADD COLUMN wkb_geometry geometry(Geometry, '+str(srid)+')'
    cur.execute(sqlAlter2)
    conn.commit()

    sqlUpdate2 = 'UPDATE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  SET wkb_geometry = ST_GeomFromText(_st_astext_temp,'+str(srid)+')'
    cur.execute(sqlUpdate2)
    conn.commit()
    
    sqlDrop2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  DROP COLUMN _st_astext_temp'
    cur.execute(sqlDrop2)
    conn.commit()

    conn.close()
    cur.close()

def merge_tables(_list):
    
    table_name_source = _list[-1]
    table_name_target = _list[-2]

    conn_string= 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
  
    db = create_engine(conn_string)
    conn = db.connect()

    attr_target_list = list(pd.read_sql("SELECT * FROM " + settings.GEOETL_DB['schema']+'."'+table_name_target+'"', con = conn).columns)
    attr_source_list = list(pd.read_sql("SELECT * FROM " + settings.GEOETL_DB['schema']+'."'+table_name_source+'"', con = conn).columns)

    conn.close()
    db.dispose()

    if 'wkb_geometry' in attr_target_list:
        srid, type_geom = get_type_n_srid(table_name_target)
        geomTar = True
    else:
        geomTar = False

    if 'wkb_geometry' in attr_source_list:
        srid, type_geom = get_type_n_srid(table_name_source)
        geomSour = True
    else:
        geomSour = False

    db = create_engine(conn_string)
    conn = db.connect()

    if geomTar:
        df_target = pd.read_sql("SELECT *, ST_ASTEXT (wkb_geometry) AS _st_astext_temp FROM " + settings.GEOETL_DB["schema"]+'."'+table_name_target+'"', con = conn)
    else:
        df_target = pd.read_sql("SELECT * FROM " + settings.GEOETL_DB['schema']+'."'+table_name_target+'"', con = conn)
    
    if geomSour:
        df_source = pd.read_sql("SELECT *, ST_ASTEXT (wkb_geometry) AS _st_astext_temp FROM " + settings.GEOETL_DB["schema"]+'."'+table_name_source+'"', con = conn)
    else:
        df_source = pd.read_sql("SELECT * FROM " + settings.GEOETL_DB['schema']+'."'+table_name_source+'"', con = conn)

    merge_ = df_target.append(df_source, sort = False)

    table_name = table_name_source[:15]+';'+table_name_target[:15]

    merge_.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
    
    conn.close()
    db.dispose()

    if geomSour or geomTar:
        drop_geom_column(table_name, srid, type_geom)

    return [table_name]

def trans_ConcatAttr(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    separator = dicc['separator']
    attrs = ', '.join(dicc['attr'])
    new_attr = dicc['new-attr']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select *, concat_ws('+"'"+separator+"', "+attrs+') as "'+new_attr+'" from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]