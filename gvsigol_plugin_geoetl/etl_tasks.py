# -*- coding: utf-8 -*-

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
from datetime import date


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

    xl = pd.read_excel(dicc["excel-file"], sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])

    js_excel ={
        'features':[]
    }

    for i in xl:
        lon = len(xl[i])
        break

    for i in range (0, lon):
        lista=[]
        for j in xl:
            try:
                value = xl[j][i]
                valueFloat =float(value)
            except:
                valueFloat = None
            
            if not valueFloat:
                lista.append((j, value))
            
            elif math.isnan(valueFloat):
                lista.append((j, 'NULL'))
            else:
                value = commaToDot(xl[j][i])
                lon = len(str(value).split(".")[-1])
                val = str(value).split(".")[-1]
                if lon == 1 and val == '0':
                    try:
                        lista.append((j, int(value)))
                    except:
                        lista.append((j, value))

                else:
                    lista.append((j, value))
        
            dicc = dict(lista)

        js_excel['features'].append({'properties':dicc})
    
    return [js_excel]

def input_Shp(dicc):

    shp = dicc['shp-file'][7:]
  
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(shp, 0)
            
    layer = dataSource.GetLayer()
        
    fc = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : "EPSG:-1"
                    }
            },
        "features": []
        }

    epsg = str(dicc['epsg'])
    
    if epsg == '':
        try:
            epsg = layer.GetSpatialRef().GetAuthorityCode(None)
        except:
            pass
    
    fc['crs']['properties']['name'] = "EPSG:"+str(epsg)

    for feature in layer:    
        f= feature.ExportToJson(as_object=True)
        fc['features'].append(f)

    return[fc]
    

def trans_RemoveAttr(dicc):

    attr = dicc['attr']
    table = dicc['data'][0]
    tableWithoutAttr = copy.deepcopy(table)
    
    k=0
    
    for i in table['features']:
        for j in i['properties']:
            if j == attr:
                del tableWithoutAttr['features'][k]['properties'][attr]
                break
        k+=1

    return [tableWithoutAttr]

def trans_KeepAttr(dicc):

    attr = dicc['attr']
    table = dicc['data'][0]
    tableWithAttr = copy.deepcopy(table)
    
    k=0
    
    for i in table['features']:
        for j in i['properties']:
            if j != attr:
                del tableWithAttr['features'][k]['properties'][j]
                
        k+=1
    
    return [tableWithAttr]

def trans_RenameAttr(dicc):

    oldAttr = dicc['old-attr']
    newAttr = dicc['new-attr']
    
    table = dicc['data'][0]
    
    tableRenamedAttr = dicc['data'][0]
    
    k=0
    
    for i in table['features']:
        for j in i['properties']:
            if j == oldAttr:
                tableRenamedAttr['features'][k]['properties'][newAttr] = tableRenamedAttr['features'][k]['properties'].pop(oldAttr)
                break
        k+=1

    return [tableRenamedAttr]

def trans_Join(dicc):

    attr1 = dicc['attr1']
    attr2 = dicc['attr2']

    table1 = dicc['data'][0]
    table2 = dicc['data'][1]
    
    join = copy.deepcopy(table1)
    join['features'] = []
    
    table1NotUsed = copy.deepcopy(table1)

    table2NotUsed = copy.deepcopy(table2)
    table2NotUsed['features'] = []
    
    lonMax = len(table1['features'])
    
    k=0
    for i in table2['features']:
        value2 = str(i['properties'][attr2])
        
        count1 = 0
        for j in table1['features']:
            value1 = str(j['properties'][attr1])
            
            if value1 == value2:

                join['features'].append(j)
                join['features'][k]['properties'].update(i['properties'])

                for l in table1NotUsed['features']:
                    if str(l['properties'][attr1]) == value1:
                        table1NotUsed['features'].remove(l)
                        break
                k+=1
                break

            else:
                count1+=1
                if count1 == lonMax:
                    table2NotUsed['features'].append(i)

    return [join, table1NotUsed, table2NotUsed]

def trans_ModifyValue(dicc):
    
    attr = dicc['attr']
    
    value = dicc['value']

    try:
        value = float(value)
        if str(value).split('.')[-1] == '0' and len(str(value).split('.')[-1])==1:
            value = int(value)
    except:
        pass
    
    table = dicc['data'][0]

    for i in table['features']:
        i['properties'][attr]=value

    return [table]

def trans_CreateAttr(dicc):

    attr = dicc['attr']
    value = dicc['value']
    table = dicc['data'][0]

    for i in table['features']:
        i['properties'][attr] = value

    return[table]

def trans_Filter(dicc):

    table = dicc['data'][0]
    attr = dicc['attr']
    
    value=str(dicc['value'])
    
    operator = dicc['operator']

    passed = copy.deepcopy(table)
    passed['features'] = []

    failed = copy.deepcopy(table)
    failed['features'] = []

    for i in table['features']:

        valueAttr=str(i['properties'][attr])

        if operator == '==':
            if valueAttr == value:
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == '!=':
            if valueAttr != value:
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == '<':
            if float(valueAttr) < float(value):
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == '>':
            if float(valueAttr) > float(value):
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == '<=':
            if float(valueAttr) <= float(value):
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == '>=':
            if float(valueAttr) >= float(value):
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == 'starts-with':
            
            if valueAttr.startswith(value):
                
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == 'ends-with':
            if valueAttr.endswith(value):
                passed['features'].append(i)
            else:
                failed['features'].append(i)
        if operator == 'contains':
            if value in valueAttr:
                passed['features'].append(i)
            else:
                failed['features'].append(i)

    return [passed, failed]

def isNumber(value):
    try:
        float(value)
        return "_"+value
    except:
        return value

def commaToDot(value):
    try:
        v = float(str(value).replace(",","."))
        return v
    except:
        return value


def is_date(string):
    try: 
        parse(string, fuzzy=False)
        return True

    except:
        return False

def output_Postgresql(dicc):

    fc = dicc['data'][0]

    tableName = dicc['tablename'].lower()

    operation = dicc['operation']

    rows = len(fc['features'])

    #connection to postgres
    conn = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
    cur = conn.cursor()

    listKeys =[]
    listKeysLower =[]
        
    for f in fc['features']:
        for p in f['properties']:
            if p not in listKeys:
                listKeys.append(str(p))
                listKeysLower.append(str(p).lower())
    
    #for creating a new table in database
    if operation=='CREATE':

        sqlCreate="CREATE TABLE IF NOT EXISTS "+tableName+" ("
        sqlInsert = "INSERT INTO "+tableName+" ("
        
        for i in listKeys:

            attr = isNumber(i)

            sqlCreate = sqlCreate + str(attr).lower().replace(": ","_").replace(" ","_")

            sqlInsert = sqlInsert + str(attr).lower().replace(": ","_").replace(" ","_")+","

            longitud=0
            tipo = 'None'

            for j in range(0,rows):

                try:
                    v = fc['features'][j]['properties'][i]
                except:
                    v = None

                value = commaToDot(v)

                if type(value) is int or type(value) == np.dtype('int64'):
                    if tipo=='None':
                        tipo = 'INTEGER'
                        longitud = len(str(value))

                    elif longitud < len(str(value)):
                        longitud = len(str(value))

                if type(value) is float or type(value) == np.dtype('float64'):

                    if tipo=='None' or 'INTEGER':
                        longi = len(str(value).split(".")[-1])
                        valor = str(value).split(".")[-1]
                        if longi == 1 and valor == '0':
                            tipo = 'INTEGER'
                        else:
                            tipo = 'DECIMAL'
                        if longitud < len(str(value)):
                            longitud = len(str(value)) 
                    else:
                        if longitud < len(str(value)):
                            longitud = len(str(value))     
                    
                if type(value) is str and value != 'NULL' :
                    if tipo=='None':
                        tipo = 'VARCHAR'
                        longitud=len(value)
                    
                    else:
                        tipo='VARCHAR'
                        if longitud < len(value):
                            longitud=len(value)
                
                if is_date(value) == True:
                    if tipo=='None' or tipo == 'VARCHAR':
                        tipo = 'DATE'
                        longitud = len(str(value))

                    elif longitud < len(str(value)):
                        longitud = len(str(value))
                
                if type(value) is str and value == 'NULL' :
                    pass
            
            if tipo == 'INTEGER' or tipo == 'DECIMAL' or tipo == 'DATE':
                sqlCreate = sqlCreate+' '+tipo+', '
            else:
                sqlCreate = sqlCreate+' '+tipo+'('+str(longitud)+'), '
            
        sqlCreate=sqlCreate[:-2]+')'

        #executing creating instance
        cur.execute(sqlCreate)

        sqlInsert = sqlInsert[:-1]+') VALUES ('

        for k in range(0, rows):

            sqlInsert2=sqlInsert

            for attr in listKeys:

                try:
                    v = fc['features'][k]['properties'][attr]
                except:
                    v = None

                value = commaToDot(v)

                if type(value) is str and value !='NULL':

                    sqlInsert2 = sqlInsert2+"'"+str(value).replace("'", "''")+"',"

                elif (type(value) is float and math.isnan(value)) or value==None or value =='NULL':

                    sqlInsert2 = sqlInsert2+"NULL,"

                else:

                    sqlInsert2 = sqlInsert2+ str(value)+','

            sqlInsert2=sqlInsert2[:-1]+")"
            
            cur.execute(sqlInsert2)
    
    #for updating rows from an existent table, matching by column
    elif operation == 'UPDATE':
        
        m = dicc['match']
        
        for k in range(0, rows):

            sqlUpdate = 'UPDATE '+tableName+' SET '

            for i in listKeys:

                try:
                    value = fc['features'][k]['properties'][i]
                except:
                    value = None

                if type(value) is str or type(value) is str and value !='NULL':
                    
                    value ="'"+ str(value).replace("'", "''")+"'"

                elif type(value) is float and math.isnan(value) or value==None:
                    value = 'NULL'

                else:
                    value = str(value)

                if i != m:
                    
                    attr = isNumber(i)
                    sqlUpdate = sqlUpdate + attr.lower().replace(": ","_") + " = "+ value +', '
                else:
                    match = isNumber(m)
                    macthValue = value
                    
            
            sqlUpdate = sqlUpdate[:-2]+' WHERE '+ match.lower().replace(": ","_")+' = ' + macthValue+';'

            cur.execute(sqlUpdate)
    
    #for removing rows from an existent table, matching by column
    elif operation == 'DELETE':
        
        i = dicc['match']
        
        for k in range(0, rows):

            sqlDelete = 'DELETE FROM '+tableName+' WHERE '

            try:
                value = fc['features'][k]['properties'][i]
            except:
                value = None

            if type(value) is str or type(value) is str and value !='NULL':
                        
                value ="'"+ str(value).replace("'", "''")+"'"

            elif type(value) is float and math.isnan(value) or value==None:
                value = 'NULL'

            else:
                value = str(value)

            match = isNumber(i)
            macthValue = value
                    
            sqlDelete = sqlDelete+ match.lower().replace(": ","_")+' = ' + macthValue+';'

            cur.execute(sqlDelete)

    conn.commit()
    conn.close()
    cur.close()

def output_Postgis(dicc):

    fc = dicc['data'][0]
    
    operation = dicc['operation']

    rows = len(fc['features'])

    if rows == 0:
        print('No hay features para '+operation)
    else:
        print(str(rows)+' features para '+ operation)
        if operation == "CREATE" or operation == 'APPEND' or operation == 'OVERWRITE':
            
            tfile = tempfile.NamedTemporaryFile(mode="w+", delete = False)
            json.dump(fc, tfile)
            tfile.flush()
            
            schemaTable= dicc['tablename'].lower()
            if "." in schemaTable:
                schema = schemaTable.split(".")[0]
                table_name = schemaTable.split(".")[1]
            else:
                schema = "public"
                table_name = schemaTable
            
            #epsg for geometry
            srs = fc['crs']['properties']['name']
            
            ogr = gdaltools.ogr2ogr()
            ogr.set_encoding('UTF-8')
            ogr.set_input(tfile.name, srs=srs)
            conn = gdaltools.PgConnectionString(host=dicc["host"], port=dicc["port"], dbname=dicc["database"], schema=schema, user=dicc["user"], password=dicc["password"])
            ogr.set_output(conn, table_name=table_name)
            
            if operation == "CREATE":
                ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_CREATE, data_source_mode=ogr.MODE_DS_UPDATE)
            elif operation == "APPEND":
                ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_APPEND, data_source_mode=ogr.MODE_DS_UPDATE)
            else:
                ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_OVERWRITE, data_source_mode=ogr.MODE_DS_UPDATE)
            
            ogr.layer_creation_options = {
                "LAUNDER": "YES",
                "precision": "NO"
            }
            ogr.config_options = {
                "OGR_TRUNCATE": "NO"
            }
            ogr.set_dim("2")
            ogr.execute()


        else:

            fc = dicc['data'][0]

            tableName = dicc['tablename'].lower()

            operation = dicc['operation']
            
            #postgres connection
            conn = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
            cur = conn.cursor()

            listKeys =[]
            listKeysLower =[]
                
            for f in fc['features']:
                for p in f['properties']:
                    if p not in listKeys:
                        listKeys.append(p)
                        listKeysLower.append(p.lower())

            if operation == 'UPDATE':

                m = dicc['match']
                
                for k in range(0, rows):

                    sqlUpdate = 'UPDATE '+tableName+' SET '

                    for i in listKeys:

                        try:
                            value = fc['features'][k]['properties'][i]
                        except:
                            value = None

                        if type(value) is str or type(value) is str and value !='NULL':

                            value ="'"+ str(value).replace("'", "''")+"'"

                        elif type(value) is float and math.isnan(value) or value==None:
                            value = 'NULL'

                        else:
                            value = str(value)

                        if i != m:
                            
                            sqlUpdate = sqlUpdate + i.lower() + " = "+ value +', '
                        else:
                            
                            macthValue = value

                    sqlUpdate = sqlUpdate[:-2]+' WHERE '+ m.lower()+' = ' + macthValue+';'
                    
                    cur.execute(sqlUpdate)
            
            elif operation == 'DELETE':
                
                m = dicc['match']
                
                for k in range(0, rows):

                    sqlDelete = 'DELETE FROM '+tableName+' WHERE '

                    try:
                        value = fc['features'][k]['properties'][m]
                    except:
                        value = None

                    if type(value) is str or type(value) is str and value !='NULL':
                                
                        value ="'"+ str(value).replace("'", "''")+"'"

                    elif type(value) is float and math.isnan(value) or value==None:
                        value = 'NULL'

                    else:
                        value = str(value)

                    macthValue = value
                            
                    sqlDelete = sqlDelete+ m.lower()+' = ' + macthValue+';'
                    
                    cur.execute(sqlDelete)

            conn.commit()
            conn.close()
            cur.close()

def input_Csv(dicc):

    csvdata = pd.read_csv(dicc["csv-file"], sep=dicc["separator"], encoding='utf8')

    js_csv ={
        'features':[]
    }
    
    for i in csvdata:
        lon = len(csvdata[i])
        break

    for i in range (0, lon):
        lista=[]
        for j in csvdata:

            try:
                value = csvdata[j][i]
                valueFloat =float(value)
            except:
                valueFloat = None

            if not valueFloat:
                lista.append((j, value))
            
            elif math.isnan(valueFloat):
                lista.append((j, 'NULL'))

            else:
                value = commaToDot(csvdata[j][i])
                lon = len(str(value).split(".")[-1])
                val = str(value).split(".")[-1]
                if lon == 1 and val == '0':
                    try:
                        lista.append((j, int(value)))
                    except:
                        lista.append((j, value))

                else:
                    lista.append((j, value))
            dicc = dict(lista)
            
        js_csv['features'].append({'properties':dicc})

    return [js_csv]

def trans_Reproject(dicc):
    table = dicc['data'][0]
    sourceepsg = str(dicc['source-epsg'])
    targetepsg = str(dicc['target-epsg'])

    source = osr.SpatialReference()

    if sourceepsg == '':
        source.ImportFromEPSG(int(table['crs']['properties']['name'].split(':')[1]))
    else:
        source.ImportFromEPSG(int(sourceepsg))

    target = osr.SpatialReference()
    target.ImportFromEPSG(int(targetepsg))

    #table['type'] = 'FeatureCollection'

    dataSet = ogr.Open(json.dumps(table))
    layer = dataSet.GetLayer()

    #for newers gdal versions (3 or uppers) we must use next sentences
    #source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    #target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    coordTrans= osr.CoordinateTransformation(source, target)

    fc = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : "EPSG:"+str(targetepsg)
                    }
            },
        "features": []
        }
    
    """for feature in layer:  
        geom = feature.GetGeometryRef()
        geom.Transform(coordTrans)
        g = geom.ExportToWkt()#, as_object=True,options=["COORDINATE_PRECISION=150"])
        geo = g.replace(',', '],[').replace(')', ']').replace('(', '[').replace(' ', ',')
        index = geo.find(',')
        f =json.loads('{"type": "Feature", "geometry":{"type": "'+geo[:index].capitalize()+'", "coordinates": ['+geo[index+1:]+']}}')
        f['properties']=(feature.ExportToJson(as_object=True)['properties'])
        #f['geometry']['epsg'] = targetepsg
        fc['features'].append(f)"""
    
    for feature in layer:    
        geom = feature.GetGeometryRef()
        geom.Transform(coordTrans)
        f = feature.ExportToJson(as_object=True)
        fc['features'].append(f)    
    
    return[fc]

def trans_Counter(dicc):
    table = dicc['data'][0]
    attr = dicc['attr']
    
    gbAttr= dicc['group-by-attr']
    
    if gbAttr == '':
        count=1
        for i in table['features']:
            i['properties'][attr] = count
            count+=1
    else:
        listGroup =[[],[]]
        for i in table['features']:
            row = i['properties']
            if row[gbAttr] not in listGroup[0]:
                listGroup[0].append(row[gbAttr])
                listGroup[1].append(1)
                row[attr] = 1
            else:
                ind = listGroup[0].index(row[gbAttr])
                count = listGroup[1][ind] + 1
                listGroup[1][ind] = count
                row[attr] = count

    return [table]

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
    
    table = dicc['data'][0]
    attr = dicc['attr']
    table["type"] = "FeatureCollection"
    table["crs"] = {"type": "name", "properties":{"name":"empty"}}
    
    for i in table['features']:
        coordinates =[]
        
        features = get_rc_polygon(i['properties'][attr])
        for feature in features:
            edgeCoord = []
            
            coords = feature['coords'].split(" ")

            if table['crs']['properties']['name'] == "empty":
            
                table['crs']['properties']['name'] = feature['srs']
            
            pairCoord = []
            for j in range (0, len(coords)):
                pairCoord.insert(0, float(coords[j]))
                
                if j != 0 and j % 2!=0:
                    
                    edgeCoord.append(pairCoord)
                    pairCoord =[]
            
            coordinates.append(edgeCoord)
        
        i["type"] = "Feature"
        i['geometry'] = {'type': 'MultiPolygon',
                        'coordinates': [coordinates]
                        }
    
    return [table]

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
    
    fc = {
        "features":[]
        }

    c = conn.cursor()
    
    attrnames = etl_schema.get_schema_oracle(dicc)

    if dicc['checkbox'] == "true":
        sql = dicc['sql']
        c.execute(sql)
    else:
        c.execute("SELECT * FROM "+dicc['owner-name']+"."+dicc['table-name'])

    for row in c:
        attrvalues = []
        for i in row:
            
            if type(i) == cx_Oracle.LOB:

                attrvalues.append(i.read())
            else:
                attrvalues.append(i)

        dicc = dict(zip(attrnames, attrvalues))
        
        fc['features'].append({'properties': dicc})

    return[fc]

def trans_WktGeom(dicc):
    
    table = dicc['data'][0]
    tablecopy = copy.deepcopy(table)
    attr = dicc['attr']
    epsg = dicc['epsg']

    tablecopy["type"] = "FeatureCollection"
    tablecopy["crs"] = {"type": "name", "properties":{"name":"EPSG:"+str(epsg)}}

    k = 0
    for i in table['features']:
        wkt_string = i['properties'][attr]
        tablecopy['features'][k]["type"] = "Feature"
        tablecopy['features'][k]["geometry"] = wkt.loads(wkt_string)
        
        for j in i['properties']:
            if j == attr:
                del tablecopy['features'][k]['properties'][attr]

        k+=1
        
    return [tablecopy]

    
def trans_SplitAttr(dicc):

    table = dicc['data'][0]
    tablecopy = copy.deepcopy(table)
    attr = dicc['attr']
    _list = dicc['list']
    _split = dicc['split']
    
    k = 0
    for i in table['features']:
        str_list = i['properties'][attr].split(_split)
        
        tablecopy['features'][k]["properties"][_list] = str_list
        
        for j in i['properties']:
            if j == attr:
                del tablecopy['features'][k]['properties'][attr]

        k+=1
    
    return [tablecopy]

def trans_ExplodeList(dicc):
    table = dicc['data'][0]
    tablecopy = copy.deepcopy(table)

    attr = dicc['attr']
    list_name = dicc['list']
    
    for i in table['features']:
        _list = i['properties'][list_name]

        for l in range (0, len(_list)):
            insert = copy.deepcopy(tablecopy['features'][0])
            
            tablecopy['features'].append(insert)
            del tablecopy['features'][-1]['properties'][list_name]
            tablecopy['features'][-1]['properties'][attr] = _list[l]
        
        del tablecopy['features'][0]

    return [tablecopy]

def trans_Union(dicc):

    table = dicc['data'][0]

    groupby = dicc['group-by-attr']
    dataSet = ogr.Open(json.dumps(table))
        
    layer = dataSet.GetLayer()

    listAttr = []

    fc = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }

    if groupby != "":

        for feature in layer:
            attr = feature.GetField(groupby)
            if attr not in listAttr:
                listAttr.append(attr)

        for i in range (0, len(listAttr)):
            layer.SetAttributeFilter(groupby + ' = ' + str(listAttr[i]))
            k=1

            for f in layer:

                if k == 1:
                    try:
                        geojson = union.ExportToJson()
                        
                        fc['features'].append({'type': 'Feature', 'geometry': json.loads(geojson), 'properties':{groupby: listAttr[i-1]}})
                    except:
                        pass
                    
                    geom1 = f.GetGeometryRef()
                    poly1 = ogr.CreateGeometryFromWkt(str(geom1))
                    
                elif k==2:
                    geom2 = f.GetGeometryRef()
                    poly2 = ogr.CreateGeometryFromWkt(str(geom2))
                    union = poly1.Union(poly2)
                    
                else:
                    geomx = f.GetGeometryRef()
                    polyx = ogr.CreateGeometryFromWkt(str(geomx))
                    union = union.Union(polyx)

                k+=1

        geojson = union.ExportToJson()

        fc['features'].append({'type': 'Feature', 'geometry': json.loads(geojson), 'properties':{groupby: listAttr[i]}})

    else:

        k=1
        for f in layer:

            if k == 1:
                
                geom1 = f.GetGeometryRef()
                poly1 = ogr.CreateGeometryFromWkt(str(geom1))
                
            elif k==2:
                geom2 = f.GetGeometryRef()
                poly2 = ogr.CreateGeometryFromWkt(str(geom2))
                union = poly1.Union(poly2)
                
            else:
                geomx = f.GetGeometryRef()
                polyx = ogr.CreateGeometryFromWkt(str(geomx))
                union = union.Union(polyx)

            k+=1

    geojson = union.ExportToJson()

    fc['features'].append({'type': 'Feature', 'geometry': json.loads(geojson)})

    return [fc]

def input_Indenova(dicc):
    
    domain = dicc['domain']
    api_key = dicc['api-key']
    client_id = dicc['client-id']
    secret = dicc['secret']
    auth = (client_id+':'+secret).encode()

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

    fc ={
        'features':[]
    }

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
                    
                    fc['features'].append({'properties': exp_copy_low})
    
    return[fc]

def input_Postgis(dicc):

    schemaTable = dicc['tablename'].lower()
    """if "." in schemaTable:
        schema = schemaTable.split(".")[0]
        table_name = schemaTable.split(".")[1]
    else:
        schema = "public"
        table_name = schemaTable"""
    
    #postgres connection
    conn = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
    cur = conn.cursor()

    schemaAttr = ','.join(dicc['schema'])

    sql = "select json_build_object('type', 'FeatureCollection', 'features', json_agg(ST_AsGeoJSON(t.*)::json) ) from ( Select "+schemaAttr+",wkb_geometry from "+schemaTable+") as t("+schemaAttr+",wkb_geometry);"
    cur.execute(sql)
    
    for i in cur:
        geojson = i[0]
    
    sql_srid = "SELECT ST_SRID(wkb_geometry) FROM "+schemaTable+" LIMIT 1;"
    cur.execute(sql_srid)

    for s in cur:
        srid = str(s[0])
    
    geojson['crs'] = {"type" : "name", "properties" : { "name" : "EPSG:"+srid }}
    
    conn.commit()
    conn.close()
    cur.close()

    return [geojson]

def trans_CompareRows(dicc):

    attr = dicc['attr']

    table1 = dicc['data'][0]
    table2 = dicc['data'][1]
    
    equals = copy.deepcopy(table1)
    equals['features'] = []
    
    news = copy.deepcopy(table1)
    news['features'] = []

    changes = copy.deepcopy(table1)
    changes['features'] = []

    table2NotUsed = copy.deepcopy(table2)
    
    lonMax = len(table2['features'])
    
    
    for i in table1['features']:
        value1 = str(i['properties'][attr])
        count1 = 0
        for j in table2['features']:
            value2 = str(j['properties'][attr])
            if value1 == value2:
                if i['properties'] == j['properties']:
                    equals['features'].append(i)
                else:
                    changes['features'].append(i)
                
                for l in table2NotUsed['features']:
                    if str(l['properties'][attr]) == value2:
                        table2NotUsed['features'].remove(l)
                        break
                break
            else:
                count1+=1
                if count1 == lonMax:
                    news['features'].append(i)
    
    return [equals, news, changes, table2NotUsed]

def trans_RemoveSmallPoly(dicc):
    tol = float(dicc['tolerance'])

    table = dicc['data'][0]
    dataSet = ogr.Open(json.dumps(table))
        
    layer = dataSet.GetLayer()

    fc = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }
    
    for f in layer:
        
        geom = f.GetGeometryRef()

        if geom.GetGeometryName() == 'MULTIPOLYGON':
            
            k=0
            for p in geom:
                
                area = p.GetArea()
                if area > tol:
                    
                    if k == 0:
                        poly = ogr.Geometry(ogr.wkbPolygon)
                        poly.AddGeometry(p)
                        geom_poly = p

                    elif k == 1:
                        multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
                        multipolygon.AddGeometry(geom_poly)
                        multipolygon.AddGeometry(p)
                        
                    else:
                        multipolygon.AddGeometry(p)
                    k+=1
                    
            if k==0:
                geojson = poly.ExportToJson()
            
            else:
                geojson = multipolygon.ExportToJson()
        
        else:
            geojson = geom.ExportToJson()

        properties = f.ExportToJson(as_object=True)['properties']
        fc['features'].append({'type': 'Feature', 'geometry': json.loads(geojson), 'properties':properties})

    return[fc]

def trans_FilterGeom(dicc):
    table = dicc['data'][0]

    points = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }

    multipoints = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }

    lines = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }

    multilines = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }

    polygons = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }

    multipolygons = { 
        "type" : "FeatureCollection", 
        "crs" : 
            {
                "type" : "name", 
                "properties" : 
                    {
                    "name" : table['crs']['properties']['name']
                    }
            },
        "features": []
        }

    for i in table['features']:
        if i['geometry']['type'] == 'Point':
            points['features'].append(i)
        elif i['geometry']['type'] == 'MultiPoint':
            multipoints['features'].append(i)
        elif i['geometry']['type'] == 'LineString':
            lines['features'].append(i)
        elif i['geometry']['type'] == 'MultiLineString':
            multilines['features'].append(i)
        elif i['geometry']['type'] == 'Polygon':
            polygons['features'].append(i)
        elif i['geometry']['type'] == 'MultiPolygon':
            multipolygons['features'].append(i)

    return [points, multipoints, lines, multilines, polygons, multipolygons]
