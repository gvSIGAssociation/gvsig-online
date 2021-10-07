from gvsigol.celery import app as celery_app
from celery.schedules import crontab
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule

from .models import ETLstatus

from . import etl_tasks

import json



@celery_app.task
def run_canvas_background(**kwargs):

    jsonCanvas = kwargs["jsonCanvas"]
    id_ws = kwargs["id_ws"]
    
    if id_ws:
        statusModel  = ETLstatus.objects.get(id_ws = id_ws)
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
    try:
        #going down the sorted list of tasks and executing them
        for s in sortedList:
            for n in nodes:
                if s == n[0]:
                    
                    #get parameters for the task
                    try:
                        parameters = n[1]['entities'][0]['parameters'][0]
                        
                    except:
                        parameters = {}
                    
                    #execute input task
                    if n[1]['type'].startswith('input'):

                        method_to_call = getattr(etl_tasks, n[1]['type'])
                        result = method_to_call(parameters)
                        n.append(result)
                    
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

                                            fc = parameters['data'][-2]
                                            
                                            for f in parameters['data'][-1]['features']:
                                                fc['features'].append(f)

                                            del parameters['data'][-1]
                                        
                                        targetPortRepeated = True      

                        method_to_call = getattr(etl_tasks, n[1]['type'])
                        result = method_to_call(parameters)
                        
                        if not n[1]['type'].startswith('output'):
                            n.append(result)
        if id_ws:
            statusModel  = ETLstatus.objects.get(id_ws = id_ws)
            statusModel.message = 'Process has been executed successfully'
            statusModel.status = 'Success'
            statusModel.save()  
        else:
            statusModel  = ETLstatus.objects.get(name = 'current_canvas')
            statusModel.message ='Process has been executed successfully'
            statusModel.status = 'Success'
            statusModel.save()
    
    except Exception as e:
        if id_ws:
            statusModel  = ETLstatus.objects.get(id_ws = id_ws)
            statusModel.message = str(e)[:250]
            statusModel.status = 'Error'
            statusModel.save()
        else:
            statusModel  = ETLstatus.objects.get(name = 'current_canvas')
            statusModel.message = str(e)[:250]
            statusModel.status = 'Error'
            statusModel.save()
    
    