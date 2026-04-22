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

import logging
from operator import concat
from urllib import response
from django.shortcuts import HttpResponse, render, redirect

logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from gvsigol_auth.utils import superuser_required, staff_required
from gvsigol_auth import auth_backend
from gvsigol_auth.django_auth import get_user_details
#from gvsigol_auth.auth_backend import get_roles, get_user_details
from django.core import serializers
from django.utils.translation import gettext as _
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from django.db import transaction

from gvsigol import settings
from gvsigol_core import utils as core_utils
from gvsigol_services import utils as services_utils

from .forms import UploadFileForm
from .models import (ETLworkspaces, ETLstatus, EtlWorkspaceEditRole, EtlWorkspaceExecuteRole,
                     EtlWorkspaceEditRestrictedRole, SendEmails, SendEndpoint, ETLPluginSettings,
                     ETLVisualizerSession, ETLVisualizerLayer)
from gvsigol_services.models import Datastore, Connection
from django.db.models import Q
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


def get_etl_connections(request):
    """
    Obtiene las conexiones disponibles para el usuario en ETL.
    Superusuarios ven todas, staff solo las que tienen permiso ETL.
    """
    if request.user.is_superuser:
        connections = Connection.objects.all()
        logger.info(f"ETL connections (superuser): count={connections.count()}, types={list(connections.values_list('name', 'type'))}")
    else:
        user_roles = auth_backend.get_roles(request.user)
        all_user_roles = list(user_roles) + [request.user.username]
        logger.info(f"ETL connections filter: user={request.user.username}, roles={all_user_roles}")
        
        # Usar filter con condiciones que apliquen al mismo registro de ConnectionRole
        from gvsigol_services.models import ConnectionRole
        role_ids_with_etl = ConnectionRole.objects.filter(
            role__in=all_user_roles,
            can_use_etl=True
        ).values_list('connection_id', flat=True)
        
        connections = Connection.objects.filter(
            Q(allow_all_etl=True) |
            Q(created_by=request.user.username) |
            Q(id__in=role_ids_with_etl)
        ).distinct()
        logger.info(f"ETL connections found: {list(connections.values_list('name', 'type'))}")
    
    return connections.order_by('name')


def get_etl_connections_list(request):
    """
    Devuelve lista de diccionarios con name y type para el frontend ETL.
    """
    connections = get_etl_connections(request)
    return [{"name": c.name, "type": c.type} for c in connections]


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

    # Obtener conexiones filtradas por permisos ETL
    dbc_list = get_etl_connections_list(request)
    dbc = json.dumps(dbc_list)  # Convertir a JSON para JavaScript
    logger.info(f"ETL canvas - user={username}, dbc count={len(dbc_list)}, dbc={dbc_list}")

    try:

        from gvsigol_plugin_geocoding.models import Provider
        from gvsigol_plugin_geocoding.settings import GEOCODING_SUPPORTED_TYPES

        providers_list = []
        providers_obj  = Provider.objects.all()

        for pr in providers_obj:
            for engine in GEOCODING_SUPPORTED_TYPES:
                if engine[0] == pr.type:
                    name = engine[1]
                    break
            providers_list.append({"type": pr.type, 'name': name})
        providers = json.dumps(providers_list)

    except:
        providers = json.dumps([])

    # Usar get_or_create para evitar duplicados
    statusModel, created = ETLstatus.objects.get_or_create(
        name='current_canvas.' + username,
        defaults={
            'message': '',
            'status': '',
            'id_ws': None
        }
    )
    if not created:
        statusModel.message = ''
        statusModel.status = ''
        statusModel.id_ws = None
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
            except PeriodicTask.DoesNotExist:
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
                'srs': srs_string,
                'dbc': dbc,
                'providers': providers
            }
            return render(request, 'etl.html', response)

def get_list(request, concat = False, datetime_string = False):
    user = request.user
    if user.is_superuser:
        etl_list = ETLworkspaces.objects.filter(concat=concat)
    elif user.is_staff:
        user_roles = auth_backend.get_roles(request)
        etl_list = (ETLworkspaces.objects.filter(etlworkspaceexecuterole__role__in=user_roles, concat=concat) |
                        ETLworkspaces.objects.filter(etlworkspaceeditrole__role__in=user_roles, concat=concat) |
                        ETLworkspaces.objects.filter(etlworkspaceeditrestrictedrole__role__in=user_roles, concat=concat) |
                        ETLworkspaces.objects.filter(username=user.username, concat=concat)).distinct()
    else:
        etl_list = []
    workspaces = []
    for w in etl_list:
        workspace = {}
        workspace['id'] = w.id
        workspace['name'] = w.name
        workspace['description'] = w.description
        # Usar filter().first() para evitar MultipleObjectsReturned
        status = ETLstatus.objects.filter(id_ws=w.id).first()
        if status and status.last_exec is not None:
            if datetime_string:
                workspace['last_run'] = str(status.last_exec)
            else:
                workspace['last_run'] = status.last_exec
        else:
            workspace['last_run'] = ''
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
        except PeriodicTask.DoesNotExist:
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

    response = {
        'workspaces': get_list(request),
        'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
    }

    return render(request, 'dashboard_geoetl_workspaces_list.html', response)

@login_required()
@staff_required
def etl_concat_workspaces(request):

    create_schema(GEOETL_DB)

    response = {
        'workspaces': get_list(request, True),
        'fm_directory': settings.FILEMANAGER_DIRECTORY + "/",
    }

    return render(request, 'dashboard_geoetl_concat_workspaces.html', response)

@transaction.atomic
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

    # Crear o actualizar el status del workspace (evitar duplicados)
    statusModel, created = ETLstatus.objects.update_or_create(
        id_ws=workspace.id,
        defaults={
            'name': workspace.name,
            'message': '',
            'status': ''
        }
    )


@transaction.atomic
def cleanup_orphan_canvas_tasks():
    """
    Limpia tareas huérfanas del tipo run_canvas_background que no corresponden
    a ningún workspace existente. Solo toca tareas con task='gvsigol_plugin_geoetl.tasks.run_canvas_background'
    """
    print("=== EJECUTANDO CLEANUP DE TAREAS HUÉRFANAS ===")
    # Obtener solo las tareas de canvas background del plugin geoetl
    canvas_tasks = PeriodicTask.objects.filter(
        task='gvsigol_plugin_geoetl.tasks.run_canvas_background'
    )
    
    # Obtener todos los IDs de workspaces existentes
    existing_workspace_ids = set(ETLworkspaces.objects.values_list('id', flat=True))
    
    orphaned_schedules_to_cleanup = {
        'interval_ids': set(),
        'crontab_ids': set()
    }
    
    tasks_cleaned = 0
    
    for task in canvas_tasks:
        # Extraer el ID del workspace del nombre de la tarea
        # Formato esperado: 'gvsigol_plugin_geoetl.{nombre}.{id}'
        try:
            task_name_parts = task.name.split('.')
            if len(task_name_parts) >= 3 and task_name_parts[0] == 'gvsigol_plugin_geoetl':
                workspace_id = int(task_name_parts[-1])  # El último elemento debería ser el ID
                
                # Si el workspace no existe, esta tarea es huérfana
                if workspace_id not in existing_workspace_ids:
                    print(f"Limpiando tarea huérfana: {task.name} (workspace_id: {workspace_id})")
                    
                    # Guardar los IDs de schedules para limpiar después
                    if task.interval_id:
                        orphaned_schedules_to_cleanup['interval_ids'].add(task.interval_id)
                    if task.crontab_id:
                        orphaned_schedules_to_cleanup['crontab_ids'].add(task.crontab_id)
                    
                    # Eliminar la tarea huérfana
                    task.delete()
                    tasks_cleaned += 1
                    
        except (ValueError, IndexError) as e:
            # Si no se puede extraer el ID o hay error de formato, continuar
            print(f"Advertencia: No se pudo procesar el nombre de tarea {task.name}: {e}")
            continue
    
    # Limpiar schedules huérfanos solo si no están siendo usados por otras tareas
    intervals_cleaned = 0
    crontabs_cleaned = 0
    
    for interval_id in orphaned_schedules_to_cleanup['interval_ids']:
        # Verificar que no hay otras tareas usando este interval
        if not PeriodicTask.objects.filter(interval_id=interval_id).exists():
            try:
                IntervalSchedule.objects.get(id=interval_id).delete()
                intervals_cleaned += 1
            except IntervalSchedule.DoesNotExist:
                pass
    
    for crontab_id in orphaned_schedules_to_cleanup['crontab_ids']:
        # Verificar que no hay otras tareas usando este crontab
        if not PeriodicTask.objects.filter(crontab_id=crontab_id).exists():
            try:
                CrontabSchedule.objects.get(id=crontab_id).delete()
                crontabs_cleaned += 1
            except CrontabSchedule.DoesNotExist:
                pass
    
    if tasks_cleaned > 0 or intervals_cleaned > 0 or crontabs_cleaned > 0:
        print(f"Cleanup completado: {tasks_cleaned} tareas, {intervals_cleaned} intervalos, {crontabs_cleaned} crontabs eliminados")

@transaction.atomic
def delete_periodic_workspace(workspace):

    try:
        periodicTask = PeriodicTask.objects.get(name = 'gvsigol_plugin_geoetl.'+workspace.name+'.'+str(workspace.id))
    except PeriodicTask.DoesNotExist:
        periodicTask = None

    if periodicTask:
        cronid = periodicTask.crontab_id
        interid = periodicTask.interval_id

        periodicTask.delete()

        if interid:

            try:
                intervalTasks = PeriodicTask.objects.filter(interval_id=interid).first()
            except Exception as e:
                print(f"Error checking interval tasks: {e}")
                intervalTasks = None

            if not intervalTasks:

                intervalSchedule = IntervalSchedule.objects.get(id = interid)
                intervalSchedule.delete()
        else:
            try:
                cronTasks = PeriodicTask.objects.filter(crontab_id=cronid).first()
            except Exception as e:
                print(f"Error checking crontab tasks: {e}")
                cronTasks = None

            if not cronTasks:

                crontabSchedule = CrontabSchedule.objects.get(id = cronid)
                crontabSchedule.delete()

    # Eliminar todos los status asociados al workspace (por si hay duplicados)
    ETLstatus.objects.filter(id_ws=workspace.id).delete()
    
    try:
        send_email  = SendEmails.objects.get(etl_ws = workspace.id)
        send_email.delete()
    except SendEmails.DoesNotExist:
        pass
    
    try:
        send_endpoint  = SendEndpoint.objects.get(etl_ws = workspace.id)
        send_endpoint.delete()
    except:
        pass

def name_user_exists(id, name, user):
    workspaces = ETLworkspaces.objects.filter(name=name, username=user)
    for w in workspaces:
        if id != w.id:
            return True
    return False


@transaction.atomic
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
            # Ejecutar cleanup de tareas huérfanas después de la actualización
            cleanup_orphan_canvas_tasks()
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
@transaction.atomic
def etl_workspace_delete(request):

    if request.method == 'POST':
        lgid = request.POST['lgid']
        instance  = ETLworkspaces.objects.get(id=int(lgid))
        if instance.can_edit(request):
            delete_periodic_workspace(instance)
            instance.delete()
            # Ejecutar cleanup de tareas huérfanas después de la eliminación
            cleanup_orphan_canvas_tasks()

    response = {}
    return render(request, 'dashboard_geoetl_workspaces_list.html', response)


@login_required()
@staff_required
def etl_workspace_add(request):
    return etl_workspace_update(request)

@login_required()
@staff_required
def etl_current_canvas_status(request):
    # Usar filter().first() para evitar MultipleObjectsReturned
    statusModel = ETLstatus.objects.filter(name='current_canvas.'+request.POST['username']).first()
    
    if statusModel:
        response = {
            'status': statusModel.status,
            'message': statusModel.message,
            'visualizer_session_id': str(statusModel.visualizer_session_id) if statusModel.visualizer_session_id else None,
        }
    else:
        response = {
            'status': '',
            'message': '',
            'visualizer_session_id': None,
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
            workspace['last_exec'] = str(sm.last_exec)
            workspace['visualizer_session_id'] = str(sm.visualizer_session_id) if sm.visualizer_session_id else None
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
                if ws.can_execute(request) or ws.can_edit(request) or ws.can_edit_restrictedly(request):
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

            elif jsParams['type-db'] == 'SharePoint':

                response = etl_schema.test_sharepoint(jsParams['parameters'][0])

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
    vis_schema = 'etl_visualizer'

    connection = psycopg2.connect(user = connection_params["user"], password = connection_params["password"], host = connection_params["host"], port = connection_params["port"], database = connection_params["database"])
    cursor = connection.cursor()

    # Clean ETL temporary schema
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

    # Clean ETL Visualizer schema (drop all session tables)
    cursor.execute(
        sql.SQL("DROP SCHEMA IF EXISTS {schema} CASCADE;").format(schema=sql.Identifier(vis_schema))
    )
    connection.commit()

    cursor.execute(
        sql.SQL("CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION {user};").format(
            schema=sql.Identifier(vis_schema),
            user=sql.SQL(user)
        )
    )
    connection.commit()

    connection.close()
    cursor.close()

    # Remove all visualizer session records (cascades to ETLVisualizerLayer)
    ETLVisualizerSession.objects.all().delete()

    # Clear visualizer_session_id from all ETLstatus entries so the
    # "Open Visualizer" button no longer appears in the workspace list
    ETLstatus.objects.all().update(visualizer_session_id=None)

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
                
            try:
                
                send_endpoint_params = SendEndpoint.objects.get(etl_ws_id = request.POST['id'])
                response['checkbox-send-endpoint-after'] = send_endpoint_params.send_after
                response['checkbox-send-endpoint-fails'] = send_endpoint_params.send_fails
                response['url-endpoint'] = send_endpoint_params.url
                response['parameters-endpoint'] = send_endpoint_params.parameters
                response['method-endpoint'] = send_endpoint_params.method

                
            except:

                response['checkbox-send-endpoint-after'] = 'False'
                response['checkbox-send-endpoint-fails'] = 'False'
                response['url-endpoint'] = ''
                response['parameters-endpoint'] = ''
                response['method-endpoint'] = 'POST'

            # Obtener conexiones filtradas por permisos ETL
            response['dbcs'] = get_etl_connections_list(request)


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
                
            try:
                send_endpoint_params = SendEndpoint.objects.get(etl_ws_id = request.POST['id'])
                
                send_endpoint_params.send_after = request.POST['checkbox-send-endpoint-after']
                send_endpoint_params.send_fails = request.POST['checkbox-send-endpoint-fails']
                send_endpoint_params.url = request.POST['url-endpoint']
                send_endpoint_params.parameters = request.POST['parameters-endpoint']
                send_endpoint_params.method = request.POST['method-endpoint'],
                send_endpoint_params.save()

            except:
                
                send_endpoint_params = SendEndpoint(
                    send_after = request.POST['checkbox-send-endpoint-after'],
                    send_fails = request.POST['checkbox-send-endpoint-fails'],
                    url = request.POST['url-endpoint'],
                    parameters = request.POST['parameters-endpoint'],
                    method = request.POST['method-endpoint'],
                    etl_ws_id = request.POST['id']
                )
                send_endpoint_params.save()

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
        'workspaces': sorted(get_list(request, False, True), key=lambda d: d['id'])
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
            # Ejecutar cleanup de tareas huérfanas después de la actualización
            cleanup_orphan_canvas_tasks()
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

@login_required()
@staff_required
def get_status_msg(request):
    
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            # Usar filter().first() para evitar MultipleObjectsReturned
            statusModel = ETLstatus.objects.filter(id_ws=request.POST['id_ws']).first()
            
            if statusModel:
                response = {
                    'status': statusModel.status,
                    'message': statusModel.message
                }
            else:
                response = {
                    'status': '',
                    'message': 'No status found'
                }
            
            return HttpResponse(json.dumps(response), content_type="application/json")
        
@login_required()
@staff_required
def etl_schema_padron_atm(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():

            jsParams = json.loads(request.POST['jsonParams'])

            listSchema = etl_schema.get_schema_padron_atm(jsParams['parameters'][0])
            response = json.dumps(listSchema)

            return HttpResponse(response, content_type="application/json")        
        

@login_required()
@staff_required
def etl_sharepoint_drives(request):
    """Obtiene las bibliotecas de documentos (drives) de un sitio SharePoint."""
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParams'])
            drives = etl_schema.get_sharepoint_drives(jsParams['parameters'][0])
            return HttpResponse(json.dumps(drives), content_type="application/json")

@login_required()
@staff_required
def etl_sharepoint_browse(request):
    """Lista el contenido de una carpeta en SharePoint."""
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParams'])
            contents = etl_schema.get_sharepoint_folder_contents(jsParams['parameters'][0])
            return HttpResponse(json.dumps(contents), content_type="application/json")

@login_required()
@staff_required
def etl_sharepoint_sheets(request):
    """Obtiene las hojas de un archivo Excel de SharePoint."""
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParams'])
            sheets = etl_schema.get_sharepoint_excel_sheets(jsParams['parameters'][0])
            return HttpResponse(json.dumps(sheets), content_type="application/json")

@login_required()
@staff_required
def etl_schema_sharepoint(request):
    """Obtiene el esquema (columnas) de un archivo de SharePoint según el formato."""
    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            jsParams = json.loads(request.POST['jsonParams'])
            schema = etl_schema.get_schema_sharepoint(jsParams['parameters'][0])
            return HttpResponse(json.dumps(schema), content_type="application/json")


def update_clean_temp_tables_task(ttl_hours):
    my_task_name = 'gvsigol_plugin_geoetl.clean_old_temp_tables'
    half_ttl = max(1, int(ttl_hours / 2))  # Evitamos 0

    interval, _ = IntervalSchedule.objects.get_or_create(
        every=half_ttl,
        period=IntervalSchedule.HOURS
    )

    task, created = PeriodicTask.objects.get_or_create(name=my_task_name)
    task.interval = interval
    task.task = 'gvsigol_plugin_geoetl.tasks.clean_old_temp_tables'
    task.save()
    

@login_required()
@staff_required
def update_ttl(request):
    if request.method == "POST":
        try:
            ttl_hours = int(request.POST.get("ttl_hours", 24))
            settings, _ = ETLPluginSettings.objects.get_or_create(id=1)
            settings.ttl_hours = ttl_hours
            settings.save()
            
            update_clean_temp_tables_task(ttl_hours)
            
            return JsonResponse({"status": "ok", "ttl_hours": ttl_hours})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# ─────────────────────────────────────────────────────────────────────────────
# Visualizer API views
# ─────────────────────────────────────────────────────────────────────────────

import re as _re


def _parse_extent(extent_str):
    """
    Convert PostGIS ST_Extent string like 'BOX(xmin ymin,xmax ymax)'
    to [xmin, ymin, xmax, ymax] list of floats, or None on failure.
    """
    if not extent_str:
        return None
    m = _re.search(r'BOX\(([^ ]+) ([^,]+),([^ ]+) ([^)]+)\)', extent_str)
    if m:
        return [float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))]
    return None


def _union_extents(extents):
    """Return the bounding box that contains all extents."""
    valid = [e for e in extents if e]
    if not valid:
        return None
    xmin = min(e[0] for e in valid)
    ymin = min(e[1] for e in valid)
    xmax = max(e[2] for e in valid)
    ymax = max(e[3] for e in valid)
    return [xmin, ymin, xmax, ymax]


@login_required()
def etl_visualizer_config(request, session_id):
    """
    GET /etl/visualizer/<session_id>/config/
    Returns session metadata + list of layers + supported CRS from settings.
    """
    try:
        session = ETLVisualizerSession.objects.get(session_id=session_id)
    except ETLVisualizerSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    # Map PostgreSQL udt_name → simple type used by Filter component
    _PG_TYPE_MAP = {
        'int2': 'integer', 'int4': 'integer', 'int8': 'integer',
        'float4': 'double', 'float8': 'double', 'numeric': 'double',
        'bool': 'boolean',
        'date': 'date', 'timestamp': 'date', 'timestamptz': 'date',
    }

    layers_data = []
    extents = []

    try:
        con_fields = psycopg2.connect(
            user=GEOETL_DB["user"], password=GEOETL_DB["password"],
            host=GEOETL_DB["host"], port=GEOETL_DB["port"],
            database=GEOETL_DB["database"]
        )
        cur_fields = con_fields.cursor()
    except Exception:
        con_fields = None
        cur_fields = None

    for layer in session.layers.all():
        parsed = _parse_extent(layer.extent_3857)
        extents.append(parsed)

        # _rowid is a synthetic PK added at query time via row_number()
        fields = [
            {
                'name': '_rowid',
                'translate': '#',
                'visible': False,
                'type': 'integer',
                'pk': 'YES',
            }
        ]
        if cur_fields:
            try:
                cur_fields.execute(
                    """
                    SELECT column_name, udt_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                      AND column_name != 'geom'
                      AND udt_name NOT IN ('geometry', 'geography')
                    ORDER BY ordinal_position
                    """,
                    ('etl_visualizer', layer.table_name)
                )
                for col_name, udt in cur_fields.fetchall():
                    fields.append({
                        'name': col_name,
                        'translate': col_name,
                        'visible': True,
                        'type': _PG_TYPE_MAP.get(udt, 'text'),
                        'pk': 'NO',
                    })
            except Exception:
                fields = [fields[0]]  # keep only _rowid on error

        layers_data.append({
            'id': layer.id,
            'name': layer.name,
            'layer_group': layer.layer_group,
            'color': layer.color,
            'has_geometry': layer.has_geometry,
            'feature_count': layer.feature_count,
            'truncated': layer.truncated,
            'extent': parsed,
            'layer_order': layer.layer_order,
            'fields': fields,
        })

    if cur_fields:
        cur_fields.close()
    if con_fields:
        con_fields.close()

    combined_extent = _union_extents(extents)

    # Build supported CRS list from Django settings (same format as the viewer)
    supported_crs = core_utils.get_supported_crs_array()

    from django.conf import settings as _dj_settings
    logo_url = _dj_settings.STATIC_URL + 'img/no_project.png'

    return JsonResponse({
        'session_id': str(session.session_id),
        'layers': layers_data,
        'combined_extent': combined_extent,
        'supported_crs': supported_crs,
        'logo_url': logo_url,
    })


@login_required()
def etl_visualizer_layer_features(request, layer_id):
    """
    GET /etl/visualizer/layer/<layer_id>/features/
        ?bbox=xmin,ymin,xmax,ymax   (optional, EPSG:3857)
        &limit=5000                  (optional, default 5000, max 10000)

    Returns a GeoJSON FeatureCollection for layers with geometry,
    or a JSON object with a 'rows' array for tabular layers.
    """
    try:
        layer = ETLVisualizerLayer.objects.select_related('session').get(id=layer_id)
    except ETLVisualizerLayer.DoesNotExist:
        return JsonResponse({'error': 'Layer not found'}, status=404)

    bbox_param = request.GET.get('bbox', '')
    try:
        offset = int(request.GET.get('offset', 0))
    except (ValueError, TypeError):
        offset = 0
    try:
        batch_size = min(int(request.GET.get('batch_size', 100000)), 500000)
    except (ValueError, TypeError):
        batch_size = 100000

    table_name = layer.table_name
    vis_schema = 'etl_visualizer'

    try:
        con = psycopg2.connect(
            user=GEOETL_DB["user"], password=GEOETL_DB["password"],
            host=GEOETL_DB["host"], port=GEOETL_DB["port"],
            database=GEOETL_DB["database"]
        )
        cur = con.cursor()

        if layer.has_geometry:
            # Get non-geom column names
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                  AND column_name != 'geom'
                  AND udt_name NOT IN ('geometry', 'geography')
                ORDER BY ordinal_position
                """,
                (vis_schema, table_name)
            )
            prop_cols = [row[0] for row in cur.fetchall()]

            prop_sql = sql.SQL(', ').join([sql.Identifier(c) for c in prop_cols])

            if bbox_param and ',' in bbox_param:
                try:
                    parts = [float(v) for v in bbox_param.split(',')]
                    xmin, ymin, xmax, ymax = parts[0], parts[1], parts[2], parts[3]
                    where_clause = sql.SQL(
                        "WHERE ST_Intersects(geom, ST_MakeEnvelope({xmin},{ymin},{xmax},{ymax},3857))"
                    ).format(
                        xmin=sql.Literal(xmin), ymin=sql.Literal(ymin),
                        xmax=sql.Literal(xmax), ymax=sql.Literal(ymax),
                    )
                except (ValueError, IndexError):
                    where_clause = sql.SQL("")
            else:
                where_clause = sql.SQL("")

            # Count total for pagination metadata
            count_q = sql.SQL(
                "SELECT COUNT(*) FROM {schema}.{tbl} {where}"
            ).format(
                schema=sql.Identifier(vis_schema),
                tbl=sql.Identifier(table_name),
                where=where_clause,
            )
            cur.execute(count_q)
            total = cur.fetchone()[0]

            query = sql.SQL(
                "SELECT gvsig_etl_rowid AS _rowid, {props}, ST_AsGeoJSON(geom) AS _geom_json "
                "FROM {schema}.{tbl} {where} "
                "ORDER BY gvsig_etl_rowid "
                "LIMIT {lim} OFFSET {off}"
            ).format(
                props=prop_sql,
                schema=sql.Identifier(vis_schema),
                tbl=sql.Identifier(table_name),
                where=where_clause,
                lim=sql.Literal(batch_size),
                off=sql.Literal(offset),
            )
            cur.execute(query)
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]

            features = []
            for row in rows:
                props = {}
                geom_json = None
                for i, col in enumerate(col_names):
                    if col == '_geom_json':
                        geom_json = row[i]
                    else:
                        val = row[i]
                        if hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        props[col] = val
                if geom_json:
                    features.append({
                        'type': 'Feature',
                        'geometry': json.loads(geom_json),
                        'properties': props,
                    })

            result = {
                'type': 'FeatureCollection',
                'features': features,
                'total': total,
                'offset': offset,
                'batch_size': batch_size,
            }
            cur.close()
            con.close()
            return JsonResponse(result)

        else:
            # Tabular data — no geometry
            count_q = sql.SQL("SELECT COUNT(*) FROM {schema}.{tbl}").format(
                schema=sql.Identifier(vis_schema),
                tbl=sql.Identifier(table_name),
            )
            cur.execute(count_q)
            total = cur.fetchone()[0]

            query = sql.SQL(
                "SELECT * FROM {schema}.{tbl} "
                "ORDER BY gvsig_etl_rowid "
                "LIMIT {lim} OFFSET {off}"
            ).format(
                schema=sql.Identifier(vis_schema),
                tbl=sql.Identifier(table_name),
                lim=sql.Literal(batch_size),
                off=sql.Literal(offset),
            )
            cur.execute(query)
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]

            result_rows = []
            for row in rows:
                r = {}
                for i, col in enumerate(col_names):
                    val = row[i]
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    r[col] = val
                result_rows.append(r)

            cur.close()
            con.close()
            return JsonResponse({'rows': result_rows, 'columns': col_names, 'total': total, 'offset': offset})

    except Exception as e:
        logger.exception("etl_visualizer_layer_features error: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


# ---------------------------------------------------------------------------
# featureapi-compatible proxy views for ETL Visualizer layers
# ---------------------------------------------------------------------------
#
# Architecture note:
#   The actual SQL logic lives in plugin_featureapi.api_geojson_layer as pure
#   Python functions that accept (request, layer, con).  This plugin owns the
#   HTTP endpoints, resolves ETLVisualizerLayer, opens the DB connection, and
#   delegates to those functions.  This way plugin_featureapi has zero
#   dependency on plugin_geoetl.
#
# URL prefix (registered in plugin_geoetl/urls.py):
#   /etl/geojson/<layer_id>/layers/<dummy>/...
#
# Frontend featureapi_endpoint in etl-visualizer/Utils.js:
#   /etl/geojson/${etlLayerId}
# ---------------------------------------------------------------------------

from gvsigol_plugin_featureapi import api_geojson_layer as featureapi_geojson

ETL_VISUALIZER_SCHEMA = 'etl_visualizer'


def _etl_layer_resolve_and_connect(layer_id):
    """
    Resolve an ETLVisualizerLayer by id and open a psycopg2 connection.

    Returns (layer, con) where layer exposes .table_name, .schema and
    .has_geometry — the duck-type interface expected by featureapi_geojson
    functions — or (None, None) if the layer does not exist.
    """
    try:
        layer = ETLVisualizerLayer.objects.get(id=layer_id)
    except ETLVisualizerLayer.DoesNotExist:
        return None, None

    # Attach the schema attribute that featureapi functions expect.
    # ETLVisualizerLayer stores its data in the dedicated visualizer schema.
    layer.schema = ETL_VISUALIZER_SCHEMA

    con = psycopg2.connect(
        user=GEOETL_DB["user"], password=GEOETL_DB["password"],
        host=GEOETL_DB["host"], port=GEOETL_DB["port"],
        database=GEOETL_DB["database"],
    )
    return layer, con


def etl_geojson_features(request, layer_id, dummy=None):
    """Proxy → featureapi_geojson.geojson_layer_features."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    layer, con = _etl_layer_resolve_and_connect(layer_id)
    if layer is None:
        return JsonResponse({'error': 'Layer not found'}, status=404)
    return featureapi_geojson.geojson_layer_features(request, layer, con)


def etl_geojson_fieldoptions(request, layer_id, dummy=None):
    """Proxy → featureapi_geojson.geojson_layer_fieldoptions."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    layer, con = _etl_layer_resolve_and_connect(layer_id)
    if layer is None:
        return JsonResponse({'error': 'Layer not found'}, status=404)
    return featureapi_geojson.geojson_layer_fieldoptions(request, layer, con)


def etl_geojson_fieldoptions_paginated(request, layer_id, dummy=None):
    """Proxy → featureapi_geojson.geojson_layer_fieldoptions_paginated."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    layer, con = _etl_layer_resolve_and_connect(layer_id)
    if layer is None:
        return JsonResponse({'error': 'Layer not found'}, status=404)
    return featureapi_geojson.geojson_layer_fieldoptions_paginated(request, layer, con)


def etl_geojson_single_feature(request, layer_id, rowid, dummy=None):
    """Proxy → featureapi_geojson.geojson_layer_single_feature."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    layer, con = _etl_layer_resolve_and_connect(layer_id)
    if layer is None:
        return JsonResponse({'error': 'Layer not found'}, status=404)
    return featureapi_geojson.geojson_layer_single_feature(request, layer, con, rowid)


_PG_TYPE_MAP_GLOBAL = {
    'int2': 'integer', 'int4': 'integer', 'int8': 'integer',
    'float4': 'double', 'float8': 'double', 'numeric': 'double',
    'bool': 'boolean',
    'date': 'date', 'timestamp': 'date', 'timestamptz': 'date',
}
