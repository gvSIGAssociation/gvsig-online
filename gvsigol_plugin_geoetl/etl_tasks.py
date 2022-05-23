# -*- coding: utf-8 -*-

#from sre_constants import SRE_INFO_CHARSET
from gvsigol import settings

import pandas as pd
import psycopg2
from psycopg2 import sql
import json
from collections import defaultdict
#from dateutil.parser import parse
import mgrs
import gdaltools
import os, shutil

import cx_Oracle
#from geomet import wkt
from .models import database_connections
import requests
import base64
from datetime import date, datetime
from sqlalchemy import create_engine, true
from django.contrib.gis.gdal import DataSource
import re
from zipfile import ZipFile
import time


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
#and the name of a table postgres -if task is not an input task-
#The output for each function must be the name of a table postgres/postgis in an array.
#Name must be the identifier of the task 
#Array will be as longer as outputs has the task. e.g filter has two outputs True and False
#so output array will be [idTrue, idFalse]

def input_Excel(dicc):

    import warnings

    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

    if dicc['reading'] == 'single':

        df = pd.read_excel(dicc["excel-file"], sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
        df = df.replace('\n', ' ', regex=True).replace('\r', '', regex=True).replace('\t', '', regex=True)
    
    else:
        x = 0
        if not os.listdir(dicc["excel-file"]):
            raise Exception("No Excel files in folder "+dicc["excel-file"])
        for file in os.listdir(dicc["excel-file"]):
            if file.endswith(".xls") or file.endswith(".xlsx"):

                if x == 0:
                    df = pd.read_excel(dicc["excel-file"]+'//'+file, sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
                    df = df.replace('\n', ' ', regex=True).replace('\r', '', regex=True).replace('\t', '', regex=True)
                    df['_filename'] = file
                else:
                    dfx = pd.read_excel(dicc["excel-file"]+'//'+file, sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
                    dfx = dfx.replace('\n', ' ', regex=True).replace('\r', '', regex=True).replace('\t', '', regex=True)
                    dfx['_filename'] = file
                    df = df.append(dfx, sort = False)
                x += 1

    table_name = dicc['id']

    conn_string = 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
  
    db = create_engine(conn_string)
    conn = db.connect()

    df.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
    
    return [table_name]

def input_Shp(dicc):

    table_name = dicc['id'].replace('-','_')

    shp = dicc['shp-file'][7:]
  
    dataSource = DataSource(shp)
            
    layer = dataSource[0]

    epsg = str(dicc['epsg'])
    
    if epsg == '':
        try:
            epsg = layer.srs['AUTHORITY', 1]
        except:
            pass
    
    srs = "EPSG:"+str(epsg)
    schema = settings.GEOETL_DB['schema']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name))
    cur.execute(sqlDrop)
    conn.commit()

    encoding = dicc['encode']
    
    _ogr = gdaltools.ogr2ogr()
    _ogr.set_encoding(encoding)
    _ogr.set_input(shp, srs=srs)
    _conn = gdaltools.PgConnectionString(host=settings.GEOETL_DB["host"], port=settings.GEOETL_DB["port"], dbname=settings.GEOETL_DB["database"], schema=schema, user=settings.GEOETL_DB["user"], password=settings.GEOETL_DB["password"])
    _ogr.set_output(_conn, table_name=table_name)
    _ogr.set_output_mode(layer_mode=_ogr.MODE_DS_CREATE_OR_UPDATE, data_source_mode=_ogr.MODE_DS_UPDATE)

    _ogr.layer_creation_options = {
        "LAUNDER": "YES",
        "precision": "NO"
    }
    _ogr.config_options = {
        "OGR_TRUNCATE": "NO"
    }
    _ogr.set_dim("2")
    _ogr.geom_type = "PROMOTE_TO_MULTI"
    _ogr.execute()
    
    return [table_name]
    

def trans_RemoveAttr(dicc):

    attrList = dicc['attr']
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(settings.GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlRemov = 'ALTER TABLE {}.{}'

    for attr in attrList:
        sqlRemov += ' DROP COLUMN {},'

    cur.execute(sql.SQL(sqlRemov[:-1]).format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target),
        *[sql.Identifier(field) for field in attrList]
        ))

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

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDatetype = 'SELECT column_name from information_schema.columns '
    sqlDatetype += 'where table_schema = %s and table_name = %s '
    cur.execute(sql.SQL(sqlDatetype).format(
    ),[settings.GEOETL_DB["schema"], table_name_source])
    conn.commit()
    
    for row in cur:
        if row[0] == 'wkb_geometry':
            attrList.append('wkb_geometry')
            break

    sqlDup = 'create table {schema}.{tbl_target} as (select '

    for attr in attrList:
        sqlDup += ' %s ,'

    sqlDup = sqlDup[:-1]+' from {schema}.{tbl_source})'

    cur.execute(sqlDup.format(
        schema = sql.Identifier(settings.GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source),
        *[sql.Identifier(field) for field in attrList]
    ))

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

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(settings.GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlRename_ = 'ALTER TABLE {}.{}'

    for x in range (0, len(oldAttr)):
        sqlRename = sqlRename_ + ' RENAME COLUMN {} TO {};'
        cur.execute(sql.SQL(sqlRename).format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target),
        sql.Identifier(oldAttr[x]),
        sql.Identifier(newAttr[x])
        ))

        conn.commit()
    
    conn.close()
    cur.close()

    return [table_name_target]

def trans_Join(dicc):

    attr1 = dicc['attr-1'].split(" ")
    attr2 = dicc['attr-2'].split(" ")

    on =''
    for pos in range (0, len(attr1)):
        on += 'A0."'+attr1[pos]+'"::TEXT = A1."'+attr2[pos]+'"::TEXT AND '

    on = on[:-5]

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
        sqlDatetype += 'where table_schema = %s and table_name = %s '
        cur.execute(sql.SQL(sqlDatetype).format(
        ),[settings.GEOETL_DB["schema"], table_name])
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

        sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(settings.GEOETL_DB["schema"]),
            sql.Identifier(out))
        
        cur.execute(sqlDrop)
        conn.commit()

    sqlJoin = sql.Composed([
        sql.SQL('create table {sch}.{tbl_join} as (select ').format(
            sch = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_join = sql.Identifier(table_name_target_join)
        ),
        sql.SQL(schema),
        sql.SQL(' from {sch}.{tbl_source_0} AS A0 INNER JOIN {sch}.{tbl_source_1} AS A1 ON ').format(
            sch = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1)
        ),sql.SQL(on),
        sql.SQL(');')]
    )

    cur.execute(sqlJoin)
    conn.commit()

    sqlNotJoin1 = sql.Composed([
            sql.SQL('create table {sch}.{tbl_not_0} as (select A0.* from {sch}.{tbl_source_0} AS A0 LEFT OUTER JOIN {sch}.{tbl_source_1} AS A1 ON ').format(
            sch = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_not_0 = sql.Identifier(table_name_target_0_not_used),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1)
        ),
        sql.SQL(on),
        sql.SQL(' WHERE '),
        sql.SQL(schema_1.split(",")[0]),
        sql.SQL(' IS NULL )')]
    )
    
    cur.execute(sqlNotJoin1)
    conn.commit()

    sqlNotJoin2 = sql.Composed([
            sql.SQL('create table {sch}.{tbl_not_1} as (select A1.* from {sch}.{tbl_source_0} AS A0 RIGHT OUTER JOIN {sch}.{tbl_source_1} AS A1 ON ').format(
            sch = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_not_1 = sql.Identifier(table_name_target_1_not_used),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1)
        ),
        sql.SQL(on),
        sql.SQL(' WHERE '),
        sql.SQL(schema_0.split(",")[0]),
        sql.SQL(' IS NULL )')]
    )
    
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

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(settings.GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlUpdate = sql.SQL('UPDATE {}.{} SET {} = %s').format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target),
        sql.Identifier(attr)
    )

    cur.execute(sqlUpdate,[value])
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

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(settings.GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )

    cur.execute(sqlDup)
    conn.commit()

    if value != '':
        
        sqlSET = sql.SQL(' DEFAULT %s')
    else:
        sqlSET = sql.SQL('')

    sqlAdd = sql.Composed([
        sql.SQL('ALTER TABLE {}.{} ADD COLUMN {} ').format(
            sql.Identifier(settings.GEOETL_DB["schema"]),
            sql.Identifier(table_name_target),
            sql.Identifier(attr)
        ),
        sql.SQL(data_type),
        sqlSET,
        ])

    
    cur.execute(sqlAdd,[value])
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_Filter(dicc):

    attr = dicc['attr']
    
    value = dicc['value']
    
    operator = dicc['option']

    expression = dicc['filter-expression']

    table_name_source = dicc['data'][0]
    table_name_target_passed = dicc['id']+'_0'
    table_name_target_failed = dicc['id']+'_1'

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_passed))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_failed))
    cur.execute(sqlDrop)
    conn.commit()

    if expression == "":

        sqlDatetype = 'SELECT  data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s and column_name = %s "
        
        cur.execute(sql.SQL(sqlDatetype).format(),[settings.GEOETL_DB["schema"],table_name_source, attr])
        conn.commit()

        data_type = ''

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

        sqlFilPassed = 'create table {schema}.{tbl_passed} as (select * from {schema}.{tbl_source} WHERE {attr} '
        
        sqlFilPassed_ = sql.Composed([
                sql.SQL(sqlFilPassed).format(
                    schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                    tbl_passed = sql.Identifier(table_name_target_passed),
                    tbl_source = sql.Identifier(table_name_source),
                    attr = sql.Identifier(attr)),
                sql.SQL(operator),
                sql.SQL(' '),
                sql.SQL(value),
                sql.SQL(')'),
        ])
        
        cur.execute(sqlFilPassed_)
        conn.commit()

        sqlFilFailed = 'create table {schema}.{tbl_failed} as (select * from {schema}.{tbl_source} WHERE NOT {attr} '

        sqlFilFailed_ = sql.Composed([
                sql.SQL(sqlFilFailed).format(
                    schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                    tbl_failed = sql.Identifier(table_name_target_failed),
                    tbl_source = sql.Identifier(table_name_source),
                    attr = sql.Identifier(attr)),
                sql.SQL(operator),
                sql.SQL(' '),
                sql.SQL(value),
                sql.SQL(')'),
        ])

        cur.execute(sqlFilFailed_)
        conn.commit()

        conn.close()
        cur.close()

    else:

        sqlFilPassed = 'create table {schema}.{tbl_passed} as (select * from {schema}.{tbl_source} WHERE ( '
        
        sqlFilPassed_ = sql.Composed([
                sql.SQL(sqlFilPassed).format(
                    schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                    tbl_passed = sql.Identifier(table_name_target_passed),
                    tbl_source = sql.Identifier(table_name_source)),
                sql.SQL(expression),
                sql.SQL(' ))'),
        ])
        
        cur.execute(sqlFilPassed_)
        conn.commit()

        sqlFilFailed = 'create table {schema}.{tbl_failed} as (select * from {schema}.{tbl_source} WHERE NOT ( '

        sqlFilFailed_ = sql.Composed([
                sql.SQL(sqlFilFailed).format(
                    schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                    tbl_failed = sql.Identifier(table_name_target_failed),
                    tbl_source = sql.Identifier(table_name_source)),
                sql.SQL(expression),
                sql.SQL(' ))')
        ])

        cur.execute(sqlFilFailed_)
        conn.commit()

        conn.close()
        cur.close()


    return [table_name_target_passed, table_name_target_failed]


def isInSamedb(params):

    if (settings.GEOETL_DB['host'] == params['host'] and 
        str(settings.GEOETL_DB["port"]) == str(params['port']) and 
        settings.GEOETL_DB["database"] == params['database'] and
        settings.GEOETL_DB["user"] == params['user'] and
        settings.GEOETL_DB["password"] == params['password']):
        
        return True
    else:
        return False


def output_Postgis(dicc):

    table_name_source = dicc['data'][0]

    db  = database_connections.objects.get(name = dicc['db-option'])

    params_str = db.connection_params
    params = json.loads(params_str)

    inSame = isInSamedb(params)

    print("Is in same server and database: "+str(inSame))

    esq = dicc['schema-name-option']
    tab = dicc['tablename']

    con_source = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = con_source.cursor()

    sqlCount = "SELECT COUNT(*) FROM "+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"'
    cur.execute(sqlCount)
    con_source.commit()
    for row in cur:
        count = row[0]
        break
    
    if count == 0:
        print('There is no features in output')

    else:

        if dicc['operation'] == 'CREATE':

            if inSame:
                
                sqlCreate = sql.SQL('create table {sch_target}.{tbl_target} as (select * from {sch_source}.{tbl_source})').format(
                    sch_target = sql.Identifier(esq),
                    tbl_target = sql.Identifier(tab),
                    sch_source = sql.Identifier(settings.GEOETL_DB["schema"]),
                    tbl_source = sql.Identifier(table_name_source))
                
                cur.execute(sqlCreate)
                con_source.commit()

                sqlAlter = sql.SQL('ALTER TABLE {sch_target}.{tbl_target}  ADD COLUMN IF NOT EXISTS ogc_fid SERIAL').format(
                    sch_target = sql.Identifier(esq),
                    tbl_target = sql.Identifier(tab))

                cur.execute(sqlAlter)
                con_source.commit()

                sqlAlter_ =  sql.SQL('ALTER TABLE {sch_target}.{tbl_target} ADD PRIMARY KEY (ogc_fid)').format(
                    sch_target = sql.Identifier(esq),
                    tbl_target = sql.Identifier(tab))
                try:
                    cur.execute(sqlAlter_)
                    con_source.commit()
                except:
                    pass

                con_source.close()
                cur.close()

            #Create en diferente servidor o bbdd
            else:
                try:
                    srid, type_geom = get_type_n_srid(table_name_source)
                except:
                    type_geom = ''

                _conn_source = gdaltools.PgConnectionString(host=settings.GEOETL_DB["host"], port=settings.GEOETL_DB["port"], dbname=settings.GEOETL_DB["database"], schema=settings.GEOETL_DB["schema"], user=settings.GEOETL_DB["user"], password=settings.GEOETL_DB["password"])
                _conn_target = gdaltools.PgConnectionString(user = params["user"], password = params["password"], host = params["host"], port = params["port"], dbname = params["database"],  schema=esq)

                _ogr = gdaltools.ogr2ogr()
                _ogr.set_input(_conn_source, table_name=table_name_source)
                _ogr.set_output(_conn_target, table_name=tab)
                _ogr.set_output_mode(layer_mode=_ogr.MODE_DS_CREATE_OR_UPDATE, data_source_mode=_ogr.MODE_DS_UPDATE)

                _ogr.layer_creation_options = {
                    "LAUNDER": "YES",
                    "precision": "NO"
                }
                _ogr.config_options = {
                    "OGR_TRUNCATE": "NO"
                }
                _ogr.set_dim("2")

                _ogr.geom_type = type_geom

                _ogr.execute()

        
        elif dicc['operation'] == 'APPEND':

            if inSame:
                sqlDatetype = 'SELECT column_name from information_schema.columns '
                sqlDatetype += "where table_schema = %s and table_name = %s "

                cur.execute(sql.SQL(sqlDatetype).format(),[settings.GEOETL_DB["schema"], table_name_source])
                con_source.commit()

                attr_source = '('

                geometry = False

                for row in cur:
                    attr_source = attr_source + '"'+row[0]+'", '
                    if 'wkb_geometry' == row[0]:
                        geometry = True
                
                attr_source = attr_source[:-2] + ')'

                if geometry:
                    sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
                    sqlDatetype += "where table_schema = %s and table_name = %s "

                    cur.execute(sql.SQL(sqlDatetype).format(),[esq, tab])
                    con_source.commit()

                    for row in cur:
                        if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                            if 'wkb_geometry' == row[0]:
                                attr_target = attr_source
                            else:
                                attr_target = attr_source.replace('"wkb_geometry"', '"'+row[0]+'"')
                            break
                
                
                sqlInsert = sql.Composed([
                    sql.SQL('INSERT INTO {sch_target}.{tbl_target} ').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab)
                        ),
                    sql.SQL(attr_target),
                    sql.SQL(' SELECT '),
                    sql.SQL(attr_source[1:-1]),
                    sql.SQL(' FROM {sch_source}.{tbl_source} ').format(
                        sch_source = sql.Identifier(settings.GEOETL_DB["schema"]),
                        tbl_source = sql.Identifier(table_name_source)
                        ),
                    ])

                cur.execute(sqlInsert)
                con_source.commit()

            
            #insert en diferente servidor o bddd
            else:
                try:
                    srid, type_geom = get_type_n_srid(table_name_source)
                except:
                    type_geom = ''

                _conn_source = gdaltools.PgConnectionString(host=settings.GEOETL_DB["host"], port=settings.GEOETL_DB["port"], dbname=settings.GEOETL_DB["database"], schema=settings.GEOETL_DB["schema"], user=settings.GEOETL_DB["user"], password=settings.GEOETL_DB["password"])
                _conn_target = gdaltools.PgConnectionString(user = params["user"], password = params["password"], host = params["host"], port = params["port"], dbname = params["database"],  schema=esq)

                _ogr = gdaltools.ogr2ogr()
                _ogr.set_input(_conn_source, table_name=table_name_source)
                _ogr.set_output(_conn_target, table_name=tab)
                _ogr.set_output_mode(layer_mode=_ogr.MODE_LAYER_APPEND, data_source_mode=_ogr.MODE_DS_UPDATE)

                _ogr.layer_creation_options = {
                    "LAUNDER": "YES",
                    "precision": "NO"
                }
                _ogr.config_options = {
                    "OGR_TRUNCATE": "NO"
                }
                _ogr.set_dim("2")
                _ogr.geom_type = type_geom
                _ogr.execute()

        elif dicc['operation'] == 'OVERWRITE':
            if inSame:
                sqlTruncate = sql.SQL('TRUNCATE TABLE {sch_target}.{tbl_target} ').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab)
                        )
                cur.execute(sqlTruncate)
                con_source.commit()


                sqlInsert = sql.SQL('INSERT INTO {sch_target}.{tbl_target} SELECT * FROM {sch_source}.{tbl_source}').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                        sch_source = sql.Identifier(settings.GEOETL_DB["schema"]),
                        tbl_source = sql.Identifier(table_name_source)
                        )

                cur.execute(sqlInsert)
                con_source.commit()
            
            #OVERWRITE en diferente servidor o bddd
            else:
                try:
                    srid, type_geom = get_type_n_srid(table_name_source)
                except:
                    type_geom = ''

                _conn_source = gdaltools.PgConnectionString(host=settings.GEOETL_DB["host"], port=settings.GEOETL_DB["port"], dbname=settings.GEOETL_DB["database"], schema=settings.GEOETL_DB["schema"], user=settings.GEOETL_DB["user"], password=settings.GEOETL_DB["password"])
                _conn_target = gdaltools.PgConnectionString(user = params["user"], password = params["password"], host = params["host"], port = params["port"], dbname = params["database"],  schema=esq)

                _ogr = gdaltools.ogr2ogr()
                _ogr.set_input(_conn_source, table_name=table_name_source)
                _ogr.set_output(_conn_target, table_name=tab)
                _ogr.set_output_mode(layer_mode=_ogr.MODE_LAYER_OVERWRITE, data_source_mode=_ogr.MODE_DS_UPDATE)

                _ogr.layer_creation_options = {
                    "LAUNDER": "YES",
                    "precision": "NO"
                }
                _ogr.config_options = {
                    "OGR_TRUNCATE": "NO"
                }
                _ogr.set_dim("2")
                _ogr.geom_type = type_geom
                _ogr.execute()

        elif dicc['operation'] == 'UPDATE':
           
            sqlDatetype = 'SELECT column_name from information_schema.columns '
            sqlDatetype += "where table_schema = %s and table_name = %s "

            cur.execute(sql.SQL(sqlDatetype).format(),[settings.GEOETL_DB["schema"], table_name_source])
            con_source.commit()

            attr_source = []

            geometry = False

            for row in cur:
                attr_source.append('"'+row[0]+'"')
                if 'wkb_geometry' == row[0]:
                    geometry = True

            if inSame:

                cur_2 = con_source.cursor()

            else:

                con_target = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
                cur_2 = con_target.cursor()

            if geometry:

                sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
                sqlDatetype += "where table_schema = %s and table_name = %s "

                if inSame:

                    cur.execute(sql.SQL(sqlDatetype).format(),[esq, tab])
                    con_source.commit()

                    for row in cur:
                        if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                            if 'wkb_geometry' == row[0]:
                                attr_target = 'wkb_geometry'
                            else:
                                attr_target = '"'+row[0]+'"'
                            break
                else:

                    cur_2.execute(sql.SQL(sqlDatetype).format(),[esq, tab])
                    con_target.commit()

                    for row in cur_2:
                        if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                            if 'wkb_geometry' == row[0]:
                                attr_target = 'wkb_geometry'
                            else:
                                attr_target = '"'+row[0]+'"'
                            break


            cur.execute(sql.SQL('SELECT * FROM {sch_source}.{tbl_source}').format(
                sch_source = sql.Identifier(settings.GEOETL_DB["schema"]),
                tbl_source = sql.Identifier(table_name_source)
            ))

            con_source.commit()

            for row in cur:
                attrs_update =''

                for i in range (0, len(attr_source)):
                    if '"'+dicc['match']+'"' == attr_source[i]:
                        value = "'"+str(row[i])+"'"
                        
                    elif attr_source[i] == '"wkb_geometry"':
                        pass
                        attrs_update = attrs_update +attr_target+' = '+"'"+ str(row[i])+"', "
                        
                    else:
                        attrs_update = attrs_update +attr_source[i]+' = '+"'"+ str(row[i])+"', "

                sqlUpdate = sql.Composed([
                    sql.SQL('UPDATE {sch_target}.{tbl_target} SET ').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                    ),
                    sql.SQL(attrs_update[:-2]),
                    sql.SQL(' WHERE {match} = ').format(
                        match = sql.Identifier(dicc['match'])
                    ),
                    sql.SQL(value)
                ])

                cur_2.execute(sqlUpdate)

                if inSame:

                    con_source.commit()

                else:
                    con_target.commit()

            con_source.close()
            cur.close()

            try:
                con_target.close()
            except:
                pass
            cur_2.close()
                    

        elif dicc['operation'] == 'DELETE':

            sqlDatetype = 'SELECT column_name from information_schema.columns '
            sqlDatetype += "where table_schema = %s and table_name = %s "

            cur.execute(sql.SQL(sqlDatetype).format(),[settings.GEOETL_DB["schema"], table_name_source])
            con_source.commit()

            attr_source = []

            geometry = False

            for row in cur:
                attr_source.append('"'+row[0]+'"')
                if 'wkb_geometry' == row[0]:
                    geometry = True

            if geometry:

                sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
                sqlDatetype += "where table_schema = %s and table_name = %s "

                cur.execute(sql.SQL(sqlDatetype).format(),[esq, tab])
                con_source.commit()

                for row in cur:
                    if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                        if 'wkb_geometry' == row[0]:
                            attr_target = 'wkb_geometry'
                        else:
                            attr_target = '"'+row[0]+'"'
                        break

            cur.execute(sql.SQL('SELECT * FROM {sch_source}.{tbl_source}').format(
                sch_source = sql.Identifier(settings.GEOETL_DB["schema"]),
                tbl_source = sql.Identifier(table_name_source)
            ))

            con_source.commit()

            if inSame:

                cur_2 = con_source.cursor()

            else:

                con_target = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
                cur_2 = con_target.cursor()

            for row in cur:

                for i in range (0, len(attr_source)):
                    if '"'+dicc['match']+'"' == attr_source[i]:
                        value = "'"+str(row[i])+"'"

                sqlDelete = sql.Composed([
                    sql.SQL('DELETE FROM {sch_target}.{tbl_target} WHERE {match} = ').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                        match = sql.Identifier(dicc['match'])
                    ),
                    sql.SQL(value)
                ])

                cur_2.execute(sqlDelete)

                if inSame:

                    con_source.commit()

                else:
                    con_target.commit()

            con_source.close()
            cur.close()

            try:
                con_target.close()
            except:
                pass
            cur_2.close()


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

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(settings.GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source))
    cur.execute(sqlDup)
    conn.commit()

    if sourceepsg == '':
        pass
    else:
        sqlAlter_ = 'ALTER TABLE {schema}.{tbl_target} ALTER COLUMN wkb_geometry TYPE geometry USING ST_SetSRID(wkb_geometry, '
        sqlAlter = sql.Composed([
                sql.SQL(sqlAlter_).format(
                    schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(table_name_target)),
                sql.SQL(sourceepsg),
                sql.SQL(' )')
        ])       
        cur.execute(sqlAlter)
        conn.commit()

    sqlTransf_ = 'ALTER TABLE {schema}.{tbl_target} ALTER COLUMN wkb_geometry TYPE geometry USING ST_Transform(wkb_geometry, '
    
    sqlTransf = sql.Composed([
            sql.SQL(sqlTransf_).format(
                schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                tbl_target = sql.Identifier(table_name_target)),
            sql.SQL(targetepsg),
            sql.SQL(' )')
    ])
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

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    if gbAttr == '':

        sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
            schema = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            tbl_source = sql.Identifier(table_name_source))
        cur.execute(sqlDup)
        conn.commit()

        sqlAdd_ = 'ALTER TABLE {schema}.{tbl_target} ADD COLUMN {attr} SERIAL; '  
        sqlAdd = sql.SQL(sqlAdd_).format(
                    schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(table_name_target),
                    attr = sql.Identifier(attr))

        cur.execute(sqlAdd)
        conn.commit()
    else:
        sqlDup = 'create table {schema}.{tbl_target} as (select *, row_number() OVER (PARTITION BY {attr}) from {schema}.{tbl_source}  ORDER BY {attr});'

        cur.execute(sql.SQL(sqlDup).format(
            schema = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            tbl_source = sql.Identifier(table_name_source),
            attr = sql.Identifier(gbAttr)
        ))
        conn.commit()
        
        sqlRename = 'ALTER TABLE {schema}.{tbl_target} RENAME COLUMN "row_number" TO {attr};'

        cur.execute(sql.SQL(sqlRename).format(
            schema = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            attr = sql.Identifier(attr)
        ))
        conn.commit()

    conn.close()
    cur.close()
 
    return [table_name_target]

def trans_Calculator(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']
    attr = dicc['attr']
    expression= dicc['expression']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(settings.GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source))
    cur.execute(sqlDup)
    conn.commit()

    sqlCount = sql.SQL('SELECT count(*) FROM {}.{}').format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target)) 
    cur.execute(sqlCount)

    run = False
    for row in cur:
        if row[0] != 0:
            run = True

    if run:
        sqlInsert = sql.Composed([
            sql.SQL('UPDATE {schema}.{tbl_target} SET {attr} = ').format(
                schema = sql.Identifier(settings.GEOETL_DB["schema"]),
                tbl_target = sql.Identifier(table_name_target),
                attr = sql.Identifier(attr)),
            sql.SQL(expression) 
            ])
        cur.execute(sqlInsert)
        conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

counter_cadastral_petitions = 0

def trans_CadastralGeom(dicc):
    from gvsigol_plugin_catastro.views import get_rc_polygon
    
    attr = dicc['attr']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    global counter_cadastral_petitions

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

        if counter_cadastral_petitions < 3000:
            try:
                cur2 = conn.cursor()
                
                features = get_rc_polygon(row[0].replace(' ', ''))
                counter_cadastral_petitions += 1
                
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
            
                    sqlInsert = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" SET wkb_geometry = ST_SetSRID(ST_GeomFromGeoJSON(' +"'"+ str(json.dumps(i["geometry"])) +"'), "+ srs +') WHERE "_id_temp" = ' + str(row[1])
                    cur2.execute(sqlInsert)
                    conn.commit()
            except Exception as e:
                print(str(e))

        else:
            print("Take a coffee. The maximum number of requests to cadastre has been reached. The process will continue in an hour.")
            time.sleep(3600)
            counter_cadastral_petitions = 0

            
    
    sqlDropCol = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN _id_temp;'
    cur.execute(sqlDropCol)
    conn.commit()

    conn.close()
    cur.close()
    cur2.close()

    return [table_name_target]

def trans_MGRS(dicc):
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()
    cur_2 = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" AS (SELECT * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" );'
    cur.execute(sqlDup)
    conn.commit()
    
    select = dicc['select']

    m = mgrs.MGRS()
    
    if select == 'mgrstolatlon':
        grid = dicc['mgrs']

        sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' ADD COLUMN _lat FLOAT DEFAULT NULL, ADD COLUMN _lon FLOAT DEFAULT NULL'
        cur.execute(sqlAdd)
        conn.commit()

        sqlSelect = 'SELECT "'+grid+'" FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
        cur.execute(sqlSelect)
        conn.commit()
        
        for row in cur:
            try:
                lat, lon = m.toLatLon(row[0].replace(" ", ""))

                sqlUpdate = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  SET _lat = '+ str(lat)+', _lon = '+ str(lon) +' WHERE "'+grid+'" = '+"'"+ str(row[0])+"'"
                cur_2.execute(sqlUpdate)
                conn.commit()

            except Exception as e:
                print('GRID: '+grid + ' ERROR: '+ str(e))

    else:
        lat = dicc['lat']
        lon = dicc['lon']

        sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'+' ADD COLUMN _grid TEXT DEFAULT NULL'
        cur.execute(sqlAdd)
        conn.commit()

        sqlSelect = 'SELECT "'+lat+'", "'+lon+'" FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
        cur.execute(sqlSelect)
        conn.commit()
        
        for row in cur:
            try:
                grid = m.toMGRS(row[0], row[1])

                sqlUpdate = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  SET _grid = '+"'"+grid+"'"+' WHERE "'+lat+'" = '+ "'"+str(row[0])+"'" + ' AND "'+lon+'" = '+"'"+str(row[1])+"'"
                cur_2.execute(sqlUpdate)
                conn.commit()

            except Exception as e:
                print("latitud: "+lat+" longitud: "+ lon+" ERROR: "+ str(e))

    conn.close()
    cur.close()
    cur_2.close()

    return [table_name_target]

def trans_TextToPoint(dicc):
    
    lat = dicc['lat']
    lon = dicc['lon']
    epsg = dicc['epsg']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" AS (SELECT *, ST_SetSRID(ST_MakePoint("'+lon+'"::float, "'+lat+'"::float), '+epsg+') AS wkb_geometry FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" );'
    cur.execute(sqlDup)
    conn.commit()
    
    return[table_name_target]

def input_Oracle(dicc):

    table_name = dicc['id']

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn_string_source = 'oracle+cx_oracle://'+params['username']+':'+params['password']+'@'+params['dsn'].split('/')[0]+'/?service_name='+params['dsn'].split('/')[1]
    db_source = create_engine(conn_string_source)
    conn_source = db_source.connect()
    
    if dicc['checkbox'] == "true":
        sql = dicc['sql']
    else:
        sql = "SELECT * FROM "+dicc['owner-name']+"."+dicc['table-name']
    
    df = pd.read_sql(sql + " WHERE rownum = 1" , con = conn_source)

    conn_string_target= 'postgresql://'+settings.GEOETL_DB['user']+':'+settings.GEOETL_DB['password']+'@'+settings.GEOETL_DB['host']+':'+settings.GEOETL_DB['port']+'/'+settings.GEOETL_DB['database']
    db_target = create_engine(conn_string_target)
    conn_target = db_target.connect()

    df.to_sql(table_name, con=conn_target, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
    
    col = list(df.columns.values)

    conn_source.close()
    db_source.dispose()
    
    conn_ORA = cx_Oracle.connect(
        params['username'],
        params['password'],
        params['dsn']
    )

    c_ORA = conn_ORA.cursor()
    c_ORA.execute(sql)

    count = 1

    for r in c_ORA:
        row = list(r)
        for i in range (0, len(row)):
            if type(row[i]) == cx_Oracle.LOB:
                row[i] = row[i].read().replace("\x00", "\uFFFD")

        df_tar = pd.DataFrame([row], columns = col)

        if count == 1:
            df_tar.to_sql(table_name, con=conn_target, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
            count +=1
        else:
            df_tar.to_sql(table_name, con=conn_target, schema= settings.GEOETL_DB['schema'], if_exists='append', index=False)


    conn_target.close()
    db_target.dispose()

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

    conn.close()
    cur.close()

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
        cur2.close()

    sqlDropCol = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN _id_temp, DROP COLUMN "'+list_name+'"; '
    sqlDropCol += 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" DROP COLUMN _id_temp; '
    cur.execute(sqlDropCol)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_Union(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    groupby = dicc['group-by-attr']

    multi =dicc['multi']

    st_multi_start = ''
    st_multi_ends = ''

    if multi == 'true':
        st_multi_start = 'ST_Multi('
        st_multi_ends = ')'

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
        sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select "'+groupby+'", '+st_multi_start+' ST_Union(wkb_geometry)'+st_multi_ends+' as wkb_geometry from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" GROUP BY "'+groupby+'");'
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

                    if domain.startswith('https://empleadopublico.alzira.es'):

                        exp_copy['url'] = domain + "/?externAccess=73ac4c3b-3ede-4436-a66a-75037ef96b4a&urlredirect=accesoexp.do?formAction=openexp&idexp="+str(exp_copy["idExp"])

                    elif domain.startswith('https://preempleadopublico.alzira.es'):
                        
                        exp_copy['url'] = domain + "/?externAccess=ce54d05d-e01b-c4c7-707a-ecd7289736ab&urlredirect=accesoexp.do?formAction=openexp&idexp="+str(exp_copy["idExp"])
                        
                    exp_copy_low = {x.lower(): v for x, v in exp_copy.items()}

                    df = pd.json_normalize(exp_copy_low)

                    df = df[schema]

                    if first:
                        df.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='replace', index=False)
                        first = False
                    else:
                        df.to_sql(table_name, con=conn, schema= settings.GEOETL_DB['schema'], if_exists='append', index=False)

    return[table_name]


def input_Postgis(dicc):

    table_name_target= dicc['id'].replace('-','_')

    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)

    esq = dicc['schema-name']
    tab = dicc['tablename']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(settings.GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    inSame = isInSamedb(params)
    
    if inSame:
    
        sqlCreate = sql.SQL('create table {sch_target}.{tbl_target} as (select * from {sch_source}.{tbl_source})').format(
            sch_target = sql.Identifier(settings.GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            sch_source = sql.Identifier(esq),
            tbl_source = sql.Identifier(tab))
        
        cur.execute(sqlCreate)
        conn.commit()

        sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s "

        cur.execute(sql.SQL(sqlDatetype).format(),[settings.GEOETL_DB["schema"], table_name_target])
        conn.commit()

        for row in cur:
            if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                if 'wkb_geometry' == row[0]:
                    pass
                else:
                    sqlAlter = sql.SQL('ALTER TABLE {sch_target}.{tbl_target} RENAME COLUMN {attr} TO "wkb_geometry"').format(
                        sch_target = sql.Identifier(settings.GEOETL_DB["schema"]),
                        tbl_target = sql.Identifier(table_name_target),
                        attr = sql.Identifier(row[0])                      
                    )

                    cur.execute(sqlAlter)
                    conn.commit()
                break
                
        conn.close()
        cur.close()

    #Create en diferente servidor o bbdd
    else:
        try:
            srid, type_geom = get_type_n_srid(tab)
        except:
            type_geom = ''

        _conn_target = gdaltools.PgConnectionString(host=settings.GEOETL_DB["host"], port=settings.GEOETL_DB["port"], dbname=settings.GEOETL_DB["database"], schema=settings.GEOETL_DB["schema"], user=settings.GEOETL_DB["user"], password=settings.GEOETL_DB["password"])
        _conn_source = gdaltools.PgConnectionString(user = params["user"], password = params["password"], host = params["host"], port = params["port"], dbname = params["database"],  schema=esq)

        _ogr = gdaltools.ogr2ogr()
        _ogr.set_input(_conn_source, table_name=tab)
        _ogr.set_output(_conn_target, table_name=table_name_target)
        _ogr.set_output_mode(layer_mode=_ogr.MODE_DS_CREATE_OR_UPDATE, data_source_mode=_ogr.MODE_DS_UPDATE)

        _ogr.layer_creation_options = {
            "LAUNDER": "YES",
            "precision": "NO"
        }
        _ogr.config_options = {
            "OGR_TRUNCATE": "NO"
        }
        _ogr.set_dim("2")

        _ogr.geom_type = type_geom

        _ogr.execute()

        sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s "

        cur.execute(sql.SQL(sqlDatetype).format(),[settings.GEOETL_DB["schema"], table_name_target])
        conn.commit()

        for row in cur:
            if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                if 'wkb_geometry' == row[0]:
                    pass
                else:
                    sqlAlter = sql.SQL('ALTER TABLE {sch_target}.{tbl_target} RENAME COLUMN {attr} TO "wkb_geometry"').format(
                        sch_target = sql.Identifier(settings.GEOETL_DB["schema"]),
                        tbl_target = sql.Identifier(table_name_target),
                        attr = sql.Identifier(row[0])                      
                    )

                    cur.execute(sqlAlter)
                    conn.commit()
                break
        
        conn.close()
        cur.close()

    return [table_name_target]

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

    #sqlTypeGeom = 'SELECT ST_ASTEXT (wkb_geometry) FROM '+settings.GEOETL_DB['schema']+'."'+table_name+'" WHERE wkb_geometry IS NOT NULL LIMIT 1'
    sqlTypeGeom = "SELECT split_part (ST_ASTEXT (wkb_geometry), '(', 1)  FROM "+settings.GEOETL_DB["schema"]+'."'+table_name+'" WHERE wkb_geometry IS NOT NULL GROUP BY split_part'
    cur.execute(sqlTypeGeom)
    conn.commit()
    type_geom = ''
    for row in cur:
        if type_geom == '':
            type_geom = row[0]
        elif type_geom != row[0]:
            type_geom = 'GEOMETRY'
            break
        else:
            pass

    srid = 0
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

    if srid != 0 and type_geom != '':

        sqlDrop2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  DROP COLUMN "wkb_geometry"'
        cur.execute(sqlDrop2)
        conn.commit()

        sqlAlter2 = 'ALTER TABLE '+settings.GEOETL_DB['schema']+'."'+table_name+'"  ADD COLUMN wkb_geometry geometry('+type_geom+', '+str(srid)+')'
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
        srid1, type_geom1 = get_type_n_srid(table_name_target)
        geomTar = True
    else:
        geomTar = False

    if 'wkb_geometry' in attr_source_list:
        srid2, type_geom2 = get_type_n_srid(table_name_source)
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

    if not df_source.empty and not df_target.empty:
        merge_ = df_target.append(df_source, sort = False)
        print('Both tables to merge have features')
        
        if geomTar and geomSour:
            
            if type_geom1 != type_geom2:
                type_geom = 'GEOMETRY'

            else:
                type_geom= type_geom1

            if srid1 != srid2:
                srid = srid1
                print('Las tablas que se quieren unir tienen diferentes sistemas de referencia')
            else:
                srid = srid1
    
        elif geomTar and not geomSour:
            type_geom = type_geom1
            srid = srid1

        elif not geomTar and geomSour:
            type_geom = type_geom2
            srid = srid2

    elif df_source.empty and not df_target.empty:
        merge_ = df_target
        print('Only one table has features')
        if geomTar:
            type_geom = type_geom1
            srid = srid1
    elif not df_source.empty and df_target.empty:
        merge_ = df_source
        print('Only one table has features')
        if geomSour:
            type_geom = type_geom2
            srid = srid2
    else:
        print('No one table has features')
        merge_ = df_target
        if geomTar:
            type_geom = type_geom1
            srid = srid1
        if geomSour:
            type_geom = type_geom2
            srid = srid2

    table_name = table_name_source[15:]+';'+table_name_target[15:]

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

def trans_Intersection(dicc):

    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]

    table_name_target = dicc['id']

    merge = dicc['merge']

    schemas = dicc['schema']

    if merge == 'true':
    
        for name in schemas[0]:
            if name in schemas[1]:
                schemas[1].remove(name)
        if len(schemas[0]) != 0:
            schema_0 = 'A0."' + '", A0."'.join(schemas[0]) + '"'
        else:
            schema_0 = ""

        if len(schemas[1]) != 0:
            schema_1 = 'A1."' + '", A1."'.join(schemas[1]) + '"'
        else:
            schema_1 = ""
        
        schema = schema_0 +' , ' + schema_1

    else:
        if len(schemas) != 0:
            schema = 'A0."' + '", A0."'.join(schemas) + '"'
        else:
            schema = ""

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlInter = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select '+ schema+' st_intersection( st_makevalid(A0.wkb_geometry), st_makevalid(A1.wkb_geometry)) as wkb_geometry from '
    sqlInter += settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" AS A0, '+settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" AS A1 '
    sqlInter += 'WHERE st_intersects(A0.wkb_geometry, A1.wkb_geometry) = true)'

    cur.execute(sqlInter)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_FilterDupli(dicc):

    attr = dicc['attr']

    table_name_source = dicc['data'][0]
    table_name_target_unique = dicc['id']+'_0'
    table_name_target_dupli = dicc['id']+'_1'

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target_unique+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDrop2 = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target_dupli+'"'
    cur.execute(sqlDrop2)
    conn.commit()

    sqlAdd = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'"'+' ADD COLUMN "_id_temp" SERIAL'
    cur.execute(sqlAdd)
    conn.commit()

    if len(attr) != 0:
        attrs = '('
        
        for a in attr:
            attrs += '"'+a + '", '
        attrs = attrs[:-2]+')'
        
        sqlUn = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_unique+'" as (SELECT DISTINCT ON '+attrs+'* from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'       
        cur.execute(sqlUn)
        conn.commit()
    else:
        sqlUn = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_unique+'" as (SELECT DISTINCT * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
        cur.execute(sqlUn)
        conn.commit()
    
    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target_dupli+'" as '
    sqlDup += '( SELECT * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" as A0 WHERE A0._id_temp NOT IN '
    sqlDup += '( SELECT _id_temp FROM '+ settings.GEOETL_DB["schema"]+'."'+table_name_target_unique+'" ))'
    cur.execute(sqlDup)
    conn.commit()

    sqlDrop3 = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'" DROP COLUMN _id_temp; '
    sqlDrop3 += 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target_unique+'" DROP COLUMN _id_temp; '
    sqlDrop3 += 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target_dupli+'" DROP COLUMN _id_temp; '
    cur.execute(sqlDrop3)
    conn.commit()

    conn.close()
    cur.close()          

    return [table_name_target_unique, table_name_target_dupli]

def trans_PadAttr(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    if dicc['side'] == 'Right':
        side = 'rpad'
    else:
        side = 'lpad'

    sqlDup = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select *, '+side+'('+'CAST("'+dicc['attr']+'" AS TEXT), '+dicc['length']+", '"+dicc['string']+"'"+') from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlRemov = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN "'+ dicc['attr'] + '"'
    cur.execute(sqlRemov)
    conn.commit()

    sqlRename = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" RENAME COLUMN "'+ side + '" TO "'+dicc['attr']+'";'
    cur.execute(sqlRename)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_ExecuteSQL(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    schemaTable = dicc['tablename'].lower()

    if '.' in schemaTable:
        esq = schemaTable.split(".")[0]
        table_name = schemaTable.split(".")[1]
    else:
        esq = 'public'
        table_name = schemaTable

    query = dicc['query']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()
    cur_3 = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'create table '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    conn_2 = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
    cur_2 = conn_2.cursor()

    sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
    sqlDatetype += "where table_schema = '"+ esq+"' and table_name ='"+table_name+"'"

    cur_2.execute(sqlDatetype)
    conn_2.commit()

    attr_query = re.search('SELECT(.*)FROM', dicc['query'])
    attr_query = attr_query.group(1).replace(' ', '')
    list_attr_query = attr_query.split(',')

    f_list = []
    
    for attr in list_attr_query:
        
        if attr == '*':
            
            for col in cur_2:

                if col[1] == 'USER-DEFINED' or col[1] == 'geometry':
                    pass
                else:
                    f_list.append(col[0])
                    sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  ADD COLUMN "'+col[0]+'" '+col[1]
                    cur.execute(sqlAlter)
                    conn.commit()

        elif attr[0] =='"' and attr[-1] == '"':
            for col in cur_2:
                if col[0] == attr[1:-1]:
                    f_list.append(col[0])
                    sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  ADD COLUMN "'+col[0]+'" '+col[1]
                    cur.execute(sqlAlter)
                    conn.commit()
                    break

        elif attr[0] =='"' and attr.endswith('"AS'):

            at = attr.split('"AS')[-1]

            if at[0] =='"' and at[-1] == '"':
                att = at[1:-1]
            else:
                att = at
            
            for col in cur_2:
                if col[0] == att:
                    f_list.append(col[0])
                    sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  ADD COLUMN "'+col[0]+'" '+col[1]
                    cur.execute(sqlAlter)
                    conn.commit()
                    break

        elif ')AS' in attr:

            at = attr.split(')AS')[-1]

            #oldat = re.search('((.*))', attr)

            if at[0] =='"' and at[-1] == '"':
                att = at[1:-1]
            else:
                att = at
            f_list.append(att)
            sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  ADD COLUMN "'+att+'" TEXT'
            cur.execute(sqlAlter)
            conn.commit()
            break

        else:
            for col in cur_2:
                if col[0] == attr:
                    f_list.append(col[0])
                    sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"  ADD COLUMN "'+col[0]+'" '+col[1]
                    cur.execute(sqlAlter)
                    conn.commit()
                    break
    
    if 'WHERE' in query:

        listAttr = []
        lst = []

        #lst_subs = []
        count = 1
        for m in re.finditer('##', query):
            
            if count%2 == 0:
                lst.append(m.start())
                #lst_subs.append(m.end())
            else:
                lst.append(m.end())
                #lst_subs.append(m.start())
            if len(lst) == 2:
                listAttr.append(query[lst[0]:lst[1]])
                lst = []
            count+=1

        sqlDis = 'SELECT '+', '.join(listAttr)+' FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
        cur.execute(sqlDis)
        conn.commit()

        for row in cur:
            q = query
            for i in range (0, len(listAttr)):
                q = q.replace('##'+listAttr[i]+'##', "'"+str(row[i])+"'")

            cur_2.execute(q)
            conn_2.commit()

            for j in cur_2:
                set = ''
                for k in range (0, len(f_list)):
                    set = set + f_list[k] +" = '"+ str(j[k])+"', "
                
                where = ''
                for l in range (0, len(listAttr)):
                    where = where + listAttr[l] + ' = ' + "'"+str(row[l])+"' AND "

                sqlUpdate = 'UPDATE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" SET '+set[:-2]+" WHERE " + where[:-5]

                cur_3.execute(sqlUpdate)
                conn.commit()

    conn.close()
    cur.close()
    cur_3.close()

    conn_2.close()
    cur_2.close()

    return [table_name_target]

def trans_SpatialRel(dicc):

    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" AS (SELECT * FROM '+settings.GEOETL_DB["schema"]+'."'+table_name_source_0+'" );'
    cur.execute(sqlDup)
    conn.commit()

    sqlAlter = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" ADD COLUMN _id_temp SERIAL, ADD COLUMN _related TEXT DEFAULT ' + "'False'"
    cur.execute(sqlAlter)
    conn.commit()

    sqlUpdate = 'UPDATE '+ settings.GEOETL_DB["schema"]+'."'+table_name_target+'" SET _related ='+"'True' WHERE _id_temp IN ("
    sqlUpdate += 'SELECT main._id_temp FROM '+ settings.GEOETL_DB["schema"]+'."'+table_name_target+'" main, ' + settings.GEOETL_DB["schema"]+'."'+table_name_source_1+'" sec'
    sqlUpdate += ' WHERE '+dicc['option']+'(main.wkb_geometry, sec.wkb_geometry))'
    cur.execute(sqlUpdate)
    conn.commit()

    sqlAlter2 = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN _id_temp '
    cur.execute(sqlAlter2)
    conn.commit()


    conn.close()
    cur.close()

    return [table_name_target]

def move(name, dicc):

    if name == 'input_Excel':
        source = dicc["excel-file"]
        target = dicc["folder"]
        suffixes = (".xls", ".xlsx")

    for file in os.listdir(source):
        if file.endswith(suffixes):
            if target != '':
                shutil.move (source+'//'+file, target+'//'+file)
            else:
                os.remove(source+'//'+file)

def input_Kml(dicc):

    table_name = dicc['id'].replace('-','_')

    file = dicc['kml-kmz-file'][7:]

    if file.endswith('.kmz'):
        kmz_file = file
        path_list = kmz_file.split('/')[:-1]
        filename = kmz_file.split('/')[-1].split('.')[0]

        kmz_zip = '//'+os.path.join(*path_list, filename+'.zip')

        shutil.copy(kmz_file, kmz_zip)

        with ZipFile(kmz_zip) as zf:
            zf.extractall('//'+os.path.join(*path_list, filename))

        kml_file = '//'+os.path.join(*path_list, filename, 'doc.kml')

    elif file.endswith('.kml'):
        kml_file = file
  
    dataSource = DataSource(kml_file)
            
    layer = dataSource[0]

    epsg = str(dicc['epsg'])
    
    if epsg == '':
        try:
            epsg = layer.srs['AUTHORITY', 1]
        except:
            pass
    
    srs = "EPSG:"+str(epsg)
    schema = settings.GEOETL_DB['schema']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name+'"'
    cur.execute(sqlDrop)
    conn.commit()

    encoding = dicc['encode']
    
    _ogr = gdaltools.ogr2ogr()
    _ogr.set_encoding(encoding)
    _ogr.set_input(kml_file, srs=srs)
    _conn = gdaltools.PgConnectionString(host=settings.GEOETL_DB["host"], port=settings.GEOETL_DB["port"], dbname=settings.GEOETL_DB["database"], schema=schema, user=settings.GEOETL_DB["user"], password=settings.GEOETL_DB["password"])
    _ogr.set_output(_conn, table_name=table_name)
    _ogr.set_output_mode(layer_mode=_ogr.MODE_DS_CREATE_OR_UPDATE, data_source_mode=_ogr.MODE_DS_UPDATE)

    _ogr.layer_creation_options = {
        "LAUNDER": "YES",
        "precision": "NO"
    }
    _ogr.config_options = {
        "OGR_TRUNCATE": "NO"
    }
    _ogr.set_dim("2")
    _ogr.geom_type = "PROMOTE_TO_MULTI"
    _ogr.execute()
    
    return [table_name]

def trans_ChangeAttrType(dicc):

    attr = dicc['attr']
    data_type = dicc['data-type']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select *, "'+attr+'"::'+data_type+' as "'+attr+'_temp" from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlRemov = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN "'+ attr + '"'
    cur.execute(sqlRemov)
    conn.commit()

    sqlRename = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" RENAME COLUMN "'+attr+'_temp" TO "'+attr+'"'
    cur.execute(sqlRename)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_RemoveGeom(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = settings.GEOETL_DB["user"], password = settings.GEOETL_DB["password"], host = settings.GEOETL_DB["host"], port = settings.GEOETL_DB["port"], database = settings.GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = 'DROP TABLE IF EXISTS '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'"'
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'CREATE TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" as (select * from '+settings.GEOETL_DB["schema"]+'."'+table_name_source+'");'
    cur.execute(sqlDup)
    conn.commit()

    sqlDrop = 'ALTER TABLE '+settings.GEOETL_DB["schema"]+'."'+table_name_target+'" DROP COLUMN wkb_geometry'
    cur.execute(sqlDrop)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]