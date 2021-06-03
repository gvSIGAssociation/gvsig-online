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

from gvsigol_plugin_trip_planner import tasks
from .models import GTFSProvider, APPMobileConfig
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from gvsigol_auth.utils import superuser_required, staff_required
from .forms_services import GtfsProviderForm, GtfsProviderUpdateForm, GtfsCrontabForm, APPMobileConfigUpdateForm
from gvsigol import settings
from gvsigol_plugin_trip_planner.utils import *
import json

from datetime import datetime, timedelta

from gvsigol.settings import INSTALLED_APPS, CRONTAB_ACTIVE
import threading
import schedule
import time

from . import settings as priv_settings
from django.apps import apps
from gvsigol_plugin_trip_planner.settings import GTFS_SCRIPT

from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule




@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def gtfs_provider_list(request):
    ls = []

    providers = None
    if request.user.is_superuser:
        providers = GTFSProvider.objects.order_by('name')


    aux = priv_settings.GTFS_CRONTAB.split(" ")

    response = {
        'providers': providers,
        'cron_hour': aux[0],
        'cron_minutes': aux[1]
    }
    return render(request, 'gtfs_provider_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def gtfs_provider_add(request):
    if request.method == 'POST':
        form = GtfsProviderForm(request.POST, request.FILES)
        has_errors = False
        try:
            newProvider = GTFSProvider()

            name = request.POST.get('name')
            newProvider.name = name
            newProvider.description = request.POST.get('description')
            newProvider.url = request.POST.get('url')

            newProvider.save()
            return redirect('gtfs_provider_list')

        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: provider could not be published")
            form.add_error(None, msg)

    else:
        form = GtfsProviderForm()
        providers = None
        if request.user.is_superuser:
            providers = GTFSProvider.objects.all()


    return render(request,'gtfs_provider_add.html',{'form': form })

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def gtfs_provider_update(request, provider_id):
    provider = GTFSProvider.objects.get(id=provider_id)

    if provider==None:
        return HttpResponseNotFound(_('GTFS Provider not found'))

    if request.method == 'POST':
        form = GtfsProviderUpdateForm(request.POST)

        if form.is_valid():
            provider.name = form.cleaned_data['name']
            provider.description = form.cleaned_data['description']
            provider.url = form.cleaned_data['url']
            provider.is_active = form.cleaned_data['is_active']

            provider.save()
            return redirect('gtfs_provider_list')
    else:
        form = GtfsProviderUpdateForm(instance=provider)
        form.fields['name'].initial = provider.name
        form.fields['description'].initial = provider.description
        form.fields['url'].initial = provider.url
        form.fields['is_active'].initial = provider.is_active


    context = {
        'form': form,
        'provider_id': provider.id,
        'name': provider.name,
        'description': provider.description,
        'url': provider.url
    }

    return render(request, 'gtfs_provider_update.html', context)

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def gtfs_provider_delete(request, provider_id):
    try:
        provider = GTFSProvider.objects.get(pk=provider_id)
        provider.delete()
        #set_providers_actives()
#         set_providers_to_geocoder()

    except Exception as e:
        return HttpResponse('Error deleting provider: ' + str(e), status=500)

    return redirect('gtfs_provider_list')

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def gtfs_crontab_update(request):
    try:
#         file_cron = CronTab(tabfile='gtfs_tasks.tab')
#         job  = file_cron.new(command='javac') #TODO: run Graph creation
#         #TODO: Pick values from request:
#         job.setall('0 2 * * *') # 2 AM every night

        # If this is a POST request then process the Form data
        if request.method == 'POST':
            my_task_name = 'gvsigol_plugin_trip_planner.trip_planner_refresh'
            try:
                periodicTask  = PeriodicTask.objects.get(name = my_task_name)
            except:
                periodicTask = None
            
            if periodicTask:
                cronid = periodicTask.crontab_id
                interid = periodicTask.interval_id

                if interid:
                    intervalSchedule = IntervalSchedule.objects.get(id = interid)
                    intervalSchedule.delete()
                else:
                    crontabSchedule = CrontabSchedule.objects.get(id = cronid)
                    crontabSchedule.delete()

                periodicTask.delete()                  
            
            """hh = int(request.POST.get('cron_hour'))
            mm = int(request.POST.get('cron_minutes'))
            if ((hh < 0) or (hh > 23)):
                return HttpResponse('Hours field is not correct:' + str(hh), status=500)
            if ((mm < 0) or (mm > 59)):
                return HttpResponse('Hours field is not correct:' + str(hh), status=500)
            # process the data in form.cleaned_data as required (here we just write it to the model due_back field)
            crontab_text = "{0} {1} * * *".format(hh, mm)
            priv_settings.GTFS_CRONTAB = crontab_text

            aux = crontab_text.split(" ")
            tAux = "{0}:{1}:00".format(aux[0], aux[1])
            t = datetime.strptime(tAux, '%H:%M:%S')
            my_app_config = apps.get_app_config('gvsigol_plugin_trip_planner')
            my_app_config.initialize_trip_planner_gtfs_cron(CRONTAB_ACTIVE, t, 1, 'days')"""
            
            if request.POST.get('program-day') != 'every':
                time = request.POST.get('program-time')
                mm = time.split(":")[1]
                hh = time.split(":")[0]

                days_of_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

                day_of_week = '*'
                for i in range(0, len(days_of_week)):
                    if request.POST.get('program-day') == days_of_week[i]:
                        day_of_week = str(i)
                
                schedule, _ = CrontabSchedule.objects.get_or_create(
                    minute=mm,
                    hour=hh,
                    day_of_week = day_of_week,
                    day_of_month='*',
                    month_of_year='*'
                )
                PeriodicTask.objects.create(
                    crontab=schedule,
                    name=my_task_name,
                    args=[0],
                    task='gvsigol_plugin_trip_planner.tasks.cron_trip_planner_refresh',
                )
            else:
                unit_program = request.POST.get('program-unit')
                if  unit_program == 'minutes':
                    unit_period = IntervalSchedule.MINUTES
                elif unit_program == 'days':
                    unit_period = IntervalSchedule.DAYS
                elif unit_program == 'hours':
                    unit_period = IntervalSchedule.HOURS
        
                schedule, created = IntervalSchedule.objects.get_or_create(
                    every = request.POST.get('program-interval'),
                    period = unit_period,
                )
                PeriodicTask.objects.create(
                    interval=schedule,
                    name=my_task_name,
                    args=[0],
                    task='gvsigol_plugin_trip_planner.tasks.cron_trip_planner_refresh',
                )

            
        else: # Update now
            tasks.cron_trip_planner_refresh.apply_async(args=[0])


    except Exception as e:
        return HttpResponse('Error with Celery:' + str(e), status=500)

    return redirect('gtfs_provider_list')



"""def initialize_trip_planner_cron(is_first_time=False):
    if CRONTAB_ACTIVE:
        print("INICIO INICIALIZACIÓN TAREAS PROGRAMADAS")
        print("Borrando tareas anteriores...")
        schedule.clear('trip-planner-tasks')

        # global my_app_config
        my_app_config = apps.get_app_config('gvsigol_plugin_trip_planner')
        t = datetime.strptime('02:00:00', '%H:%M:%S')

        my_app_config.initialize_trip_planner_gtfs_cron(CRONTAB_ACTIVE, t, 1, 'days')

        print("FIN INICIALIZACIÓN TAREAS PROGRAMADAS")"""


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def app_mobile_config_update(request):

    app_config = APPMobileConfig.objects.first()

    if request.method == 'POST':
        form = APPMobileConfigUpdateForm(request.POST)

        app_config = APPMobileConfig.objects.first()
        if not app_config:
            app_config = APPMobileConfig()

        if form.is_valid():
            app_config.name = form.cleaned_data['name']
            app_config.description = form.cleaned_data['description']
            if form.cleaned_data['params']:
                app_config.params = form.cleaned_data['params']

            app_config.save()

            context = {
                'form': form,
                'name': app_config.name,
                'description': app_config.description,
                'params':  app_config.params,
                'is_saved': True
            }

    else:
        form = APPMobileConfigUpdateForm(instance=app_config)


        if app_config:
            form.fields['name'].initial = app_config.name
            form.fields['description'].initial = app_config.description
            form.fields['params'].initial = app_config.params

            params = {}
            if app_config.params:
                params = app_config.params

            context = {
                'form': form,
                'name': app_config.name,
                'description': app_config.description,
                'params': params
            }
        else:
            context = {
                'form': form,
                'name': '',
                'description': '',
                'params': {}
            }

    return render(request, 'app_mobile_config_update.html', context)



@csrf_exempt
def get_app_mobile_config(request):
    app_config = APPMobileConfig.objects.first()
    if app_config != None:
        response = json.loads(app_config.params)
    else:
        response = {}

    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

