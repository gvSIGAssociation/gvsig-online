# -*- coding: utf-8 -*-
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from gvsigol_auth.utils import superuser_required
from gvsigol_core.models import GolSettings

from gvsigol_plugin_sysadmin.models import SysadminTestRun
from gvsigol_plugin_sysadmin.tasks import run_sysadmin_tests
from gvsigol_plugin_sysadmin.test_registry import (
    discover_tests_payload,
    list_discovered_test_ids,
    validate_sysadmin_test_labels,
)

logger = logging.getLogger(__name__)


@login_required()
@superuser_required
def sysadmin_home(request):
    return render(request, 'sysadmin_home.html', {})


@login_required()
@superuser_required
def sysadmin_tests(request):
    return render(request, 'sysadmin_tests.html', {})


@login_required()
@superuser_required
def tests_discover(request):
    """JSON inventory of discoverable tests for the sysadmin UI."""
    return JsonResponse(discover_tests_payload())


def _dt_iso(dt):
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except AttributeError:
        return None


def _run_to_dict(run):
    return {
        'id': run.id,
        'status': run.status,
        'labels': run.labels,
        'filters': run.filters,
        'started_at': _dt_iso(run.started_at),
        'finished_at': _dt_iso(run.finished_at),
        'return_code': run.return_code,
        'stdout': run.stdout,
        'stderr': run.stderr,
        'summary': run.summary,
    }


@login_required()
@superuser_required
@require_POST
def tests_run(request):
    """Create a SysadminTestRun and enqueue Celery task (subprocess manage.py test)."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, TypeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    labels = body.get('labels')
    filters = body.get('filters', {})

    if not isinstance(labels, list) or not all(
        isinstance(x, str) for x in labels
    ):
        return JsonResponse(
            {'error': 'Field "labels" must be a list of strings'},
            status=400,
        )
    if filters is not None and not isinstance(filters, dict):
        return JsonResponse(
            {'error': 'Field "filters" must be a JSON object'},
            status=400,
        )

    stripped = [x.strip() for x in labels if x and str(x).strip()]
    if not stripped:
        return JsonResponse(
            {'error': 'At least one non-empty test label is required'},
            status=400,
        )

    allowed = frozenset(list_discovered_test_ids())
    ok, err, unknown = validate_sysadmin_test_labels(stripped, allowed)
    if not ok:
        if unknown:
            return JsonResponse(
                {'error': err or 'Unknown test label(s)', 'unknown': unknown},
                status=400,
            )
        return JsonResponse({'error': err or 'Invalid labels'}, status=400)

    with transaction.atomic():
        locked = SysadminTestRun.objects.select_for_update().filter(
            status=SysadminTestRun.STATUS_RUNNING
        )
        if locked.exists():
            return JsonResponse(
                {
                    'error': 'A test run is already in progress; wait for it to finish.',
                },
                status=409,
            )
        run = SysadminTestRun.objects.create(
            requested_by=request.user,
            labels=stripped,
            filters=filters or {},
            status=SysadminTestRun.STATUS_PENDING,
        )
        transaction.on_commit(lambda rid=run.id: run_sysadmin_tests.delay(rid))

    payload = _run_to_dict(run)
    payload['message'] = 'Run queued'
    return JsonResponse(payload, status=201)


@login_required()
@superuser_required
def tests_status(request, run_id):
    """JSON status for polling a SysadminTestRun."""
    try:
        run = SysadminTestRun.objects.get(pk=run_id)
    except SysadminTestRun.DoesNotExist:
        return JsonResponse({'error': 'Run not found'}, status=404)
    return JsonResponse(_run_to_dict(run))


@login_required()
@superuser_required
def gol_settings(request):
    """
    View/edit GolSettings (runtime key/value per plugin_name).
    Changes are audited via Django messages and the application log on save/delete.
    """
    items = GolSettings.objects.all().order_by('plugin_name', 'key')
    return render(request, 'sysadmin_gol_settings.html', {'items': items})


@login_required()
@superuser_required
@require_POST
def gol_settings_save(request):
    """Create or update a GolSettings row."""
    plugin_name = request.POST.get('plugin_name', '').strip()
    key = request.POST.get('key', '').strip()
    value = request.POST.get('value', '')
    if not plugin_name or not key:
        messages.error(request, 'plugin_name and key are required.')
        return redirect('sysadmin_gol_settings')
    GolSettings.objects.set_value(plugin_name, key, value)
    logger.info(
        'sysadmin GolSettings save user=%s plugin=%s key=%s',
        getattr(request.user, 'username', ''),
        plugin_name,
        key,
    )
    messages.success(
        request, 'Saved GolSettings %s / %s' % (plugin_name, key),
    )
    return redirect('sysadmin_gol_settings')


@login_required()
@superuser_required
@require_POST
def gol_settings_delete(request):
    plugin_name = request.POST.get('plugin_name', '').strip()
    key = request.POST.get('key', '').strip()
    if not plugin_name or not key:
        messages.error(request, 'plugin_name and key are required.')
        return redirect('sysadmin_gol_settings')
    deleted, _ = GolSettings.objects.filter(
        plugin_name=plugin_name,
        key=key,
    ).delete()
    if deleted:
        logger.info(
            'sysadmin GolSettings delete user=%s plugin=%s key=%s',
            getattr(request.user, 'username', ''),
            plugin_name,
            key,
        )
        messages.success(
            request, 'Deleted GolSettings %s / %s' % (plugin_name, key),
        )
    else:
        messages.warning(request, 'No matching row to delete.')
    return redirect('sysadmin_gol_settings')


@login_required()
@superuser_required
@require_POST
def gol_settings_create(request):
    """Create only if (plugin_name, key) does not exist yet."""
    plugin_name = request.POST.get('plugin_name', '').strip()
    key = request.POST.get('key', '').strip()
    value = request.POST.get('value', '')
    if not plugin_name or not key:
        messages.error(request, 'plugin_name and key are required.')
        return redirect('sysadmin_gol_settings')
    if GolSettings.objects.filter(plugin_name=plugin_name, key=key).exists():
        messages.error(
            request,
            'That key already exists for this plugin; use Save on the row below.',
        )
        return redirect('sysadmin_gol_settings')
    GolSettings.objects.set_value(plugin_name, key, value)
    logger.info(
        'sysadmin GolSettings create user=%s plugin=%s key=%s',
        getattr(request.user, 'username', ''),
        plugin_name,
        key,
    )
    messages.success(
        request,
        'Created GolSettings %s / %s' % (plugin_name, key),
    )
    return redirect('sysadmin_gol_settings')
