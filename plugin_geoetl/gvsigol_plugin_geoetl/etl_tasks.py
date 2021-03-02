# -*- coding: utf-8 -*-

import pandas as pd
import psycopg2
import json
import math
import numpy as np
from collections import defaultdict, OrderedDict
import tempfile
import shutil
from osgeo import ogr, osr
import copy

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
                pass
            
            if math.isnan(valueFloat):
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
        "features": []
        }

    epsg = str(dicc['epsg'])
    
    if epsg == '':
        try:
            epsg = layer.GetSpatialRef().GetAuthorityCode(None)
        except:
            epsg = '-1'
    
    for feature in layer:    
        f= feature.ExportToJson(as_object=True)
        f['geometry']['epsg'] = epsg
        
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

    rows = len(table1['features'])

    join = {
        'features': []
        }
    
    table1NotUsed = copy.deepcopy(table1)

    table2NotUsed = {
        'features': []
        }
    
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
                    if l['properties'][attr1] == value1:
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

    passed = {
        "features": []
        }

    failed = {
        "features": []
        }

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
                listKeys.append(p)
                listKeysLower.append(p.lower())
    
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
                
                if type(value) is str and value == 'NULL' :
                    pass
            
            if tipo == 'INTEGER' or tipo == 'DECIMAL':
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

    tableName = dicc['tablename'].lower()
    
    #epsg for geometry
    epsg = fc['features'][0]['geometry']['epsg']

    operation = dicc['operation']

    rows = len(fc['features'])

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
                
                if type(value) is str and value == 'NULL':
                    pass
            
            if tipo == 'INTEGER' or tipo == 'DECIMAL':
                sqlCreate = sqlCreate+' '+tipo+', '
            else:
                sqlCreate = sqlCreate+' '+tipo+'('+str(longitud)+'), '
            
        sqlCreate=sqlCreate[:-2]+')'

        cur.execute(sqlCreate)

        #adding geometry column if it not exists
        try:
            addGeomCol = "SELECT AddGeometryColumn ('"+tableName+"', 'geom',"+epsg+", 'GEOMETRY', 2)"
            cur.execute(addGeomCol)
        except:
            pass

        sqlInsert = sqlInsert+'geom) VALUES ('

        for k in range(0, rows):

            sqlInsert2=sqlInsert

            #geojson geometry
            coord = fc['features'][k]['geometry']
            del coord['epsg']
            coord = str(coord).replace("'", '"')

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
            
            sqlInsert2=sqlInsert2+"ST_SetSRID(ST_GeomFromGeoJSON('"+str(coord)+"'), "+ str(epsg)+") )"
            
            cur.execute(sqlInsert2)

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
                pass
            
            if math.isnan(valueFloat):
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
        source.ImportFromEPSG(int(table['features'][0]['geometry']['epsg']))
    else:
        source.ImportFromEPSG(int(sourceepsg))

    target = osr.SpatialReference()
    target.ImportFromEPSG(int(targetepsg))

    table['type'] = 'FeatureCollection'

    dataSet = ogr.Open(json.dumps(table))
    layer = dataSet.GetLayer()

    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    coordTrans= osr.CoordinateTransformation(source, target)

    fc = {
        "features": []
        }

    for feature in layer:    
        geom = feature.GetGeometryRef()
        geom.Transform(coordTrans)
        f = feature.ExportToJson(as_object=True)
        f['geometry']['epsg'] = targetepsg
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



