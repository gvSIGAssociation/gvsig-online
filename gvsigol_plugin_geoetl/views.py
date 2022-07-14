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
from gvsigol_auth.utils import superuser_required, staff_required
from django.core import serializers
from django.utils.translation import ugettext as _
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule

from gvsigol import settings
from gvsigol_core import utils as core_utils
from gvsigol_services import utils as services_utils

from .forms import UploadFileForm
from .models import ETLworkspaces, ETLstatus, database_connections
from gvsigol_services.models import Datastore
from django.contrib.auth.models import User
from . import settings as settings_geoetl
from . import etl_tasks
from . import etl_schema
from .tasks import run_canvas_background

import psycopg2
from psycopg2 import sql
from datetime import datetime
import numpy as np
import json
import os


def get_conf(request):
    if request.method == 'POST': 
        response = {
            'etl_url': settings_geoetl.ETL_URL
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

def create_schema(connection_params):

    user = connection_params.get('user')
    schema = connection_params.get('schema')

    connection = psycopg2.connect(user = connection_params["user"], password = connection_params["password"], host = connection_params["host"], port = connection_params["port"], database = connection_params["database"])
    cursor = connection.cursor()

    try:
        create_schema = sql.SQL("CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION {user};").format(
            schema = sql.SQL(schema),
            user = sql.SQL(user)
        )
        cursor.execute(create_schema)

    except Exception as e:
        print("SQL Error", e)
        if e.pgcode == '42710':
            return True
        else:
            return False

    connection.commit()
    connection.close()
    cursor.close()
    return True

@login_required()
@staff_required
def etl_canvas(request):
    
    #from gvsigol.celery import app as celery_app
    #celery_app.control.purge()

    srs = core_utils.get_supported_crs_array()
    srs_string = json.dumps(srs)

    dbc =[]

    databases  = database_connections.objects.all()

    for db in databases:
        dbc.append({"name": db.name, "type": db.type})

    try:
        statusModel  = ETLstatus.objects.get(name = 'current_canvas')
        statusModel.message = ''
        statusModel.status = ''
        statusModel.id_ws = None
        statusModel.save()    

    except:
        
        statusModel = ETLstatus(
            name = 'current_canvas',
            message = '',
            status = '',
            id_ws = None
        )
        statusModel.save()

    try:
        lgid = request.GET['lgid']
        instance  = ETLworkspaces.objects.get(id=int(lgid))

        response = {
            'id':lgid,
            'name': instance.name,
            'description': instance.description,
            'workspace': json.dumps(instance.workspace),
            'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
            'srs': srs_string,
            'dbc': dbc
        }

        try:
            periodicTask = PeriodicTask.objects.get(name = 'gvsigol_plugin_geoetl.'+instance.name+'.'+str(lgid))
        except:
            periodicTask = None
        
        if periodicTask:
            cronid = periodicTask.crontab_id
            interid = periodicTask.interval_id
            if cronid:
                crontab = CrontabSchedule.objects.get(id= cronid)
                response['minute'] = crontab.minute
                response['hour'] = crontab.hour

                days_of_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
                try:
                    response['day_of_week'] = days_of_week[int(crontab.day_of_week)]
                except:
                    response['day_of_week'] = 'all'
            else:
                interval = IntervalSchedule.objects.get(id= interid)
                response['every'] = interval.every
                response['period'] = interval.period

        return render(request, 'etl.html', response)
    
    except:
        response = {
            'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
            'srs': srs,
            'dbc': dbc
        }
        return render(request, 'etl.html', response)

def get_list(user):
    
    etl_list = ETLworkspaces.objects.all()
    
    user_ob = User.objects.get(username = user)

    workspaces = []
    for w in etl_list:
        if w.username == user or user_ob.is_superuser:
            workspace = {}
            workspace['id'] = w.id
            workspace['name'] = w.name
            workspace['description'] = w.description
            #workspace['workspace'] = w.workspace
            workspace['username'] = w.username

            try:
                periodicTask = PeriodicTask.objects.get(name = 'gvsigol_plugin_geoetl.'+w.name+'.'+str(w.id))
            except:
                periodicTask = None
            
            if periodicTask:
                cronid = periodicTask.crontab_id
                interid = periodicTask.interval_id
                if cronid:
                    crontab = CrontabSchedule.objects.get(id= cronid)
                    if crontab.minute != '0':
                        workspace['minute'] = crontab.minute
                    else: 
                        workspace['minute'] = '00'

                    if crontab.hour != '0':
                        workspace['hour'] = crontab.hour
                    else:
                        workspace['hour'] = '00'

                    days_of_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
                    try:
                        workspace['day_of_week'] = days_of_week[int(crontab.day_of_week)]
                    except:
                        workspace['day_of_week'] = "all"
                else:
                    interval = IntervalSchedule.objects.get(id= interid)
                    workspace['every'] = interval.every
                    workspace['period'] = interval.period

            workspaces.append(workspace)
    
    return workspaces


@login_required()
@staff_required
def etl_workspace_list(request):

    create_schema(settings.GEOETL_DB)

    #datastores  = Datastore.objects.filter(type = 'v_PostGIS')

    #for ds in datastores:
    try:
        bbdd_con = database_connections(
            type = 'PostgreSQL',
            name = settings.GEOETL_DB['database'],
            connection_params = '{ "user": "'+settings.GEOETL_DB['user']+'", "password": "'+settings.GEOETL_DB['password']+'", "host": "'+settings.GEOETL_DB['host']+'", "port":'+settings.GEOETL_DB['port']+', "database": "'+settings.GEOETL_DB['database']+'"}'
        )
        bbdd_con.save()
        
    except Exception as e:
        print(e)
    
    username = request.GET['user']

    response = {
        'workspaces': get_list(username),
        'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
    }

    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

def save_periodic_workspace(request, workspace):

    day = request.POST.get('day')
    num_program = request.POST.get('interval')
    unit_program = request.POST.get('unit')

    try:
        jsonCanvas = json.loads(request.POST['workspace'])
    except:
        jsonCanvas = json.loads(workspace.workspace)
    
    my_task_name = 'gvsigol_plugin_geoetl.'+workspace.name+'.'+str(workspace.id)

    if day == 'every':
        
        if unit_program == 'minutes':
            unit_period = IntervalSchedule.MINUTES
        elif unit_program == 'days':
            unit_period = IntervalSchedule.DAYS
        elif unit_program == 'hours':
            unit_period = IntervalSchedule.HOURS
        
        schedule, created = IntervalSchedule.objects.get_or_create(
            every = num_program,
            period=unit_period,
        )

        PeriodicTask.objects.create(
            interval=schedule,
            name=my_task_name,
            kwargs=json.dumps({'jsonCanvas': jsonCanvas, 'id_ws': workspace.id}),
            task='gvsigol_plugin_geoetl.tasks.run_canvas_background',
        )
    else:

        time = datetime.strptime(request.POST.get('time'), '%H:%M:%S').time()

        days_of_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

        day_of_week = '*'
        for i in range(0, len(days_of_week)):
            if day == days_of_week[i]:
                day_of_week = str(i)

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=time.minute,
            hour=time.hour,
            day_of_week = day_of_week,
            day_of_month='*',
            month_of_year='*'
        )
        PeriodicTask.objects.create(
            crontab=schedule,
            name=my_task_name,
            kwargs=json.dumps({'jsonCanvas': jsonCanvas, 'id_ws': workspace.id}),
            task='gvsigol_plugin_geoetl.tasks.run_canvas_background',
        )

    statusModel = ETLstatus(
        name = workspace.name,
        message = '',
        status = '',
        id_ws = workspace.id
    )
    statusModel.save()


def delete_periodic_workspace(workspace):

    try:
        periodicTask = PeriodicTask.objects.get(name = 'gvsigol_plugin_geoetl.'+workspace.name+'.'+str(workspace.id))
    except:
        periodicTask = None
    
    if periodicTask:
        cronid = periodicTask.crontab_id
        interid = periodicTask.interval_id

        periodicTask.delete()

        if interid:
            
            try:
                intervalTasks = PeriodicTask.objects.get(crontab_id =interid)
            except:
                intervalTasks = None
            
            if not intervalTasks:

                intervalSchedule = IntervalSchedule.objects.get(id = interid)
                intervalSchedule.delete()
        else:
            try:
                cronTasks = PeriodicTask.objects.get(crontab_id =cronid)
            except:
                cronTasks = None
            
            if not cronTasks:
            
                crontabSchedule = CrontabSchedule.objects.get(id = cronid)
                crontabSchedule.delete()

    try:
        statusModel  = ETLstatus.objects.get(id_ws = workspace.id)
        statusModel.delete()
    except:
        pass

def name_user_exists(id, name, user):
    workspaces = ETLworkspaces.objects.all()
    for w in workspaces:
        if w.name == name and w.username == user and id != w.id:
            return True
    return False

@login_required()
@staff_required
def etl_workspace_add(request):
    if request.method == 'POST':
    
        try: 
            ws = ETLworkspaces.objects.get(id = int(request.POST.get('id')))
            id = int(request.POST.get('id'))
            user = ws.username
            name = request.POST.get('name')
            exists = name_user_exists(id, name, user)
            if exists:
                response = {
                    'exists': 'true',
                }   
                return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
            
            if request.POST.get('superuser') == 'false':
                
                workspace = ETLworkspaces(
                    id = id,
                    name = name,
                    description = request.POST.get('description'),
                    workspace = request.POST.get('workspace'),
                    username = user
                    
                )
                workspace.save()
            
            else:
                user = request.POST.get('username')
                id = int(request.POST.get('id'))
                name = request.POST.get('name')
                exists = name_user_exists(id, name, user)
                if exists:
                    response = {
                        'exists': 'true',
                    }   
                    return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

                workspace = ETLworkspaces(
                    id = id,
                    name = name,
                    description = request.POST.get('description'),
                    workspace = request.POST.get('workspace'),
                    username = user
                    
                )
                workspace.save()
            
        except:
            user = request.POST.get('username')
            id = None
            name = request.POST.get('name')
            exists = name_user_exists(id, name, user)
            if exists:
                response = {
                    'exists': 'true',
                }   
                return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

            workspace = ETLworkspaces(
                name = request.POST.get('name'),
                description = request.POST.get('description'),
                workspace = request.POST.get('workspace'),
                username = user
            )
            workspace.save()
        
        delete_periodic_workspace(workspace)

        if request.POST.get('checked') == 'true':

            save_periodic_workspace(request, workspace)

        response = {
            'workspaces': get_list(user)
        }

        return render(request, 'dashboard_geoetl_workspaces_list.html', response)
        

@login_required()
@staff_required
def etl_workspace_delete(request):
    lgid = request.POST['lgid']
    if request.method == 'POST':
        
        instance  = ETLworkspaces.objects.get(id=int(lgid))
        
        delete_periodic_workspace(instance)
        
        instance.delete()

    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

@login_required()
@staff_required
def etl_workspace_update(request):
    if request.method == 'POST':
        lgid = request.POST['id']
        instance  = ETLworkspaces.objects.get(id=int(lgid))
        if request.POST.get('superuser') == 'false':
            
            user = instance.username
            id = int(request.POST.get('id'))
            name = request.POST.get('name')
            exists = name_user_exists(id, name, user)
            if exists:
                response = {
                    'exists': 'true',
                }   
                return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
            
            workspace = ETLworkspaces(
                id = id,
                name = name,
                description = request.POST.get('description'),
                workspace = instance.workspace,
                username = user
            )
            workspace.save()
        else:

            user = request.POST.get('username')
            id = int(request.POST.get('id'))
            name = request.POST.get('name')
            exists = name_user_exists(id, name, user)
            if exists:
                response = {
                    'exists': 'true',
                }   
                return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

            workspace = ETLworkspaces(
                id = id,
                name = name,
                description = request.POST.get('description'),
                workspace = instance.workspace,
                username = user
            )
            workspace.save()            

        delete_periodic_workspace(instance)

        if request.POST.get('checked') == 'true':

            save_periodic_workspace(request, instance)
            
    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

@login_required()
@staff_required
def etl_current_canvas_status(request):
    try:
        statusModel  = ETLstatus.objects.get(name = 'current_canvas')
        status = statusModel.status
        msg = statusModel.message

        response = {
            'status': status, 'message': msg
        }      
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    except:
        response = {
            'status': '', 'message': ''
        }      
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required()
@staff_required
def etl_list_canvas_status(request):

    statusModel  = ETLstatus.objects.all()
    
    workspaces = []

    for sm in statusModel:
        if sm.name != 'current_canvas':
            
            workspace = {}
            workspace['id_ws'] = sm.id_ws
            workspace['status'] = sm.status
            workspace['message'] = sm.message
            workspaces.append(workspace)
    
    response = {
        'workspaces': workspaces
    }   
    
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@login_required()
@staff_required
def etl_read_canvas(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        
        if form.is_valid():

            if request.POST['jsonCanvas'] == 'false':
                
                id_ws = request.POST['id_ws']
                ws  = ETLworkspaces.objects.get(id=int(id_ws))
                jsonCanvas = json.loads(ws.workspace)

            else:

                jsonCanvas = json.loads(request.POST['jsonCanvas'])
                id_ws = None

            run_canvas_background.apply_async(kwargs = {'jsonCanvas': jsonCanvas, 'id_ws': id_ws})
            #run_canvas_background({'jsonCanvas': jsonCanvas, 'id_ws': id_ws})
 
        else:
            print ('invalid form')
            print((form.errors))
       
    response = {
           'refresh': True
       }

    return HttpResponse(json.dumps(response, indent=4), content_type='project/json')

@login_required()
@staff_required
def etl_sheet_excel(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            f= request.POST['file']
            r = request.POST['reading']
            listSheets = etl_schema.get_sheets_excel(f, r)

            response = json.dumps(listSheets)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schema_excel(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParamsExcel'])
            listSchema = etl_schema.get_schema_excel(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schema_shape(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            f= request.POST['file']

            listSchema = etl_schema.get_schema_shape(f)
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')   
@staff_required 
def test_conexion(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParams'])

            if jsParams['type-db'] == 'PostgreSQL':

                response = etl_schema.test_postgres(jsParams['parameters'][0])
                
            elif jsParams['type-db'] == 'Oracle':

                response = etl_schema.test_oracle(jsParams['parameters'][0])

            return HttpResponse(json.dumps(response), content_type="application/json")

@login_required(login_url='/gvsigonline/auth/login_user/')   
@staff_required 
def save_conexion(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParams'])

            try:
                bbdd_con = database_connections(
                    type = jsParams['type-db'],
                    name = jsParams['name-db'],
                    connection_params = json.dumps(jsParams['parameters'][0])
                )
                bbdd_con.save()

                response = {
                    'saved': 'true',
                    'name': jsParams['name-db'],
                    'type': jsParams['type-db']
                }  
                
            except Exception as e:
                response = {
                    'saved': 'false',
                }  
                print(e)

            return HttpResponse(json.dumps(response), content_type="application/json")


@login_required()
@staff_required    
def etl_schema_csv(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParamsCSV'])

            response = etl_schema.get_schema_csv(jsParams['parameters'][0])
            
            return HttpResponse(json.dumps(response), content_type="application/json")

@login_required()
@staff_required
def etl_owners_oracle(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            
            jsParams = json.loads(request.POST['jsonParamsOracle'])

            listOwners = etl_schema.get_owners_oracle(jsParams['parameters'][0])
            response = json.dumps(listOwners)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_tables_oracle(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            
            jsParams = json.loads(request.POST['jsonParamsOracle'])

            listtabl = etl_schema.get_tables_oracle(jsParams['parameters'][0])
            response = json.dumps(listtabl)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schema_oracle(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            
            jsParams = json.loads(request.POST['jsonParamsOracle'])

            listSchema = etl_schema.get_schema_oracle(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")


@login_required()
@staff_required
def etl_proced_indenova(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParamsProced'])

            listProcedures = etl_schema.get_proced_indenova(jsParams['parameters'][0])
            response = json.dumps(listProcedures)
            
            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schema_indenova(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            #jsParams = json.loads(request.POST['jsonParamsIndenova'])
            #listSchema = etl_schema.get_schema_indenova(jsParams['parameters'][0])
            listSchema = ['idexp', 'numexp', 'issue', 'idtram', 'nametram', 'initdate', 'status', 'regnumber', 'regdate', 'adirefcatt', 'identifier', 'name', 'town', 'city', 'postalcode', 'country', 'enddate', 'url']

            response = json.dumps(listSchema)
            
            return HttpResponse(response, content_type="application/json")


@login_required()
@staff_required
def etl_schema_postgresql(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParamsPostgres'])

            listSchema = etl_schema.get_schema_postgres(jsParams['parameters'][0])
            response = json.dumps(listSchema)
            return HttpResponse(response, content_type="application/json")

def etl_workspace_download(request):
    lgid = request.GET['lgid']

    workspace = ETLworkspaces.objects.get(id=int(lgid))

    folder = "etl_workspaces"

    folder_path = os.path.join(settings.FILEMANAGER_DIRECTORY, folder)

    try:
        os.mkdir(folder_path)
    except:
        pass

    file_path = os.path.join(folder_path, workspace.name.replace(' ', '_')+'.json')

    with open(file_path, 'w') as f:
        f.write(workspace.workspace)

    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/txt")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response

def etl_workspace_upload(request):
    name = request.POST['name']
    desc = request.POST['description']
    file = request.POST['file']
    user = request.POST['username']
    id = None
    
    exists = name_user_exists(id, name, user)
    
    if exists:
        response = {
            'exists': 'true',
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

    f = open(file[7:], 'r')

    workspace = ETLworkspaces(
        name = name,
        description = desc,
        workspace = f.read(),
        username = user
    )
    workspace.save()

    f.close()

    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

@login_required()
@staff_required
def etl_schema_kml(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            f = request.POST['file']

            listSchema = etl_schema.get_schema_kml(f)
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schemas_name_postgres(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParams'])
            listSchema = etl_schema.get_schema_name_postgres(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_table_name_postgres(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParams'])
            listSchema = etl_schema.get_table_name_postgres(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")


@login_required()
@staff_required
def etl_workspace_is_running(request):
    if request.method == 'POST':
        statusModel  = ETLstatus.objects.all()

        response = {"run": 'false'}

        for sm in statusModel:
            if sm.status == 'Running':
                response['run'] = 'true'
                break
        
        if response['run'] == 'false':
            etl_clean_tmp_tables(request)

    return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

@login_required()
@staff_required
def etl_clean_tmp_tables(request):

    connection_params = settings.GEOETL_DB

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
    
    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)
