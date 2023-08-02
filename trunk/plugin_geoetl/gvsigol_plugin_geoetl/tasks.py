
from gvsigol.celery import app as celery_app
from celery.schedules import crontab
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from celery.utils.log import get_task_logger

from .models import ETLworkspaces, ETLstatus, database_connections, cadastral_requests
from gvsigol import settings

from . import etl_tasks, views
from .settings import GEOETL_DB

import psycopg2
from psycopg2 import sql
import json
from datetime import date, datetime, timedelta
import copy

logger = get_task_logger(__name__)


@celery_app.task
def run_canvas_background(**kwargs):

    if kwargs["concat"]:
        listConcatIds = kwargs["jsonCanvas"]

    else:
        listConcatIds = [kwargs["id_ws"]]
    
    for wspc in listConcatIds:
        
        if kwargs["concat"]:
            id_ws = kwargs["id_ws"]
            etl_ws  = ETLworkspaces.objects.get(id=int(wspc))
            jsonCanvas = json.loads(etl_ws.workspace)
            username = kwargs["username"]
            if etl_ws.parameters:
                params = json.loads(etl_ws.parameters)
            else:
                params = etl_ws.parameters
        else:
            jsonCanvas = kwargs["jsonCanvas"]
            id_ws = kwargs["id_ws"]
            username = kwargs["username"]
            params = kwargs["parameters"]


    
        if id_ws:
            try:

                statusModel  = ETLstatus.objects.get(id_ws = id_ws)
                statusModel.message = 'Running'
                statusModel.status = 'Running'
                statusModel.save()

            except:

                statusModel = ETLstatus(
                    name = 'name',
                    message = 'Running',
                    status = 'Running',
                    id_ws = id_ws
                )
                
                statusModel.save()
        else:

            statusModel  = ETLstatus.objects.get(name = 'current_canvas.'+username)
            statusModel.message = 'Running'
            statusModel.status = 'Running'
            statusModel.save()
        
        nodes=[]
        edges =[]

        count = 0
        for i in jsonCanvas:
            if i['type'] != 'draw2d.Connection':
                nodes.append([count,i])
                count+=1
            else:
                del i['id']
                if i not in edges:
                    edges.append(i)

        g = etl_tasks.Graph(len(nodes))

        for e in edges:
            source = -1
            target = -1
            for n in nodes:
                if e['source']['node'] == n[1]['id']:
                    source = n[0]
                elif e['target']['node'] == n[1]['id']:
                    target = n[0]
                elif source !=-1 and target !=-1:
                    break
            g.addEdge(source, target)

        sortedList = g.topologicalSort()

        tables_list_name =[]

        move = []

        loop_list = ['sin parámetro de usuario variable']

        #### ordena ejecucion de salidas postgres ####
        tupleOutputOrder = []
        for s in sortedList:
            for n in nodes:
                if s == n[0]:
                    if n[1]['type'].startswith('output_Postgis'):
                        if 'order' in n[1]['entities'][0]['parameters'][0]:
                            tupleOutputOrder.append((n[1]['entities'][0]['parameters'][0]['order'], n[0]))
        
        tupleOutputOrder.sort()

        for ord in tupleOutputOrder:
            sortedList.remove(ord[1])
            sortedList.append(ord[1])
        #### ####

        try:

            if params and not statusModel.name.startswith('current_canvas'):
                if len(params['sql-before']) > 0:
                    executeSQL(params['db'], params['sql-before'])
            
                if params['checkbox-user-params'] == 'True':

                    if params['radio-params-user'] == 'integer':
                        loop_list = [*range(params['init-loop-integer-user-params'], params['end-loop-integer-user-params']+1, 1)]
                    elif params['radio-params-user'] == 'postgres':
                        loop_list = getLoopListFromPostgres(params)

                json_user_params = params['json-user-params']

            for iter_value in loop_list:

                if params and not statusModel.name.startswith('current_canvas'):
                    print('Valor del parámetro de usuario variable: '+str(iter_value))
                    if params['checkbox-user-params'] == 'True':                    
                        json_user_params[params['loop-user-params']] = iter_value

                #going down the sorted list of tasks and executing them
                for s in sortedList:
                    for n in nodes:
                        if s == n[0]:
                            
                            #get parameters for the task
                            try:
                                parameters_copy = n[1]['entities'][0]['parameters'][0]
                                parameters_copy['id'] = n[1]['id']
                                tables_list_name.append(n[1]['id'])
                                
                            except:
                                parameters_copy = {}

                            parameters = copy.deepcopy(parameters_copy)

                            if params and not statusModel.name.startswith('current_canvas'):
                                if json_user_params !={}:
                                    for key in json_user_params:
                                        for key2 in parameters:
                                            if isinstance(parameters[key2], list):
                                                for x in range (0, len(parameters[key2])):
                                                    if '@@'+key+'@@' in parameters[key2][x]:
                                                        parameters[key2][x] = parameters[key2][x].replace('@@'+key+'@@', str(json_user_params[key]))
                                            else:
                                                if '@@'+key+'@@' in parameters[key2]:
                                                    parameters[key2] = parameters[key2].replace('@@'+key+'@@', str(json_user_params[key]))

                            print('Task ' + n[1]['type'] +' ('+n[1]['id']+ ') starts.')
                            #execute input task
                            if n[1]['type'].startswith('input'):

                                if 'move' in parameters:
                                    if parameters['move'] != '':
                                        move.append(n[1])

                                method_to_call = getattr(etl_tasks, n[1]['type'])
                                result = method_to_call(parameters)
                                n.append(result)
                                tables_list_name.append(result)
                            
                            #execute trasnformers or outputs tasks    
                            else:
                                
                                for ip in n[1]['ports']:
                                    if ip['name'].startswith('input'):
                                        
                                        targetPort = ip['name']
                                        targetPortRepeated = False
                                        for e in edges:
                                            if e['target']['port'] == targetPort:

                                                sourceNode = e['source']['node']
                                                sourcePort = e['source']['port']
                                                
                                                for nd in nodes:
                                                    if nd[1]['id'] == sourceNode:
                                                        
                                                        outputPortCounter=-1
                                                        for op in nd[1]['ports']:
                                                            
                                                            if op['name'].startswith('output'):
                                                                outputPortCounter+=1
                                                            if op['name']== sourcePort:
                                                                break
                                                        if 'data' in parameters:
                                                            parameters['data'].append(nd[2][outputPortCounter])
                                                        else:
                                                            parameters['data'] = [nd[2][outputPortCounter]]
                                                            
                                                        break
                                                
                                                #if more than one edge have the end in the same port
                                                if targetPortRepeated == True:
                                                    
                                                    result = etl_tasks.merge_tables(parameters['data'])
                                                    parameters['data'] = result
                                                    tables_list_name.append(result)
                                                
                                                targetPortRepeated = True      

                                method_to_call = getattr(etl_tasks, n[1]['type'])
                                parameters['id'] = n[1]['id']
                                result = method_to_call(parameters)
                                tables_list_name.append(result)
                                
                                if not n[1]['type'].startswith('output'):
                                    n.append(result)
            
            if move:
                for m in move:
                    parameters = m['entities'][0]['parameters'][0]
                    method_to_call = etl_tasks.move (m['type'], parameters)

            if params:
                if len(params['sql-after']) > 0:
                    executeSQL(params['db'], params['sql-after'])

            if id_ws:
                statusModel  = ETLstatus.objects.get(id_ws = id_ws)
                statusModel.message = 'Process has been executed successfully'
                statusModel.status = 'Success'
                statusModel.save()  
            else:
                statusModel  = ETLstatus.objects.get(name = 'current_canvas.'+username)
                statusModel.message ='Process has been executed successfully'
                statusModel.status = 'Success'
                statusModel.save()
            
            delete_tables(tables_list_name)
        
        except Exception as e:
            logger.exception('Error running workspace')
            
            if id_ws:
                statusModel  = ETLstatus.objects.get(id_ws = id_ws)
                statusModel.message = str(e)[:600]
                statusModel.status = 'Error'
                statusModel.save()
            else:
                statusModel  = ETLstatus.objects.get(name = 'current_canvas.'+username)
                statusModel.message = str(e)[:600]
                statusModel.status = 'Error'
                statusModel.save()
            
            delete_tables(tables_list_name)
            
            logger.error('ERROR: In '+n[1]['type']+' Node, '+ str(e))
            print('ERROR: In '+n[1]['type']+' Node, '+ str(e))
            break
        
    
def delete_tables(nodes):
    conn_ = psycopg2.connect(user = GEOETL_DB["user"], password = GEOETL_DB["password"], host = GEOETL_DB["host"], port = GEOETL_DB["port"], database = GEOETL_DB["database"])
    cur_ = conn_.cursor()

    sqlBlocks = "SELECT pid, query FROM pg_stat_activity WHERE query != '<IDLE>' AND query NOT ILIKE '%pg_stat_activity%' ORDER BY query_start desc"
    cur_.execute(sqlBlocks)
    conn_.commit()

    pids = []

    for c in cur_:

        if 'ds_plugin_geoetl.' in c[1]:
            pids.append(c[0])

    for pid in pids:
        sqlTerm = "select pg_terminate_backend("+str(pid)+")"
        cur_.execute(sqlTerm)
        conn_.commit()

    tables = []
    for n in nodes:
        if isinstance(n, list):
            for t in n:
                if t not in tables and t != None:
                    tables.append(t)
        else:
            if n not in tables and n != None:
                tables.append(n)

    for tbl in tables:

        sqlDrop = sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
            sql.Identifier(GEOETL_DB["schema"]),
            sql.Identifier(tbl),
        )
        cur_.execute(sqlDrop)
        conn_.commit()
    conn_.close()
    cur_.close()

@celery_app.on_after_finalize.connect
def setup_periodic_clean(**kwargs):
    my_task_name = 'gvsigol_plugin_geoetl.periodic_clean'
    if not PeriodicTask.objects.filter(name=my_task_name).exists():

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='00',
            hour='22',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*'
        )
        PeriodicTask.objects.create(
            crontab=schedule,
            name=my_task_name,
            task='gvsigol_plugin_geoetl.tasks.periodic_clean',
        )

@celery_app.task   
def periodic_clean():
    statusModel  = ETLstatus.objects.all()

    response = {"run": 'false'}

    for sm in statusModel:
        if sm.status == 'Running':
            response['run'] = 'true'
            break
    
    if response['run'] == 'false':
        connection_params = GEOETL_DB

        user = connection_params.get('user')
        schema = connection_params.get('schema')

        connection = psycopg2.connect(user = connection_params["user"], password = connection_params["password"], host = connection_params["host"], port = connection_params["port"], database = connection_params["database"])
        cursor = connection.cursor()

        drop_schema = sql.SQL("DROP SCHEMA {schema} CASCADE;").format(
            schema = sql.SQL(schema)
        )
        cursor.execute(drop_schema)
        connection.commit()

        create_schema = sql.SQL("CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION {user};").format(
            schema = sql.SQL(schema),
            user = sql.SQL(user)
        )
        cursor.execute(create_schema)
        connection.commit()
        
        connection.close()
        cursor.close()


def executeSQL(db, query_list):

    query = ' '.join(query_list)

    db_model  = database_connections.objects.get(name = db)

    params_str = db_model.connection_params
    connection_params = json.loads(params_str)

    connection = psycopg2.connect(user = connection_params["user"], password = connection_params["password"], host = connection_params["host"], port = connection_params["port"], database = connection_params["database"])
    cursor = connection.cursor()

    sql_ = sql.SQL(query.replace('_##_', '"').replace('#--#', "'"))
    cursor.execute(sql_)
    connection.commit()
    
    connection.close()
    cursor.close()


@celery_app.on_after_finalize.connect
def setup_periodic_cadastral_requests(**kwargs):

    my_task_name = 'gvsigol_plugin_geoetl.periodic_cadastral_requests'
    if not PeriodicTask.objects.filter(name=my_task_name).exists():

        schedule, created = IntervalSchedule.objects.get_or_create(
            every = 15,
            period = IntervalSchedule.MINUTES,
        )
        PeriodicTask.objects.create(
            interval=schedule,
            name=my_task_name,
            task='gvsigol_plugin_geoetl.tasks.periodic_cadastral_requests',
        )

@celery_app.task   
def periodic_cadastral_requests():
        try:
            cr_model  = cadastral_requests.objects.get(name = 'cadastral_requests')
            cadastral_requests_count = cr_model.requests
            date_saved = (cr_model.lastRequest).replace(tzinfo=None)

            if cadastral_requests_count > 0 and (datetime.now() - date_saved).total_seconds() >= 3600:
                cr_model.requests = 0
                cr_model.lastRequest = datetime.now()
                cr_model.save()

        except:
            pass


def getLoopListFromPostgres(params):
    
    db_model  = database_connections.objects.get(name = params['db'])

    params_str = db_model.connection_params
    connection_params = json.loads(params_str)

    connection = psycopg2.connect(user = connection_params["user"], password = connection_params["password"], host = connection_params["host"], port = connection_params["port"], database = connection_params["database"])
    cursor = connection.cursor()

    sql_ = sql.SQL("SELECT {column} FROM {schema}.{table};").format(
        column = sql.Identifier(params['attr-name-user-params']),
        schema = sql.Identifier(params['schema-name-user-params']),
        table = sql.Identifier(params['table-name-user-params']),
    )

    loopList = []
    cursor.execute(sql_)
    connection.commit()

    for value in cursor:
        loopList.append(value[0])
    
    connection.close()
    cursor.close()

    return loopList