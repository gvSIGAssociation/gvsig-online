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

import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from gvsigol_auth.utils import superuser_required
from gvsigol_plugin_trip_planner import gtfs_files, tasks
from gvsigol_plugin_trip_planner.settings import GTFS_SCRIPT

from .forms_services import APPMobileConfigUpdateForm, GtfsProviderForm
from .models import APPMobileConfig, GTFSProvider, GTFSstatus

logger = logging.getLogger(__name__)

# celery crontab day_of_week: 0 = sunday
DAYS_OF_WEEK = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
INTERVAL_UNITS = {
    'minutes': IntervalSchedule.MINUTES,
    'hours': IntervalSchedule.HOURS,
    'days': IntervalSchedule.DAYS,
}


def _day_of_week_name(dow):
    """Convert a stored crontab day_of_week ('*', '1', 'monday', 'mon'...) to the form value."""
    if dow == '*':
        return 'all'
    if dow.isdigit() and 0 <= int(dow) <= 6:
        return DAYS_OF_WEEK[int(dow)]
    for name in DAYS_OF_WEEK:
        if dow.lower()[:3] == name[:3]:
            return name
    return 'all'


def _parse_config(params):
    if not params:
        return {}
    try:
        value = json.loads(params)
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


def _save_provider(form):
    """Save provider and uploaded file atomically: if the file cannot be written
    (permissions, disk full...) the provider is not created/modified."""
    try:
        with transaction.atomic():
            form.save()
        return True
    except OSError as e:
        logger.exception('Error saving GTFS file')
        form.add_error(None, _('The GTFS file could not be saved on the server: %(error)s') % {'error': e.strerror or e})
        return False


@login_required()
@superuser_required
def gtfs_provider_list(request):
    GTFSstatus.objects.get_or_create(name='update', defaults={'message': '', 'status': ''})

    response = {
        'providers': GTFSProvider.objects.order_by('name'),
        'schedule_enabled': False,
        'gtfs_script': GTFS_SCRIPT,
        'gtfs_dir': tasks.gtfs_dir(),
    }

    periodicTask = PeriodicTask.objects.filter(name=tasks.REFRESH_TASK_NAME).first()
    if periodicTask and periodicTask.enabled:
        response['schedule_enabled'] = True
        if periodicTask.interval:
            response['every'] = periodicTask.interval.every
            response['period'] = periodicTask.interval.period
        elif periodicTask.crontab:
            response['day_of_week'] = _day_of_week_name(periodicTask.crontab.day_of_week)
            response['hour'] = periodicTask.crontab.hour
            response['minute'] = periodicTask.crontab.minute

    return render(request, 'gtfs_provider_list.html', response)


@login_required()
@superuser_required
def gtfs_update_status(request):
    statusModel = GTFSstatus.objects.filter(name='update').first()
    updated = statusModel.updated if statusModel else None
    response = {
        'status': (statusModel.status or '') if statusModel else '',
        'message': (statusModel.message or '') if statusModel else '',
        'updated': date_format(timezone.localtime(updated), 'SHORT_DATETIME_FORMAT') if updated else '',
    }
    return JsonResponse(response)


@login_required()
@superuser_required
def gtfs_provider_add(request):
    if request.method == 'POST':
        form = GtfsProviderForm(request.POST, request.FILES)
        if form.is_valid() and _save_provider(form):
            return redirect('gtfs_provider_list')
    else:
        form = GtfsProviderForm(initial={'is_active': True})

    return render(request, 'gtfs_provider_add.html', {'form': form})


@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@superuser_required
def gtfs_provider_update(request, provider_id):
    provider = get_object_or_404(GTFSProvider, id=provider_id)

    if request.method == 'POST':
        form = GtfsProviderForm(request.POST, request.FILES, instance=provider)
        if form.is_valid() and _save_provider(form):
            return redirect('gtfs_provider_list')
    else:
        form = GtfsProviderForm(instance=provider)

    context = {
        'form': form,
        'provider': provider,
        'has_file': gtfs_files.has_source(provider.id),
        'provider_id': provider.id,
        'name': provider.name,
        'description': provider.description,
        'url': provider.url
    }
    return render(request, 'gtfs_provider_update.html', context)


@login_required()
@require_POST
@superuser_required
def gtfs_provider_delete(request, provider_id):
    provider = get_object_or_404(GTFSProvider, pk=provider_id)
    provider.delete()
    gtfs_files.delete_source(provider_id)
    return JsonResponse({'success': True})


@login_required()
@require_POST
@superuser_required
def gtfs_crontab_update(request):
    """Create/update the refresh PeriodicTask. Only the PeriodicTask is modified:
    schedules are shared between tasks (get_or_create) and must never be deleted here."""
    enabled = bool(request.POST.get('repeat_periodically'))
    program_day = request.POST.get('program-day', 'all')

    crontab = None
    interval = None
    if program_day == 'every':
        unit = INTERVAL_UNITS.get(request.POST.get('program-unit'))
        try:
            every = int(request.POST.get('program-interval', ''))
        except ValueError:
            every = 0
        if enabled and (unit is None or every < 1):
            return HttpResponseBadRequest(_('Invalid interval'))
        if unit is not None and every >= 1:
            interval, _created = IntervalSchedule.objects.get_or_create(every=every, period=unit)
    else:
        t = None
        for fmt in ('%H:%M', '%H:%M:%S'):
            try:
                t = datetime.strptime(request.POST.get('program-time', ''), fmt)
                break
            except ValueError:
                pass
        if enabled and t is None:
            return HttpResponseBadRequest(_('Invalid time'))
        if program_day != 'all' and program_day not in DAYS_OF_WEEK:
            return HttpResponseBadRequest(_('Invalid day of week'))
        if t is not None:
            day_of_week = '*' if program_day == 'all' else str(DAYS_OF_WEEK.index(program_day))
            crontab, _created = CrontabSchedule.objects.get_or_create(
                minute=str(t.minute),
                hour=str(t.hour),
                day_of_week=day_of_week,
                day_of_month='*',
                month_of_year='*'
            )

    periodicTask = PeriodicTask.objects.filter(name=tasks.REFRESH_TASK_NAME).first()
    if periodicTask is None:
        if not (crontab or interval):
            # nothing to schedule and nothing to disable
            return redirect('gtfs_provider_list')
        periodicTask = PeriodicTask(name=tasks.REFRESH_TASK_NAME, task=tasks.REFRESH_TASK, args='[0]')

    if crontab or interval:
        periodicTask.crontab = crontab
        periodicTask.interval = interval
    # Disable instead of deleting: setup_periodic_tasks would recreate it on worker start.
    periodicTask.enabled = enabled
    periodicTask.save()

    return redirect('gtfs_provider_list')


@login_required()
@require_POST
@superuser_required
def gtfs_update_now(request):
    try:
        # manual update: rebuild the graph even if no GTFS feed changed
        tasks.cron_trip_planner_refresh.apply_async(args=[0], kwargs={'force': True})
    except Exception as e:
        logger.exception('Error launching trip planner refresh')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': True})


@login_required()
@superuser_required
def app_mobile_config_update(request):
    app_config = APPMobileConfig.objects.first()
    is_saved = False

    if request.method == 'POST':
        form = APPMobileConfigUpdateForm(request.POST, instance=app_config)
        if form.is_valid():
            app_config = form.save(commit=False)
            if not form.cleaned_data['params'] and app_config.pk:
                # keep the previous configuration if none was sent
                app_config.params = APPMobileConfig.objects.get(pk=app_config.pk).params
            app_config.save()
            is_saved = True
            params = app_config.params
        else:
            # re-display what the user sent (if parseable)
            params = request.POST.get('params') or (app_config.params if app_config else '')
    else:
        form = APPMobileConfigUpdateForm(instance=app_config)
        params = app_config.params if app_config else ''

    context = {
        'form': form,
        'config': _parse_config(params),
        'is_saved': is_saved,
    }
    return render(request, 'app_mobile_config_update.html', context)


# Public endpoint consumed by the mobile app.
@csrf_exempt
def get_app_mobile_config(request):
    app_config = APPMobileConfig.objects.first()
    response = _parse_config(app_config.params) if app_config else {}
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
