# -*- coding: utf-8 -*-

from copy import deepcopy
from gvsigol import settings
from .settings import URL_GEOCODER, GEOETL_DB

import pandas as pd
import psycopg2
from psycopg2 import sql
import json
from collections import defaultdict
#from dateutil.parser import parse
import mgrs
import gdaltools
import os, shutil, tempfile

import cx_Oracle
import pymssql
from .models import database_connections, segex_FechaFinGarantizada, cadastral_requests
import requests
import base64
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, false, true
from django.contrib.gis.gdal import DataSource
import re
from zipfile import ZipFile
import time
import math
from . import etl_schema
import xml.etree.ElementTree as ET

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


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

def get_temp_dir():
    """
    Creates a unique, temporary directory under os.path.join(settings.TEMP_ROOT, 'plugin_geoetl')
    and returns the absolute path to the temporary directory.
    The created directory is NOT automatically removed.
    """
    base_temp = os.path.join(settings.TEMP_ROOT, 'plugin_geoetl')
    if not os.path.exists(base_temp):
        os.makedirs(base_temp)
    return tempfile.mkdtemp(dir=base_temp)

#functions associated to tasks. 
#All of them receive a dictionary with the parameters for the task
#and the name of a table postgres -if task is not an input task-
#The output for each function must be the name of a table postgres/postgis in an array.
#Name must be the identifier of the task 
#Array will be as longer as outputs has the task. e.g filter has two outputs True and False
#so output array will be [idTrue, idFalse]


def getXpath(child, list_):

    parentTag = ['.']

    for x in range (0, len(list_)):
        r = list_[x]

        if r[1].strip() == child:

            if r[0].split('-')[0] == 0:
                break
            else:
                parentTag.insert(1, r[0].split('-')[1])
                child = r[0].split('-')[1]
                x = 0

    return '/'.join(parentTag)

def input_Xml(dicc):

    table_name = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name))
    cur.execute(sqlDrop)
    conn.commit()
    
    if dicc['reading'] == 'single':

        listXmlFile = [dicc['xml-file'].split('//')[1]]

    else:
        listXmlFile = []
        for file in os.listdir(dicc['xml-file']):
            if file.endswith(".xml"):
                listXmlFile.append(dicc['xml-file'] +'//'+ file)
        
    for xmlFile in listXmlFile:

        root = ET.parse(xmlFile)

        schemaList = dicc['selected-schema'].split(',')

        sqlCreate = "CREATE TABLE IF NOT EXISTS {schema}.{table_name} ("

        for s in schemaList:
            sqlCreate = sqlCreate + '{} TEXT, '

        sqlCreate = sqlCreate[:-2]+')'

        _sqlCreate = sql.SQL(sqlCreate).format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_name = sql.Identifier(table_name),
            *[sql.Identifier(field) for field in schemaList])
        cur.execute(_sqlCreate)
        conn.commit()

        child = schemaList[0]

        xpath = getXpath(child, dicc["get_tag-list"])

        for i in root.findall(xpath):
            p = [i.find(n).text for n in schemaList]

            sqlInsert = "INSERT INTO {schema}.{table_name} ("
            for s in schemaList:
                sqlInsert = sqlInsert + '{}, '

            sqlInsert = sqlInsert[:-2]+') VALUES ('

            for s in schemaList:
                sqlInsert = sqlInsert + '%s, '

            sqlInsert = sqlInsert[:-2]+')'

            _sqlInsert = sql.SQL(sqlInsert).format(
                schema = sql.Identifier(GEOETL_DB["schema"]),
                table_name = sql.Identifier(table_name),
                *[sql.Identifier(field) for field in schemaList])
            cur.execute(_sqlInsert, p)
            conn.commit()

        if dicc['other-tags'] != '':

            colAd = dicc['other-tags'].split(',')

            sqlAlter = 'ALTER TABLE {schema}.{table_name} '
            for s in colAd:
                sqlAlter = sqlAlter + 'ADD COLUMN IF NOT EXISTS {} TEXT, '

            _sqlAlter = sql.SQL(sqlAlter[:-2]).format(
                schema = sql.Identifier(GEOETL_DB["schema"]),
                table_name = sql.Identifier(table_name),
                *[sql.Identifier(field) for field in colAd])

            cur.execute(_sqlAlter, colAd)
            conn.commit()

            for col in colAd:
                xpath = getXpath(col, dicc["get_tag-list"])

                for val in root.findall(xpath+'/'+col):

                    sqlUpdate = sql.SQL('UPDATE {schema}.{table_name} SET {attr} = %s').format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        table_name = sql.Identifier(table_name),
                        attr = sql.Identifier(col))

                    cur.execute(sqlUpdate, [val.text])
                    conn.commit()

    
    return[table_name]



def input_Excel(dicc):

    import warnings

    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

    if dicc['reading'] == 'single':

        df = pd.read_excel(dicc["excel-file"], sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
        df = df.replace('\n', ' ', regex=True).replace('\r', '', regex=True).replace('\t', '', regex=True)
        df_obj = df.select_dtypes(['object'])
        df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
    
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
                    df_obj = df.select_dtypes(['object'])
                    df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
                else:
                    dfx = pd.read_excel(dicc["excel-file"]+'//'+file, sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
                    dfx = dfx.replace('\n', ' ', regex=True).replace('\r', '', regex=True).replace('\t', '', regex=True)
                    dfx['_filename'] = file
                    df_obj = dfx.select_dtypes(['object'])
                    dfx[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
                    df = df.append(dfx, sort = False)
                x += 1

    table_name = dicc['id']

    conn_string = 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
  
    db = create_engine(conn_string)
    conn = db.connect()

    df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)

    conn.close()
    db.dispose()
    
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
    schema = GEOETL_DB['schema']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name))
    cur.execute(sqlDrop)
    conn.commit()

    encoding = dicc['encode']
    
    _ogr = gdaltools.ogr2ogr()
    _ogr.set_encoding(encoding)
    _ogr.set_input(shp, srs=srs)
    _conn = gdaltools.PgConnectionString(host=GEOETL_DB["host"], port=GEOETL_DB["port"], dbname=GEOETL_DB["database"], schema=schema, user=GEOETL_DB["user"], password=GEOETL_DB["password"])
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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlRemov = 'ALTER TABLE {}.{}'

    for attr in attrList:
        sqlRemov += ' DROP COLUMN {},'

    cur.execute(sql.SQL(sqlRemov[:-1]).format(
        sql.Identifier(GEOETL_DB["schema"]),
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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDatetype = 'SELECT column_name from information_schema.columns '
    sqlDatetype += 'where table_schema = %s and table_name = %s '
    cur.execute(sql.SQL(sqlDatetype).format(
    ),[GEOETL_DB["schema"], table_name_source])
    conn.commit()
    
    for row in cur:
        if row[0] == 'wkb_geometry':
            attrList.append('wkb_geometry')
            break

    sqlDup = 'create table {schema}.{tbl_target} as (select '

    for attr in attrList:
        sqlDup += ' {} ,'

    sqlDup = sqlDup[:-1]+' from {schema}.{tbl_source})'

    cur.execute(sql.SQL(sqlDup).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlRename_ = 'ALTER TABLE {}.{}'

    for x in range (0, len(oldAttr)):
        sqlRename = sqlRename_ + ' RENAME COLUMN {} TO {};'
        cur.execute(sql.SQL(sqlRename).format(
        sql.Identifier(GEOETL_DB["schema"]),
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

    onAttr =[]

    on =''
    for pos in range (0, len(attr1)):
        onAttr.append(attr1[pos])
        onAttr.append(attr2[pos])
        on += 'A0.{}::TEXT = A1.{}::TEXT AND '

    on = on[:-5]

    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]

    table_name_target_join = dicc['id']+'_0'
    table_name_target_0_not_used = dicc['id']+'_1'
    table_name_target_1_not_used = dicc['id']+'_2'

    output = [table_name_target_join, table_name_target_0_not_used, table_name_target_1_not_used]

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    schemas =[]

    for table_name in dicc['data']:
        sqlDatetype = 'SELECT column_name from information_schema.columns '
        sqlDatetype += 'where table_schema = %s and table_name = %s '
        cur.execute(sql.SQL(sqlDatetype).format(
        ),[GEOETL_DB["schema"], table_name])
        conn.commit()

        sc =[]
        for row in cur:
            sc.append(row[0])
        schemas.append(sc)

    schemaList =[]
    schema = ''

    for name in schemas[0]:
        schemaList.append(name)
        if schema == '':
            schema = 'A0.{}'
        else:
            schema = schema + ', A0.{}'

    for name in schemas[1]:
        if name not in schemaList:
            schemaList.append(name)
            schema = schema + ', A1.{}'

    for out in output:

        sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(GEOETL_DB["schema"]),
            sql.Identifier(out))
        
        cur.execute(sqlDrop)
        conn.commit()

    sqlJoin_ = 'create table {sch}.{tbl_join} as (select '+schema +' from {sch}.{tbl_source_0} AS A0 INNER JOIN {sch}.{tbl_source_1} AS A1 ON '+ on + ');'

    sqlJoin = sql.SQL(sqlJoin_).format(
            sch = sql.Identifier(GEOETL_DB["schema"]),
            tbl_join = sql.Identifier(table_name_target_join),
            *[sql.Identifier(field) for field in schemaList],
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1),
            *[sql.Identifier(field) for field in onAttr],
        )

    cur.execute(sqlJoin)
    conn.commit()

    sqlNotJoin1_ = 'create table {sch}.{tbl_not_0} as (select A0.* from {sch}.{tbl_source_0} AS A0 LEFT OUTER JOIN {sch}.{tbl_source_1} AS A1 ON '+on + ' WHERE A1.{attr} IS NULL)'

    sqlNotJoin1 = sql.SQL(sqlNotJoin1_).format(
            sch = sql.Identifier(GEOETL_DB["schema"]),
            tbl_not_0 = sql.Identifier(table_name_target_0_not_used),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1),
            *[sql.Identifier(field) for field in onAttr],
            attr = sql.Identifier(schemas[1][0])
        )
    
    cur.execute(sqlNotJoin1)
    conn.commit()

    sqlNotJoin2_ = 'create table {sch}.{tbl_not_1} as (select A1.* from {sch}.{tbl_source_0} AS A0 RIGHT OUTER JOIN {sch}.{tbl_source_1} AS A1 ON '+on + ' WHERE A0.{attr} IS NULL)'

    sqlNotJoin2 = sql.SQL(sqlNotJoin2_).format(
            sch = sql.Identifier(GEOETL_DB["schema"]),
            tbl_not_1 = sql.Identifier(table_name_target_1_not_used),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1),
            *[sql.Identifier(field) for field in onAttr],
            attr = sql.Identifier(schemas[0][0])
        )

    cur.execute(sqlNotJoin2)
    conn.commit()

    return output

def trans_ModifyValue(dicc):
    
    attr = dicc['attr']
    
    value = dicc['value']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlUpdate = sql.SQL('UPDATE {}.{} SET {} = %s').format(
        sql.Identifier(GEOETL_DB["schema"]),
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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )

    cur.execute(sqlDup)
    conn.commit()

    if value != '':
        sqlSET = ' DEFAULT %s'
    else:
        sqlSET = ''

    sqlAdd = sql.SQL('ALTER TABLE {}.{} ADD COLUMN {} {}').format(
            sql.Identifier(GEOETL_DB["schema"]),
            sql.Identifier(table_name_target),
            sql.Identifier(attr),
            sql.SQL(data_type+sqlSET)
        )

    if value != '':
        cur.execute(sqlAdd,[value])
    else:
        cur.execute(sqlAdd)
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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_passed))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_failed))
    cur.execute(sqlDrop)
    conn.commit()

    if expression == "":

        sqlDatetype = 'SELECT  data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s and column_name = %s "
        
        cur.execute(sql.SQL(sqlDatetype).format(),[GEOETL_DB["schema"],table_name_source, attr])
        conn.commit()

        data_type = ''
        toVar = ''

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
            pass
        elif operator == 'LIKE':
            toVar = "::varchar"

        sqlFilPassed = 'create table {schema}.{tbl_passed} as (select * from {schema}.{tbl_source} WHERE {attr}{tovar} {oper} %s)'
        
        sqlFilPassed_ = sql.SQL(sqlFilPassed).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_passed = sql.Identifier(table_name_target_passed),
                    tbl_source = sql.Identifier(table_name_source),
                    attr = sql.Identifier(attr),
                    tovar = sql.SQL(toVar),
                    oper = sql.SQL(operator))
        
        cur.execute(sqlFilPassed_,[value])
        conn.commit()

        sqlFilFailed = 'create table {schema}.{tbl_failed} as (select * from {schema}.{tbl_source} WHERE NOT {attr}{tovar} {oper} %s)'

        sqlFilFailed_ = sql.SQL(sqlFilFailed).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_failed = sql.Identifier(table_name_target_failed),
                    tbl_source = sql.Identifier(table_name_source),
                    attr = sql.Identifier(attr),
                    tovar = sql.SQL(toVar),
                    oper = sql.SQL(operator))

        cur.execute(sqlFilFailed_,[value])
        conn.commit()

        conn.close()
        cur.close()

    else:

        sqlFilPassed = 'create table {schema}.{tbl_passed} as (select * from {schema}.{tbl_source} WHERE ( {expres} ))'
        
        sqlFilPassed_ = sql.SQL(sqlFilPassed).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_passed = sql.Identifier(table_name_target_passed),
                    tbl_source = sql.Identifier(table_name_source),
                    expres = sql.SQL(expression))

        
        cur.execute(sqlFilPassed_)
        conn.commit()

        sqlFilFailed = 'create table {schema}.{tbl_failed} as (select * from {schema}.{tbl_source} WHERE NOT ( {expres} ))'

        sqlFilFailed_ = sql.SQL(sqlFilFailed).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_failed = sql.Identifier(table_name_target_failed),
                    tbl_source = sql.Identifier(table_name_source),
                    expres = sql.SQL(expression))

        cur.execute(sqlFilFailed_)
        conn.commit()

        conn.close()
        cur.close()


    return [table_name_target_passed, table_name_target_failed]


def isInSamedb(params):

    if (GEOETL_DB['host'] == params['host'] and 
        str(GEOETL_DB["port"]) == str(params['port']) and 
        GEOETL_DB["database"] == params['database'] and
        GEOETL_DB["user"] == params['user'] and
        GEOETL_DB["password"] == params['password']):
        
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

    con_source = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = con_source.cursor()
    cur_2 = con_source.cursor()

    sqlCount = sql.SQL("SELECT COUNT(*) FROM {sch_source}.{tbl_source}").format(
            sch_source = sql.Identifier(GEOETL_DB["schema"]),
            tbl_source = sql.Identifier(table_name_source))
    
    cur.execute(sqlCount)
    con_source.commit()
    for row in cur:
        count = row[0]
        break

    if count == 0 and dicc['operation'] != 'CREATE' and dicc['operation'] != 'OVERWRITE':
        print('There is no features in output')

    else:

        if dicc['operation'] == 'CREATE':

            if inSame:

                if count != 0:
                
                    sqlCreate = sql.SQL('create table {sch_target}.{tbl_target} as (select * from {sch_source}.{tbl_source})').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                        sch_source = sql.Identifier(GEOETL_DB["schema"]),
                        tbl_source = sql.Identifier(table_name_source))
                    
                    cur.execute(sqlCreate)
                    con_source.commit()
                else:
                    sqlCreate = sql.SQL('create table IF NOT EXISTS {sch_target}.{tbl_target} as (select * from {sch_source}.{tbl_source})').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                        sch_source = sql.Identifier(GEOETL_DB["schema"]),
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

                try:

                    sqlIndex = sql.SQL('CREATE INDEX "{tbl}_wkb_geometry_geom_idx" on {sch_target}.{tbl_target} USING gist (wkb_geometry);').format(
                        tbl = sql.SQL(tab),
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab))
                    
                    cur.execute(sqlIndex)
                    con_source.commit()

                except:
                    
                    print("No se ha podido crear el índice espacial")

                con_source.close()
                cur.close()

            #Create en diferente servidor o bbdd
            else:
                try:
                    srid, type_geom = get_type_n_srid(table_name_source)
                except:
                    type_geom = ''

                _conn_source = gdaltools.PgConnectionString(host=GEOETL_DB["host"], port=GEOETL_DB["port"], dbname=GEOETL_DB["database"], schema=GEOETL_DB["schema"], user=GEOETL_DB["user"], password=GEOETL_DB["password"])
                _conn_target = gdaltools.PgConnectionString(user = params["user"], password = params["password"], host = params["host"], port = params["port"], dbname = params["database"],  schema=esq)

                _ogr = gdaltools.ogr2ogr()
                _ogr.set_input(_conn_source, table_name=table_name_source)
                _ogr.set_output(_conn_target, table_name=tab)

                if count == 0:
                    _ogr.set_output_mode(layer_mode=_ogr.MODE_LAYER_APPEND, data_source_mode=_ogr.MODE_DS_UPDATE)
                else:
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

        elif dicc['operation'] == 'APPEND' or dicc['operation'] == 'OVERWRITE':

            if inSame:

                if dicc['operation'] == 'OVERWRITE':

                    sqlTruncate = sql.SQL('TRUNCATE TABLE {sch_target}.{tbl_target} ').format(
                            sch_target = sql.Identifier(esq),
                            tbl_target = sql.Identifier(tab)
                            )
                    cur.execute(sqlTruncate)
                    con_source.commit()

                sqlDatetype = 'SELECT column_name from information_schema.columns '
                sqlDatetype += "where table_schema = %s and table_name = %s "

                cur.execute(sql.SQL(sqlDatetype).format(),[GEOETL_DB["schema"], table_name_source])
                con_source.commit()

                attr_source = '('

                attrSourceList = []
                attrTargetList = []


                for row in cur:
                    attr_source = attr_source + ' {}, '
                    attrSourceList.append(row[0])
                    
                    if 'wkb_geometry' == row[0]:

                        sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
                        sqlDatetype += "where table_schema = %s and table_name = %s "

                        cur_2.execute(sql.SQL(sqlDatetype).format(),[esq, tab])
                        #con_source.commit()

                        for r in cur_2:
                            if  r[1] == 'USER-DEFINED' or r[1] == 'geometry':
                                if 'wkb_geometry' == r[0]:
                                    attrTargetList.append(row[0])
                                else:
                                    attrTargetList.append(r[0])
                                break

                    else:
                        attrTargetList.append(row[0])
                
                attr_source = attr_source[:-2] + ')'

                cur_2.close()

                sqlInsert_ = 'INSERT INTO {sch_target}.{tbl_target} {attrs_target} SELECT {attrs_source} FROM {sch_source}.{tbl_source} '
                
                sqlInsert = sql.SQL(sqlInsert_).format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                        attrs_source = sql.SQL(attr_source[1:-1]).format(
                            *[sql.Identifier(field) for field in attrSourceList],
                        ),
                        attrs_target = sql.SQL(attr_source).format(
                            *[sql.Identifier(field) for field in attrTargetList],
                        ),
                        sch_source = sql.Identifier(GEOETL_DB["schema"]),
                        tbl_source = sql.Identifier(table_name_source)
                        )

                cur.execute(sqlInsert)
                con_source.commit()

                con_source.close()
                cur.close()
                

            #insert en diferente servidor o bddd
            else:

                try:
                    srid, type_geom = get_type_n_srid(table_name_source)
                except:
                    type_geom = ''

                _conn_source = gdaltools.PgConnectionString(host=GEOETL_DB["host"], port=GEOETL_DB["port"], dbname=GEOETL_DB["database"], schema=GEOETL_DB["schema"], user=GEOETL_DB["user"], password=GEOETL_DB["password"])
                _conn_target = gdaltools.PgConnectionString(user = params["user"], password = params["password"], host = params["host"], port = params["port"], dbname = params["database"],  schema=esq)
                _ogr = gdaltools.ogr2ogr()
                _ogr.set_input(_conn_source, table_name=table_name_source)
                _ogr.set_output(_conn_target, table_name=tab)

                if dicc['operation'] == 'OVERWRITE':
                    _ogr.set_output_mode(layer_mode=_ogr.MODE_LAYER_OVERWRITE, data_source_mode=_ogr.MODE_DS_UPDATE)
                    _ogr.config_options = {
                        "OGR_TRUNCATE": "YES"
                    }
                else:
                    _ogr.set_output_mode(layer_mode=_ogr.MODE_LAYER_APPEND, data_source_mode=_ogr.MODE_DS_UPDATE)
                    _ogr.config_options = {
                        "OGR_TRUNCATE": "NO"
                    }

                _ogr.layer_creation_options = {
                    "LAUNDER": "YES",
                    "precision": "NO"
                }

                _ogr.set_dim("2")
                _ogr.geom_type = type_geom
                _ogr.execute()

        elif dicc['operation'] == 'UPDATE':
           
            sqlDatetype = 'SELECT column_name from information_schema.columns '
            sqlDatetype += "where table_schema = %s and table_name = %s "

            cur.execute(sql.SQL(sqlDatetype).format(),[GEOETL_DB["schema"], table_name_source])
            con_source.commit()

            attr_source = []

            geometry = False

            for row in cur:
                attr_source.append(row[0])
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
                                attr_target = row[0]
                            break
                else:

                    cur_2.execute(sql.SQL(sqlDatetype).format(),[esq, tab])
                    con_target.commit()

                    for row in cur_2:
                        if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                            if 'wkb_geometry' == row[0]:
                                attr_target = 'wkb_geometry'
                            else:
                                attr_target = row[0]
                            break


            cur.execute(sql.SQL('SELECT * FROM {sch_source}.{tbl_source}').format(
                sch_source = sql.Identifier(GEOETL_DB["schema"]),
                tbl_source = sql.Identifier(table_name_source)
            ))

            con_source.commit()

            for row in cur:
                attrs_update ='UPDATE {sch_target}.{tbl_target} SET '
                attrList =[]
                valueList =[]

                for i in range (0, len(attr_source)):
                    if dicc['match'] == attr_source[i]:
                        value = row[i]
                        
                    elif attr_source[i] == 'wkb_geometry':
                        attrList.append(attr_target)
                        valueList.append(row[i])
                        attrs_update = attrs_update + '{} = %s, '
                        
                    else:
                        attrList.append(attr_source[i])
                        valueList.append(row[i])
                        attrs_update = attrs_update + '{} = %s, '

                valueList.append(value)
                attrs_update = attrs_update[:-2] + ' WHERE {match} = %s'

                sqlUpdate = sql.SQL(attrs_update).format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                        *[sql.Identifier(field) for field in attrList],
                        match = sql.Identifier(dicc['match'])
                        
                    )

                cur_2.execute(sqlUpdate,valueList)

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

            cur.execute(sql.SQL(sqlDatetype).format(),[GEOETL_DB["schema"], table_name_source])
            con_source.commit()

            attr_source = []

            geometry = False

            for row in cur:
                attr_source.append(row[0])
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
                            attr_target = row[0]
                        break

            cur.execute(sql.SQL('SELECT * FROM {sch_source}.{tbl_source}').format(
                sch_source = sql.Identifier(GEOETL_DB["schema"]),
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
                    if dicc['match'] == attr_source[i]:
                        value = row[i]

                sqlDelete = sql.SQL('DELETE FROM {sch_target}.{tbl_target} WHERE {match} = %s').format(
                        sch_target = sql.Identifier(esq),
                        tbl_target = sql.Identifier(tab),
                        match = sql.Identifier(dicc['match'])
                    )

                cur_2.execute(sqlDelete,[value])

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

    skiprows = 0

    first = True

    counter = 10000

    while counter == 10000:

        df = pd.read_csv(dicc["csv-file"], sep=dicc["separator"], encoding='utf8', skiprows=skiprows, nrows=10000)

        counter = df.shape[0]

        table_name = dicc['id']

        conn_string = 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
    
        db = create_engine(conn_string)
        conn = db.connect()

        if first:

            column_names = df.columns

            df_obj = df.select_dtypes(['object'])
            df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))

            df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
            first = False
            
        else:

            df.columns = column_names

            df_obj = df.select_dtypes(['object'])
            df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))

            df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='append', index=False)

        skiprows += 10000


        conn.close()
        db.dispose()
        
    return [table_name]

def trans_Reproject(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    sourceepsg = str(dicc['source-epsg'])
    targetepsg = str(dicc['target-epsg'])

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source))
    cur.execute(sqlDup)
    conn.commit()

    try:
        srid, type_geom = get_type_n_srid(table_name_source)
    except:
        type_geom = ''

    if sourceepsg == '':
        pass
    else:
        sqlAlter_ = 'ALTER TABLE {schema}.{tbl_target} ALTER COLUMN wkb_geometry TYPE geometry({type_geom},{epsg}) USING ST_SetSRID(wkb_geometry, {epsg})'
        sqlAlter = sql.SQL(sqlAlter_).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(table_name_target),
                    type_geom = sql.SQL(type_geom),
                    epsg = sql.SQL(sourceepsg))
      
        cur.execute(sqlAlter)
        conn.commit()

    sqlTransf_ = 'ALTER TABLE {schema}.{tbl_target} ALTER COLUMN wkb_geometry TYPE geometry({type_geom},{epsg}) USING ST_Transform(wkb_geometry, {epsg})'
    
    sqlTransf = sql.SQL(sqlTransf_).format(
                schema = sql.Identifier(GEOETL_DB["schema"]),
                tbl_target = sql.Identifier(table_name_target),
                type_geom = sql.SQL(type_geom),
                epsg = sql.SQL(targetepsg))

    cur.execute(sqlTransf)
    conn.commit()
    
    return[table_name_target]

def trans_Counter(dicc):

    attr = dicc['attr']
    
    gbAttr= dicc['group-by-attr']
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    if gbAttr == '':

        sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            tbl_source = sql.Identifier(table_name_source))
        cur.execute(sqlDup)
        conn.commit()

        sqlAdd_ = 'ALTER TABLE {schema}.{tbl_target} ADD COLUMN {attr} SERIAL; '  
        sqlAdd = sql.SQL(sqlAdd_).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(table_name_target),
                    attr = sql.Identifier(attr))

        cur.execute(sqlAdd)
        conn.commit()
    else:
        sqlDup = 'create table {schema}.{tbl_target} as (select *, row_number() OVER (PARTITION BY {attr}) from {schema}.{tbl_source}  ORDER BY {attr});'

        cur.execute(sql.SQL(sqlDup).format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            tbl_source = sql.Identifier(table_name_source),
            attr = sql.Identifier(gbAttr)
        ))
        conn.commit()
        
        sqlRename = 'ALTER TABLE {schema}.{tbl_target} RENAME COLUMN "row_number" TO {attr};'

        cur.execute(sql.SQL(sqlRename).format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source))
    cur.execute(sqlDup)
    conn.commit()

    sqlCount = sql.SQL('SELECT count(*) FROM {}.{}').format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target)) 
    cur.execute(sqlCount)

    run = False
    for row in cur:
        if row[0] != 0:
            run = True

    if run:
        sqlInsert = sql.SQL('UPDATE {schema}.{tbl_target} SET {attr} = {expres} ').format(
                schema = sql.Identifier(GEOETL_DB["schema"]),
                tbl_target = sql.Identifier(table_name_target),
                attr = sql.Identifier(attr),
                expres = sql.SQL(expression))
             

        cur.execute(sqlInsert)
        conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_CadastralGeom(dicc):

    from gvsigol_plugin_catastro.views import get_rc_polygon
    
    attr = dicc['attr']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()
    cur2 = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()


    # Definición de la columna de texto
    refcat_column = sql.Identifier("refcat")
    text_column = sql.SQL("{} TEXT").format(refcat_column)

    # Definición de la columna de geometría multipolígono
    geom_column = sql.Identifier("wkb_geometry")
    geometry_column = sql.SQL("{} GEOMETRY(MULTIPOLYGON, 4326)").format(geom_column)

    # Crear la tabla
    create_table_query = sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({});").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier("geometriacatastral"),
        sql.SQL(', ').join([text_column, geometry_column])
    )

    # Ejecutar la consulta para crear la tabla
    cur.execute(create_table_query)
    conn.commit()


    sqlJoin_ = 'create table {sch}.{tbl_target} as (select A0.*, A1.wkb_geometry from {sch}.{tbl_source} AS A0 LEFT JOIN {sch}."geometriacatastral" AS A1 ON A0.{attr} = A1."refcat");'

    sqlJoin = sql.SQL(sqlJoin_).format(
        sch = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source),
        attr = sql.Identifier(attr))
        
    cur.execute(sqlJoin)
    conn.commit()    


    sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_target} ADD COLUMN "_id_temp" SERIAL; ').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target)
    )

    cur.execute(sqlAdd)
    conn.commit()

    sqlSel = sql.SQL('SELECT {attr}, "_id_temp" FROM {schema}.{tbl_target} WHERE wkb_geometry is NULL').format(
        attr = sql.Identifier(attr),
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target)
    )
    cur.execute(sqlSel)
    
    for row in cur:

        try:
            cr_model  = cadastral_requests.objects.get(name = 'cadastral_requests')
            cadastral_requests_count = cr_model.requests

        except:
            
            cr_model = cadastral_requests(
                name = 'cadastral_requests',
                requests = 0,
            )
            cr_model.save()

            cadastral_requests_count = 0

        if cadastral_requests_count < 3600:
            
            try:

                cadastral_requests_count += 1

                cr_model.requests = cadastral_requests_count
                cr_model.lastRequest = datetime.now()
                cr_model.save()
                
                features = get_rc_polygon(row[0].replace(' ', ''))
                
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
            
                sqlUpdate = sql.SQL('UPDATE {schema}.{tbl_target} SET wkb_geometry = ST_SetSRID(ST_GeomFromGeoJSON( %s), %s) WHERE "_id_temp" = %s').format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        tbl_target = sql.Identifier(table_name_target)
                    )
                
                cur2.execute(sqlUpdate,[str(json.dumps(i["geometry"])), srs, str(row[1])])
                conn.commit()
        
                insert = True

                sqlSelDup = sql.SQL('SELECT count(*) FROM {schema}.geometriacatastral WHERE refcat = %s').format(
                        schema = sql.Identifier(GEOETL_DB["schema"])
                    )

                cur2.execute(sqlSelDup, [row[0]])
                conn.commit()

                for d in cur2:
                    print(d)
                    if int(d[0]) > 0:
                        insert = False

                if insert:
                    
                    sqlInsert = sql.SQL('INSERT INTO {schema}.geometriacatastral(refcat, wkb_geometry) VALUES (%s, ST_SetSRID(ST_GeomFromGeoJSON( %s), %s))').format(
                            schema = sql.Identifier(GEOETL_DB["schema"])
                        )
                    
                    cur2.execute(sqlInsert, [row[0], str(json.dumps(i["geometry"])), srs])
                    conn.commit()
            
            
            except Exception as e:
                print(str(e))

        else:

            dif = 3600.0 - (datetime.now() - (cr_model.lastRequest).replace(tzinfo=None)).total_seconds()
            print("Take a coffee. The maximum number of requests to cadastre has been reached. The process will continue in "+str(dif/60)+" minutes.")

            time.sleep(dif)
            cr_model.requests = 0
            cr_model.lastRequest = datetime.now()
            cr_model.save()
    
    sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN _id_temp;').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target)
    )

    cur.execute(sqlDropCol)
    conn.commit()

    conn.close()
    cur.close()
    cur2.close()

    return [table_name_target]

def trans_MGRS(dicc):
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()
    cur_2 = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source});').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source))
    cur.execute(sqlDup)
    conn.commit()
    
    select = dicc['select']

    m = mgrs.MGRS()
    
    if select == 'mgrstolatlon':
        grid = dicc['mgrs']

        sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_target} ADD COLUMN _lat FLOAT DEFAULT NULL, ADD COLUMN _lon FLOAT DEFAULT NULL').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target))
        
        cur.execute(sqlAdd)
        conn.commit()

        sqlSelect = sql.SQL('SELECT {grid} FROM {schema}.{tbl_target}').format(
            grid = sql.Identifier(grid),
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target)
        )
        cur.execute(sqlSelect)
        conn.commit()
        
        for row in cur:
            try:
                lat, lon = m.toLatLon(row[0].replace(" ", ""))

                sqlUpdate = sql.SQL('UPDATE {schema}.{tbl_target}  SET _lat = %s, _lon = %s WHERE {grid} = %s ').format(
                    grid = sql.Identifier(grid),
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(table_name_target)
                )
                cur_2.execute(sqlUpdate,[lat, lon, row[0]])
                conn.commit()

            except Exception as e:
                logger.error('GRID: '+row[0] + ' ERROR: '+ str(e))
                print('GRID: '+row[0] + ' ERROR: '+ str(e))

    else:
        lat = dicc['lat']
        lon = dicc['lon']

        sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_target} ADD COLUMN _grid TEXT DEFAULT NULL').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target))

        cur.execute(sqlAdd)
        conn.commit()

        sqlSelect = sql.SQL('SELECT {lat}, {lon} FROM {schema}.{tbl_target}').format(
            lat = sql.Identifier(lat),
            lon = sql.Identifier(lon),
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target))

        cur.execute(sqlSelect)
        conn.commit()
        
        for row in cur:
            try:
                grid = m.toMGRS(row[0], row[1])

                sqlUpdate = sql.SQL('UPDATE {schema}.{tbl_target} SET _grid = %s WHERE {lat} = %s AND {lon} = %s ').format(
                    lat = sql.Identifier(lat),
                    lon = sql.Identifier(lon),
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(table_name_target))
                
                cur_2.execute(sqlUpdate,[grid, row[0], row[1]])
                conn.commit()

            except Exception as e:
                logger.error("latitud: "+str(row[0])+" longitud: "+ str(row[1])+" ERROR: "+ str(e))
                print("latitud: "+str(row[0])+" longitud: "+ str(row[1])+" ERROR: "+ str(e))

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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('CREATE TABLE {schema}.{tbl_target} AS (SELECT *, ST_SetSRID(ST_MakePoint({lon}::float, {lat}::float), {epsg}) AS wkb_geometry FROM {schema}.{tbl_source} );').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source),
        lon = sql.Identifier(lon),
        lat = sql.Identifier(lat),
        epsg = sql.SQL(epsg)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_name} ALTER COLUMN wkb_geometry TYPE Geometry(Point, {srid})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_name = sql.Identifier(table_name_target),
        srid = sql.SQL(str(epsg))
    )

    cur.execute(sqlAlter)
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

    conn_string_target= 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
    db_target = create_engine(conn_string_target)
    conn_target = db_target.connect()

    df.to_sql(table_name, con=conn_target, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
    
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
        df_obj = df_tar.select_dtypes(['object'])
        df_tar[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))

        if count == 1:
            df_tar.to_sql(table_name, con=conn_target, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
            count +=1
        else:
            df_tar.to_sql(table_name, con=conn_target, schema= GEOETL_DB['schema'], if_exists='append', index=False)


    conn_target.close()
    db_target.dispose()

    return [table_name]

def trans_WktGeom(dicc):
    
    attr = dicc['attr']
    epsg = dicc['epsg']
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    if epsg =='':
        sqlDup = sql.SQL('create table {schema}.{tbl_target}  as (SELECT *, ST_GeomFromText({attr}) as wkb_geometry  FROM {schema}.{tbl_source});').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            attr = sql.Identifier(attr),
            tbl_source = sql.Identifier(table_name_source))

        cur.execute(sqlDup)
        conn.commit()
    else:
        sqlDup = sql.SQL('create table {schema}.{tbl_target}  as (SELECT *, ST_SetSRID ( ST_GeomFromText({attr}), {epsg} ) as wkb_geometry  FROM {schema}.{tbl_source});').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            attr = sql.Identifier(attr),
            epsg = sql.SQL(epsg),
            tbl_source = sql.Identifier(table_name_source))

        cur.execute(sqlDup)
        conn.commit()

        srid, type_geom = get_type_n_srid(table_name_target)

        sqlSet = sql.SQL('ALTER TABLE {schema}.{tbl_target}  ALTER COLUMN wkb_geometry TYPE geometry({type}, {epsg}) USING ST_SetSRID(wkb_geometry,{epsg});').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            type = sql.Identifier(type_geom),
            epsg = sql.SQL(epsg))
        
        cur.execute(sqlSet)
        conn.commit()

    sqlRemov = sql.SQL('ALTER TABLE {schema}.{tbl_target}  DROP COLUMN {attr}').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(attr))

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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select *, string_to_array({attr}, %s) as {list} from {schema}.{tbl_source});').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(attr),
        list = sql.SQL(_list),
        tbl_source = sql.Identifier(table_name_source))
    
    cur.execute(sqlDup, [_split])
    conn.commit()

    sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN {attr}; ').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(attr),
    )
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
    
    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlCreate = sql.SQL('CREATE TABLE {schema}.{tbl_target} as (SELECT * FROM {schema}.{tbl_source}); TRUNCATE TABLE {schema}.{tbl_target}').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source))

    cur.execute(sqlCreate)
    conn.commit()

    sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_target} ADD COLUMN "_id_temp" SERIAL, ADD COLUMN {attr} TEXT').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(attr)
    )
    cur.execute(sqlAdd)
    conn.commit()

    sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_source} ADD COLUMN "_id_temp" SERIAL;').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_source = sql.Identifier(table_name_source))
    cur.execute(sqlAdd)
    conn.commit()

    sqlSel = sql.SQL('SELECT {list}, _id_temp FROM {schema}.{tbl_source};').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        list = sql.Identifier(list_name),
        tbl_source = sql.Identifier(table_name_source))       
    
    cur.execute(sqlSel)
    
    for row in cur:
        cur2 = conn.cursor()
        try:
            _len = len(row[0])
        except:
            _len = 0
        for i in range (0, _len):
            sqlInsert = sql.SQL('INSERT INTO {schema}.{tbl_target}  SELECT *, %s FROM {schema}.{tbl_source} WHERE "_id_temp" = %s').format(
                schema = sql.Identifier(GEOETL_DB["schema"]),
                tbl_target = sql.Identifier(table_name_target),
                tbl_source = sql.Identifier(table_name_source))
                
            cur2.execute(sqlInsert,[row[0][i],row[1]])
            conn.commit()
        cur2.close()

    sqlDropCol = 'ALTER TABLE {schema}.{tbl_target}  DROP COLUMN _id_temp, DROP COLUMN {list}; '
    sqlDropCol += 'ALTER TABLE {schema}.{tbl_source} DROP COLUMN _id_temp; '
    cur.execute(sql.SQL(sqlDropCol).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source),
        list = sql.Identifier(list_name)
    ))
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
    st_multi_end = ''

    if multi == 'true':
        st_multi_start = 'ST_Multi('
        st_multi_end = ')'

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlIndex = sql.SQL('CREATE INDEX IF NOT EXISTS "{table_source}_wkb_geometry_geom_idx" on {schema}."{table_source}" USING gist (wkb_geometry);').format(
        table_source = sql.SQL(table_name_source),
        schema = sql.Identifier(GEOETL_DB["schema"]))
    
    cur.execute(sqlIndex)
    conn.commit()

    if groupby == '':
        sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select ST_Union(wkb_geometry) as wkb_geometry from {schema}.{tbl_source});').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            tbl_source = sql.Identifier(table_name_source))

        cur.execute(sqlDup)
        conn.commit()
    else:
        sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select {groupby}, {start} ST_Union(wkb_geometry) {end} as wkb_geometry from {schema}.{tbl_source} GROUP BY {groupby});').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            tbl_source = sql.Identifier(table_name_source),
            groupby = sql.Identifier(groupby),
            start = sql.SQL(st_multi_start),
            end = sql.SQL(st_multi_end))

        cur.execute(sqlDup)
        conn.commit()

    if multi == 'true':
        srid, type_geom = get_type_n_srid(table_name_source)

        if type_geom.startswith('MULTI'):
            pass
        else:
            type_geom = 'MULTI'+type_geom

        sqlAlter_ = 'ALTER TABLE {schema}.{tbl_target} ALTER COLUMN wkb_geometry TYPE geometry({type_geom},{epsg}) USING ST_SetSRID(wkb_geometry, {epsg})'
        sqlAlter = sql.SQL(sqlAlter_).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(table_name_target),
                    type_geom = sql.SQL(type_geom),
                    epsg = sql.SQL(str(srid)))
        
        cur.execute(sqlAlter)
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

    conn_string = 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
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
                    df_obj = df.select_dtypes(['object'])
                    df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))

                    if first:
                        df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
                        first = False
                    else:
                        df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='append', index=False)

    return[table_name]


def input_Postgis(dicc):

    table_name_target= dicc['id'].replace('-','_')

    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)

    esq = dicc['schema-name']
    tab = dicc['tablename']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    inSame = isInSamedb(params)
    
    if inSame:

        if dicc['checkbox'] == 'true':
            where_clause = 'WHERE ' + dicc['clause']
        else:
            where_clause = ''
    
        sqlCreate = sql.SQL('create table {sch_target}.{tbl_target} as (select * from {sch_source}.{tbl_source} {where_clause})').format(
            sch_target = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            sch_source = sql.Identifier(esq),
            tbl_source = sql.Identifier(tab),
            where_clause = sql.SQL(where_clause))
        
        cur.execute(sqlCreate)
        conn.commit()

        sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s "

        cur.execute(sql.SQL(sqlDatetype).format(),[GEOETL_DB["schema"], table_name_target])
        conn.commit()

        for row in cur:
            if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                if 'wkb_geometry' == row[0]:
                    pass
                else:
                    sqlAlter = sql.SQL('ALTER TABLE {sch_target}.{tbl_target} RENAME COLUMN {attr} TO "wkb_geometry"').format(
                        sch_target = sql.Identifier(GEOETL_DB["schema"]),
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

        conn_2 = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
        cur_2 = conn_2.cursor()
    
        sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s "

        cur_2.execute(sql.SQL(sqlDatetype).format(),[esq, tab])
        conn_2.commit()

        geometry = ''
        for r in cur_2:
            if  r[1] == 'USER-DEFINED' or r[1] == 'geometry':
                geometry = r[0]
                break
        type_geom = ''
        
        if geometry != '':

            srid, type_geom = get_type_n_srid(tab, esq, geometry, params)


        if dicc['checkbox'] == 'true':
            where_clause = 'WHERE ' + dicc['clause']
            _sql = sql.SQL('select * from {sch_source}.{tbl_source} {where_clause}').format(
                sch_source = sql.Identifier(esq),
                tbl_source = sql.Identifier(tab),
                where_clause = sql.SQL(where_clause))
        else:
            where_clause = ''

        _conn_source = gdaltools.PgConnectionString(user = params["user"], password = params["password"], host = params["host"], port = params["port"], dbname = params["database"],  schema=esq)
        _conn_target = gdaltools.PgConnectionString(host=GEOETL_DB["host"], port=GEOETL_DB["port"], dbname=GEOETL_DB["database"], schema=GEOETL_DB["schema"], user=GEOETL_DB["user"], password=GEOETL_DB["password"])

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


        if dicc['checkbox'] == 'true':

            _ogr.set_sql(_sql.as_string(conn))

        _ogr.geom_type = type_geom

        _ogr.execute()

        conn_2.close()
        cur_2.close()

        sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s "

        cur.execute(sql.SQL(sqlDatetype).format(),[GEOETL_DB["schema"], table_name_target])
        conn.commit()

        for row in cur:
            if  row[1] == 'USER-DEFINED' or row[1] == 'geometry':
                if 'wkb_geometry' == row[0]:
                    pass
                else:
                    sqlAlter = sql.SQL('ALTER TABLE {sch_target}.{tbl_target} RENAME COLUMN {attr} TO "wkb_geometry"').format(
                        sch_target = sql.Identifier(GEOETL_DB["schema"]),
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

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    for out in output:
        sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(GEOETL_DB["schema"]),
            sql.Identifier(out))
        cur.execute(sqlDrop)
        conn.commit()

    sqlEquals = sql.SQL('CREATE TABLE {schema}.{tbl_target_equals} as (SELECT * FROM {schema}.{tbl_source}); TRUNCATE TABLE {schema}.{tbl_target_equals}').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target_equals = sql.Identifier(table_name_target_equals),
            tbl_source = sql.Identifier(table_name_source_0))
    
    cur.execute(sqlEquals)
    conn.commit()

    sqlNew = sql.SQL('create table {schema}.{tbl_target_news} as (select A0.* from {schema}.{tbl_source_0} AS A0 LEFT OUTER JOIN {schema}.{tbl_source_1} AS A1 ON A0.{attr} = A1.{attr} WHERE A1.{attr} IS NULL );').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target_news = sql.Identifier(table_name_target_news),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1),
            attr = sql.Identifier(attr))

    cur.execute(sqlNew)
    conn.commit()

    sqlNotJoin2 = sql.SQL('create table {schema}.{tbl_target_1_not_used} as (select A1.* from {schema}.{tbl_source_0} AS A0 RIGHT OUTER JOIN {schema}.{tbl_source_1} AS A1 ON A0.{attr} = A1.{attr} WHERE A0.{attr} IS NULL );').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target_1_not_used = sql.Identifier(table_name_target_1_not_used),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            tbl_source_1 = sql.Identifier(table_name_source_1),
            attr = sql.Identifier(attr))

    cur.execute(sqlNotJoin2)
    conn.commit()

    sqlChanges = sql.SQL('CREATE TABLE {schema}.{tbl_target_changes} as (SELECT * FROM {schema}.{tbl_source_0}); TRUNCATE TABLE {schema}.{tbl_target_changes}').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target_changes = sql.Identifier(table_name_target_changes),
            tbl_source_0 = sql.Identifier(table_name_source_0))

    cur.execute(sqlChanges)
    conn.commit()

    sqlSelect0 = sql.SQL('SELECT {attr}, * FROM {schema}.{tbl_source_0}').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_source_0 = sql.Identifier(table_name_source_0),
            attr = sql.Identifier(attr))

    cur.execute(sqlSelect0)
    
    for row in cur:
        cur2 = conn.cursor()
        sqlSelect1 = sql.SQL('SELECT {attr}, * FROM {schema}.{tbl_source_1} WHERE {attr} = %s ').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_source_1 = sql.Identifier(table_name_source_1),
            attr = sql.Identifier(attr))

        cur2.execute(sqlSelect1,[row[0]])
        
        for row2 in cur2:
            if row == row2:
                sqlInsert = sql.SQL('INSERT INTO {schema}.{tbl_target_equals} SELECT * FROM {schema}.{tbl_source_0} WHERE {attr} = %s ').format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target_equals = sql.Identifier(table_name_target_equals),
                    tbl_source_0 = sql.Identifier(table_name_source_0),
                    attr = sql.Identifier(attr))
                    
                cur2.execute(sqlInsert,[row[0]])
                conn.commit()
            else:
                sqlInsert = sql.SQL('INSERT INTO {schema}.{tbl_target_changes} SELECT * FROM {schema}.{tbl_source_0} WHERE {attr} = %s ').format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target_changes = sql.Identifier(table_name_target_changes),
                    tbl_source_0 = sql.Identifier(table_name_source_0),
                    attr = sql.Identifier(attr))

                cur2.execute(sqlInsert,[row[0]])
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
    
    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    for out in output:

        sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(GEOETL_DB["schema"]),
            sql.Identifier(out))

        cur.execute(sqlDrop)
        conn.commit()

    typeGeom = ['POINT%', 'MULTIPOINT%', 'LINESTRING%', 'MULTILINESTRING%', 'POLYGON%', 'MULTIPOLYGON%']

    for i in range (0, len(typeGeom)):
        
        sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source} WHERE ST_ASTEXT(wkb_geometry) LIKE %s );').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(output[i]),
            tbl_source = sql.Identifier(table_name_source)
        )
        cur.execute(sqlDup,[typeGeom[i]])
        conn.commit()

        srid, tg = get_type_n_srid(table_name_source)

        sqlAlter_ = 'ALTER TABLE {schema}.{tbl_target} ALTER COLUMN wkb_geometry TYPE geometry({type_geom},{epsg}) USING ST_SetSRID(wkb_geometry, {epsg})'
        sqlAlter = sql.SQL(sqlAlter_).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    tbl_target = sql.Identifier(output[i]),
                    type_geom = sql.SQL(typeGeom[i][:-1]),
                    epsg = sql.SQL(str(srid)))
        
        cur.execute(sqlAlter)
        conn.commit()

    conn.close()
    cur.close()

    return output

def trans_CalcArea(dicc):
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    attr = dicc['attr']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select *, ST_Area(wkb_geometry) as {attr}  from {schema}.{tbl_source} );').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            tbl_source = sql.Identifier(table_name_source),
            attr = sql.Identifier(attr))
            
    cur.execute(sqlDup)
    conn.commit()

    conn.close()
    cur.close()

    return[table_name_target]

def trans_CurrentDate(dicc):
    
    attr = dicc['attr']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    if dicc['checkbox'] == 'true':
        sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_target} ADD COLUMN {attr} TIMESTAMP; UPDATE {schema}.{tbl_target} SET {attr} = CURRENT_TIMESTAMP;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            attr = sql.Identifier(attr)
        )
    else:

        sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_target} ADD COLUMN {attr} DATE; UPDATE {schema}.{tbl_target} SET {attr} = CURRENT_DATE;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            attr = sql.Identifier(attr)
        )
    cur.execute(sqlAdd)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_ExplodeGeom(dicc):
    
    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('create table {schema}.{tbl_target} as (select *, (st_dump(wkb_geometry)).geom from {schema}.{tbl_source});').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN wkb_geometry;').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target)
    )
    cur.execute(sqlDropCol)
    conn.commit()

    sqlRename = sql.SQL('ALTER TABLE {schema}.{tbl_target} RENAME COLUMN geom TO wkb_geometry;').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target)
    )
    cur.execute(sqlRename)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]


def get_type_n_srid(table_name, schema = GEOETL_DB["schema"], geom = 'wkb_geometry', params = None):

    if not params:

        conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    else:
        conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])

    
    cur = conn.cursor()

    #sqlTypeGeom = 'SELECT ST_ASTEXT (wkb_geometry) FROM '+GEOETL_DB['schema']+'."'+table_name+'" WHERE wkb_geometry IS NOT NULL LIMIT 1'
    sqlTypeGeom = sql.SQL("SELECT type, srid FROM geometry_columns WHERE f_table_schema = %s AND f_table_name = %s and f_geometry_column = %s").format()
    
    cur.execute(sqlTypeGeom, [schema, table_name, geom])
    conn.commit()

    type_geom = ''
    srid = 0
    for row in cur:
        type_geom = row[0]
        srid = row[1]

    conn.close()
    cur.close()

    print(srid, type_geom)

    return srid, type_geom

def merge_tables(_list):
    
    table_name_source = _list[-1]
    table_name_target = _list[-2]

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    attr_target_list = list(pd.read_sql(sql.SQL('SELECT * FROM {schema}.{table}').format(schema = sql.Identifier(GEOETL_DB['schema']), table = sql.Identifier(table_name_target)), con = conn).columns)
    attr_source_list = list(pd.read_sql(sql.SQL('SELECT * FROM {schema}.{table}').format(schema = sql.Identifier(GEOETL_DB['schema']), table = sql.Identifier(table_name_source)), con = conn).columns)
    
    attr_select = deepcopy(attr_target_list)

    for attr in attr_source_list:
        if attr not in attr_select:
            attr_select.append(attr)

    attr_select_target =[]
    attr_select_source =[]

    attr_select_par =''

    for attr in attr_select:

        attr_select_par += '{}, '        

        if attr in attr_target_list:
            attr_select_target.append(sql.Identifier(attr))
        else:
            attr_select_target.append(sql.SQL('NULL AS {}').format(sql.Identifier(attr)))

        if attr in attr_source_list:
            attr_select_source.append(sql.Identifier(attr))
        else:
            attr_select_source.append(sql.SQL('NULL AS {}').format(sql.Identifier(attr)))

    table_name = table_name_source[15:]+';'+table_name_target[15:]

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name))
    cur.execute(sqlDrop)
    conn.commit()

    sql_ = 'create table {schema}.{tbl_name} as (select '+ attr_select_par[:-2] +' FROM {schema}.{tbl_target} UNION'
    sql_ += ' select '+ attr_select_par[:-2] +' FROM {schema}.{tbl_source})'
    
    sqlDup = sql.SQL(sql_).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_name = sql.Identifier(table_name[:60]),
        *[ex for ex in attr_select_target],
        tbl_target = sql.Identifier(table_name_target),
        *[ex for ex in attr_select_source],
        tbl_source = sql.Identifier(table_name_source)
    )

    cur.execute(sqlDup)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name[:60]]

def trans_ConcatAttr(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    separator = dicc['separator']

    new_attr = dicc['new-attr']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = 'CREATE TABLE {schema}.{tbl_target} as (select *, concat_ws(%s, '

    for at in dicc['attr']:
        sqlDup += '{}, '

    sqlDup = sqlDup[:-2]+') as {new_attr} from {schema}.{tbl_source});'
    
    sqlDup_ = sql.SQL(sqlDup).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source),
        *[sql.Identifier(attr) for attr in dicc['attr']],
        new_attr = sql.Identifier(new_attr)
    )
    
    cur.execute(sqlDup_,[separator])
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_Intersection(dicc):

    table_name_source_0 = dicc['data'][0]

    table_name_target = dicc['id']

    merge = dicc['merge']

    self_int = dicc['self-intersect']

    schemas = dicc['schema']

    schema = ''
    attrs =[]

    if merge == 'true':
    
        for name in schemas[0]:
            if name in schemas[1]:
                schemas[1].remove(name)
        
        for attr in schemas[0]:
            schema += 'A0.{},'
            attrs.append(attr)

        for attr in schemas[1]:
            schema += 'A1.{},'
            attrs.append(attr)

    else:
        for attr in schemas[0]:
            schema += 'A0.{},'
            attrs.append(attr)

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()


    sqlIndex1 = sql.SQL('CREATE INDEX IF NOT EXISTS "{table_source_0}_wkb_geometry_geom_idx" on {schema}."{table_source_0}" USING gist (wkb_geometry);').format(
        table_source_0 = sql.SQL(table_name_source_0),
        schema = sql.Identifier(GEOETL_DB["schema"]))
    
    cur.execute(sqlIndex1)
    conn.commit()

    if self_int == '':

        table_name_source_1 = dicc['data'][1]

        sqlIndex2 = sql.SQL('CREATE INDEX IF NOT EXISTS "{table_source_1}_wkb_geometry_geom_idx" on {schema}."{table_source_1}" USING gist (wkb_geometry);').format(
            table_source_1 = sql.SQL(table_name_source_1),
            schema = sql.Identifier(GEOETL_DB["schema"]))
        
        cur.execute(sqlIndex2)
        conn.commit()

        sqlInter = 'create table {schema}.{table_target} as (select '+ schema[:-1] + ', st_intersection( st_makevalid(A0.wkb_geometry), st_makevalid(A1.wkb_geometry)) as wkb_geometry from '
        sqlInter += '{schema}.{table_source_0} AS A0, {schema}.{table_source_1}  AS A1 '
        sqlInter += 'WHERE st_intersects(st_makevalid(A0.wkb_geometry), st_makevalid(A1.wkb_geometry)) = true)'

    
        sql_ = sql.SQL(sqlInter).format(
            schema =  sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target),
            *[sql.Identifier(field) for field in attrs],
            table_source_0 = sql.Identifier(table_name_source_0),
            table_source_1 = sql.Identifier(table_name_source_1)
        )

        cur.execute(sql_)
        conn.commit()
    else:
        sqlAdd = sql.SQL('ALTER TABLE {schema}.{table_source} ADD COLUMN "_id_temp" SERIAL').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_source = sql.Identifier(table_name_source_0))
        
        cur.execute(sqlAdd)
        conn.commit()


        sqlInter = 'create table {schema}.{table_target} as (select '+ schema[:-1] + ', A0._id_temp, A1._id_temp AS _id_temp_2, st_intersection( st_makevalid(A0.wkb_geometry), st_makevalid(A1.wkb_geometry)) as wkb_geometry from '
        sqlInter += '{schema}.{table_source_0} AS A0, {schema}.{table_source_0}  AS A1 '
        sqlInter += 'WHERE st_intersects(st_makevalid(A0.wkb_geometry), st_makevalid(A1.wkb_geometry)) = true AND A0._id_temp < A1._id_temp)'

        sql_ = sql.SQL(sqlInter).format(
            schema =  sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target),
            *[sql.Identifier(field) for field in attrs],
            table_source_0 = sql.Identifier(table_name_source_0),
        )

        cur.execute(sql_)
        conn.commit()

        sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN _id_temp, DROP COLUMN _id_temp_2;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target))

        cur.execute(sqlDropCol)
        conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_FilterDupli(dicc):

    attr = dicc['attr']

    table_name_source = dicc['data'][0]
    table_name_target_unique = dicc['id']+'_0'
    table_name_target_dupli = dicc['id']+'_1'

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_unique))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDrop2 = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_dupli))
    cur.execute(sqlDrop2)
    conn.commit()

    sqlAdd = sql.SQL('ALTER TABLE {schema}.{table_source} ADD COLUMN "_id_temp" SERIAL').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_source = sql.Identifier(table_name_source))
    
    cur.execute(sqlAdd)
    conn.commit()

    if len(attr) != 0:
        attrs = '('
        
        for a in attr:
            attrs += '{}, '
        attrs = attrs[:-2]+')'
        
        sqlUn = sql.SQL('create table {schema}.{table_unique} as (SELECT DISTINCT ON '+attrs+'* from {schema}.{table_source});').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_unique = sql.Identifier(table_name_target_unique),
            *[sql.Identifier(field) for field in attr],
            table_source = sql.Identifier(table_name_source))
          
        cur.execute(sqlUn)
        conn.commit()
    else:
        sqlUn = sql.SQL('create table {schema}.{table_unique} as (SELECT DISTINCT * from {schema}.{table_source});').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_unique = sql.Identifier(table_name_target_unique),
            table_source = sql.Identifier(table_name_source))
        cur.execute(sqlUn)
        conn.commit()
    
    sqlDup = 'create table {schema}.{table_dup}  as '
    sqlDup += '( SELECT * FROM {schema}.{table_source} as A0 WHERE A0._id_temp NOT IN '
    sqlDup += '( SELECT _id_temp FROM {schema}.{table_unique} ))'
    cur.execute(sql.SQL(sqlDup).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_dup = sql.Identifier(table_name_target_dupli),
        table_source = sql.Identifier(table_name_source),
        table_unique = sql.Identifier(table_name_target_unique)
    ))
    conn.commit()

    sqlDrop3 = 'ALTER TABLE {schema}.{table_source} DROP COLUMN _id_temp; '
    sqlDrop3 += 'ALTER TABLE {schema}.{table_unique} DROP COLUMN _id_temp; '
    sqlDrop3 += 'ALTER TABLE {schema}.{table_dup} DROP COLUMN _id_temp; '

    cur.execute(sql.SQL(sqlDrop3).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_dup = sql.Identifier(table_name_target_dupli),
        table_source = sql.Identifier(table_name_source),
        table_unique = sql.Identifier(table_name_target_unique)
    ))
    conn.commit()

    conn.close()
    cur.close()          

    return [table_name_target_unique, table_name_target_dupli]

def trans_PadAttr(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    if dicc['side-option'] == 'Right':
        side = 'rpad'
    else:
        side = 'lpad'

    sqlDup = sql.SQL('CREATE TABLE {schema}.{table_target} as (select *, {side}('+'CAST({attr} AS TEXT), %s, %s) from {schema}.{table_source});').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        side = sql.SQL(side),
        attr = sql.Identifier(dicc['attr']),
        table_source = sql.Identifier(table_name_source)
    )
    
    cur.execute(sqlDup,[dicc['length'], dicc['string']])
    conn.commit()

    sqlRemov = sql.SQL('ALTER TABLE {schema}.{table_target} DROP COLUMN {attr}').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(dicc['attr'])
    )
    cur.execute(sqlRemov)
    conn.commit()

    sqlRename = sql.SQL('ALTER TABLE {schema}.{table_target} RENAME COLUMN {side} TO {attr};').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        side = sql.Identifier(side),
        attr = sql.Identifier(dicc['attr'])
    )
    cur.execute(sqlRename)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_ExecuteSQL(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']
    
    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)

    query = dicc['query']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()
    cur_3 = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('CREATE TABLE {schema}.{table_target} AS (SELECT * FROM {schema}.{table_source} );').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        table_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    if db.type == 'PostgreSQL':

        esq = dicc['schema-name']
        table_name = dicc['tablename']

        conn_2 = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
        cur_2 = conn_2.cursor()

        sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
        sqlDatetype += "where table_schema = %s and table_name = %s"

        cur_2.execute(sql.SQL(sqlDatetype),[esq, table_name])
        conn_2.commit()

        attr_query = re.search('SELECT(.*)FROM', dicc['query'])
        attr_query = attr_query.group(1).replace(' ', '')
        list_attr_query = attr_query.split(',')

    elif db.type == 'Oracle':
        conn_2 = cx_Oracle.connect(
            params['username'],
            params['password'],
            params['dsn']
        )

        c = conn_2.cursor()

        sql_ = 'SELECT '

        attr_query = re.search('SELECT(.*)FROM', dicc['query'])
        attr_query = attr_query.group(1).replace(' ', '')
        list_attr_query = attr_query.split(',')

        for a in list_attr_query:
            sql_ = sql_ + 'DUMP('+a+'),'

        from_query = re.search('FROM(.*)WHERE', dicc['query'])
        from_query = from_query.group(1)

        sql_ = sql_[:-1]+' FROM '+from_query
        
        c.execute(sql_)

        cur_2 = []

        null = True
        first = True

        for row in c:
            
            if null:
                null = False
                for i in range (0, len(list_attr_query)):
                    
                    if first:
                    
                        typ = row[i].split(' ')[0]

                        if typ == 'Typ=1':

                            cur_2.insert(i, [list_attr_query[i], 'VARCHAR'])
                        elif typ == 'Typ=2':

                            cur_2.insert(i, [list_attr_query[i], 'INTEGER'])

                        elif typ == 'Typ=12':
                            cur_2.insert(i, [list_attr_query[i], 'DATE'])

                        else:
                            cur_2.insert(i, [list_attr_query[i], 'NULL'])
                            null = True

                    elif cur_2[i][1] == 'NULL':
                        
                        typ = row[i].split(' ')[0]

                        if typ == 'Typ=1':

                            cur_2[i] = [list_attr_query[i], 'VARCHAR']
                        elif typ == 'Typ=2':

                            cur_2[i] = [list_attr_query[i], 'INTEGER']

                        elif typ == 'Typ=12':
                            cur_2[i] = [list_attr_query[i], 'DATE']
                        else:
                            cur_2[i] = [list_attr_query[i], 'NULL']
                            null = True

                first = False

            else:
                break

    f_list = []
    
    for attr in list_attr_query:
        
        if attr == '*':
            
            for col in cur_2:

                if col[1] == 'USER-DEFINED' or col[1] == 'geometry':
                    pass
                else:
                    f_list.append(col[0])
                    sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_target}  ADD COLUMN {atrib} {type}').format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        table_target = sql.Identifier(table_name_target),
                        atrib = sql.Identifier(col[0]),
                        type = sql.SQL(col[1])
                    )
                    cur.execute(sqlAlter)
                    conn.commit()

        elif attr[0] =='"' and attr[-1] == '"':
            for col in cur_2:
                if col[0] == attr[1:-1]:
                    f_list.append(col[0])
                    sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_target}  ADD COLUMN {atrib} {type}').format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        table_target = sql.Identifier(table_name_target),
                        atrib = sql.Identifier(col[0]),
                        type = sql.SQL(col[1])
                    )                    
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
                    sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_target}  ADD COLUMN {atrib} {type}').format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        table_target = sql.Identifier(table_name_target),
                        atrib = sql.Identifier(col[0]),
                        type = sql.SQL(col[1])
                    )
                    cur.execute(sqlAlter)
                    conn.commit()
                    break

        elif ')AS' in attr:

            at = attr.split(')AS')[-1]

            if at[0] =='"' and at[-1] == '"':
                att = at[1:-1]
            else:
                att = at
            f_list.append(att)
            #sqlAlter = 'ALTER TABLE '+GEOETL_DB["schema"]+'."'+table_name_target+'"  ADD COLUMN "'+att+'" TEXT'
            sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_target}  ADD COLUMN {atrib} TEXT').format(
                schema = sql.Identifier(GEOETL_DB["schema"]),
                table_target = sql.Identifier(table_name_target),
                atrib = sql.Identifier(att)
            )
            cur.execute(sqlAlter)
            conn.commit()
            break

        else:
            for col in cur_2:
                if col[0] == attr:
                    f_list.append(col[0])
                    sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_target}  ADD COLUMN {atrib} {type}').format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        table_target = sql.Identifier(table_name_target),
                        atrib = sql.Identifier(col[0]),
                        type = sql.SQL(col[1])
                    )
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

        endlistAttr = []   
        sqlDis = 'SELECT '
        for item in listAttr:
            if item[0] == '"' and item[-1] == '"':
                endlistAttr.append(item[1:-1])
            else:
                endlistAttr.append(item)
            sqlDis += '{}, '

        sqlDis = sqlDis[:-2]+' FROM {schema}.{table_target}'
        sql_ = sql.SQL(sqlDis).format(
            *[sql.Identifier(field) for field in endlistAttr],
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target),
        )

        cur.execute(sql_)
        conn.commit()

        for row in cur:
            q = query
            for i in range (0, len(listAttr)):
                q = q.replace('##'+listAttr[i]+'##', "'"+str(row[i])+"'")

            if db.type == 'Oracle':

                cur_2 = c.execute(q)

            elif db.type == 'PostgreSQL':

                cur_2.execute(q)

            set_attr = []
            set_value = []

            sqlUpdate = 'UPDATE {schema}.{table_target} SET '

            where = ' WHERE '

            for j in cur_2:
                for k in range (0, len(f_list)):
                    set_attr.append(f_list[k])
                    set_value.append(str(j[k]))
                    sqlUpdate += "{} = %s, "
                
                where_attr = []
                where_value = []
                
                for l in range (0, len(listAttr)):
                    where_attr.append(listAttr[l])
                    where_value.append(str(row[l]))
                    where = where + ' {} = %s AND '

                sqlUpdate = sqlUpdate[:-2] + where[:-5]
                _sql_ = sql.SQL(sqlUpdate).format(
                    schema = sql.Identifier(GEOETL_DB["schema"]),
                    table_target = sql.Identifier(table_name_target),
                    *[sql.Identifier(field) for field in set_attr],
                    *[sql.Identifier(field) for field in where_attr],
                )
                
                joined_list = set_value + where_value
                cur_3.execute(_sql_, joined_list)
                conn.commit()

    conn.close()
    cur.close()
    cur_3.close()

    if db.type == 'Oracle':

        cur_2.close()

    elif db.type == 'PostgreSQL':

        conn_2.close()
        cur_2.close()

    return [table_name_target]

def trans_SpatialRel(dicc):

    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('CREATE TABLE {schema}.{table_target} AS (SELECT * FROM {schema}.{table_source_0} );').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        table_source_0 = sql.Identifier(table_name_source_0)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlAlter = sql.SQL("ALTER TABLE {schema}.{table_target} ADD COLUMN _id_temp SERIAL, ADD COLUMN _related TEXT DEFAULT 'False' ").format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target)
    )
    cur.execute(sqlAlter)
    conn.commit()

    sqlIndex1 = sql.SQL('CREATE INDEX IF NOT EXISTS "{tbl_target}_wkb_geometry_geom_idx" on {schema}."{tbl_target}" USING gist (wkb_geometry);').format(
        tbl_target = sql.SQL(table_name_target),
        schema = sql.Identifier(GEOETL_DB["schema"]))
    
    cur.execute(sqlIndex1)
    conn.commit()

    sqlIndex2 = sql.SQL('CREATE INDEX IF NOT EXISTS "{table_source_1}_wkb_geometry_geom_idx" on {schema}."{table_source_1}" USING gist (wkb_geometry);').format(
        table_source_1 = sql.SQL(table_name_source_1),
        schema = sql.Identifier(GEOETL_DB["schema"]))
    
    cur.execute(sqlIndex2)
    conn.commit()

    sqlUpdate = 'UPDATE  {schema}.{table_target}  SET _related ='+"'True' WHERE _id_temp IN ("
    sqlUpdate += 'SELECT main._id_temp FROM  {schema}.{table_target}  main, {schema}.{table_source_1} sec'
    sqlUpdate += ' WHERE {option}(st_makevalid(main.wkb_geometry), st_makevalid(sec.wkb_geometry)))'
    
    cur.execute(sql.SQL(sqlUpdate).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        table_source_1 = sql.Identifier(table_name_source_1),
        option = sql.SQL(dicc['option'])
    ))
    conn.commit()

    sqlAlter2 = sql.SQL('ALTER TABLE {schema}.{table_target} DROP COLUMN _id_temp ').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target))
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

    elif name == 'input_Kml':
        source= dicc['kml-kmz-file'][7:]
        target = dicc["folder"]
        suffixes = (".kml", ".kmz")

    elif name == 'input_Xml':
        source= dicc['xml-file']
        target = dicc["folder"]
        suffixes = (".xml")

    if os.path.isdir(source):

        for file in os.listdir(source):
            if file.endswith(suffixes):
                if target != '':
                    shutil.move (source+'/'+file, target+'/'+file)
                else:
                    os.remove(source+'/'+file)

    elif os.path.isfile(source):

        if target != '':
            shutil.move (source, target+'/'+source.split('/')[-1])
        else:
            os.remove(source)

def input_Kml(dicc):
    table_name = dicc['id'].replace('-','_')

    file = dicc['kml-kmz-file'][7:]

    if file.endswith('.kmz'):
        kmz_file = file

        filename = kmz_file.split('/')[-1].split('.')[0]

        temp_dir = get_temp_dir()
        kmz_zip = '/'+os.path.join(temp_dir, filename+'.zip')

        shutil.copy(kmz_file, kmz_zip)

        with ZipFile(kmz_zip) as zf:
            zf.extractall('/'+os.path.join(temp_dir, filename))

        kml_file = '/'+os.path.join(temp_dir, filename, 'doc.kml')

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
    schema = GEOETL_DB['schema']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name))
    cur.execute(sqlDrop)
    conn.commit()

    encoding = dicc['encode']
    
    _ogr = gdaltools.ogr2ogr()
    _ogr.set_encoding(encoding)
    _ogr.set_input(kml_file, srs=srs)
    _conn = gdaltools.PgConnectionString(host=GEOETL_DB["host"], port=GEOETL_DB["port"], dbname=GEOETL_DB["database"], schema=schema, user=GEOETL_DB["user"], password=GEOETL_DB["password"])
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

    srid, type_geom = get_type_n_srid(table_name)

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_name} ALTER COLUMN wkb_geometry TYPE Geometry({type_geom}, {srid})').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_name = sql.Identifier(table_name),
        type_geom = sql.SQL(type_geom),
        srid = sql.SQL(str(srid))
    )

    cur.execute(sqlAlter)
    conn.commit()

    conn.close()
    cur.close()

    if file.endswith('.kmz'):
        
        shutil.rmtree(temp_dir)
    
    return [table_name]

def trans_ChangeAttrType(dicc):

    attr = dicc['attr']
    data_type = dicc['data-type-option']

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target)
        )
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('CREATE TABLE {schema}.{table_target} as (select *, {attr}::{data_type} as {attr_temp} from {schema}.{table_source});').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(attr),
        data_type = sql.SQL(data_type),
        attr_temp = sql.Identifier('attr_temp'),
        table_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlRemov = sql.SQL('ALTER TABLE {schema}.{table_target} DROP COLUMN {attr}').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(attr)
    )
    cur.execute(sqlRemov)
    conn.commit()

    sqlRename = sql.SQL('ALTER TABLE {schema}.{table_target} RENAME COLUMN {attr_temp} TO {attr}').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        attr = sql.Identifier(attr),
        attr_temp = sql.Identifier('attr_temp')
    )
    cur.execute(sqlRename)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_RemoveGeom(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL('DROP TABLE IF EXISTS {schema}.{table_target}').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target)
        )
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('CREATE TABLE {schema}.{table_target} as (select * from {schema}.{table_source});').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        table_source = sql.Identifier(table_name_source)
        )
    cur.execute(sqlDup)
    conn.commit()

    sqlDrop = sql.SQL('ALTER TABLE {schema}.{table_target} DROP COLUMN wkb_geometry').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target)
        )
    cur.execute(sqlDrop)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def trans_Geocoder(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    conn_2 = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur_2 = conn_2.cursor()

    sqlDrop = sql.SQL('DROP TABLE IF EXISTS {schema}.{table_target}').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target)
        )
    cur.execute(sqlDrop)
    conn.commit()

    sqlDup = sql.SQL('CREATE TABLE {schema}.{table_target} as (select * from {schema}.{table_source});').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        table_source = sql.Identifier(table_name_source)
        )
    cur.execute(sqlDup)
    conn.commit()

    engine = dicc["engine-option"]

    mode = dicc["mode-option"]

    if mode == 'direct':
        attrs = dicc["attr-selected"].split(' ')

        sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_target}  ADD COLUMN IF NOT EXISTS "_X" FLOAT, ADD COLUMN IF NOT EXISTS "_Y" FLOAT, ADD COLUMN IF NOT EXISTS _id_temp SERIAL').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target)
        )
        cur.execute(sqlAlter)
        conn.commit()

        _sql = 'SELECT _id_temp,'
        for i in attrs:
            _sql+= '{},'
        _sql = _sql[:-1] + ' FROM {schema}.{table_target}'

        sqlSel = sql.SQL(_sql).format(
            *[sql.Identifier(field) for field in attrs],
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target)
        )
        cur.execute(sqlSel)
        conn.commit()

        sqlUpdate = sql.SQL('UPDATE {schema}.{table_target}  SET "_X" = %s, "_Y" = %s WHERE _id_temp = %s').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target)
        )

        for row in cur:

            address_list = []
            for x in range (1, len(row)):
                if row[x]:
                    address_list.append(str(row[x]))
            address = ' '.join(address_list)
            
            if engine == 'ICV':
                
                r = requests.get(URL_GEOCODER['icv-direct'] % address)

                try:
                    result = json.loads(r.content.decode('utf-8')[1:-1])['results'][0]['relacionespacial']

                    if result.startswith('POINT'):
                        coord = result[result.find("(")+1:result.find(")")].split(' ')

                        cur_2.execute(sqlUpdate,[coord[0], coord[1],row[0]])
                        conn_2.commit()
                except Exception as e:
                    print(e)

            #En este else entran todos los motores de búsqueda del plugin_geocoding que estén configurados
            else:

                try:

                    from gvsigol_plugin_geocoding.geocoder import Geocoder

                    geocoder = Geocoder()

                    result = geocoder.geocoding_direct_from_etl(address, engine)

                    if engine != 'generic':

                        cur_2.execute(sqlUpdate,[result['address']['lng'], result['address']['lat'], row[0]])
                        conn_2.commit()
                    else:
                        cur_2.execute(sqlUpdate,[result['address'][0]['lng'], result['address'][0]['lat'], row[0]])
                        conn_2.commit()

                except Exception as e:
                    print(e)

    else:

        _x = dicc["x"]
        _y = dicc["y"]

        sqlAlter = sql.SQL('ALTER TABLE {schema}.{table_target}  ADD COLUMN IF NOT EXISTS "_ADDRESS" TEXT, ADD COLUMN IF NOT EXISTS _id_temp SERIAL').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target)
        )
        cur.execute(sqlAlter)
        conn.commit()

        sqlSel = sql.SQL('SELECT _id_temp, {x}, {y} FROM {schema}.{table_target}').format(
            x = sql.Identifier(_x),
            y = sql.Identifier(_y),
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target)
        )
        cur.execute(sqlSel)
        conn.commit()

        sqlUpdate = sql.SQL('UPDATE {schema}.{table_target}  SET "_ADDRESS" = %s WHERE _id_temp = %s').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            table_target = sql.Identifier(table_name_target)
        )

        for row in cur:

            if engine == 'ICV':
                r = requests.get(URL_GEOCODER['icv-reverse'] % (row[1], row[2]))
                
                try:
                    result = json.loads(r.content.decode('utf-8'))
                    address = str(result['dtipo_vial'])+' '+str(result['nombre'])+', '+str(result['dtipo_porpk'])+' '+str(result['numero'])+', '+str(result['municipio'])

                    cur_2.execute(sqlUpdate,[address, row[0]])
                    conn_2.commit()
                except Exception as e:
                    print(e)

            #En este else entran todos los motores de búsqueda del plugin_geocoding que estén configurados
            else:

                try:
                    from gvsigol_plugin_geocoding.geocoder import Geocoder

                    geocoder = Geocoder()

                    result = geocoder.geocoding_reverse_from_etl(row[1], row[2], engine)

                    if 'cartociudad' in engine:
                        address = str(result['tip_via'])+' '+str(result['address'])+', '+str(result['portalNumber'])+', '+str(result['muni'])

                    else:
                        address = result['address']
                    
                    cur_2.execute(sqlUpdate,[address, row[0]])
                    conn_2.commit()
                except Exception as e:
                    print(e)

    sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN _id_temp;').format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target)
    )

    cur.execute(sqlDropCol)
    conn.commit()

    conn_2.close()
    cur_2.close()    
    
    conn.close()
    cur.close()

    return [table_name_target]


def input_Segex(dicc):

    entity = dicc['entities-list'][0]

    types_list = dicc['types-list']

    types_text_list = dicc['get_types-list']

    schema = dicc['schema']

    if dicc['domain'] == 'PRE':
        url = 'https://pre-%s.sedipualba.es/apisegex/' % (entity)
    else:
        url = 'https://%s.sedipualba.es/apisegex/' % (entity)

    wsSegUser = dicc['user']

    conn_string = 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
    db = create_engine(conn_string)
    conn = db.connect()

    first = True

    table_name = dicc['id']

    tpt = 0

    for tp in types_list:

        offset = 0

        if tp != 'all':

            while offset%100 == 0:

                wsSegPass = etl_schema.getwsSegPass(dicc['password'])
                
                listGeoref = 'Georef/ListGeorefs?wsSegUser=%s&wsSegPass=%s&idEntidad=%s&idTipo=%s&offset=%s' % (wsSegUser, wsSegPass, entity, tp, offset)
                
                if dicc['date-segex'] == 'check-init-date':
                    
                    if dicc['init-segex'] == 'init':
                    
                        ts_now = datetime.now()

                        subs_ts = ts_now - timedelta(minutes = int(dicc['minute-before']))

                        ts_init = subs_ts.strftime('%Y-%m-%d %H:%M:%S')

                    elif dicc['init-segex'] == 'init-guaranteed':

                        segexModel  = segex_FechaFinGarantizada.objects.get(entity = dicc['entities-list'][1], type = tp)
                        ts_init = segexModel.fechafingarantizada.strftime('%Y-%m-%d %H:%M:%S')

                    else:
                        ts = datetime.strptime(dicc['init-date'], '%Y-%m-%dT%H:%M')

                        ts_init = ts.strftime('%Y-%m-%d %H:%M:%S')

                    listGeoref += '&fechaInicio=%s' % (ts_init)

                elif dicc['date-segex'] == 'check-init-end-date':

                    if dicc['init-segex'] == 'init':
                    
                        ts_now = datetime.now()

                        subs_ts = ts_now - timedelta(minutes = int(dicc['minute-before']))

                        ts_init = subs_ts.strftime('%Y-%m-%d %H:%M:%S')

                    elif dicc['init-segex'] == 'init-guaranteed':
                        segexModel  = segex_FechaFinGarantizada.objects.get(entity = dicc['entities-list'][1], type = tp)
                        ts_init = segexModel.fechafingarantizada.strftime('%Y-%m-%d %H:%M:%S')

                    else:
                        ts = datetime.strptime(dicc['init-date'], '%Y-%m-%dT%H:%M')

                        ts_init = ts.strftime('%Y-%m-%d %H:%M:%S')

                    if dicc['checkbox-end'] == 'true':
                    
                        ts_now = datetime.now()

                        ts_end = ts_now.strftime('%Y-%m-%d %H:%M:%S')

                    else:
                        ts = datetime.strptime(dicc['end-date'], '%Y-%m-%dT%H:%M')

                        ts_end = ts.strftime('%Y-%m-%d %H:%M:%S')

                    listGeoref += '&fechaInicio=%s&fechaFin=%s' % (ts_init, ts_end)
                
                r = requests.get(url+listGeoref)

                print('listGeorefStatus: '+str(r.status_code))

                try:
                    segexModel  = segex_FechaFinGarantizada.objects.get(entity = dicc['entities-list'][1], type = tp)
                    segexModel.fechafingarantizada = r.json()['FechaFinGarantizada']
                    segexModel.save()

                except:
                    
                    segexModel = segex_FechaFinGarantizada(
                        entity = dicc['entities-list'][1],
                        type = tp,
                        fechafingarantizada = r.json()['FechaFinGarantizada']
                    )
                    segexModel.save()

                if r.status_code == 200:

                    for georef in r.json()['Georefs']:

                        wsSegPass = etl_schema.getwsSegPass(dicc['password'])

                        getGeoref = 'Georef/GetGeoref?wsSegUser=%s&wsSegPass=%s&idEntidad=%s&idGeoref=%s' % (wsSegUser, wsSegPass, entity, georef['IdGeoref'])

                        r_geof = requests.get(url+getGeoref)

                        print('getGeorefStatus: '+str(r.status_code))

                        if r.status_code == 200:
                            
                            if r_geof.json():

                                exp = r_geof.json()
                        
                            else:
                                exp = dict.fromkeys(schema, '')
                                exp['IdGeorreferencia'] = georef['IdGeoref']

                                exp["Latitud"] = 0.0
                                exp["Longitud"] = 0.0
                                exp["EstadoExpediente"] = 0

                            for tt in types_text_list:

                                if str(tt[0]) == str(tp):
                                    exp['TipoGeorreferencia']= tt[1]
                                    break


                            exp['Operacion']= georef['Operacion']

                            exp["IdGeorreferencia"] = int(exp["IdGeorreferencia"])
                            exp["Operacion"] = int(exp["Operacion"])
                            exp["Latitud"] = float(exp["Latitud"])
                            exp["Longitud"] = float(exp["Longitud"])
                            exp["EstadoExpediente"] = int(exp["EstadoExpediente"])

                            df = pd.json_normalize(exp)

                            df['FechaCreacionExpediente'] = pd.to_datetime(df['FechaCreacionExpediente'], errors='coerce')
                            df['FechaInicioExpediente'] = pd.to_datetime(df['FechaInicioExpediente'], errors='coerce')
                            df['FechaFinalizacionExpediente'] = pd.to_datetime(df['FechaFinalizacionExpediente'], errors='coerce')

                            df = df[schema]
                            
                            df_obj = df.select_dtypes(['object'])
                            
                            df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))

                            if first:
                                df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
                                first = False
                            else:
                                df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='append', index=False)

                    if len(r.json()['Georefs']) == 100:
                    
                        offset += 100

                    else:

                        offset += 10

        tpt += 1
    if first:
        df = pd.DataFrame(columns = schema)
        df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)

    conn.close()
    db.dispose()

    return [table_name]


def input_Json(dicc):
    
    conn_string = 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
    db = create_engine(conn_string)
    conn = db.connect()

    table_name = dicc['id']

    if dicc['api-rest'] == 'true':

        """if dicc['is-pag'] == 'true':

            start = int(dicc['init-pag'])

            first = True

            while requests.get(dicc['url']+'&'+dicc['pag-par']+'='+str(start)).status_code == 200:
                
                df = pd.read_json(dicc['url']+'&'+dicc['pag-par']+'='+str(start))

                if first:
                    df_obj = df.select_dtypes(['object'])
                    df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
                    df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
                    first = False
                else:
                    df_obj = df.select_dtypes(['object'])
                    df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
                    df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='append', index=False)

                print('pagina: '+ str(start))

                start +=1

        else:"""
        
        df = pd.read_json(dicc['url'])

        """df_obj = df.select_dtypes(['object'])
        df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
        df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)"""
    
    else:
        df = pd.read_json(dicc['json-file'])

    df_obj = df.select_dtypes(['object'])
    df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))
    df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
    
    conn.close()
    db.dispose()
    
    return [table_name]

def trans_Difference(dicc):

    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]

    table_name_target = dicc['id']

    schemas = dicc['schema']


    schema = ''
    attrs =[]

    for attr in schemas:
        schema += 'A0.{},'
        attrs.append(attr)


    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()


    sqlIndex1 = sql.SQL('CREATE INDEX IF NOT EXISTS "{table_source_0}_wkb_geometry_geom_idx" on {schema}."{table_source_0}" USING gist (wkb_geometry);').format(
        table_source_0 = sql.SQL(table_name_source_0),
        schema = sql.Identifier(GEOETL_DB["schema"]))
    
    cur.execute(sqlIndex1)
    conn.commit()

    sqlIndex2 = sql.SQL('CREATE INDEX IF NOT EXISTS "{table_source_1}_wkb_geometry_geom_idx" on {schema}."{table_source_1}" USING gist (wkb_geometry);').format(
        table_source_1 = sql.SQL(table_name_source_1),
        schema = sql.Identifier(GEOETL_DB["schema"]))
    
    cur.execute(sqlIndex2)
    conn.commit()

    sqlDiff = 'create table {schema}.{table_target} as (select '+ schema[:-1] + ', ST_Difference( st_makevalid(A0.wkb_geometry), st_union(st_makevalid(A1.wkb_geometry))) as wkb_geometry from '
    sqlDiff += '{schema}.{table_source_0} AS A0, {schema}.{table_source_1}  AS A1 '
    sqlDiff += 'GROUP BY '+ schema+' A0.wkb_geometry)'

   
    sql_ = sql.SQL(sqlDiff).format(
        schema =  sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target),
        *[sql.Identifier(field) for field in attrs],
        table_source_0 = sql.Identifier(table_name_source_0),
        table_source_1 = sql.Identifier(table_name_source_1),
        *[sql.Identifier(field) for field in attrs],
    )

    cur.execute(sql_)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]

def input_PadronAlbacete(dicc):

    conn_string = 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
    db = create_engine(conn_string)
    conn = db.connect()

    table_name = dicc['id']
    
    if dicc['service'] == 'PRE':
        url_est = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pre_estadisticas_padron&u=fPqq2xHVQkix&pag=%s"
        url_count = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pre_estadisticas_padron_cuenta&u=fPqq2xHVQkix"
    
    elif dicc['service'] == 'PRO':
        url_est = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pro_estadisticas_padron&u=fPqq2xHVQkix&pag=%s"
        url_count = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pro_estadisticas_padron_cuenta&u=fPqq2xHVQkix"

    df_count = pd.read_json(url_count)

    last_pag = df_count['NUMPAGINAS'][0]

    for i in range(1, last_pag+1):
        url = url_est % (str(i))
        df = pd.read_json(url, dtype={"DISTRITO": str, 
                                    "SECCION": str, 
                                    "MANZANA": str, 
                                    "HOJA": str, 
                                    "ORDEN": str,
                                    "KM": str,
                                    "CODIGOPOSTAL": str,
                                    })

        df['FECHANACIMIENTO'] = pd.to_datetime(df['FECHANACIMIENTO'])

        df_obj = df.select_dtypes(['object'])
        df[df_obj.columns] = df_obj.apply(lambda x: x.str.lstrip(' '))

        if i == 1:

            df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
        else:
            df.to_sql(table_name, con=conn, schema= GEOETL_DB['schema'], if_exists='append', index=False)

    conn.close()
    db.dispose()

    return [table_name]


def crea_Grid(dicc):

    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()


    gridFunction = sql.SQL("""
                        CREATE OR REPLACE FUNCTION ST_CreateGrid(
                            nrow integer, ncol integer,
                            xsize float8, ysize float8,
                            x0 float8 DEFAULT 0, y0 float8 DEFAULT 0,
                            OUT "row" integer, OUT col integer,
                            OUT geom geometry)
                        RETURNS SETOF record AS
                    $$
                    SELECT i + 1 AS row, j + 1 AS col, ST_Translate(cell, j * $3 + $5, i * $4 + $6) AS geom
                    FROM generate_series(0, $1 - 1) AS i,
                        generate_series(0, $2 - 1) AS j,
                    (
                    SELECT ('POLYGON((0 0, 0 '||$4||', '||$3||' '||$4||', '||$3||' 0,0 0))')::geometry AS cell
                    ) AS foo;
                    $$ LANGUAGE sql IMMUTABLE STRICT;
            """)

    cur.execute(gridFunction)
    conn.commit()

    sqlGrid = "CREATE TABLE {schema}.{table_target} AS (SELECT row as _row, col as _column, st_setsrid(geom, %s) as wkb_geometry "
    sqlGrid += "FROM ST_CreateGrid(%s, %s, %s, %s, %s, %s))"
    
    sql_ = sql.SQL(sqlGrid).format(
        schema =  sql.Identifier(GEOETL_DB["schema"]),
        table_target = sql.Identifier(table_name_target)
    )
    
    if dicc['create'] == 'Coordinates':

        cur.execute(sql_, [dicc['epsg'], dicc['rows'], dicc['columns'], dicc['width'], dicc['height'], dicc['init-x'], dicc['init-y']])
        conn.commit()

    elif dicc['create'] == 'Extent':
        table_name_source = dicc['data'][0]

        sqlExtent = sql.SQL("SELECT ST_Extent(wkb_geometry) FROM {schema}.{tbl_source}").format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_source = sql.Identifier(table_name_source)
        )

        cur.execute(sqlExtent)
        conn.commit()

        for row in cur:
            coords = row[0][4:-1].split(',')
            xmin, ymin, xmax, ymax = float(coords[0].split(' ')[0]), float(coords[0].split(' ')[1]), float(coords[1].split(' ')[0]), float(coords[1].split(' ')[1])

        columns = math.ceil((xmax - xmin) / float(dicc['width']))

        rows = math.ceil((ymax - ymin) / float(dicc['height']))

        srid, type_geom = get_type_n_srid(table_name_source)

        cur.execute(sql_, [srid, rows, columns, dicc['width'], dicc['height'], xmin, ymin])
        conn.commit()
    
    conn.close()
    cur.close()

    return[table_name_target]


def trans_ExposeAttr(dicc):

    attr = dicc['attr']
    schemaList = dicc['schema']


    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()


    sqlDatetype = 'SELECT column_name, data_type from information_schema.columns '
    sqlDatetype += "where table_schema = %s and table_name = %s "

    cur.execute(sql.SQL(sqlDatetype).format(),[GEOETL_DB["schema"], table_name_source])
    conn.commit()

    for row in cur:
        if 'wkb_geometry' == row[0]:
            if 'wkb_geometry' not in schemaList:
                schemaList.append('wkb_geometry')
            break

    sql_ = 'create table {schema}.{tbl_target} as (select '

    for at in schemaList:
        sql_ = sql_ + '{},'
    
    
    sql_ = sql_[:-1] +' from {schema}.{tbl_source})'

    sqlDup = sql.SQL(sql_).format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        *[sql.Identifier(field) for field in schemaList],
        tbl_source = sql.Identifier(table_name_source)
    )

    cur.execute(sqlDup)
    conn.commit()

    conn.close()
    cur.close()

    return [table_name_target]


def trans_ValGeom(dicc):

    table_name_source = dicc['data'][0]
    table_name_target_valid = dicc['id']+'_0'
    table_name_target_invalid = dicc['id']+'_1'

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_valid))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDrop2 = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_invalid))
    cur.execute(sqlDrop2)
    conn.commit()

    sqlDup = sql.SQL("create table {schema}.{tbl_target} as (select *, valid(ST_IsValidDetail(wkb_geometry)) as _valid from {schema}.{tbl_source} WHERE valid(ST_IsValidDetail(wkb_geometry)) = 't')").format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target_valid),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlDup2 = sql.SQL("create table {schema}.{tbl_target} as (select *, valid(ST_IsValidDetail(wkb_geometry)) as _valid, reason(ST_IsValidDetail(wkb_geometry)) as _reason, st_AsText(location(ST_IsValidDetail(wkb_geometry))) as _location from {schema}.{tbl_source} WHERE valid(ST_IsValidDetail(wkb_geometry)) = 'f')").format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target_invalid),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup2)
    conn.commit()

    if dicc['stop'] == 'true':
        sqlCount = sql.SQL("SELECT * from {schema}.{tbl_target} LIMIT 1").format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target_invalid)
        )
        cur.execute(sqlCount)
        conn.commit()

        _count = 0

        for row in cur:
            reason = row[-2]
            location = row[-1]
            _count +=1
            break

        if _count == 1:
            raise Exception ("There is an invalid feature. Reason: "+reason+'. Location: '+location +'. Feature: '+ str(row[:-3]))

    conn.close()
    cur.close()          

    return [table_name_target_valid, table_name_target_invalid]


def trans_SimpGeom(dicc):

    table_name_source = dicc['data'][0]
    table_name_target_simple = dicc['id']+'_0'
    table_name_target_no_simple = dicc['id']+'_1'

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_simple))
    cur.execute(sqlDrop)
    conn.commit()

    sqlDrop2 = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target_no_simple))
    cur.execute(sqlDrop2)
    conn.commit()

    sqlDup = sql.SQL("create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source} WHERE ST_IsSimple(wkb_geometry) = 't')").format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target_simple),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup)
    conn.commit()

    sqlDup2 = sql.SQL("create table {schema}.{tbl_target} as (select * from {schema}.{tbl_source} WHERE ST_IsSimple(wkb_geometry) = 'f')").format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target_no_simple),
        tbl_source = sql.Identifier(table_name_source)
    )
    cur.execute(sqlDup2)
    conn.commit()

    if dicc['stop'] == 'true':
        sqlCount = sql.SQL("SELECT * from {schema}.{tbl_target} LIMIT 1").format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target_no_simple)
        )
        cur.execute(sqlCount)
        conn.commit()

        _count = 0

        for row in cur:
            _count +=1
            break

        if _count == 1:
            raise Exception ("There are features with geometries no simple. "+ str(row))

    conn.close()
    cur.close()          

    return [table_name_target_simple, table_name_target_no_simple]


def trans_Buffer(dicc):

    table_name_source = dicc['data'][0]
    table_name_target = dicc['id']

    mode_option = dicc['mode-option']
    radio_radius = dicc['radio-radius']
    radius_value = dicc['radius-value']
    radius_attr = dicc['radius-attr']
    #current_area_attr = dicc['current-area-attr'] 
    area_attr_reach = dicc['area-attr-reach']
    radius_increase = float(dicc['radius-increase'])
    quad_segs = dicc['quad-segs']
    end_cap = dicc['end-cap-option']
    join = dicc['join-option']
    mitre_limit = dicc['mitre-limit']
    side = dicc['side-option']

    attrs = dicc['schema']

    srid, type_geom = get_type_n_srid(table_name_source)

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()
    cur2 = conn.cursor()

    sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
        sql.Identifier(GEOETL_DB["schema"]),
        sql.Identifier(table_name_target))
    cur.execute(sqlDrop)
    conn.commit()

    style_parameters = "quad_segs="+str(quad_segs)+" endcap="+end_cap+" join="+join+" mitre_limit="+str(mitre_limit)+" side="+side

    sch = ''
    
    for attr in attrs:
        sch += '{},'

    if  type_geom.startswith('MULTI'):
        multi ='ST_MULTI'
    else:
        multi =''

    if mode_option == 'radius':

        if radio_radius == 'value':


            sqlDup = sql.SQL("CREATE TABLE {schema}.{tbl_target} AS (SELECT "+sch[:-1]+", {multi}(ST_BUFFER(wkb_geometry, %s, %s)) AS wkb_geometry  FROM {schema}.{tbl_source})").format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            multi = sql.SQL(multi),
            *[sql.Identifier(field) for field in attrs],
            tbl_source = sql.Identifier(table_name_source)
            )
            cur.execute(sqlDup, [radius_value, style_parameters])
            conn.commit()

        elif radio_radius == 'attr':

            sqlDup = sql.SQL("CREATE TABLE {schema}.{tbl_target} AS (SELECT "+sch[:-1]+", {multi}(ST_BUFFER(wkb_geometry, {attr}, %s)) AS wkb_geometry  FROM {schema}.{tbl_source})").format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            multi = sql.SQL(multi),
            *[sql.Identifier(field) for field in attrs],
            tbl_source = sql.Identifier(table_name_source),
            attr = sql.Identifier(radius_attr)
            )
            cur.execute(sqlDup, [style_parameters])
            conn.commit()

    elif mode_option == 'reach-area':

        sqlDup = sql.SQL("CREATE TABLE {schema}.{tbl_target} AS (SELECT * FROM {schema}.{tbl_source})").format(
        schema = sql.Identifier(GEOETL_DB["schema"]),
        tbl_target = sql.Identifier(table_name_target),
        tbl_source = sql.Identifier(table_name_source)
        )
        cur.execute(sqlDup)
        conn.commit()

        sqlAdd = sql.SQL('ALTER TABLE {schema}.{tbl_target} ADD COLUMN "_id_temp" SERIAL;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target)
        )
        cur.execute(sqlAdd)
        conn.commit()

        sqlSel= sql.SQL('SELECT "_id_temp", ST_AREA(wkb_geometry), {reach_attr}, wkb_geometry FROM {schema}.{tbl_target} ;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target),
            reach_attr = sql.Identifier(area_attr_reach)
        )
        cur.execute(sqlSel)
        conn.commit()

        for row in cur:
            noBreak = True
            
            dif = row[2] - row[1]
            
            if dif > 0:
                radius_buffer = radius_increase
                increasement = '+'
            elif dif < 0:
                radius_buffer = -radius_increase
                increasement = '-'
            else:
                radius_buffer = 0

            while noBreak:

                if radius_buffer == 0:
                    break

                else:

                    sqlBuffer= sql.SQL('SELECT ST_AREA(ST_BUFFER(wkb_geometry, %s, %s)) FROM {schema}.{tbl_target} WHERE "_id_temp" = %s;').format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        tbl_target = sql.Identifier(table_name_target)
                    )
                    cur2.execute(sqlBuffer, [radius_buffer, style_parameters, row[0]])
                    
                    for fila in cur2:
                        area_buffer = fila[0]
                        break

                    _sqlUp = 'UPDATE {schema}.{tbl_target} SET wkb_geometry = subquery.wkb_geometry FROM ' 

                    if type_geom == 'MULTIPOLYGON':
                        _sqlUp+= '(SELECT ST_Multi(ST_Buffer(wkb_geometry, %s, %s)) AS wkb_geometry FROM {schema}.{tbl_target} WHERE _id_temp = %s) AS subquery'
                    else:
                        _sqlUp+= '(SELECT ST_Buffer(wkb_geometry, %s, %s) AS wkb_geometry FROM {schema}.{tbl_target} WHERE _id_temp = %s) AS subquery'
                    
                    _sqlUp+= ' WHERE _id_temp = %s'

                    sqlUpdate = sql.SQL(_sqlUp).format(
                        schema = sql.Identifier(GEOETL_DB["schema"]),
                        tbl_target = sql.Identifier(table_name_target)
                        )

                    cur2.execute(sqlUpdate, [radius_buffer, style_parameters, row[0], row[0]])
                    conn.commit()

                    if increasement == '+':
                        if row[2] - area_buffer <= 0:
                            noBreak = False
                            break

                    elif increasement == '-':
                        if row[2] - area_buffer >= 0:
                            noBreak = False
                            break
        cur2.close()

        sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN _id_temp;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target)
        )

        cur.execute(sqlDropCol)
        conn.commit()

    if type_geom.startswith('MULTI'):
        tg = 'MULTIPOLYGON'
    else:
        tg = 'POLYGON'

    sqlAlter_ = 'ALTER TABLE {schema}.{tbl_target} ALTER COLUMN wkb_geometry TYPE geometry({type_geom},{epsg}) USING ST_SetSRID({multi}(wkb_geometry), {epsg})'
    
    sqlAlter = sql.SQL(sqlAlter_).format(
                schema = sql.Identifier(GEOETL_DB["schema"]),
                tbl_target = sql.Identifier(table_name_target),
                multi = sql.SQL(multi),
                type_geom = sql.SQL(tg),
                epsg = sql.SQL(str(srid)))
    
    cur.execute(sqlAlter)
    conn.commit()

    conn.close()
    cur.close() 

    return [table_name_target]

def input_SqlServer(dicc):

    table_name = dicc['id']

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn_source_sqlserver = pymssql.connect(params['server-sql-server'], params['username-sql-server'], params['password-sql-server'], params['db-sql-server'], params['db-sql-server'], tds_version = params["tds-version-sql-server"])
    cursor_source = conn_source_sqlserver.cursor(as_dict=True)

    if dicc['checkbox'] == 'true':
        _sql = "SELECT name AS COLUMN_NAME, system_type_name AS DATA_TYPE FROM sys.dm_exec_describe_first_result_set ('%s', NULL, 0) ;" % (dicc['sql'])

    else:
        _sql = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '%s' AND TABLE_NAME  = '%s'" % (dicc['schema-name'], dicc['table-name'])
  
    cursor_source.execute(_sql)

    strColumns = ''
    columns = []
    data_types = []
    geometry = None

    for row in cursor_source:
        columns.append(row['COLUMN_NAME'])
        data_types.append(row['DATA_TYPE'])
        if row['DATA_TYPE'] != 'geometry' and row['DATA_TYPE'] != 'geography':
            strColumns = strColumns + row['COLUMN_NAME'] + ', '
        else:
            strColumns = strColumns + row['COLUMN_NAME'] + '.STAsText() AS '+row['COLUMN_NAME']+', '+row['COLUMN_NAME']+'.STSrid AS SRID, '
            columns.append('SRID')
            data_types.append('int')
    
    if dicc['checkbox'] == 'true':
        sql_df = "SELECT TOP 1 %s FROM (%s) a" % (strColumns[:-2], dicc['sql'])

    else:
        sql_df = 'SELECT TOP 1 %s FROM %s.%s.%s' % (strColumns[:-2], params['db-sql-server'], dicc['schema-name'], dicc['table-name'])
    
    os.environ['TDSVER'] = params["tds-version-sql-server"]
    
    conn_string_source = "mssql+pymssql://%s:%s@%s/%s" % (params['username-sql-server'], params['password-sql-server'], params['server-sql-server'], params['db-sql-server'])
    db_source = create_engine(conn_string_source)
    conn_source = db_source.connect()

    df = pd.read_sql(sql_df, con = conn_source)

    _decimals = ['decimal', 'numeric', 'float', 'real', 'money', 'smallmoney']
    _integers = ['int', 'bigint', 'smallint', 'tinyint']
    _text = ['char', 'varchar', 'nchar', 'nvarchar']
    _date = ['date', 'datetime', 'datetime2', 'datetimeoffset', 'smalldatetime', 'time']
    _geo = ['geography', 'geometry']

    convert_dict = {}
    for i in range (0, len(columns)):
        
        if data_types[i] in _integers:
            convert_dict[columns[i]] = 'int64'

        elif data_types[i] in _decimals:
            convert_dict[columns[i]] = 'float64'

        elif data_types[i] in _text:
            convert_dict[columns[i]] = 'string'

        elif data_types[i] in _geo:
            convert_dict[columns[i]] = 'string'
            geometry = columns[i]

        elif data_types[i] in _date:
            convert_dict[columns[i]] = 'datetime64'
        
        else:
            convert_dict[columns[i]] = 'string'
    
    df = df.astype(convert_dict)
    
    conn_string_target= 'postgresql://'+GEOETL_DB['user']+':'+GEOETL_DB['password']+'@'+GEOETL_DB['host']+':'+GEOETL_DB['port']+'/'+GEOETL_DB['database']
    db_target = create_engine(conn_string_target)
    conn_target = db_target.connect()

    df.to_sql(table_name, con=conn_target, schema= GEOETL_DB['schema'], if_exists='replace', index=False)

    conn_source.close()
    db_source.dispose()

    if dicc['checkbox'] == 'true':
        _sql = "SELECT %s FROM (%s) a" % (strColumns[:-2], dicc['sql'])

    else:
        _sql = 'SELECT %s FROM %s.%s.%s' % (strColumns[:-2], params['db-sql-server'], dicc['schema-name'], dicc['table-name'])

    cursor_source.execute(_sql)

    count = 1

    for row in cursor_source:
        
        for j in row:
            if convert_dict[j] == 'string' and row[j]:
                row[j] = row[j].replace("\x00", "\uFFFD")

        df_tar = pd.DataFrame([row])
        if count == 1:
            df_tar.to_sql(table_name, con=conn_target, schema= GEOETL_DB['schema'], if_exists='replace', index=False)
            count +=1
        else:
            df_tar.to_sql(table_name, con=conn_target, schema= GEOETL_DB['schema'], if_exists='append', index=False)

    conn_target.close()
    db_target.dispose()

    conn_source_sqlserver.close()

    if geometry:

        type_geom = ''
        srid = 0

        conn_tgt = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
        cur_tgt = conn_tgt.cursor()

        sqlTypeGeom = sql.SQL("SELECT split_part({geomAttr},' (', 1) FROM {schema}.{tbl_target} WHERE {geomAttr} is not null GROUP BY split_part({geomAttr},' (', 1);").format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name),
            geomAttr = sql.Identifier(geometry))

        cur_tgt.execute(sqlTypeGeom)
        conn_tgt.commit()

        for row in cur_tgt:
            if type_geom == '':
                type_geom = row[0]
            else:
                type_geom = 'GEOMETRY'

        sqlSRID =  sql.SQL("SELECT {srid} FROM {schema}.{tbl_target} WHERE {srid} is not null GROUP BY {srid} ;").format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name),
            srid = sql.Identifier('SRID'))

        cur_tgt.execute(sqlSRID)
        conn_tgt.commit()

        for row in cur_tgt:
            if srid == 0:
                srid = row[0]
            else:
                srid = 0

        sqlAlter_ = 'ALTER TABLE {schema}.{tbl_target} ADD COLUMN wkb_geometry geometry ({type_geom},{epsg});'
        sqlAlter = sql.SQL(sqlAlter_).format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name),
            type_geom = sql.SQL(type_geom),
            epsg = sql.SQL(str(srid)))

        cur_tgt.execute(sqlAlter)
        conn_tgt.commit()

        sqlUpdate_ = 'UPDATE {schema}.{tbl_target} SET wkb_geometry = ST_GEOMFROMTEXT({geomAttr}) ;'
        sqlUpdate = sql.SQL(sqlUpdate_).format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name),
            geomAttr = sql.Identifier(geometry))

        cur_tgt.execute(sqlUpdate)
        conn_tgt.commit()       

        if srid != 0:
            sqlDropColumn_ = 'ALTER TABLE {schema}.{tbl_target} DROP COLUMN {geomAttr}, DROP COLUMN "SRID";'
        else:
            sqlDropColumn_ = 'ALTER TABLE {schema}.{tbl_target} DROP COLUMN {geomAttr};'

        sqlDropColumn = sql.SQL(sqlDropColumn_).format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name),
            geomAttr = sql.Identifier(geometry))


        cur_tgt.execute(sqlDropColumn)
        conn_tgt.commit()

        cur_tgt.close()
        conn_tgt.close()

    return [table_name]

def trans_NearestNeighbor(dicc):

    attr = dicc['attr']
    tol = dicc['tol']


    table_name_source_0 = dicc['data'][0]
    table_name_source_1 = dicc['data'][1]

    table_name_target_matched = dicc['id']+'_0'
    table_name_target_0_not_used = dicc['id']+'_1'
    table_name_target_1_not_used = dicc['id']+'_2'

    output = [table_name_target_matched, table_name_target_0_not_used, table_name_target_1_not_used]

    conn = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur = conn.cursor()

    schemas =[]

    for table_name in dicc['data']:

        sqlDatetype = 'SELECT column_name from information_schema.columns '
        sqlDatetype += 'where table_schema = %s and table_name = %s '
        cur.execute(sql.SQL(sqlDatetype).format(
        ),[GEOETL_DB["schema"], table_name])
        conn.commit()

        sc =[]
        for row in cur:
            sc.append(row[0])
        schemas.append(sc)

        cur.execute(sql.SQL('ALTER TABLE {schema}.{tbl} ADD COLUMN "_id_temp" SERIAL; ').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl = sql.Identifier(table_name)
        ))

        cur.execute(sql.SQL('CREATE INDEX IF NOT EXISTS "{tbl}_geom_idx" ON {schema}."{tbl}" USING GIST (wkb_geometry);').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl = sql.SQL(table_name)
        ))

    schemaList =[]
    schema = ''

    schemaListA0 =[]
    schemaA0 = ''

    schemaListA1 =[]
    schemaA1 = ''

    for name in schemas[0]:
        schemaList.append(name)
        schemaListA0.append(name)
        if schema == '':
            schema = 'A0.{}'
            schemaA0 = 'A0.{}'
        else:
            schema = schema + ', A0.{}'
            schemaA0 = schemaA0 + ', A0.{}'

    for name in schemas[1]:
        schemaListA1.append(name)
        if name not in schemaList:
            schemaList.append(name)
            schema = schema + ', A1.{}'

        if schemaA1 == '':
            schemaA1 = 'A1.{}'
        else:
            schemaA1 = schemaA1 + ', A1.{}'

    for out in output:

        sqlDrop = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
            sql.Identifier(GEOETL_DB["schema"]),
            sql.Identifier(out))
        
        cur.execute(sqlDrop)
        conn.commit()
        
    if attr == '' and tol == '':

        sqlMatched_ = """CREATE TABLE {sch}.{tbl_matched} AS 
            (SELECT DISTINCT ON (A0."_id_temp")
                    """ + schema +""", 
                    ST_Distance(A0.wkb_geometry, A1.wkb_geometry) AS _distance,
                    A1."_id_temp"
                FROM 
                    {sch}.{tbl_source_0} AS A0 
                JOIN 
                    {sch}.{tbl_source_1} AS A1 ON 1=1
                ORDER BY A0._id_temp, ST_Distance(A0.wkb_geometry, A1.wkb_geometry) )"""

        sqlMatched = sql.SQL(sqlMatched_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_matched = sql.Identifier(table_name_target_matched),
                *[sql.Identifier(field) for field in schemaList],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_source_1 = sql.Identifier(table_name_source_1),
            )
        cur.execute(sqlMatched)
        conn.commit()

        sqlNotJoin1_ = """CREATE TABLE {sch}.{tbl_} AS 
            (
                SELECT 
                    """ + schemaA0 +"""
                FROM 
                    {sch}.{tbl_source_0} AS A0 

                WHERE A0."_id_temp" IS NULL
            )"""

        sqlNotJoin1 = sql.SQL(sqlNotJoin1_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_0_not_used),
                *[sql.Identifier(field) for field in schemaListA0],
                tbl_source_0 = sql.Identifier(table_name_source_0)
            )
        
        cur.execute(sqlNotJoin1)
        conn.commit()


        sqlNotJoin2_ = """CREATE TABLE {sch}.{tbl_} AS 
            (SELECT 
                """ + schemaA1 +"""
            FROM 
                {sch}.{tbl_source_1} AS A1
            WHERE A1."_id_temp" NOT IN
                (SELECT 
                    _id_temp
                FROM
                    {sch}.{tbl_matched}
                )
            ) """

        sqlNotJoin2 = sql.SQL(sqlNotJoin2_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_1_not_used),
                *[sql.Identifier(field) for field in schemaListA1],
                tbl_source_1 = sql.Identifier(table_name_source_1),
                tbl_matched = sql.Identifier(table_name_target_matched)
            )
        
        cur.execute(sqlNotJoin2)
        conn.commit()

        sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN _id_temp;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target_matched)
        )

        cur.execute(sqlDropCol)
        conn.commit()


    elif attr != '' and tol == '':
        sqlMatched_ = """CREATE TABLE {sch}.{tbl_matched} AS 
            (SELECT
                """ +schema.replace('A0.', '').replace('A1.', '') +""",
                _distance 
            FROM (
                SELECT 
                    """ + schema +""", 
                    ST_Distance(A0.wkb_geometry, A1.wkb_geometry) AS _distance,
                    ROW_NUMBER() OVER (PARTITION BY A0._id_temp ORDER BY ST_Distance(A0.wkb_geometry, A1.wkb_geometry)) AS rn
                FROM 
                    {sch}.{tbl_source_0} AS A0 
                LEFT JOIN 
                    {sch}.{tbl_source_1} AS A1 ON A0.{attr} = A1.{attr}
                WHERE A1.{attr} IS NOT NULL
            ) AS subconsulta
            WHERE rn = 1)"""

        sqlMatched = sql.SQL(sqlMatched_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_matched = sql.Identifier(table_name_target_matched),
                *[sql.Identifier(field) for field in schemaList],
                *[sql.Identifier(field) for field in schemaList],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_source_1 = sql.Identifier(table_name_source_1),
                attr = sql.Identifier(attr)
            )
        cur.execute(sqlMatched)
        conn.commit()

        sqlNotJoin1_ = """CREATE TABLE {sch}.{tbl_} AS 
            (
                SELECT 
                    """ + schemaA0 +"""
                FROM 
                    {sch}.{tbl_source_0} AS A0 
                LEFT JOIN 
                    {sch}.{tbl_source_1} AS A1 ON A0.{attr} = A1.{attr}
                WHERE A1.{attr} IS NULL
            )"""

        sqlNotJoin1 = sql.SQL(sqlNotJoin1_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_0_not_used),
                *[sql.Identifier(field) for field in schemaListA0],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_source_1 = sql.Identifier(table_name_source_1),
                attr = sql.Identifier(attr)
            )
        
        cur.execute(sqlNotJoin1)
        conn.commit()

        sqlNotJoin2_ = """CREATE TABLE {sch}.{tbl_} AS 
            (
                SELECT 
                    """ + schemaA1 +"""
                FROM 
                    {sch}.{tbl_source_0} AS A0 
                RIGHT JOIN 
                    {sch}.{tbl_source_1} AS A1 ON A0.{attr} = A1.{attr}
                WHERE A0.{attr} IS NULL
            ) """

        sqlNotJoin2 = sql.SQL(sqlNotJoin2_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_1_not_used),
                *[sql.Identifier(field) for field in schemaListA1],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_source_1 = sql.Identifier(table_name_source_1),
                attr = sql.Identifier(attr)
            )
        
        cur.execute(sqlNotJoin2)
        conn.commit()

    elif attr == '' and tol != '':

        sqlMatched_ = """CREATE TABLE {sch}.{tbl_matched} AS 
            (SELECT DISTINCT ON (A0."_id_temp")
                    """ + schema +""", 
                    ST_Distance(A0.wkb_geometry, A1.wkb_geometry) AS _distance,
                    A0."_id_temp" AS _id_temp_a0,
                    A1."_id_temp" AS _id_temp_a1
                FROM 
                    {sch}.{tbl_source_0} AS A0 
                JOIN 
                    {sch}.{tbl_source_1} AS A1 
                ON 
                    ST_DWithin(A0.wkb_geometry, A1.wkb_geometry, {tol})
                ORDER BY 
                    A0._id_temp, ST_Distance(A0.wkb_geometry, A1.wkb_geometry) )"""

        sqlMatched = sql.SQL(sqlMatched_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_matched = sql.Identifier(table_name_target_matched),
                *[sql.Identifier(field) for field in schemaList],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_source_1 = sql.Identifier(table_name_source_1),
                tol = sql.SQL(tol)
            )
        cur.execute(sqlMatched)
        conn.commit()

        sqlNotJoin1_ = """CREATE TABLE {sch}.{tbl_} AS 
            (SELECT 
                """ + schemaA0 +"""
            FROM 
                {sch}.{tbl_source_0} AS A0
            WHERE A0."_id_temp" NOT IN
                (SELECT 
                    _id_temp_a0
                FROM
                    {sch}.{tbl_matched}
                )
            ) """

        sqlNotJoin1 = sql.SQL(sqlNotJoin1_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_0_not_used),
                *[sql.Identifier(field) for field in schemaListA0],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_matched = sql.Identifier(table_name_target_matched)
            )
        
        cur.execute(sqlNotJoin1)
        conn.commit()

        sqlNotJoin2_ = """CREATE TABLE {sch}.{tbl_} AS 
            (SELECT 
                """ + schemaA1 +"""
            FROM 
                {sch}.{tbl_source_1} AS A1
            WHERE A1."_id_temp" NOT IN
                (SELECT 
                    _id_temp_a1
                FROM
                    {sch}.{tbl_matched}
                )
            ) """

        sqlNotJoin2 = sql.SQL(sqlNotJoin2_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_1_not_used),
                *[sql.Identifier(field) for field in schemaListA1],
                tbl_source_1 = sql.Identifier(table_name_source_1),
                tbl_matched = sql.Identifier(table_name_target_matched)
            )
        
        cur.execute(sqlNotJoin2)
        conn.commit()

        sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN _id_temp_a0, DROP COLUMN _id_temp_a1;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target_matched)
        )

        cur.execute(sqlDropCol)
        conn.commit()


    elif attr != '' and tol != '':

        sqlMatched_ = """CREATE TABLE {sch}.{tbl_matched} AS 
            (SELECT
                """ + schema.replace('A0.', '').replace('A1.', '') + """,
                _distance, 
                _id_temp_a0, 
                _id_temp_a1
            FROM (
                SELECT 
                    """ + schema +""", 
                    ST_Distance(A0.wkb_geometry, A1.wkb_geometry) AS _distance,
                    ROW_NUMBER() OVER (PARTITION BY A0._id_temp ORDER BY ST_Distance(A0.wkb_geometry, A1.wkb_geometry)) AS rn,
                    A0."_id_temp" AS _id_temp_a0,
                    A1."_id_temp" AS _id_temp_a1
                FROM 
                    {sch}.{tbl_source_0} AS A0 
                LEFT JOIN 
                    {sch}.{tbl_source_1} AS A1 ON A0.{attr} = A1.{attr}
                WHERE ST_DWithin(A0.wkb_geometry, A1.wkb_geometry, {tol}) AND A1.{attr} IS NOT NULL
            ) AS subconsulta
            WHERE rn = 1)"""

        sqlMatched = sql.SQL(sqlMatched_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_matched = sql.Identifier(table_name_target_matched),
                *[sql.Identifier(field) for field in schemaList],
                *[sql.Identifier(field) for field in schemaList],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_source_1 = sql.Identifier(table_name_source_1),
                attr = sql.Identifier(attr),
                tol = sql.SQL(tol)
            )
        cur.execute(sqlMatched)
        conn.commit()

        sqlNotJoin1_ = """CREATE TABLE {sch}.{tbl_} AS 
            (SELECT 
                """ + schemaA0 +"""
            FROM 
                {sch}.{tbl_source_0} AS A0
            WHERE A0."_id_temp" NOT IN
                (SELECT 
                    _id_temp_a0
                FROM
                    {sch}.{tbl_matched}
                )
            ) """

        sqlNotJoin1 = sql.SQL(sqlNotJoin1_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_0_not_used),
                *[sql.Identifier(field) for field in schemaListA0],
                tbl_source_0 = sql.Identifier(table_name_source_0),
                tbl_matched = sql.Identifier(table_name_target_matched)
            )
        
        cur.execute(sqlNotJoin1)
        conn.commit()

        sqlNotJoin2_ = """CREATE TABLE {sch}.{tbl_} AS 
            (SELECT 
                """ + schemaA1 +"""
            FROM 
                {sch}.{tbl_source_1} AS A1
            WHERE A1."_id_temp" NOT IN
                (SELECT 
                    _id_temp_a1
                FROM
                    {sch}.{tbl_matched}
                )
            ) """

        sqlNotJoin2 = sql.SQL(sqlNotJoin2_).format(
                sch = sql.Identifier(GEOETL_DB["schema"]),
                tbl_ = sql.Identifier(table_name_target_1_not_used),
                *[sql.Identifier(field) for field in schemaListA1],
                tbl_source_1 = sql.Identifier(table_name_source_1),
                tbl_matched = sql.Identifier(table_name_target_matched)
            )
        
        cur.execute(sqlNotJoin2)
        conn.commit()

        sqlDropCol = sql.SQL('ALTER TABLE {schema}.{tbl_target} DROP COLUMN _id_temp_a0, DROP COLUMN _id_temp_a1;').format(
            schema = sql.Identifier(GEOETL_DB["schema"]),
            tbl_target = sql.Identifier(table_name_target_matched)
        )

        cur.execute(sqlDropCol)
        conn.commit()

    return output