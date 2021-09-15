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
@author: nbrodin <carlesmarti@scolab.es>
'''

from django.shortcuts import HttpResponse, render, redirect
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.utils.translation import ugettext as _
from .forms import UploadFileForm
import settings
import json
import etl_tasks
import etl_schema

def get_conf(request):
    if request.method == 'POST': 
        response = {
            'etl_url': settings.ETL_URL
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_canvas(request):

    return render(request, 'etl.html')

    
@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_read_canvas(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        
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
                                filesCounter=0
                                for r in request.FILES:
                                    #input with unique files uploaded
                                    if r == n[1]['id']:
                                        parameters['file'] = request.FILES[n[1]['id']]
                                        break

                                    #input with multiple files uploaded
                                    elif r.startswith(n[1]['id']):
                                        if filesCounter==0:
                                            filesList=[]
                                        
                                        filesList.append(request.FILES[n[1]['id']+'_'+str(filesCounter)])
                                        parameters['file'] = filesList
                                        filesCounter+=1

                            
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
            print 'invalid form'
            print form.errors

    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_sheet_excel(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f= request.FILES['file']
            listSheets = etl_schema.get_sheets_excel(f)

            response = json.dumps(listSheets)

            return HttpResponse(response, content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_schema_excel(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f= request.FILES['file']
            jsParams = json.loads(request.POST['jsonParamsExcel'])
            listSchema = etl_schema.get_schema_excel(f, jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')
def etl_schema_shape(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            listFiles =[]
            for i in range(0, len(request.FILES)):
                listFiles.append(request.FILES['file_'+str(i)])

            listSchema = etl_schema.get_schema_shape(listFiles)
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
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f= request.FILES['file']
            jsParams = json.loads(request.POST['jsonParamsCSV'])
            response = etl_schema.get_schema_csv(f, jsParams['parameters'][0])
            
            return HttpResponse(json.dumps(response), content_type="application/json")