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

from operator import concat
from urllib import response
from django.shortcuts import HttpResponse, render, redirect
from django.contrib.auth.decorators import login_required
from gvsigol_auth.utils import superuser_required, staff_required
from gvsigol_auth import auth_backend
from gvsigol_auth.django_auth import get_user_details
#from gvsigol_auth.auth_backend import get_roles, get_user_details
from django.core import serializers
from django.utils.translation import ugettext as _
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule

from gvsigol import settings
from gvsigol_core import utils as core_utils
from gvsigol_services import utils as services_utils

from .forms import UploadFileForm
from .models import ETLworkspaces, ETLstatus, database_connections,EtlWorkspaceEditRole,EtlWorkspaceExecuteRole,EtlWorkspaceEditRestrictedRole, SendEmails
from gvsigol_services.models import Datastore
from django.contrib.auth.models import User
from . import settings as settings_geoetl
from . import etl_tasks
from . import etl_schema
from .tasks import run_canvas_background
from .settings import GEOETL_DB

import psycopg2
from psycopg2 import sql
from datetime import datetime
import json
import os

class EtlWorkspaceExists(Exception):
    pass

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

    username = request.user.username

    srs = core_utils.get_supported_crs_array()
    srs_string = json.dumps(srs)

    dbc =[]

    databases  = database_connections.objects.all()

    for db in databases:
        dbc.append({"name": db.name, "type": db.type})

    try:

        from gvsigol_plugin_geocoding.models import Provider
        from gvsigol_plugin_geocoding.settings import GEOCODING_SUPPORTED_TYPES

        providers = []
        providers_obj  = Provider.objects.all()

        for pr in providers_obj:
            for engine in GEOCODING_SUPPORTED_TYPES:
                if engine[0] == pr.type:
                    name = engine[1]
                    break
            providers.append({"type": pr.type, 'name': name})

    except:
        providers = []

    try:
        statusModel  = ETLstatus.objects.get(name = 'current_canvas.'+username)
        statusModel.message = ''
        statusModel.status = ''
        statusModel.id_ws = None
        statusModel.save()

    except:

        statusModel = ETLstatus(
            name = 'current_canvas.'+username,
            message = '',
            status = '',
            id_ws = None
        )
        statusModel.save()

    try:
        lgid = request.GET['lgid']

        instance  = ETLworkspaces.objects.get(id=int(lgid))

        if instance.can_edit(request) or instance.can_edit_restrictedly(request):

            response = {
                'id':lgid,
                'name': instance.name,
                'description': instance.description,
                'workspace': json.dumps(instance.workspace),
                'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
                'srs': srs_string,
                'dbc': dbc,
                'providers': providers
            }

            if instance.can_edit_restrictedly(request) and not instance.can_edit(request):
                response['editablerestrictedly'] = 'true'

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

        else:

            return redirect('etl_workspace_list')

    except Exception as e:
        if str(e) == 'ETLworkspaces matching query does not exist.':
            return redirect('etl_workspace_list')
        else:
            response = {
                'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
                'srs': srs,
                'dbc': dbc,
                'providers': providers
            }
            return render(request, 'etl.html', response)

def get_list(request, concat = False):
    user = request.user
    if user.is_superuser:
        etl_list = ETLworkspaces.objects.filter(concat=concat)
    elif user.is_staff:
        user_roles = auth_backend.get_roles(request)
        etl_list = (ETLworkspaces.objects.filter(etlworkspaceexecuterole__role__in=user_roles) |
                        ETLworkspaces.objects.filter(etlworkspaceeditrole__role__in=user_roles) |
                        ETLworkspaces.objects.filter(etlworkspaceeditrestrictedrole__role__in=user_roles) |
                        ETLworkspaces.objects.filter(username=user.username, concat=concat)).distinct()
    else:
        etl_list = []
    workspaces = []
    for w in etl_list:
        workspace = {}
        workspace['id'] = w.id
        workspace['name'] = w.name
        workspace['description'] = w.description
        if concat == True:
            workspace['workspace'] = w.workspace
        workspace['username'] = w.username
        if user.is_superuser or w.username == request.user.username:
            workspace['editable'] = 'true'
            workspace['execute'] = 'true'
        else:
            workspace['editable'] = 'true' if w.can_edit(request) else 'false'
            workspace['editable_restrictedly'] = 'true' if w.can_edit_restrictedly(request) else 'false'
            workspace['execute'] = 'true' if w.can_execute(request) else 'false'

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
def permissons_tab(request, id_wks):

    all_roles=auth_backend.get_all_roles_details(request)

    if (id_wks !=0 and id_wks is not None):
        ws = ETLworkspaces.objects.get(id=id_wks)

        editing_role=[]
        execution_role=[]
        editing_restricted_role=[]

        if ws.can_edit(request):

            role_edit_wks = EtlWorkspaceEditRole.objects.filter(etl_ws=id_wks)
            for b in role_edit_wks:
                editing_role.append(b.role)

        if ws.can_execute(request):

            role_execute_wks = EtlWorkspaceExecuteRole.objects.filter(etl_ws=id_wks)
            for b in role_execute_wks:
                execution_role.append(b.role)

        if ws.can_edit_restrictedly(request):

            role_edit_restrictedly_wks = EtlWorkspaceEditRestrictedRole.objects.filter(etl_ws=id_wks)
            for b in role_edit_restrictedly_wks:
                editing_restricted_role.append(b.role)
    else:
        editing_role=all_roles
        execution_role=all_roles
        editing_restricted_role = all_roles

    response = {
            'groups': all_roles,
            'editing_role' : editing_role,
            'execution_role' : execution_role,
            'editing_restricted_role' : editing_restricted_role
            }

    if ws.can_edit_restrictedly(request) and not ws.can_edit(request):
        response['editablerestrictedly'] = 'true'

    return render(request,  "geoetl_workspaces_permissions.html", response)


@login_required()
@staff_required
def etl_workspace_list(request):

    create_schema(GEOETL_DB)

    #datastores  = Datastore.objects.filter(type = 'v_PostGIS')

    #for ds in datastores:
    try:
        bbdd_con = database_connections(
            type = 'PostgreSQL',
            name = GEOETL_DB['database'],
            connection_params = '{ "user": "'+GEOETL_DB['user']+'", "password": "'+GEOETL_DB['password']+'", "host": "'+GEOETL_DB['host']+'", "port":'+GEOETL_DB['port']+', "database": "'+GEOETL_DB['database']+'"}'
        )
        bbdd_con.save()

    except Exception as e:
        print(e)

    response = {
        'workspaces': get_list(request),
        'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
    }

    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

@login_required()
@staff_required
def etl_concat_workspaces(request):

    create_schema(GEOETL_DB)

    #datastores  = Datastore.objects.filter(type = 'v_PostGIS')

    #for ds in datastores:
    try:
        bbdd_con = database_connections(
            type = 'PostgreSQL',
            name = GEOETL_DB['database'],
            connection_params = '{ "user": "'+GEOETL_DB['user']+'", "password": "'+GEOETL_DB['password']+'", "host": "'+GEOETL_DB['host']+'", "port":'+GEOETL_DB['port']+', "database": "'+GEOETL_DB['database']+'"}'
        )
        bbdd_con.save()

    except Exception as e:
        print(e)

    response = {
        'workspaces': get_list(request, True),
        'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
    }

    return render(request, 'dashboard_geoetl_concat_workspaces.html', response)

def save_periodic_workspace(request, workspace):

    day = request.POST.get('day')
    num_program = request.POST.get('interval')
    unit_program = request.POST.get('unit')

    try:
        jsonCanvas = json.loads(request.POST['workspace'])
    except:
        jsonCanvas = json.loads(workspace.workspace)

    if workspace.parameters:
        params = json.loads(workspace.parameters)
    else:
        params = None

    if workspace.concat:
        concat = workspace.concat
    else:
        concat = False

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
            kwargs=json.dumps({'jsonCanvas': jsonCanvas, 'id_ws': workspace.id, 'username': request.POST['username'], 'parameters': params, 'concat': concat}),
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
            kwargs=json.dumps({'jsonCanvas': jsonCanvas, 'id_ws': workspace.id, 'username': request.POST['username'], 'parameters': params, 'concat': concat}),
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
    workspaces = ETLworkspaces.objects.filter(name=name, username=user)
    for w in workspaces:
        if id != w.id:
            return True
    return False


def _etl_workspace_update(instance, request, name, description, workspace, params, concat, periodic_task, set_superuser=False):
    if request.user.is_superuser and set_superuser:
        username = request.user.username
    else:
        if instance.username is None or instance.can_edit_restrictedly(request):
            username = instance.username
        else:
            username = request.user.username
    if name_user_exists(instance.id, name, username):
        raise EtlWorkspaceExists

    instance.username = username
    instance.name = name
    instance.description = description
    instance.parameters = params
    instance.workspace = workspace
    instance.concat = concat
    instance.save()

    if instance.id is not None:
        delete_periodic_workspace(instance)

    if periodic_task == 'true':
        save_periodic_workspace(request, instance)

    edit_roles = json.loads(request.POST.get('editRoles', '[]'))
    EtlWorkspaceEditRole.objects.filter(etl_ws=instance.id).delete()
    for rol in edit_roles:
        try:
            wsRole = EtlWorkspaceEditRole.objects.get(etl_ws_id=instance.id, role=rol)
        except:
            wsRole = EtlWorkspaceEditRole()
            wsRole.etl_ws = instance
            wsRole.role = rol
            wsRole.save()
    execute_roles = json.loads(request.POST.get('executeRoles', '[]'))
    EtlWorkspaceExecuteRole.objects.filter(etl_ws=instance.id).delete()
    for rol in execute_roles:
        try:
            ws_role = EtlWorkspaceExecuteRole.objects.get(etl_ws_id=instance.id, role=rol)
        except:
            ws_role = EtlWorkspaceExecuteRole()
            ws_role.etl_ws = instance
            ws_role.role = rol
            ws_role.save()

    editing_restricted_roles = json.loads(request.POST.get('restrictedEditRoles', '[]'))
    EtlWorkspaceEditRestrictedRole.objects.filter(etl_ws=instance.id).delete()
    for rol in editing_restricted_roles:
        try:
            ws_role = EtlWorkspaceEditRestrictedRole.objects.get(etl_ws_id=instance.id, role=rol)
        except:
            ws_role = EtlWorkspaceEditRestrictedRole()
            ws_role.etl_ws = instance
            ws_role.role = rol
            ws_role.save()


@login_required()
@staff_required
def changeInputsAndOutputs(request):
    
    id = int(request.POST.get('id'))
    ws = ETLworkspaces.objects.get(id = id)
    wks_saved = json.loads(ws.workspace)
    wks_to_save = json.loads(request.POST.get('workspace'))

    workspace = []

    inout_to_save = []
    con_to_save = []

    inout_saved = []


    for item in wks_to_save:
        if item['type'].startswith('input_') or item['type'].startswith('output_') or item['type'] == 'trans_ExecuteSQL':
            inout_to_save.append(item)
        elif item['type'] != 'draw2d.Connection':
            workspace.append(item)
        else:
            con_to_save.append(item)

    for item in wks_saved:
        if item['type'].startswith('input_') or item['type'].startswith('output_') or item['type'] == 'trans_ExecuteSQL':
            workspace.append(item)
            inout_saved.append(item)

    for i in inout_to_save:
        #id_to_depr = i['id']
        for io in inout_saved:
            if i['type'] == io['type'] and i['entities'][0]['parameters'] == io['entities'][0]['parameters']:
                id_to_keep = io['id']
                id_port_to_keep = io['ports'][0]['name']
                break

        for c in con_to_save:
            if c['source']['node'] == i['id']:
                c['source']['node'] = id_to_keep
                c['source']['port'] = id_port_to_keep

            elif c['target']['node'] == i['id']:
                c['target']['node'] = id_to_keep
                c['target']['port'] = id_port_to_keep


    for con in con_to_save:
        workspace.append(con)

    return json.dumps(workspace)



@login_required()
@staff_required
def etl_workspace_update(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        workspace = request.POST.get('workspace')
        periodic_task = request.POST.get('checked')
        set_superuser = request.POST.get('superuser')
        
        try:
            id = int(request.POST.get('id'))
            ws = ETLworkspaces.objects.get(id = id)
            if not ws.can_edit(request) and not ws.can_edit_restrictedly(request):
                return HttpResponse(json.dumps({'status': 'not allowed'}, indent=4), content_type='folder/json')

            if not ws.can_edit(request) and ws.can_edit_restrictedly(request):
                workspace = changeInputsAndOutputs(request)

            params = ws.parameters
        except Exception as e:
            print(str(e))
            ws = ETLworkspaces()
            params = None
        try:
            if workspace:
                pass
            else:
                workspace = ws.workspace
            _etl_workspace_update(ws, request, name, description, workspace, params, False, periodic_task, set_superuser)
        except EtlWorkspaceExists:
            response = {
                'exists': 'true',
            }
            return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

        response = {
            'workspaces': get_list(request)
        }

        return render(request, 'dashboard_geoetl_workspaces_list.html', response)

@login_required()
@staff_required
def etl_workspaces_roles(request):


    response = {
        'roles': auth_backend.get_all_roles_details(request)
    }

    return HttpResponse(json.dumps(response), content_type="application/json")

@login_required()
@staff_required
def etl_workspace_delete(request):

    if request.method == 'POST':
        lgid = request.POST['lgid']
        instance  = ETLworkspaces.objects.get(id=int(lgid))
        if instance.can_edit(request):
            delete_periodic_workspace(instance)
            instance.delete()

    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)


@login_required()
@staff_required
def etl_workspace_add(request):
    return etl_workspace_update(request)

@login_required()
@staff_required
def etl_current_canvas_status(request):
    try:
        statusModel  = ETLstatus.objects.get(name = 'current_canvas.'+request.POST['username'])
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
        if not sm.name.startswith('current_canvas'):

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
                if ws.parameters:
                    params = json.loads(ws.parameters)
                else:
                    params = None

                concat = ws.concat

            else:

                jsonCanvas = json.loads(request.POST['jsonCanvas'])
                id_ws = None
                params = None
                concat = False

            if id_ws:
                if ws.can_execute(request):
                    run_canvas_background.apply_async(kwargs = {'jsonCanvas': jsonCanvas,
                                                                'id_ws': id_ws,
                                                                'username': request.user.username,
                                                                'parameters': params,
                                                                'concat': concat})

            else: # executing a workspace that has not been saved yet
                run_canvas_background.apply_async(kwargs = {'jsonCanvas': jsonCanvas,
                                                            'id_ws': id_ws,
                                                            'username': request.user.username,
                                                            'parameters': params,
                                                            'concat': concat})


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

            elif jsParams['type-db'] == 'SQLServer':

                response = etl_schema.test_sqlserver(jsParams['parameters'][0])

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

@login_required
@staff_required
def etl_workspace_download(request):
    lgid = request.GET['lgid']

    workspace = ETLworkspaces.objects.get(id=int(lgid))
    if workspace.can_edit(request):
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

@login_required
@staff_required
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

    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)


@login_required()
@staff_required
def get_workspace_parameters(request):
    if request.method == 'POST':

        ws = ETLworkspaces.objects.get(id = request.POST['id'])
        if ws.can_edit(request):
            if ws.parameters:

                response = json.loads(ws.parameters)
                try:
                    response['json-user-params'] = json.dumps(response['json-user-params'])
                except:
                    response['json-user-params'] = json.dumps({})
            else:
                response = {"db": "",
                            "sql-before": "",
                            "sql-after": "",
                            "json-user-params": json.dumps({}),
                            "checkbox-user-params": "",
                            "get_loop-user-params": [],
                            "loop-user-params": "",
                            "radio-params-user": "",
                            "init-loop-integer-user-params": 0,
                            "end-loop-integer-user-params": 0,
                            "get_schema-name-user-params": [],
                            "schema-name-user-params": "",
                            "get_table-name-user-params": [],
                            "table-name-user-params": "",
                            "get_attr-name-user-params": [],
                            "attr-name-user-params": ""
                            }

            try:
                send_mail_params = SendEmails.objects.get(etl_ws_id = request.POST['id'])
                response['checkbox-send-mail-after'] = str(send_mail_params.send_after).capitalize()
                response['checkbox-send-mail-fails'] = str(send_mail_params.send_fails).capitalize()
                response['emails'] = send_mail_params.emails

            except:

                response['checkbox-send-mail-after'] = 'False'
                response['checkbox-send-mail-fails'] = 'False'
                response['email'] = ''

            response['dbcs'] = []

            databases  = database_connections.objects.all()

            for db in databases:
                response['dbcs'].append({"name": db.name, "type": db.type})


            return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
        return HttpResponse(json.dumps({"status": "error"}, indent=4), content_type='folder/json')

@login_required()
@staff_required
def set_workspace_parameters(request):
    if request.method == 'POST':

        ws = ETLworkspaces.objects.get(id = request.POST['id'])
        if ws.can_edit(request):

            sql_before = request.POST['sql-before'].splitlines()
            sql_after = request.POST['sql-after'].splitlines()



            params = '{"db": "'+request.POST['db']
            params +='", "sql-before": '+str(sql_before).replace("'", '"')
            params += ', "sql-after": '+str(sql_after).replace("'", '"')
            params += ', "json-user-params": '+request.POST['json-user-params']
            params += ', "checkbox-user-params": "'+request.POST['checkbox-user-params']
            params += '", "get_loop-user-params": ["'+request.POST['get_loop-user-params']
            params += '"], "loop-user-params": "'+request.POST['loop-user-params']
            params += '", "radio-params-user": "'+request.POST['radio-params-user']
            params += '", "init-loop-integer-user-params": '+request.POST['init-loop-integer-user-params']
            params += ', "end-loop-integer-user-params": '+request.POST['end-loop-integer-user-params']
            params += ', "get_schema-name-user-params": ["'+request.POST['get_schema-name-user-params']
            params += '"], "schema-name-user-params": "'+request.POST['schema-name-user-params']
            params += '", "get_table-name-user-params": ["'+request.POST['get_table-name-user-params']
            params += '"], "table-name-user-params": "'+request.POST['table-name-user-params']
            params += '", "get_attr-name-user-params": ["'+request.POST['get_attr-name-user-params']
            params += '"], "attr-name-user-params": "'+request.POST['attr-name-user-params']
            params += '"}'

            ws.parameters = params
            ws.save()

            try:
                send_mail_params = SendEmails.objects.get(etl_ws_id = request.POST['id'])

                send_mail_params.send_after = request.POST['checkbox-send-mail-after']
                send_mail_params.send_fails = request.POST['checkbox-send-mail-fails']
                send_mail_params.emails = request.POST['emails']
                send_mail_params.save()

            except:

                send_mail_params = SendEmails(
                    send_after = request.POST['checkbox-send-mail-after'],
                    send_fails = request.POST['checkbox-send-mail-fails'],
                    emails = request.POST['emails'],
                    etl_ws_id = request.POST['id']
                )
                send_mail_params.save()

            response = {}

            return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
        else:
            return HttpResponse(json.dumps({"result": "error"}, indent=4), content_type='folder/json')


@login_required()
@staff_required
def etl_entities_segex(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParamsEntities'])

            listEntities = etl_schema.get_entities_segex(jsParams['parameters'][0])

            response = json.dumps(listEntities)

            return HttpResponse(response, content_type="application/json")

def etl_types_segex(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParamsTypes'])

            listTypes = etl_schema.get_types_segex(jsParams['parameters'][0])

            response = json.dumps(listTypes)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schema_json(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParamsJSON'])

            listSchema = etl_schema.get_schema_json(jsParams['parameters'][0])

            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schema_padron_alba(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParamsJSON'])

            listSchema = etl_schema.get_schema_padron_alba(jsParams['parameters'][0])

            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_xml_tags(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            f = request.POST['file']
            r = request.POST['reading']
            listTagsLevels = etl_schema.get_xml_tags(f, r)

            response = json.dumps(listTagsLevels)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def get_workspaces(request):

    response = {
        'workspaces': sorted(get_list(request), key=lambda d: d['id'])
    }

    return HttpResponse(json.dumps(response), content_type="application/json")

@login_required()
@staff_required
def etl_concatenate_workspace_update(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        workspace = request.POST.get('workspace')
        periodic_task = request.POST.get('checked')
        set_superuser = request.POST.get('superuser')
        try:
            id = int(request.POST.get('id'))
            ws = ETLworkspaces.objects.get(id = id)
            if not ws.can_edit(request):
                return HttpResponse(json.dumps({'status': 'not allowed'}, indent=4), content_type='folder/json')
            params = ws.parameters
        except:
            ws = ETLworkspaces()
            params = None
        try:
            _etl_workspace_update(ws, request, name, description, workspace, params, True, periodic_task, set_superuser)
        except EtlWorkspaceExists:
            response = {
                'exists': 'true',
            }
            return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

    response = {}
    return render(request, 'dashboard_geoetl_concat_workspaces.html', response)

@login_required()
@staff_required
def etl_tables_sqlserver(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParamsSQLServer'])

            listtabl = etl_schema.get_tables_sqlserver(jsParams['parameters'][0])
            response = json.dumps(listtabl)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def etl_schemas_sqlserver(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParamsSQLServer'])

            listSchema = etl_schema.get_schemas_sqlserver(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")


@login_required()
@staff_required
def etl_data_schema_sqlserver(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonSqlServer'])

            listSchema = etl_schema.get_data_schemas_sqlserver(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")

@login_required()
@staff_required
def get_emails(request):

    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
    
            users = User.objects.all()
            emails = []

            for user in users:
                if user.email not in emails:
                    emails.append(user.email)

            response = json.dumps(emails)

            return HttpResponse(response, content_type="application/json")