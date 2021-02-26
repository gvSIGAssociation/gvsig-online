# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
@author: carlesmarti <carlesmarti@scolab.es>
'''

from django.shortcuts import HttpResponse, render, redirect
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.utils.translation import ugettext as _
from gvsigol import settings as core_settings
from .forms import UploadFileForm
from .models import ETLworkspaces
from . import settings
import json
from . import etl_tasks
from . import etl_schema
import numpy as np

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)

def get_conf(request):
    if request.method == 'POST': 
        response = {
            'etl_url': settings.ETL_URL
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_canvas(request):
    try:
        lgid = request.GET['lgid']
        instance  = ETLworkspaces.objects.get(id=int(lgid))

        response = {
            'id':lgid,
            'name': instance.name,
            'description': instance.description,
            'workspace': instance.workspace,
            'fm_directory': core_settings.FILEMANAGER_DIRECTORY + "/"
        }
        
        return render(request, 'etl.html', response)
    
    except:
        response = {
            'fm_directory': core_settings.FILEMANAGER_DIRECTORY + "/"
        }
        return render(request, 'etl.html', response)

def get_list():
    etl_list = ETLworkspaces.objects.all()
    
    workspaces = []
    for w in etl_list:
        workspace = {}
        workspace['id'] = w.id
        workspace['name'] = w.name
        workspace['description'] = w.description
        workspace['workspace'] = w.workspace[:200]+" (...) ]"
        workspaces.append(workspace)
    return workspaces


@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_workspace_list(request):
    response = {
        'workspaces': get_list()
    }

    return render(request, 'dashboard_geoetl_workspaces_list.html', response)


@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_workspace_add(request):
    if request.method == 'POST':
       
        try: 
            int(request.POST.get('id'))
            lgid = request.POST['id']

            workspace = ETLworkspaces(
                id = int(request.POST.get('id')),
                name = request.POST.get('name'),
                description = request.POST.get('description'),
                workspace = request.POST.get('workspace')
            )
            workspace.save()
            
        except:

            workspace = ETLworkspaces(
                name = request.POST.get('name'),
                description = request.POST.get('description'),
                workspace = request.POST.get('workspace')
            )
            workspace.save()

        return redirect('etl_workspace_list')
        

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_workspace_delete(request):
    lgid = request.POST['lgid']
    if request.method == 'POST':
        instance  = ETLworkspaces.objects.get(id=int(lgid))
        instance.delete()
    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_workspace_update(request):
    if request.method == 'POST':
        lgid = request.POST['id']
        instance  = ETLworkspaces.objects.get(id=int(lgid))

        workspace = ETLworkspaces(
            id = int(request.POST.get('id')),
            name = request.POST.get('name'),
            description = request.POST.get('description'),
            workspace = instance.workspace
        )
        workspace.save()
    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

    
@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_read_canvas(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        
        if form.is_valid():

            jsonCanvas = json.loads(request.POST['jsonCanvas'])

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
                                                
                                                #if more than an edge has the end in the same port
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
            
            except Exception as e:
                result = {"error": "ERROR - "+str(e)}
 
        else:
            print ('invalid form')
            print((form.errors))

    return HttpResponse(json.dumps(result, cls=NpEncoder), content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_sheet_excel(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            f= request.POST['file']
            listSheets = etl_schema.get_sheets_excel(f)

            response = json.dumps(listSheets)

            return HttpResponse(response, content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_schema_excel(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParamsExcel'])
            listSchema = etl_schema.get_schema_excel(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_schema_shape(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            f= request.POST['file']

            listSchema = etl_schema.get_schema_shape(f)
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')    
def test_postgres_conexion(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParamsPostgres'])

            response = etl_schema.test_postgres(jsParams['parameters'][0])

            return HttpResponse(json.dumps(response), content_type="application/json")


@login_required(login_url='/gvsigonline/auth/login_user/')    
def etl_schema_csv(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParamsCSV'])

            response = etl_schema.get_schema_csv(jsParams['parameters'][0])
            
            return HttpResponse(json.dumps(response), content_type="application/json")

