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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from gvsigol_core.utils import get_supported_crs, get_user_projects, get_user_applications, get_available_tools
from gvsigol_symbology.models import StyleLayer
from gdaltools.metadata import project
from gvsigol_core.models import SharedView
from django.http.response import JsonResponse
from gvsigol_core import forms
from gvsigol.basetypes import CloneConf
from gvsigol_auth import auth_backend
from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.http import FileResponse
from .models import Project, ProjectLayerGroup, ProjectRole, Application, ApplicationRole, UserHomeOrder
from gvsigol_services.models import Server, Workspace, Datastore, Layer, LayerGroup, ServiceUrl, LayerReadRole, LayerGroupRole, SqlView
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse
from gvsigol_auth.utils import superuser_required, is_superuser, staff_required, get_primary_user_role_details
from . import utils as core_utils
from gvsigol_services import geographic_servers, utils, backend_postgis
from gvsigol_services.utils import paginate
from django.views.decorators.cache import cache_control
from gvsigol import settings
from django.conf import settings as django_settings
import gvsigol_services.utils as services_utils
from operator import itemgetter
from django.core.mail import send_mail
from owslib.wmts import WebMapTileService
from django.utils import timezone
import gvsigol
from urllib.parse import urlparse, quote, unquote, urljoin
import random
import datetime
import string
import json
import ast
import re
import os
import uuid
import unicodedata

from django.views.decorators.clickjacking import xframe_options_exempt
from actstream import action
from actstream.models import Action
from iso639 import languages
from django.core.exceptions import PermissionDenied
from django.db.utils import OperationalError, ProgrammingError
from django.utils.crypto import get_random_string
from gvsigol_core.forms import CloneProjectForm
from django.contrib import messages
from django.shortcuts import redirect
from gvsigol_auth import signals
from gvsigol_core.middleware import GVSIGOL_SET_STATIC_CACHE_RESPONSE_KEY


_valid_projectname_regex=re.compile("^[a-zA-Z0-9_\-]+$")
import logging
logger = logging.getLogger("gvsigol")

def role_deleted_handler(sender, **kwargs):
    try:
        role = kwargs['role']
        ProjectRole.objects.filter(role=role).delete()
    except Exception as e:
        print(e)
        pass

def connect_signals():
    signals.role_deleted.connect(role_deleted_handler)

connect_signals()

def not_found_view(request):
    return render(request, '404.html', {}, status=404)

def forbidden_view(request):
    return render(request, 'illegal_operation.html', {}, status=403)

@login_required()
def home(request):
    hidden_prefix = getattr(settings, 'UI_HIDEN_PROJECTS_PREFIX', '')
    projects = []
    public_projects = []
    if request.user.is_superuser:
        query = Project.objects.filter(expiration_date__gte=datetime.datetime.now()) | Project.objects.filter(expiration_date=None)
    else:
        query = get_user_projects(request)
    for p in query.order_by('title'):
        if hidden_prefix and p.name.startswith(hidden_prefix):
            continue
        image = p.image_url
        project = {}
        project['id'] = p.id
        project['name'] = p.name
        project['title'] = p.title
        project['description'] = p.description
        project['image'] = unquote(image)
        project['url'] = p.url

        if p.is_public:
            project['item_type'] = 'public'
            public_projects.append(project)
        else:
            project['item_type'] = 'private'
            projects.append(project)

    applications = []
    if request.user.is_superuser:
        apps_query = Application.objects.all()
    else:
        apps_query = get_user_applications(request)
    for app in apps_query.order_by('title'):
        if hidden_prefix and app.name.startswith(hidden_prefix):
            continue
        applications.append({
            'id': app.id,
            'name': app.name,
            'title': app.title or app.name,
            'description': app.description or '',
            'image': app.image_url,
            'url': app.absurl,
            'item_type': 'app',
        })

    order_type = UserHomeOrder.ORDER_ALPHA
    all_items_ordered = None
    editing_scope = 'my_order'  # 'global' | 'my_order'; only superuser can use 'global'

    global_order = UserHomeOrder.objects.filter(user__isnull=True).first()
    user_order = UserHomeOrder.objects.filter(user=request.user).first()

    if request.user.is_superuser:
        scope = request.GET.get('scope') or ('my_order' if user_order else 'global')
        if scope not in ('global', 'my_order'):
            scope = 'my_order'
        editing_scope = scope
    else:
        scope = 'my_order'
    saved_order = global_order if scope == 'global' else (user_order or global_order)
    if saved_order:
        order_type = saved_order.order_type
    if order_type == UserHomeOrder.ORDER_MANUAL and saved_order and saved_order.order_data:
        try:
            order_list = json.loads(saved_order.order_data)
            lookup = {}
            for p in projects:
                lookup[('private', p['id'])] = p
            for p in public_projects:
                lookup[('public', p['id'])] = p
            for a in applications:
                lookup[('app', a['id'])] = a
            seen = set()
            all_items_ordered = []
            for entry in order_list:
                key = (entry['type'], entry['id'])
                if key in lookup and key not in seen:
                    all_items_ordered.append(lookup[key])
                    seen.add(key)
            # append new items not yet in saved order
            for key, item in lookup.items():
                if key not in seen:
                    all_items_ordered.append(item)
        except Exception:
            all_items_ordered = None
    elif order_type == UserHomeOrder.ORDER_ALPHA:
        def _sort_key_no_accents(s):
            if not s:
                return ''
            nfd = unicodedata.normalize('NFD', (s or '').lower())
            return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
        all_items_ordered = list(projects) + list(public_projects) + list(applications)
        all_items_ordered.sort(key=lambda item: _sort_key_no_accents(item.get('title') or item.get('name') or ''))

    manage_passwords_url = getattr(settings, 'MANAGE_PASSWORD_URL', None)
    if settings.AUTH_DASHBOARD_UI:        
        if 'AD' in settings.GVSIGOL_LDAP and settings.GVSIGOL_LDAP['AD']:
            allow_password_update = False
        else:
            allow_password_update = True
    else:
        allow_password_update = (manage_passwords_url is not None)
    if settings.USE_SPA_PROJECT_LINKS:
        useClassicViewer = False
    else:
        useClassicViewer = True

    return render(request, 'home.html', {
        'projects': projects,
        'public_projects': public_projects,
        'applications': applications,
        'all_items_ordered': all_items_ordered,
        'order_type': order_type,
        'editing_scope': editing_scope,
        'allow_password_update': allow_password_update,
        'manage_passwords_url': manage_passwords_url,
        'use_classic_viewer': useClassicViewer,
        'has_hidden_items': bool(hidden_prefix),
    })


@login_required()
def home_order_get(request):
    scope = request.GET.get('scope', 'my_order')
    if scope == 'global' and not request.user.is_superuser:
        scope = 'my_order'
    if scope == 'global' and request.user.is_superuser:
        saved = UserHomeOrder.objects.filter(user__isnull=True).first()
    else:
        saved = UserHomeOrder.objects.filter(user=request.user).first()
        if not saved:
            saved = UserHomeOrder.objects.filter(user__isnull=True).first()
    if saved:
        return JsonResponse({'order_type': saved.order_type, 'order_data': saved.order_data or '[]'})
    return JsonResponse({'order_type': UserHomeOrder.ORDER_ALPHA, 'order_data': '[]'})


@login_required()
def home_order_save(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        order_type = body.get('order_type', UserHomeOrder.ORDER_ALPHA)
        order_data = body.get('order_data', [])
        scope = body.get('scope', 'my_order')
        if order_type not in (UserHomeOrder.ORDER_ALPHA, UserHomeOrder.ORDER_MANUAL):
            return JsonResponse({'success': False, 'error': 'Invalid order_type'}, status=400)
        if scope == 'global' and request.user.is_superuser:
            obj, _ = UserHomeOrder.objects.get_or_create(user=None, defaults={'order_type': order_type, 'order_data': json.dumps(order_data)})
        else:
            obj, _ = UserHomeOrder.objects.get_or_create(user=request.user)
        obj.order_type = order_type
        obj.order_data = json.dumps(order_data)
        obj.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required()
def home_hidden_items(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden()
    hidden_prefix = getattr(settings, 'UI_HIDEN_PROJECTS_PREFIX', '')
    if not hidden_prefix:
        return JsonResponse({'items': []})

    items = []
    if request.user.is_superuser:
        proj_query = Project.objects.filter(
            expiration_date__gte=datetime.datetime.now()
        ) | Project.objects.filter(expiration_date=None)
    else:
        proj_query = get_user_projects(request)
    for p in proj_query.filter(name__startswith=hidden_prefix).order_by('title'):
        items.append({
            'id': p.id,
            'name': p.name,
            'title': p.title,
            'description': p.description or '',
            'image': unquote(p.image_url),
            'url': p.url,
            'item_type': 'public' if p.is_public else 'private',
        })

    if request.user.is_superuser:
        apps_query = Application.objects.filter(name__startswith=hidden_prefix)
    else:
        apps_query = get_user_applications(request).filter(name__startswith=hidden_prefix)
    for app in apps_query.order_by('title'):
        items.append({
            'id': app.id,
            'name': app.name,
            'title': app.title or app.name,
            'description': app.description or '',
            'image': app.image_url,
            'url': app.absurl,
            'item_type': 'app',
        })

    return JsonResponse({'items': items})


@login_required()
@staff_required
def project_list(request):

    project_list_qs = None
    if request.user.is_superuser:
        project_list_qs = Project.objects.all()
    else:
        project_list_qs = get_user_projects(request, permissions=[ProjectRole.PERM_READ, ProjectRole.PERM_MANAGE])

    # Aplicar búsqueda si se proporciona el parámetro 'search'
    search_query = request.GET.get('search', '').strip()
    if search_query:
        project_list_qs = project_list_qs.filter(
            Q(name__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Paginar antes de construir los diccionarios
    page_projects, page_ctx = paginate(
        request,
        project_list_qs,
        default_page_size=10,
        max_page_size=200,
        page_param="page",
        page_size_param="page_size",
    )

    projects = []
    for p in page_projects:
        project = {}
        project['id'] = p.id
        project['name'] = p.name
        project['title'] = p.title
        project['description'] = p.description
        project['is_public'] = p.is_public
        can_manage = 'true' if p.can_manage(request) else 'false'
        project['can_manage'] = can_manage
        projects.append(project)

    # temporalmente mostramos todos los proyectos ignorando VIEWER_UI_CHOICES para poder comparar
    #show_bootstrap_project_links = Project.BOOTSTRAP_UI in settings.VIEWER_UI_CHOICES
    #show_spa_project_links = Project.REACT_SPA_UI in settings.VIEWER_UI_CHOICES
    show_bootstrap_project_links = True
    show_spa_project_links = True
    
    frontend_base_url = settings.FRONTEND_BASE_URL.rstrip('/')

    response = {
        'projects': projects,
        'servers': Server.objects.all().order_by('-default'),
        'frontend_base_url': frontend_base_url,
        'SHOW_SPA_PROJECT_LINKS': show_spa_project_links,
        'SHOW_BOOTSTRAP_PROJECT_LINKS': show_bootstrap_project_links,
        'request': request,
        'search_query': search_query,
        **page_ctx,  # Agrega paginator/page_obj/page_size/etc al template
    }
    return render(request, 'project_list.html', response)


@login_required()
@staff_required
def project_package_export_preflight(request, pid):
    """JSON inventory for export wizard (foreign layers, permissions prompt)."""
    from django.http import JsonResponse
    from gvsigol_core.project_package.connection_utils import analyze_project_layers

    try:
        project = Project.objects.get(id=int(pid))
    except Project.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
    if not project.can_manage(request):
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
    return JsonResponse({'ok': True, **analyze_project_layers(project)})


@login_required()
@staff_required
@require_http_methods(['GET', 'POST'])
def project_package_export(request, pid):
    """
    ZIP export (async): creates a ProjectPackageExportJob, fires the Celery task and
    redirects to the status/progress page. The user downloads the ZIP from there.

    POST accepts export_permissions and layer_vector_mode_<layer_id> fields from the wizard.
    """
    from gvsigol_core.models import ProjectPackageExportJob
    from gvsigol_core.project_package.tasks import export_project_task

    try:
        project = Project.objects.get(id=int(pid))
    except Project.DoesNotExist:
        messages.error(request, _('Operation not allowed on this project.'))
        return redirect('project_list')
    if not project.can_manage(request):
        messages.error(request, _('Operation not allowed on this project.'))
        return redirect('project_list')

    export_options = {}
    if request.method == 'POST':
        export_options['export_permissions'] = bool(request.POST.get('export_permissions'))
        export_options['include_raster_sidecars'] = bool(request.POST.get('include_raster_sidecars'))
        export_options['include_tools'] = bool(request.POST.get('include_tools'))
        layer_modes = {}
        for key, val in request.POST.items():
            if key.startswith('layer_vector_mode_') and val in ('embedded', 'definition_only', 'view_sql_definition'):
                lid = key[len('layer_vector_mode_'):]
                layer_modes[lid] = val
        export_options['layer_vector_modes'] = layer_modes

    job = ProjectPackageExportJob.objects.create(
        created_by=request.user.username,
        project_id=project.id,
        project_name=(project.title or project.name)[:200],
        export_options_json=export_options,
    )
    try:
        export_project_task.apply_async(kwargs={
            'export_job_id': str(job.id),
            'pid': pid,
            'export_options': export_options,
            'username': request.user.username,
        })
    except Exception:
        logger.exception('project_package_export: could not enqueue task (job %s)', job.id)
    return redirect('project_package_activity_log')


@login_required()
@staff_required
def export_job_status(request, job_id):
    """Progress page for an async export job."""
    from gvsigol_core.models import ProjectPackageExportJob

    job = get_object_or_404(ProjectPackageExportJob, pk=job_id)
    if job.created_by != request.user.username and not request.user.is_superuser:
        raise PermissionDenied
    return render(request, 'project_package_job_status.html', {
        'job': job,
        'job_type': 'export',
        'status_json_url': reverse('export_job_status_json', kwargs={'job_id': job_id}),
    })


@login_required()
@staff_required
def export_job_status_json(request, job_id):
    """JSON status endpoint polled by the progress page."""
    from django.http import JsonResponse
    from gvsigol_core.models import ProjectPackageExportJob

    job = get_object_or_404(ProjectPackageExportJob, pk=job_id)
    if job.created_by != request.user.username and not request.user.is_superuser:
        return JsonResponse({'error': 'forbidden'}, status=403)

    summary = job.summary_json or {}
    export_errors = summary.get('export_errors') or []
    data = {
        'status': job.status,
        'project_name': job.project_name,
        'export_errors': export_errors,
    }
    if job.status == ProjectPackageExportJob.ST_DONE:
        data['download_url'] = reverse('export_job_download', kwargs={'job_id': job_id})
        data['zip_filename'] = job.zip_filename
    elif job.status == ProjectPackageExportJob.ST_FAILED:
        data['error'] = summary.get('error', _('Export failed. Check server logs.'))
    return JsonResponse(data)


@login_required()
@staff_required
def export_job_download(request, job_id):
    """Serve the export ZIP once the task is done."""
    from gvsigol_core.models import ProjectPackageExportJob

    job = get_object_or_404(ProjectPackageExportJob, pk=job_id)
    if job.created_by != request.user.username and not request.user.is_superuser:
        raise PermissionDenied
    if job.status != ProjectPackageExportJob.ST_DONE or not job.zip_path:
        messages.error(request, _('Export is not ready for download.'))
        return redirect('export_job_status', job_id=job_id)
    resp = FileResponse(open(job.zip_path, 'rb'), as_attachment=True, filename=job.zip_filename or 'export.zip')
    resp['Content-Type'] = 'application/zip'
    return resp


@login_required()
@staff_required
def import_job_status(request, job_id):
    """Progress page for an async import job."""
    from gvsigol_core.models import ProjectPackageImportJob

    job = get_object_or_404(ProjectPackageImportJob, pk=job_id)
    if job.created_by != request.user.username and not request.user.is_superuser:
        raise PermissionDenied
    return render(request, 'project_package_job_status.html', {
        'job': job,
        'job_type': 'import',
        'status_json_url': reverse('import_job_status_json', kwargs={'job_id': job_id}),
    })


@login_required()
@staff_required
def import_job_status_json(request, job_id):
    """JSON status endpoint polled by the progress page for an import job."""
    from django.http import JsonResponse
    from gvsigol_core.models import ProjectPackageImportJob

    job = get_object_or_404(ProjectPackageImportJob, pk=job_id)
    if job.created_by != request.user.username and not request.user.is_superuser:
        return JsonResponse({'error': 'forbidden'}, status=403)

    summary = job.summary_json or {}
    status = job.status
    data = {
        'status': status,
        'project_name': (job.manifest_json or {}).get('project_name', ''),
    }
    if status == ProjectPackageImportJob.ST_COMMITTED:
        data['status'] = 'done'
        data['result_url'] = reverse('project_package_import_result', kwargs={'job_id': job_id})
        if summary.get('skipped_layers'):
            data['warning'] = str(_('Project imported with warnings. Some layers were skipped — see the import report.'))
    elif status == ProjectPackageImportJob.ST_FAILED:
        data['error'] = summary.get('error', str(_('Import failed. Check server logs.')))
    return JsonResponse(data)


@login_required()
@staff_required
def activity_log_inprogress_json(request):
    """
    AJAX endpoint that returns current in-progress export/import jobs with Celery progress.
    Used by the activity log page for non-flickering live updates.
    """
    from django.http import JsonResponse
    from django.utils import timezone
    from datetime import timedelta
    from gvsigol_core.models import ProjectPackageExportJob, ProjectPackageImportJob

    cutoff = timezone.now() - timedelta(hours=2)

    def _celery_progress(celery_task_id):
        """Read percent/step from Celery result backend if available."""
        if not celery_task_id:
            return None, None
        try:
            from celery.result import AsyncResult
            result = AsyncResult(celery_task_id)
            if result.state == 'PROGRESS':
                meta = result.info or {}
                return meta.get('percent'), meta.get('step', '')
            if result.state == 'SUCCESS':
                return 100, 'done'
        except Exception:
            pass
        return None, None

    exports = []
    for job in ProjectPackageExportJob.objects.filter(
        status__in=[ProjectPackageExportJob.ST_PENDING, ProjectPackageExportJob.ST_RUNNING],
        created_at__gte=cutoff,
    ).order_by('created_at'):
        percent, step = _celery_progress(job.celery_task_id)
        exports.append({
            'id': str(job.id),
            'status': job.status,
            'project_name': job.project_name or '\u2014',
            'created_at': job.created_at.strftime('%Y-%m-%d %H:%M'),
            'percent': percent,
            'step': step or '',
        })

    imports = []
    for job in ProjectPackageImportJob.objects.filter(
        status__in=[
            ProjectPackageImportJob.ST_DRAFT,
            ProjectPackageImportJob.ST_PREFLIGHT_OK,
            ProjectPackageImportJob.ST_RUNNING,
        ],
        created_at__gte=cutoff,
    ).order_by('created_at'):
        percent, step = _celery_progress(job.celery_task_id)
        project_name = ''
        if job.manifest_json:
            project_name = (job.manifest_json.get('source_project_name') or '')
        imports.append({
            'id': str(job.id),
            'status': job.status,
            'project_name': project_name or '\u2014',
            'created_at': job.created_at.strftime('%Y-%m-%d %H:%M'),
            'percent': percent,
            'step': step or '',
        })

    return JsonResponse({
        'exports': exports,
        'imports': imports,
        'has_in_progress': bool(exports or imports),
    })


@login_required()
@staff_required
@require_http_methods(['POST'])
def cancel_package_job(request, job_type, job_id):
    """Mark a stuck pending/running job as failed so it disappears from the in-progress list."""
    from gvsigol_core.models import ProjectPackageExportJob, ProjectPackageImportJob

    if job_type == 'export':
        job = get_object_or_404(ProjectPackageExportJob, pk=job_id)
        if job.created_by != request.user.username and not request.user.is_superuser:
            raise PermissionDenied
        job.status = ProjectPackageExportJob.ST_FAILED
        job.summary_json = {**(job.summary_json or {}), 'error': 'Cancelled by user'}
        job.save(update_fields=['status', 'summary_json'])
    elif job_type == 'import':
        job = get_object_or_404(ProjectPackageImportJob, pk=job_id)
        if job.created_by != request.user.username and not request.user.is_superuser:
            raise PermissionDenied
        job.status = ProjectPackageImportJob.ST_FAILED
        job.save(update_fields=['status'])
    return redirect('project_package_activity_log')


@login_required()
@staff_required
@require_http_methods(['GET', 'POST'])
def project_package_import(request):
    """
    Accept ZIP upload, store it, then continue in the import wizard (preflight + commit).
    """
    from gvsigol_core.models import ProjectPackageImportJob

    if request.method == 'POST':
        package = request.FILES.get('package')
        if not package:
            messages.error(request, _('No package file was selected.'))
            return redirect('project_list')
        incoming = os.path.join(django_settings.MEDIA_ROOT, 'project_packages', 'incoming')
        os.makedirs(incoming, exist_ok=True)
        job_id = uuid.uuid4()
        dest = os.path.join(incoming, str(job_id) + '.zip')
        try:
            with open(dest, 'wb') as out:
                for chunk in package.chunks():
                    out.write(chunk)
        except Exception:
            logger.exception('project_package_import save failed')
            messages.error(request, _('Could not store the package file.'))
            return redirect('project_list')
        try:
            ProjectPackageImportJob.objects.create(
                id=job_id,
                zip_path=dest,
                created_by=request.user.username,
                status=ProjectPackageImportJob.ST_DRAFT,
            )
        except (ProgrammingError, OperationalError):
            logger.exception('project_package_import: ProjectPackageImportJob table missing?')
            try:
                os.unlink(dest)
            except OSError:
                pass
            messages.error(
                request,
                _(
                    'Project package import is not set up in the database. '
                    'Run migrations on the server (for example: python manage.py migrate gvsigol_core).'
                ),
            )
            return redirect('project_list')
        return redirect('project_package_import_wizard', job_id=job_id)
    return redirect('project_list')


@login_required()
@staff_required
@require_http_methods(['GET', 'POST'])
def project_package_import_wizard(request, job_id):
    from gvsigol_core.project_package.import_service import preflight_job
    from gvsigol_core.models import ProjectPackageImportJob

    job = get_object_or_404(ProjectPackageImportJob, pk=job_id)
    if job.created_by != request.user.username and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        wiz = {
            'target_server_id': int(request.POST.get('target_server')),
        }
        foreign_connection_map = {}
        for key, val in request.POST.items():
            if key.startswith('foreign_connection_') and val:
                ck = key[len('foreign_connection_'):]
                try:
                    foreign_connection_map[ck] = int(val)
                except (TypeError, ValueError):
                    pass
        if foreign_connection_map:
            wiz['foreign_connection_map'] = foreign_connection_map
        gpkg_foreign_datastores = {}
        for key, val in request.POST.items():
            if key.startswith('gpkg_datastore_') and val:
                ck = key[len('gpkg_datastore_'):]
                try:
                    gpkg_foreign_datastores[ck] = int(val)
                except (TypeError, ValueError):
                    pass
        if gpkg_foreign_datastores:
            wiz['gpkg_foreign_datastores'] = gpkg_foreign_datastores
        skip_foreign_connections = []
        for key, val in request.POST.items():
            if key.startswith('skip_foreign_connection_') and val:
                skip_foreign_connections.append(key[len('skip_foreign_connection_'):])
        if skip_foreign_connections:
            wiz['skip_foreign_connection_keys'] = skip_foreign_connections
        skip_gpkg_connections = []
        for key, val in request.POST.items():
            if key.startswith('skip_gpkg_connection_') and val:
                skip_gpkg_connections.append(key[len('skip_gpkg_connection_'):])
        if skip_gpkg_connections:
            wiz['skip_gpkg_connection_keys'] = skip_gpkg_connections
        skip_gpkg_layers = []
        for key, val in request.POST.items():
            if key.startswith('skip_gpkg_layer_') and val:
                skip_gpkg_layers.append(key[len('skip_gpkg_layer_'):])
        if skip_gpkg_layers:
            wiz['skip_gpkg_layer_export_ids'] = skip_gpkg_layers
        skip_rasters = []
        for key, val in request.POST.items():
            if key.startswith('skip_raster_') and val:
                skip_rasters.append(key[len('skip_raster_'):])
        if skip_rasters:
            wiz['skip_raster_export_ids'] = skip_rasters
        skip_externals = []
        for key, val in request.POST.items():
            if key.startswith('skip_external_') and val:
                skip_externals.append(key[len('skip_external_'):])
        if skip_externals:
            wiz['skip_external_export_ids'] = skip_externals
        skip_view_layers = []
        for key, val in request.POST.items():
            if key.startswith('skip_view_layer_') and val:
                skip_view_layers.append(key[len('skip_view_layer_'):])
        if skip_view_layers:
            wiz['skip_view_layer_export_ids'] = skip_view_layers
        view_sql_overrides = {}
        for key, val in request.POST.items():
            if key.startswith('view_sql_') and val.strip():
                eid = key[len('view_sql_'):]
                view_sql_overrides[eid] = val.strip()
        if view_sql_overrides:
            wiz['view_sql_overrides'] = view_sql_overrides
        # Target datastore overrides for local GPKG layers and SQL views
        local_ds_overrides = {}
        for key, val in request.POST.items():
            if key.startswith('local_ds_') and val:
                eid = key[len('local_ds_'):]
                try:
                    local_ds_overrides[eid] = int(val)
                except (TypeError, ValueError):
                    pass
        if local_ds_overrides:
            wiz['local_datastore_overrides'] = local_ds_overrides
        on = (request.POST.get('override_project_name') or '').strip()
        if on:
            wiz['override_project_name'] = on
        ot = (request.POST.get('override_project_title') or '').strip()
        if ot:
            wiz['override_project_title'] = ot
        job.wizard_json = wiz
        job.save()
        from gvsigol_core.project_package.tasks import import_project_task
        try:
            import_project_task.apply_async(kwargs={'import_job_id': str(job.id)})
        except Exception:
            logger.exception('project_package_import_wizard: could not enqueue task (job %s)', job.id)
        return redirect('project_package_activity_log')

    if job.status == ProjectPackageImportJob.ST_DRAFT:
        result = preflight_job(job)
        if not result.get('ok'):
            messages.error(request, _('Package validation failed: ') + ', '.join(result.get('errors', [])))

    from gvsigol_services.models import Connection, Datastore

    servers = Server.objects.all().order_by('-default')
    postgis_connections = Connection.objects.filter(type='PostGIS').order_by('name')
    package_layout = None
    if job.extract_dir:
        import json
        import os
        from gvsigol_core.project_package.constants import PROJECT_JSON
        from gvsigol_core.project_package.import_service import extract_snapshot_layout

        pj_path = os.path.join(job.extract_dir, PROJECT_JSON.replace('/', os.sep))
        if os.path.isfile(pj_path):
            with open(pj_path, 'r', encoding='utf-8') as f:
                package_layout = extract_snapshot_layout(json.load(f))
    if package_layout is None:
        for row in job.report_json or []:
            if isinstance(row, dict) and 'package_layout' in row:
                package_layout = row['package_layout']
                break
    wizard = job.wizard_json or {}
    foreign_map = wizard.get('foreign_connection_map') or {}
    gpkg_foreign_map = wizard.get('gpkg_foreign_datastores') or {}
    target_server_id = wizard.get('target_server_id')
    if not target_server_id and servers:
        target_server_id = servers[0].id
    server_datastores = []
    if target_server_id:
        from gvsigol_core.project_package.connection_utils import local_cartodb_datastores_for_server

        server_datastores = local_cartodb_datastores_for_server(target_server_id)
    import_report_warnings = []
    import_last_error = None
    for row in job.report_json or []:
        if not isinstance(row, dict):
            continue
        if row.get('warning'):
            import_report_warnings.append(row['warning'])
        if row.get('error') and not import_last_error:
            import_last_error = row['error']
        if row.get('fatal') and row.get('error'):
            import_last_error = row['error']

    if package_layout:
        for fc in package_layout.get('foreign_connections') or []:
            ck = fc.get('connection_key')
            if ck:
                fc['selected_connection_id'] = foreign_map.get(ck)
        gpkg_rows = package_layout.get('gpkg_connection_targets') or []
        package_layout['gpkg_local_targets'] = [r for r in gpkg_rows if not r.get('is_foreign_source')]
        package_layout['gpkg_foreign_targets'] = [r for r in gpkg_rows if r.get('is_foreign_source')]
        for row in gpkg_rows:
            ck = row.get('connection_key')
            if ck and row.get('is_foreign_source'):
                row['selected_datastore_id'] = gpkg_foreign_map.get(ck)
        # Propagate selected_datastore_id to individual gpkg_layers entries too,
        # so the inline dropdown in each row can pre-select the right datastore.
        for ly in package_layout.get('gpkg_layers') or []:
            ck = ly.get('connection_key')
            if ck and ly.get('is_foreign_source'):
                ly['selected_datastore_id'] = gpkg_foreign_map.get(ck)

        # For local layers and views: find if the exported workspace/datastore
        # already exists on the target server so the template can pre-select it
        # and warn when it will be newly created.
        ds_lookup = {
            (ds.workspace.name, ds.name): ds.id
            for ds in server_datastores
        }
        local_ds_overrides = (wizard.get('local_datastore_overrides') or {})
        for ly in package_layout.get('gpkg_layers') or []:
            if not ly.get('is_foreign_source'):
                eid = ly.get('export_id') or ''
                ly['existing_ds_id'] = ds_lookup.get(
                    (ly.get('exported_workspace', ''), ly.get('exported_datastore', ''))
                )
                ly['selected_local_ds_id'] = local_ds_overrides.get(eid) or ly['existing_ds_id']
        for v in package_layout.get('view_sql_layers') or []:
            eid = v.get('export_id') or ''
            v['existing_ds_id'] = ds_lookup.get(
                (v.get('exported_workspace', ''), v.get('exported_datastore', ''))
            )
            v['selected_local_ds_id'] = local_ds_overrides.get(eid) or v['existing_ds_id']
    recent_package_activity = []
    try:
        from gvsigol_core.project_package.activity_log import recent_package_activity as _recent_activity

        recent_package_activity = _recent_activity()
    except Exception:
        logger.exception('recent_package_activity')

    return render(
        request,
        'project_package_import_wizard.html',
        {
            'job': job,
            'servers': servers,
            'postgis_connections': postgis_connections,
            'server_datastores': server_datastores,
            'package_layout': package_layout,
            'wizard': wizard,
            'foreign_map': foreign_map,
            'import_report_warnings': import_report_warnings,
            'import_last_error': import_last_error,
            'recent_package_activity': recent_package_activity,
        },
    )


@login_required()
@staff_required
def project_package_import_result(request, job_id):
    """Import outcome: skipped layers, warnings, link to project."""
    from gvsigol_core.models import ProjectPackageImportJob
    from gvsigol_core.project_package.report_summary import summarize_import_report

    job = get_object_or_404(ProjectPackageImportJob, pk=job_id)
    if job.created_by != request.user.username and not request.user.is_superuser:
        raise PermissionDenied

    # Always regenerate from report_json so messages are translated in the
    # request locale.  summary_json was built inside the Celery task which has
    # no user locale, so it would always be in the server's default language.
    summary = summarize_import_report(job.report_json) if job.report_json else (job.summary_json or {})
    project = None
    if job.result_project_id:
        try:
            project = Project.objects.get(pk=job.result_project_id)
        except Project.DoesNotExist:
            project = None

    return render(
        request,
        'project_package_import_result.html',
        {
            'job': job,
            'summary': summary,
            'project': project,
        },
    )


@login_required()
@staff_required
def project_package_export_result(request, log_id):
    """Export outcome: technical log matching reports/export_log.jsonl in the ZIP."""
    from gvsigol_core.models import ProjectPackageActivityLog

    log_entry = get_object_or_404(
        ProjectPackageActivityLog,
        pk=log_id,
        operation=ProjectPackageActivityLog.OP_EXPORT,
    )
    if log_entry.created_by != request.user.username and not request.user.is_superuser:
        raise PermissionDenied

    summary = log_entry.summary_json or {}
    report_lines = summary.get('report_lines') or []

    project_obj = None
    if log_entry.project_id:
        try:
            project_obj = Project.objects.get(pk=log_entry.project_id)
        except Project.DoesNotExist:
            project_obj = None

    return render(
        request,
        'project_package_export_result.html',
        {
            'log_entry': log_entry,
            'summary': summary,
            'report_lines': report_lines,
            'project': project_obj,
        },
    )


@login_required()
@staff_required
def project_package_activity_log(request):
    """Last 20 import/export operations, plus any jobs still in progress."""
    from django.db.utils import OperationalError, ProgrammingError

    from gvsigol_core.project_package.activity_log import RECENT_ACTIVITY_LIMIT, get_package_report_rows
    from gvsigol_core.models import ProjectPackageExportJob, ProjectPackageImportJob

    migration_missing = False
    report_rows = []
    try:
        rows = get_package_report_rows(limit=RECENT_ACTIVITY_LIMIT)
        # Attach download URL for completed exports that still have a zip on disk
        for row in rows:
            ej_id = (row.get('summary') or {}).get('export_job_id')
            if ej_id:
                try:
                    ej = ProjectPackageExportJob.objects.get(pk=ej_id)
                    if ej.status == ProjectPackageExportJob.ST_DONE and ej.zip_path:
                        row['download_url'] = reverse('export_job_download', kwargs={'job_id': ej_id})
                        row['zip_filename'] = ej.zip_filename
                except ProjectPackageExportJob.DoesNotExist:
                    pass
        report_rows = rows
    except (ProgrammingError, OperationalError):
        migration_missing = True
    except Exception:
        logger.exception('project_package_activity_log')

    # In-progress jobs: only show those created in the last 2 hours to avoid
    # infinite refresh from orphaned/stuck jobs.
    from django.utils import timezone as _tz
    import datetime as _dt
    _cutoff = _tz.now() - _dt.timedelta(hours=2)
    in_progress_exports = []
    in_progress_imports = []
    try:
        in_progress_exports = list(
            ProjectPackageExportJob.objects
            .filter(
                status__in=[ProjectPackageExportJob.ST_PENDING, ProjectPackageExportJob.ST_RUNNING],
                created_at__gte=_cutoff,
            )
            .order_by('-created_at')[:10]
        )
        in_progress_imports = list(
            ProjectPackageImportJob.objects
            .filter(
                status__in=[
                    ProjectPackageImportJob.ST_DRAFT,
                    ProjectPackageImportJob.ST_PREFLIGHT_OK,
                    ProjectPackageImportJob.ST_RUNNING,
                ],
                created_at__gte=_cutoff,
            )
            .order_by('-created_at')[:10]
        )
    except Exception:
        pass

    has_in_progress = bool(in_progress_exports or in_progress_imports)
    return render(
        request,
        'project_package_activity_log.html',
        {
            'report_rows': report_rows,
            'limit': RECENT_ACTIVITY_LIMIT,
            'migration_missing': migration_missing,
            'in_progress_exports': in_progress_exports,
            'in_progress_imports': in_progress_imports,
            'has_in_progress': has_in_progress,
        },
    )


def _get_prepared_layer_groups(request):
    if request.user.is_superuser:
        layergroups = LayerGroup.objects.exclude(name='__default__')
    else:
        layergroups = services_utils.get_user_layergroups(request, permissions=[LayerGroupRole.PERM_MANAGE, LayerGroupRole.PERM_INCLUDEINPROJECTS]).distinct()
        
    prepared_layer_groups = []
    for lg in layergroups:
        layer_group = {}
        layer_group['id'] = lg.id
        layer_group['name'] = lg.name
        layer_group['title'] = lg.title
        layer_group['layers'] = []
        layers = Layer.objects.filter(layer_group_id=lg.id)
        for l in layers:
            layer_group['layers'].append({
                'id': l.id,
                'title': l.title
            })
        prepared_layer_groups.append(layer_group)
    return prepared_layer_groups

@login_required()
@staff_required
def project_add(request):

    has_geocoding_plugin = False
    if 'gvsigol_plugin_geocoding' in settings.INSTALLED_APPS:
        from gvsigol_plugin_geocoding.models import Provider
        providers = Provider.objects.all()
        has_geocoding_plugin = providers.__len__() > 0

    project_tools = get_available_tools(True, False)
    form = forms.getSupportedSRS()

    if request.method == 'POST':
        name = request.POST.get('project-name')

        name = re.sub(r'[^a-zA-Z0-9 ]',r'',name) #for remove all characters
        name = re.sub(' ','',name)

        logo_link = request.POST.get('project-logo-link')
        title = request.POST.get('project-title')
        description = request.POST.get('project-description')
        latitude = request.POST.get('center-lat')
        longitude = request.POST.get('center-lon')
        extent = core_utils.get_canonical_epsg3857_extent(request.POST.get('extent'))
        extent4326_minx = request.POST.get('extent4326_minx')
        extent4326_miny = request.POST.get('extent4326_miny')
        extent4326_maxx = request.POST.get('extent4326_maxx')
        extent4326_maxy = request.POST.get('extent4326_maxy')
        zoom = request.POST.get('zoom')
        layer_group_order = request.POST.get('toc_value')
        toc_mode = request.POST.get('toc_mode')
        tools = request.POST.get('project_tools')
        expiration_date_utc = request.POST.get('expiration_date_utc')
        layer_overview = request.POST.get('selected_overview_layer')
        viewer_default_crs = request.POST.get('srs')
        viewer_preferred_ui = request.POST.get('viewer_preferred_ui', settings.DEFAULT_VIEWER_UI)


        is_public = False
        if 'is_public' in request.POST:
            is_public = True
            
        show_project_icon = False
        if 'show_project_icon' in request.POST:
            show_project_icon = True
        
        selectable_groups = False
        if 'selectable_groups' in request.POST:
            selectable_groups = True
            
        restricted_extent = False
        if 'restricted_extent' in request.POST:
            restricted_extent = True

        has_image = False
        if 'project-image' in request.FILES:
            has_image = True
            
        has_logo = False
        if 'project-logo' in request.FILES:
            has_logo = True

        try:
            selected_base_layer = int(request.POST.get('selected_base_layer'))
        except:
            selected_base_layer = None
            
        selected_base_group = None
        if 'selected_base_group' in request.POST:
            selected_base_group = request.POST.get('selected_base_group')

        labels_added = None
        if 'labels_added' in request.POST:
            labels_added = request.POST.get('labels_added')

        if 'expiration_date_utc' in request.POST:
            expiration_date_utc = request.POST.get('expiration_date_utc')

        creator_user_role = auth_backend.get_primary_role(request.user.username)
        assigned_layergroups = []
        assigned_read_roles = []
        assigned_manage_roles = []
        for key in request.POST:
            if 'layergroup-' in key:
                assigned_layergroups.append(int(key.split('-')[1]))
            if 'read-role-' in key:
                assigned_read_roles.append(key[len('read-role-'):])
            if 'manage-role-' in key:
                assigned_manage_roles.append(key[len('manage-role-'):])

        if name == '':
            groups = core_utils.get_checked_project_roles(assigned_read_roles, assigned_manage_roles, creator_user_role)
            message = _('You must enter an project name')
            return render(request, 'project_add.html',
                          {
                            'message': message,
                            'layergroups': _get_prepared_layer_groups(request),
                            'tools': project_tools,
                            'groups': groups,
                            'has_geocoding_plugin': has_geocoding_plugin,
                            'form': form
                          }
                        )

        if _valid_projectname_regex.search(name) == None:
            groups = core_utils.get_checked_project_roles(assigned_read_roles, assigned_manage_roles, creator_user_role)
            message = _("Invalid project name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
            return render(request, 'project_add.html',
                          {
                            'message': message,
                            'layergroups': _get_prepared_layer_groups(request),
                            'tools': project_tools,
                            'groups': groups,
                            'has_geocoding_plugin': has_geocoding_plugin,
                            'form': form
                          }
                        )
    
        toc_order = core_utils.get_json_toc(assigned_layergroups, selected_base_group, json.loads(layer_group_order))

        if Project.objects.filter(name=name).exists():
            groups = core_utils.get_checked_project_roles(assigned_read_roles, assigned_manage_roles, creator_user_role)
            message = _('Project name already exists')
            return render(request, 'project_add.html', {'message': message,
                                                        'tools': project_tools ,
                                                        'layergroups': _get_prepared_layer_groups(request),
                                                        'groups': groups,
                                                        'has_geocoding_plugin': has_geocoding_plugin,
                                                        'form': form
                                                    })

        if layer_overview == '':
            custom_overview = False
        else:
            custom_overview = True

        project = Project(
            name = name,
            title = title,
            logo_link = logo_link,
            description = description,
            center_lat = latitude,
            center_lon = longitude,
            zoom = int(float(zoom)),
            extent = extent,
            toc_order = toc_order,
            toc_mode = toc_mode,
            created_by = request.user.username,
            is_public = is_public,
            show_project_icon = show_project_icon,
            selectable_groups = selectable_groups,
            restricted_extent = restricted_extent,
            extent4326_minx = extent4326_minx,
            extent4326_miny = extent4326_miny,
            extent4326_maxx = extent4326_maxx,
            extent4326_maxy = extent4326_maxy,
            tools = tools,
            labels = labels_added,
            custom_overview = custom_overview,
            layer_overview = layer_overview,
            viewer_default_crs = viewer_default_crs,
            viewer_preferred_ui = viewer_preferred_ui
        )
        if expiration_date_utc is not None and expiration_date_utc != '':
            try:
                ts = int(expiration_date_utc) / 1000
                project.expiration_date = datetime.datetime.fromtimestamp(ts)
            except Exception as e:
                pass
        else:
            project.expiration_date = None

        project.save()
        
        if has_image:
            project.image = request.FILES['project-image']
            project.save()
        
        if has_logo:
            project.logo = request.FILES['project-logo']
            project.save()

        for alg in assigned_layergroups:
            layergroup = LayerGroup.objects.get(id=alg)
            baselayer_group = False
            if selected_base_group != '' and alg == int(selected_base_group):
                baselayer_group = True
            project_layergroup = ProjectLayerGroup(
                project = project,
                layer_group = layergroup,
                multiselect = True,
                baselayer_group = baselayer_group
            )
            project_layergroup.save()
            if baselayer_group and selected_base_layer:
                project_layergroup.default_baselayer = selected_base_layer
                project_layergroup.save()

        ProjectRole.objects.filter(project_id=project.id).delete()
        roles = auth_backend.get_all_roles()
        admin_role = auth_backend.get_admin_role()
        mandatory_roles = [admin_role, creator_user_role]
        assigned_read_roles.extend(mandatory_roles)
        assigned_manage_roles.extend(mandatory_roles)
        for role in set(assigned_read_roles):
            if role in roles:
                project_role = ProjectRole(
                    project = project,
                    role = role,
                    permission = ProjectRole.PERM_READ
                )
                project_role.save()
        for role in set(assigned_manage_roles):
            if role in roles:
                project_role = ProjectRole(
                    project = project,
                    role = role,
                    permission = ProjectRole.PERM_MANAGE
                )
                project_role.save()

        if 'redirect' in request.GET:
            redirect_var = request.GET.get('redirect')
            if redirect_var == 'new-layer-group':
                url = reverse('layergroup_add_with_project', kwargs={'project_id': project.id}) + '?redirect=project-update'
                return redirect(url)

        return redirect('project_list')

    else:
        creator_role = auth_backend.get_primary_role(request.user.username)
        roles = core_utils.get_all_roles_checked_by_project(None, creator_user_role=creator_role)
        prepared_layer_groups = _get_prepared_layer_groups(request)
        labels = []
        for l in settings.PRJ_LABELS:
            labels.append({'label': l, 'checked': ''})

        print(settings.DEFAULT_VIEWER_UI)

        return render(request,
            'project_add.html',
            {
                'layergroups': prepared_layer_groups,
                'tools': project_tools,
                'groups': roles,
                'has_geocoding_plugin': has_geocoding_plugin,
                'label_list': labels,
                'form': form,
                'REACT_SPA_UI': Project.REACT_SPA_UI if Project.REACT_SPA_UI in settings.VIEWER_UI_CHOICES else None,
                'BOOTSTRAP_UI': Project.BOOTSTRAP_UI if Project.BOOTSTRAP_UI in settings.VIEWER_UI_CHOICES else None,
                'DEFAULT_VIEWER_UI': settings.DEFAULT_VIEWER_UI if settings.DEFAULT_VIEWER_UI in settings.VIEWER_UI_CHOICES else settings.VIEWER_UI_CHOICES[0]
            }
        )


@login_required()
@staff_required
def project_update(request, pid):

    has_geocoding_plugin = False
    if 'gvsigol_plugin_geocoding' in settings.INSTALLED_APPS:
        from gvsigol_plugin_geocoding.models import Provider
        providers = Provider.objects.all()
        has_geocoding_plugin = providers.__len__() > 0

    if request.method == 'POST':
        name = request.POST.get('project-name')
        title = request.POST.get('project-title')
        logo_link = request.POST.get('project-logo-link')
        description = request.POST.get('project-description')
        latitude = request.POST.get('center-lat')
        longitude = request.POST.get('center-lon')
        extent = core_utils.get_canonical_epsg3857_extent(request.POST.get('extent'))
        extent4326_minx = request.POST.get('extent4326_minx')
        extent4326_miny = request.POST.get('extent4326_miny')
        extent4326_maxx = request.POST.get('extent4326_maxx')
        extent4326_maxy = request.POST.get('extent4326_maxy')
        zoom = request.POST.get('zoom')
        layer_group_order = request.POST.get('toc_value')
        toc_mode = request.POST.get('toc_mode')
        tools = request.POST.get('project_tools')
        expiration_date_utc = request.POST.get('expiration_date_utc')
        layer_overview = request.POST.get('selected_overview_layer')
        viewer_default_crs = request.POST.get('srs')
        viewer_preferred_ui = request.POST.get('viewer_preferred_ui', settings.FALLBACK_VIEWER_UI)

        is_public = False
        if 'is_public' in request.POST:
            is_public = True
            
        show_project_icon = False
        if 'show_project_icon' in request.POST:
            show_project_icon = True
            
        selectable_groups = False
        if 'selectable_groups' in request.POST:
            selectable_groups = True
            
        restricted_extent = False
        if 'restricted_extent' in request.POST:
            restricted_extent = True

        try:
            selected_base_layer = int(request.POST.get('selected_base_layer'))
        except:
            selected_base_layer = None
            
        selected_base_group = None
        if 'selected_base_group' in request.POST:
            try:
                selected_base_group = int(request.POST.get('selected_base_group'))
            except:
                pass

        label_added = None
        if 'labels_added' in request.POST:
            labels_added = request.POST.get('labels_added')

        assigned_layergroups = []
        assigned_read_roles = []
        assigned_manage_roles = []
        for key in request.POST:
            if 'layergroup-' in key:
                assigned_layergroups.append(int(key.split('-')[1]))
            if 'read-role-' in key:
                assigned_read_roles.append(key[len('read-role-'):])
            if 'manage-role-' in key:
                assigned_manage_roles.append(key[len('manage-role-'):])

        has_image = False
        if 'project-image' in request.FILES:
            has_image = True
            
        has_logo = False
        if 'project-logo' in request.FILES:
            has_logo = True

        if layer_overview == '':
            custom_overview = False
        else:
            custom_overview = True

        project = Project.objects.get(id=int(pid))

        old_order = project.toc_order
        old_layer_groups = []
        for lg in ProjectLayerGroup.objects.filter(project_id=project.id):
            old_layer_groups.append(lg.layer_group.id)

        if not old_order or (old_order != layer_group_order) or list(assigned_layergroups) != list(old_layer_groups):
            project.toc_order = core_utils.get_json_toc(assigned_layergroups, selected_base_group, json.loads(layer_group_order))

        name = re.sub(r'[^a-zA-Z0-9 ]',r'',name) #for remove all characters
        name = re.sub(' ','',name)

        project.name = name
        project.title = title
        project.logo_link = logo_link
        project.description = description
        project.center_lat = latitude
        project.center_lon = longitude
        project.zoom = int(float(zoom))
        project.extent = extent
        project.is_public = is_public
        project.toc_mode = toc_mode
        project.tools = tools
        project.show_project_icon = show_project_icon
        project.selectable_groups = selectable_groups
        project.restricted_extent = restricted_extent
        project.extent4326_minx = extent4326_minx
        project.extent4326_miny = extent4326_miny
        project.extent4326_maxx = extent4326_maxx
        project.extent4326_maxy = extent4326_maxy
        project.labels = labels_added
        project.custom_overview = custom_overview
        project.layer_overview = layer_overview
        project.viewer_default_crs = viewer_default_crs
        project.viewer_preferred_ui = viewer_preferred_ui

        if expiration_date_utc is not None and expiration_date_utc != '':
            try:
                ts = int(expiration_date_utc) / 1000
                #project.expiration_date = datetime.datetime.fromtimestamp(ts)
                aware_datetime = timezone.make_aware(datetime.datetime.fromtimestamp(ts), timezone=timezone.get_current_timezone())
                project.expiration_date=aware_datetime
            except Exception as e:
                pass
        else:
            project.expiration_date = None
        

        if has_image:
            project.image = request.FILES['project-image']
            
        if has_logo:
            project.logo = request.FILES['project-logo']

        project.save()

        for lg in ProjectLayerGroup.objects.filter(project_id=project.id):
            lg.delete()
            
        for alg in assigned_layergroups:
            layergroup = LayerGroup.objects.get(id=alg)
            baselayer_group = False
            try:
                if alg == selected_base_group:
                    baselayer_group = True
            except:
                print('ERROR: selected_base_group is not defined')
            project_layergroup = ProjectLayerGroup(
                project = project,
                layer_group = layergroup,
                multiselect = True,
                baselayer_group = baselayer_group
            )
            project_layergroup.save()
            if baselayer_group and selected_base_layer:
                project_layergroup.default_baselayer = selected_base_layer
                project_layergroup.save()

        ProjectRole.objects.filter(project_id=project.id).delete()
        roles = auth_backend.get_all_roles()
        for role in assigned_read_roles:
            if role in roles:
                project_role = ProjectRole(
                    project = project,
                    role = role,
                    permission = ProjectRole.PERM_READ
                )
                project_role.save()
        for role in assigned_manage_roles:
            if role in roles:
                project_role = ProjectRole(
                    project = project,
                    role = role,
                    permission = ProjectRole.PERM_MANAGE
                )
                project_role.save()

        admin_role = auth_backend.get_admin_role()
        project_role = ProjectRole(
            project = project,
            role = admin_role,
            permission = ProjectRole.PERM_READ
        )
        project_role.save()
        project_role = ProjectRole(
            project = project,
            role = admin_role,
            permission = ProjectRole.PERM_MANAGE
        )
        project_role.save()

        if 'redirect' in request.GET:
            redirect_var = request.GET.get('redirect')
            if redirect_var == 'new-layer-group':
                url = reverse('layergroup_add_with_project', kwargs={'project_id': project.id}) + '?redirect=project-update'
                return redirect(url)

        return redirect('project_list')

    else:
        project = Project.objects.get(id=int(pid))
        creator_role = auth_backend.get_primary_role(project.created_by)
        roles = core_utils.get_all_roles_checked_by_project(project, creator_user_role=creator_role)
        layer_groups = core_utils.get_all_layer_groups_checked_by_project(request, project)

        if project.toc_order:
            toc = json.loads(project.toc_order)
        else:
            toc = {}
        ordered_toc = {}
        for g in layer_groups:
            if g.get('checked'):
                if g.get('baselayer_group', False):
                    order = 500
                else:
                    order = 1000
                layers = {}
                for gnames in toc:
                    if g['name'] == gnames:
                        group = toc.get(gnames)
                        order = group.get('order', order)
                        ordered_layers = sorted(iter(group.get('layers').items()), key=lambda x_y: x_y[1]['order'], reverse=True)
                        layers = ordered_layers
                        break
                ordered_toc[g['name']] = {'name': g['name'], 'id': g['id'], 'title': g['title'], 'order': order, 'layers': layers}
        ordered_toc = sorted(iter(ordered_toc.items()), key=lambda x_y2: x_y2[1]['order'], reverse=True)
        if project.tools:
            try:
                projectTools = json.loads(project.tools)
                # get all tools to ensure the config includes all existing tools
                all_tools = get_available_tools(False, False)
                for tool in all_tools:
                    for projectTool in projectTools:
                        if projectTool['name'] == tool['name']:
                            tool['checked'] = projectTool['checked']
                            break
                projectTools = all_tools
            except:
                projectTools = get_available_tools(True, True)
        else:
            projectTools = get_available_tools(True, True)
        for lg in layer_groups:
            lg['layers'] = []
            layers = Layer.objects.filter(layer_group_id=lg['id'])
            for l in layers:   
                baselayer = False           
                if lg['baselayer_group']:
                    if l.id == lg['default_baselayer']:
                        baselayer = True
                lg['layers'].append({
                    'id': l.id,
                    'title': l.title,
                    'baselayer': baselayer
                })
        
        labels_added = []
        if project.labels:
            labels_added = project.labels.split(',')   

        labels = []
        for l in settings.PRJ_LABELS:
            check = ''
            for la in labels_added:
                if l == la:
                    check = 'checked'
            labels.append({'label': l, 'checked': check})
        
        if project.expiration_date is not None:
            project.expiration_date = int(project.expiration_date.timestamp() * 1000)
        
        if not project.viewer_preferred_ui:
            project.viewer_preferred_ui = settings.FALLBACK_VIEWER_UI if settings.FALLBACK_VIEWER_UI in settings.VIEWER_UI_CHOICES else settings.VIEWER_UI_CHOICES[0]
        
        form = forms.getSupportedSRS()
        return render(request, 'project_update.html', {'tools': projectTools,
                                                       'pid': pid, 
                                                       'project': project,
                                                       'groups': roles,
                                                       'layergroups': layer_groups, 
                                                       'has_geocoding_plugin': has_geocoding_plugin, 
                                                       'toc': ordered_toc, 
                                                       'label_list': labels,
                                                       'form': form,
                                                       'REACT_SPA_UI': Project.REACT_SPA_UI if Project.REACT_SPA_UI in settings.VIEWER_UI_CHOICES else None,
                                                       'BOOTSTRAP_UI': Project.BOOTSTRAP_UI if Project.BOOTSTRAP_UI in settings.VIEWER_UI_CHOICES else None
                                                       })


@login_required()
@staff_required
def project_delete(request, pid):
    if request.method == 'POST':
        try:
            if request.user.is_superuser:
                project = Project.objects.get(id=int(pid))
            else:
                project = Project.objects.get(id=int(pid), created_by__exact=request.user.username)
            project.delete()
            response = {
                'deleted': True
            }
            return HttpResponse(json.dumps(response, indent=4), content_type='project/json')
        except:
            logger.exception("Error deleting project")
            return HttpResponseForbidden({"deleted": False, "error": "Not allowed"})

def load(request, project_name):
    project = Project.objects.get(name__exact=project_name)

    if project.is_public:
        if request.user and request.user.is_authenticated:
            return redirect('load_project', project_name=project.name)
        else:
            return redirect('load_public_project', project_name=project.name)

    else:
        return redirect('load_project', project_name=project.name)

@login_required()
@cache_control(max_age=86400)
def load_project(request, project_name):
    if core_utils.can_read_project(request, project_name):
        project = Project.objects.get(name__exact=project_name)

        plugins_config = core_utils.get_plugins_config()
        enabled_plugins = core_utils.get_enabled_plugins(project)
        resp = {
            'has_image': bool(project.image),
            'supported_crs': core_utils.get_supported_crs(),
            'project': project,
            'project_logo': project.logo_url,
            'project_image': project.image_url,
            'pid': project.id,
            'extra_params': json.dumps(request.GET),
            'plugins_config': plugins_config,
            'enabled_plugins': enabled_plugins,
            'is_shared_view': False,
            'main_page': settings.LOGOUT_REDIRECT_URL,
            'is_viewer_template': True,
            'url_doc': get_manual(request, 'gvsigol_user_manual.pdf', default={}).get('url', 'javascript:void(0)'),
            'project_title' : project.title,
            'viewer_default_crs': project.viewer_default_crs
        }
        response = render(request, 'viewer.html', resp)

        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie('key', expires = expires)

        action.send(request.user, verb="gvsigol_core/get_conf", action_object=project)

        return response

    else:
        return render(request, 'illegal_operation.html', {})


@cache_control(max_age=86400)
def load_public_project(request, project_name):
    project = Project.objects.get(name__exact=project_name)
    if not core_utils.can_read_project(request, project):
        return render(request, 'illegal_operation.html', {})

    plugins_config = core_utils.get_plugins_config()
    enabled_plugins = core_utils.get_enabled_plugins(project)
    response = render(request, 'viewer.html', {
        'has_image': bool(project.image),
        'supported_crs': core_utils.get_supported_crs(),
        'project': project,
        'project_logo': project.logo_url,
        'project_image': project.image_url,
        'pid': project.id,
        'extra_params': json.dumps(request.GET),
        'plugins_config': plugins_config,
        'enabled_plugins': enabled_plugins,
        'is_shared_view': False,
        'main_page': settings.LOGOUT_REDIRECT_URL,
        'is_viewer_template': True,
        'url_doc': get_manual(request, 'gvsigol_user_manual.pdf', default={}).get('url', 'javascript:void(0)'),
        'project_title' : project.title,
        'viewer_default_crs': project.viewer_default_crs
        }
    )

    #Expira la caché cada día
    tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
    tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
    expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie('key', expires = expires)

    action.send(project, verb="gvsigol_core/get_conf", action_object=project)

    return response


@login_required()
@xframe_options_exempt
@cache_control(max_age=86400)
def portable_project_load(request, project_name):
    if core_utils.can_read_project(request, project_name):
        project = Project.objects.get(name__exact=project_name)
        response = render(request, 'portable_viewer.html', {'supported_crs': core_utils.get_supported_crs(), 'project': project, 'pid': project.id, 'extra_params': json.dumps(request.GET)})
        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie('key', expires = expires)
        return response
    else:
        return render(request, 'illegal_operation.html', {})


@login_required()
def blank_page(request):
    return render(request, 'blank_page.html', {})


def get_layer_styles(layer):
    styles = []
    stllyrs = StyleLayer.objects.filter(layer_id = layer.id)
    for stllyr in stllyrs:
        stl=stllyr.style
        if not stl.name.endswith('__tmp'):
            style={
                'name' : stl.name,
                'title' : stl.title,
                'is_default': stl.is_default,
                'has_custom_legend': stl.has_custom_legend,
                'custom_legend_url': stl.custom_legend_url
                }
            styles.append(style)
    return styles

def get_default_style(layer):
    default = None
    stllyrs = StyleLayer.objects.filter(layer_id = layer.id)
    for stllyr in stllyrs:
        stl=stllyr.style
        if stl.is_default:
            default = stl
    return default
       

@csrf_exempt
@require_http_methods(['GET', 'POST', 'HEAD'])
def project_get_conf(request):
    errors = []
    if request.method == 'POST':
        pid = request.POST.get('pid')
        is_shared_view = json.loads(request.POST.get('shared_view'))
    elif request.method == 'GET':
        pid = request.GET.get('pid')
        is_shared_view = json.loads(request.GET.get('shared_view'))
    else:
        return HttpResponse('', content_type='application/json')

    project = Project.objects.get(id=int(pid))
    if not project.toc_order:
        project.toc_order = "{}"
    toc = json.loads(project.toc_order)
    user_roles = auth_backend.get_roles(request)

    used_crs = []
    crs_code = int('EPSG:4326'.split(':')[1])
    if crs_code in core_utils.get_supported_crs():
        epsg = core_utils.get_supported_crs()[crs_code]
        used_crs.append(epsg)
    crs_code = int('EPSG:3857'.split(':')[1])
    if crs_code in core_utils.get_supported_crs():
        epsg = core_utils.get_supported_crs()[crs_code]
        used_crs.append(epsg)
    crs_code = int('EPSG:4258'.split(':')[1])
    if crs_code in core_utils.get_supported_crs():
        epsg = core_utils.get_supported_crs()[crs_code]
        used_crs.append(epsg)

    project_layers_groups = ProjectLayerGroup.objects.filter(project_id=project.id).select_related("layer_group")
    layer_groups = []
    workspaces = []
    
    language = core_utils.get_iso_language(request)

    count = 0
    all_public = True
    for project_group in project_layers_groups:
        group = project_group.layer_group
        server = Server.objects.get(id=group.server_id)

        conf_group = {}
        conf_group['groupTitle'] = group.title
        conf_group['groupId'] = ''.join(random.choice(string.ascii_uppercase) for i in range(6))
        if toc.get(group.name):
            conf_group['groupOrder'] = toc.get(group.name).get('order')
        else:
            conf_group['groupOrder'] = count
        count = count + 1
        conf_group['groupName'] = group.name
        conf_group['cached'] = group.cached
        conf_group['visible'] = group.visible
        if project_group.baselayer_group:
            conf_group['visible'] = False 
        conf_group['basegroup'] = project_group.baselayer_group
        conf_group['wms_endpoint'] = server.getWmsEndpoint(relative=True)
        conf_group['wfs_endpoint'] = server.getWfsEndpoint(relative=True)
        conf_group['cache_endpoint'] = server.getCacheEndpoint(relative=True)
        layers_in_group = Layer.objects.filter(layer_group_id=group.id).order_by('order')
        layers = []
        
        allows_getmap = True
        servers_list = []
        
        idx = 0
        for l in layers_in_group:
            if not l.public:
                all_public = False
            if not l.external:
                try:
                    read_roles = services_utils.get_read_roles(l)
                    write_roles = services_utils.get_write_roles(l)
                    if request.user.is_superuser or l.public:
                        readable = True
                    else:
                        readable = False
                        for user_role in user_roles:
                            if user_role in read_roles:
                                readable = True
                                break
                    if readable:
                        layer = {}
                        layer['external'] = False
                        if project_group.baselayer_group:
                            layer['baselayer'] = True
                            if l.id == project_group.default_baselayer:
                                layer['default_baselayer'] = True
                            else:
                                layer['default_baselayer'] = False
                        else:
                            layer['baselayer'] = False
                            
                        layer['layer_id'] = l.id
                        layer['name'] = l.name
                        layer['title'] = l.title
                        layer['abstract'] = l.abstract
                        layer['visible'] = l.visible
                        layer['type'] = l.type
                        layer['queryable'] = l.queryable
                        layer['allow_download'] = l.allow_download
                        layer['detailed_info_enabled'] = l.detailed_info_enabled
                        layer['detailed_info_button_title'] = l.detailed_info_button_title
                        layer['detailed_info_html'] = l.detailed_info_html
                        layer['real_time'] = l.real_time
                        layer['update_interval'] = l.update_interval
                        layer['time_enabled'] = l.time_enabled
                        if layer['time_enabled']:
                            layer['ref'] = l.id
                            layer['time_enabled_field'] = l.time_enabled_field
                            layer['time_enabled_endfield'] = l.time_enabled_endfield
                            layer['time_presentation'] = l.time_presentation
                            layer['time_resolution_year'] = l.time_resolution_year
                            layer['time_resolution_month'] = l.time_resolution_month
                            layer['time_resolution_week'] = l.time_resolution_week
                            layer['time_resolution_day'] = l.time_resolution_day
                            layer['time_resolution_hour'] = l.time_resolution_hour
                            layer['time_resolution_minute'] = l.time_resolution_minute
                            layer['time_resolution_second'] = l.time_resolution_second
                            layer['time_default_value_mode'] = l.time_default_value_mode
                            layer['time_default_value'] = l.time_default_value

                            layer['time_resolution'] = l.time_resolution

                        layer['cached'] = l.cached

                        order = int(conf_group['groupOrder']) + l.order
                        layer['order'] = order
                        layer['single_image'] = l.single_image
                        layer['read_roles'] = read_roles
                        layer['write_roles'] = write_roles
                        layer['public'] = l.public
                        layer['styles'] = get_layer_styles(l)
                        
                        if l.external_params:
                            params = json.loads(l.external_params)
                            layer['format'] = params.get('format')

                        try:
                            json_conf = ast.literal_eval(l.conf)
                            layer['conf'] = json.dumps(json_conf)
                        except:
                            layer['conf'] = "{\"fields\":[]}"
                            pass

                        datastore = Datastore.objects.get(id=l.datastore_id)
                        workspace = Workspace.objects.get(id=datastore.workspace_id)
                        
                        servers_list.append(workspace.server.name)
                        
                        if datastore.type == 'v_SHP' or datastore.type == 'v_PostGIS':
                            layer['is_vector'] = True
                        else:
                            layer['is_vector'] = False

                        layer['is_view'] = False
                        if l.type == 'v_PostGIS':
                            src_key = l.source_name if l.source_name else l.name
                            try:
                                dbi, src, schema = l.get_db_connection()
                                with dbi as c:
                                    layer['is_view'] = (
                                        c.is_view(schema, src)
                                        or c.is_materialized_view(schema, src)
                                    )
                            except Exception:
                                logger.exception('Error checking is_view for layer %s', l.id)
                                layer['is_view'] = False
                            if not layer['is_view']:
                                try:
                                    layer['is_view'] = SqlView.objects.filter(
                                        datastore_id=l.datastore_id, name=src_key
                                    ).exists()
                                except Exception:
                                    logger.exception(
                                        'Error checking SqlView for layer %s', l.id
                                    )

                        defaultCrs = None
                        if str(datastore.type) == 'e_WMS':
                            defaultCrs = 'EPSG:4326'
                        else:
                            defaultCrs = l.native_srs

                        crs_code = int(defaultCrs.split(':')[1])
                        if crs_code in core_utils.get_supported_crs():
                            epsg = core_utils.get_supported_crs()[crs_code]
                            layer['crs'] = {
                                'crs': defaultCrs,
                                'units': epsg['units']
                            }
                            used_crs.append(epsg)
                            
                        layer['native_srs'] = l.native_srs
                        layer['native_extent'] = l.native_extent
                        layer['latlong_extent'] = l.latlong_extent
                        layer['opacity'] = 1
                        layer['wms_url'] = core_utils.get_wms_url(workspace)
                        layer['wms_url_no_auth'] = core_utils.get_wms_url(workspace)
                        if datastore.type.startswith('v_'):
                            layer['wfs_url'] = core_utils.get_wfs_url(workspace)
                            layer['wfs_url_no_auth'] = core_utils.get_wfs_url(workspace)
                        elif datastore.type.startswith('c_'):
                            layer['wcs_url'] = core_utils.get_wcs_url(workspace)
                        layer['namespace'] = core_utils.get_absolute_url(workspace.uri, request.META)
                        layer['workspace'] = workspace.name
                        layer['metadata'] = core_utils.get_layer_metadata_uuid(l)
                        layer['metadata_url'] = core_utils.get_catalog_url_from_uuid(request, layer['metadata'], lang=language.part2b)
                        if l.cached:
                            layer['cache_url'] = core_utils.get_cache_url(workspace)
                            if params.get('wmts_options'):
                                layer['wmts_options'] = services_utils.wmts_options_for_openlayers(params.get('wmts_options'), layer.get('format'), layer_styles=layer['styles'], projection=project.viewer_default_crs)
                        else:
                            layer['cache_url'] = core_utils.get_wms_url(workspace)

                        if datastore.type == 'e_WMS':
                            layer['legend'] = ""
                        else:
                            ls = get_default_style(l)
                            if ls is None:
                                layer['legend'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                layer['legend_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                layer['legend_graphic'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                layer['legend_graphic_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'

                            else:
                                if not ls.has_custom_legend:
                                    layer['legend'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                else:
                                    layer['legend'] = ls.custom_legend_url
                                    layer['legend_no_auth'] = ls.custom_legend_url
                                    layer['legend_graphic'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                        
                        layer['timeout'] = l.timeout
                        _, urlicon = utils.get_layer_img(l.id, None)
                        layer['icon'] = urlicon 
                        layers.append(layer)

                        w = {}
                        w['name'] = workspace.name
                        w['wms_url'] = core_utils.get_wms_url(workspace)
                        workspaces.append(w)
                    idx = idx + 1

                except Exception as e:
                    logger.exception('error getting layer conf')
                    datastore = Datastore.objects.get(id=l.datastore_id)
                    workspace = Workspace.objects.get(id=datastore.workspace_id)

                    error = {
                        'layer': l.name,
                        'datastore': datastore.name,
                        'workspace': workspace.name,
                        'error': str(e)
                    }
                    errors.append(error)
                    pass
                
            else:
                allows_getmap = False
                
                layer = {}
                if project_group.baselayer_group:
                    layer['baselayer'] = True
                    if l.id == project_group.default_baselayer:
                        layer['default_baselayer'] = True
                    else:
                        layer['default_baselayer'] = False
                else:
                    layer['baselayer'] = False
                
                layer['layer_id'] = l.id
                layer['id'] = l.id
                layer['opacity'] = 1
                layer['external'] = True   
                layer['name'] = l.name
                layer['title'] = l.title
                layer['abstract'] = l.abstract
                layer['visible'] = l.visible
                layer['queryable'] = l.queryable
                layer['cached'] = l.cached
                layer['type'] = l.type
                layer['detailed_info_enabled'] = l.detailed_info_enabled
                layer['detailed_info_button_title'] = l.detailed_info_button_title
                layer['detailed_info_html'] = l.detailed_info_html
                layer['metadata'] = core_utils.get_layer_metadata_uuid(l)
                layer['metadata_url'] = core_utils.get_catalog_url_from_uuid(request, layer['metadata'], lang=language.part2b)

                if l.external_params:
                    params = json.loads(l.external_params)
                    if l.type == 'WMTS':
                        if 'wmts_options' in params:
                            wmts_options = params['wmts_options']
                            params['wmts_options'] = services_utils.wmts_options_for_openlayers(wmts_options, params['format'], projection=project.viewer_default_crs)
                            if 'capabilities' in params and 'tileGrid' in params['wmts_options']:
                                del params['capabilities']
                                
                        elif not 'capabilities' in params:
                            version = settings.WMTS_MAX_VERSION
                            if 'version' in params:
                                version = params['version']
                            wmts = WebMapTileService(params['url'], version=version)
                            capabilities = wmts.getServiceXML()
                            params['capabilities'] = capabilities.decode('utf-8')
                            l.external_params = json.dumps(params)
                            l.save()
                    elif l.type == 'WMS' and l.cached and params.get('wmts_options'):
                        try:
                            wmts_options = params['wmts_options']
                            params['wmts_options'] = services_utils.wmts_options_for_openlayers(
                                wmts_options, params.get('format'), projection=project.viewer_default_crs
                            )
                        except Exception:
                            logger.exception(
                                "wmts_options_for_openlayers failed for external cached WMS layer id=%s; sending stored wmts_options as-is",
                                l.id,
                            )
                    if l.type == 'WMS':
                        params['styles'] = services_utils.mark_default_external_wms_style(
                            params.get('styles') or [], params.get('layers')
                        )
                    layer.update(params)
                    if params.get('get_map_url'):
                        layer['url'] = params.get('get_map_url')
                    layer['external_url'] = params.get('get_map_url') or params.get('url', '')
                    layer['external_layers'] = params.get('layers', '')
                    layer['external_params'] = dict(params)
                    if l.type == 'WMS':
                        layer['styles'] = params.get('styles') or []

                order = int(conf_group['groupOrder']) + l.order
                layer['order'] = order
                
                layer['timeout'] = l.timeout
                layers.append(layer)
        
        if allows_getmap:
            if len(servers_list) > 0 :
                allows_getmap = all(elem == servers_list[0] for elem in servers_list)        
        conf_group['allows_getmap'] = allows_getmap
        
        if len(layers) > 0:
            ordered_layers = sorted(layers, key=itemgetter('order'), reverse=True)
            conf_group['layers'] = ordered_layers
            layer_groups.append(conf_group)

    supported_crs = core_utils.get_supported_crs(used_crs)
    ordered_layer_groups = sorted(layer_groups, key=itemgetter('groupOrder'), reverse=True)

    resource_manager = 'gvsigol'
    if 'gvsigol_plugin_alfresco' in gvsigol.settings.INSTALLED_APPS:
        resource_manager = 'alfresco'



    auth_urls = []
    for s in Server.objects.all():
        auth_url = s.frontend_url 
        if auth_url.startswith(settings.BASE_URL):
            auth_url = auth_url.replace(settings.BASE_URL, '')
        auth_urls.append(auth_url)
    project_tools = json.loads(project.tools) if project.tools else get_available_tools(True, True)

    gvsigol_app = None
    for app in settings.INSTALLED_APPS:
        if 'gvsigol_app_' in app:
            gvsigol_app = app

    conf = {
        'pid': pid,
        'gvsigol_app': gvsigol_app,
        'project_name': project.name,
        'project_title': project.title,
        'project_logo': project.logo_url,
        'project_logo_link': project.logo_link,
        'project_image': project.image_url,
        'project_tools': project_tools,
        "view": {
            "restricted_extent": project.restricted_extent,
            "extent": [ float(f) for f in project.extent.split(',') ] if project.extent else None,
            "extent4326": [project.extent4326_minx, project.extent4326_miny, project.extent4326_maxx, project.extent4326_maxy],
            "center_lat": project.center_lat,
            "center_lon": project.center_lon,
            "zoom": project.zoom,
            "max_zoom_level": gvsigol.settings.MAX_ZOOM_LEVEL
        },
        'supported_crs': supported_crs,
        'workspaces': workspaces,
        'layerGroups': ordered_layer_groups,
        'tools': gvsigol.settings.GVSIGOL_TOOLS,
        'tile_size': gvsigol.settings.TILE_SIZE,
        'is_public_project': project.is_public,
        'show_project_icon': project.show_project_icon,
        'selectable_groups': project.selectable_groups,
        'resource_manager': resource_manager,
        'remote_auth': settings.AUTH_WITH_REMOTE_USER,
        'temporal_advanced_parameters': gvsigol.settings.TEMPORAL_ADVANCED_PARAMETERS,
        'errors': errors,
        'auth_urls': auth_urls,
        'check_tileload_error': settings.CHECK_TILELOAD_ERROR,
        'SHP_DOWNLOAD_DEFAULT_ENCODING': getattr(settings, 'SHP_DOWNLOAD_DEFAULT_ENCODING', 'UTF-8'),
        'custom_overview': project.custom_overview,
        'layer_overview': project.layer_overview,
        'viewer_default_crs': project.viewer_default_crs      
        
    }
    
    if language:
        conf['language'] = {
            'iso639_1': request.LANGUAGE_CODE,
            'iso639_2b': language.part2b
        }
    

    if request.user and request.user.id:
        conf['user'] = {
            'id': request.user.id,
            'username': request.user.first_name + ' ' + request.user.last_name,
            'login': request.user.username,
            'email': request.user.email,
            'permissions': {
                'is_superuser': is_superuser(request.user),
                'roles': auth_backend.get_roles(request)
            }
        }
        if request.session.get('oidc_access_token'):
            conf['user']['token'] = request.session.get('oidc_access_token')
            conf['user']['refresh_token'] = request.session.get('oidc_refresh_token')
            try:
                conf['user']['refresh_url'] = django_settings.OIDC_OP_TOKEN_ENDPOINT
                conf['user']['client_id'] = django_settings.OIDC_RP_CLIENT_ID
            except:
                pass
        else:
            try:
                conf['user']['credentials'] = {
                    'username': request.session['username'],
                    'password': request.session['password']
                }
            except KeyError:
                # happens when using OIDC auth, the session has expired and the token has not been provided
                logger.debug(str(user_roles))
                return JsonResponse({"status": "error", "message": "Token missing or expired"}, status=401)
    if is_shared_view:
        view_name = request.GET.get('shared_view_name')
        shared_view = SharedView.objects.get(name__exact=view_name)
        state = json.loads(shared_view.state)

        conf = core_utils.set_state(conf, state)

    indent = 4 if settings.DEBUG else None
    response = HttpResponse(json.dumps(conf, indent=indent), content_type='application/json')
    all_public = all_public and project.is_public
    if all_public and ((not request.user) or (not request.user.is_authenticated)):
        setattr(response, GVSIGOL_SET_STATIC_CACHE_RESPONSE_KEY, True)
    return response


def toc_update(request, pid):
    if request.method == 'POST':
        project = Project.objects.get(id=int(pid))
        toc = request.POST.get('toc')
        project.toc_order = toc
        project.save()

        toc_object = json.loads(toc)
        server = geographic_servers.get_instance().get_server_by_id(id)
        server.createOrUpdateSortedGeoserverLayerGroup(toc_object)

        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')

    else:
        project = Project.objects.get(id=int(pid))
        toc = json.loads(project.toc_order)
        for g in toc:
            group = toc.get(g)
            ordered_layers = sorted(iter(group.get('layers').items()), key=lambda x_y3: x_y3[1]['order'], reverse=True)
            group['layers'] = ordered_layers
        ordered_toc = sorted(iter(toc.items()), key=lambda x_y4: x_y4[1]['order'], reverse=True)
        return render(request, 'toc_update.html', {'toc': ordered_toc, 'pid': pid})

def export(request, pid):
    p = Project.objects.get(id=pid)
    image = p.image_url
    return render(request, 'app_print_template.html', {'print_logo_url': unquote(image)})

def ogc_services(request):
    wms = ServiceUrl.objects.filter(type='WMS')
    wmts = ServiceUrl.objects.filter(type='WMTS')
    wfs = ServiceUrl.objects.filter(type='WFS')
    csw = ServiceUrl.objects.filter(type='CSW')
    return render(request, 'services_view.html', {'wms': wms, 'wmts': wmts, 'wfs': wfs, 'csw': csw})

def select_public_project(request):
    public_projects = Project.objects.filter(is_public=True)
    public_apps = Application.objects.filter(is_public=True)

    if len (public_projects) == 1 and len(public_apps) == 0:
        return redirect('load', project_name=public_projects[0].name)
    elif len (public_projects) == 0 and len(public_apps) == 1:
        return redirect(public_apps[0].absurl)
    
    projects = []
    apps = []
    for p in public_projects:
        image = p.image_url
        project = {}
        project['id'] = p.id
        project['name'] = p.name
        project['title'] = p.title
        project['description'] = p.description
        project['image'] = unquote(image)
        project['absurl'] = p.url
        projects.append(project)
    for pa in public_apps:
        image = pa.image_url
        app = {}
        app['id'] = pa.id
        app['name'] = pa.name
        app['title'] = pa.title
        app['description'] = pa.description
        app['image'] = unquote(image)
        app['absurl'] = pa.absurl
        apps.append(app)
    return render(request, 'select_public_project.html', {'projects': projects, 'applications': apps})

def select_public_mobile_project(request):
    public_projects = Project.objects.filter(is_public=True)
    public_apps = Application.objects.filter(is_public=True)

    if len (public_projects) == 1 and len(public_apps) == 0:
        return redirect(public_projects[0].url)
    elif len (public_projects) == 0 and len(public_apps) == 1:
        return redirect(public_apps[0].absurl)

    projects = []
    apps = []
    for p in public_projects:
        image = p.image_url
        project = {}
        project['id'] = p.id
        project['name'] = p.name
        project['title'] = p.title
        project['description'] = p.description
        project['image'] = unquote(image)
        project['absurl'] = p.mobile_url
        projects.append(project)
    for pa in public_apps:
        image = pa.image_url
        app = {}
        app['id'] = pa.id
        app['name'] = pa.name
        app['title'] = pa.title
        app['description'] = pa.description
        app['image'] = unquote(image)
        app['absurl'] = pa.absurl
        apps.append(app)
    return render(request, 'select_public_mobile_project.html', {'projects': projects, 'applications': apps})

def get_manual(request, doc_name, forced_lang=None, default=None):
    if forced_lang:
        lang = forced_lang
    else:
        lang = request.LANGUAGE_CODE

    base_docs_url = getattr(settings, 'DOCS_PATH', os.path.join(settings.STATIC_ROOT, '../../docs'))

    doc_path = os.path.join(base_docs_url, lang, doc_name)
    if os.path.exists(doc_path):
        return {
            'url': settings.DOCS_URL + os.path.relpath(doc_path, base_docs_url),
            'lang': forced_lang
        }
    elif not forced_lang:
        return get_manual(request, doc_name, 'es', default=default)
    return default
    return default


def documentation(request):
    lang = request.LANGUAGE_CODE
    base_docs_url = getattr(settings, 'DOCS_PATH', os.path.join(settings.STATIC_ROOT, '../../docs'))

    admin = get_manual(request, 'gvsigol_admin_guide.pdf')
    mobile = get_manual(request, 'gvsigmapps_manual.pdf')
    
    # Obtener viewers disponibles, por defecto ambos si no está definido
    
    
    available_viewers = getattr(settings, 'VIEWER_UI_CHOICES', [Project.REACT_SPA_UI, Project.BOOTSTRAP_UI])
    
    if isinstance(available_viewers, str):
        import ast
        try:
            available_viewers = ast.literal_eval(available_viewers)
        except Exception as e:
            available_viewers = ['react_spa_ui', 'bootstrap_ui']
    elif isinstance(available_viewers, list) and len(available_viewers) == 1 and isinstance(available_viewers[0], str):
        import ast
        try:
            available_viewers = ast.literal_eval(available_viewers[0])
        except Exception as e:
            available_viewers = ['react_spa_ui', 'bootstrap_ui']
    
    
    # Solo cargar los manuales de viewers que están en VIEWER_UI_CHOICES
    viewer = get_manual(request, 'gvsigol_user_manual.pdf') if 'bootstrap_ui' in available_viewers else None
    spaviewer = get_manual(request, 'gvsigolfrontend_manual.pdf') if 'react_spa_ui' in available_viewers else None
    

    
    
    plugins_base_path = base_docs_url + '/plugins'
    plugin_manuals = []
    for app_name in settings.INSTALLED_APPS:
        if  app_name.startswith('gvsigol_'):
            the_path = os.path.join(plugins_base_path, app_name, app_name + '_' + lang + '.pdf')
            if os.path.exists(the_path):
                the_url = settings.DOCS_URL + os.path.relpath(the_path, base_docs_url)
                plugin_manuals.append({
                    'url': the_url,
                    'title': _(app_name + ' manual title'),
                    'desc': _(app_name + ' manual desc'),
                    'lang': None
                })
            else:
                plugin_path = os.path.join(plugins_base_path, app_name, app_name + '_es.pdf')
                if os.path.exists(plugin_path):
                    the_url = settings.DOCS_URL + os.path.relpath(plugin_path, base_docs_url)
                    plugin_manuals.append({
                        'url': the_url,
                        'title': _(app_name + ' manual title'),
                        'desc': _(app_name + ' manual desc'),
                        'lang': 'es'
                    })
        
    response = {
        'plugin_manuals': plugin_manuals,
    }
    
    if admin:
        response['admin'] = admin
    if viewer:
        response['viewer'] = viewer
    if spaviewer:
        response['spaviewer'] = spaviewer
    if mobile:
        response['mobile'] = mobile
        
    return render(request, 'documentation.html', response)

def do_save_shared_view(pid, description, view_state, expiration, user, internal = False, url = False):
    
    if url:
        shared_url = url
        name = url.split('/')[-1]
    else:
        name = datetime.date.today().strftime("%Y%m%d") + get_random_string(length=32)
        shared_url = settings.BASE_URL + '/gvsigonline/core/load_shared_view/' + name

    try:
        shared_project = SharedView.objects.get(name = name)
        shared_project.expiration_date = expiration

    except:

        shared_project = SharedView(
            name=name,
            project_id=pid,
            description=description,
            url=shared_url,
            state=view_state,
            expiration_date=expiration,
            created_by=user.username,
            internal=internal
        )
        
    shared_project.save()

    return shared_project

def create_shared_view(request):
    if request.method == 'POST':

        name = datetime.date.today().strftime("%Y%m%d") + get_random_string(length=32)
        shared_url = settings.BASE_URL + '/gvsigonline/core/load_shared_view/' + name
        response = {
            'shared_url': shared_url
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')

#@login_required(login_url='/gvsigonline/auth/login_user/')
def save_shared_view(request):
    if request.method == 'POST':
        pid = int(request.POST.get('pid'))
        if not core_utils.can_read_project(request, pid):
            return HttpResponse(json.dumps({'result': 'illegal_operation', 'shared_url': ''}, indent=4), content_type='folder/json')
        #emails = request.POST.get('emails')
        description = request.POST.get('description')
        view_state = request.POST.get('view_state')
        
        if request.POST.get('checked') == 'false':
            expiration_date = datetime.datetime.now() + datetime.timedelta(days = settings.SHARED_VIEW_EXPIRATION_TIME)
        else:
            expiration_date = datetime.datetime.max
        
        if request.POST.get('shared_url'):
            shared_url = request.POST.get('shared_url')
            do_save_shared_view(pid, description, view_state, expiration_date, request.user, False, shared_url)
        else:
            shared_view = do_save_shared_view(pid, description, view_state, expiration_date, request.user)
            shared_url = shared_view.shared_url
        #for email in emails.split(';'):
        #    send_shared_view(email, shared_url)
        response = {
            'shared_url': shared_url
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
    
def send_shared_view(destination, shared_url):
    if gvsigol.settings.EMAIL_BACKEND_ACTIVE:       
        subject = _('Shared view')
        
        body = _('Shared view') + ':\n\n'   
        body = body + '  - ' + _('Link') + ': ' + shared_url + '\n'
        
        toAddress = [destination]           
        fromAddress = gvsigol.settings.EMAIL_HOST_USER
        
        print('Restore message: ' + body)
        try:
            send_mail(subject, body, fromAddress, toAddress, fail_silently=False)
        except Exception as e:
            print(e.smtp_error)
            pass

@cache_control(max_age=86400)
def load_shared_view(request, view_name):
    try:
        shared_view = SharedView.objects.get(name__exact=view_name)
        project = Project.objects.get(id=shared_view.project_id)
        if shared_view.internal and not request.user.is_superuser:
            raise PermissionDenied
        if not (project.is_public or request.user.is_authenticated):
            shared_url = settings.BASE_URL + '/gvsigonline/auth/login_user/?next=/gvsigonline/core/load_shared_view/' + view_name
            return redirect(shared_url)

        plugins_config = core_utils.get_plugins_config()
        enabled_plugins = core_utils.get_enabled_plugins(project)
        response = render(request, 'viewer.html', {
            'has_image': bool(project.image),
            'supported_crs': core_utils.get_supported_crs(),
            'project': project,
            'project_logo': project.logo_url,
            'project_image': project.image_url,
            'pid': project.id,
            'extra_params': json.dumps(request.GET),
            'plugins_config': plugins_config,
            'enabled_plugins': enabled_plugins,
            'is_shared_view': True,
            'shared_view_name': shared_view.name,
            'main_page': settings.LOGOUT_REDIRECT_URL,
            'is_viewer_template': True,
            'viewer_default_crs': project.viewer_default_crs
            }
        )

        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie('key', expires = expires)

        return response

    except Exception:
        return redirect('not_found_sharedview')

@login_required()
@staff_required
def shared_view_list(request):

    shared_view_list = SharedView.objects.filter(internal=False)

    shared_views = []
    for sv in shared_view_list:
        shared_view = {}
        shared_view['id'] = sv.id
        shared_view['url'] = sv.url
        shared_view['expiration_date'] = sv.expiration_date
        shared_view['description'] = sv.description
        shared_views.append(shared_view)

    response = {
        'shared_views': shared_views
    }
    return render(request, 'shared_view_list.html', response)

@login_required()
@staff_required
def shared_view_delete(request, svid):
    if request.method == 'POST':
        shared_view = SharedView.objects.get(id=int(svid))
        shared_view.delete()

        response = {
            'deleted': True
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='project/json')

def not_found_sharedview(request):
    response = render(request, 'not_found_sharedview.html', {})
    response.status_code = 404
    return response

def _project_clone(project, new_project_name, title, target_server, target_workspace_name, target_datastore_name, username, clone_conf=None):
    if not clone_conf:
        clone_conf = CloneConf()
    if target_server.frontend_url.endswith("/"):
        uri = target_server.frontend_url + target_workspace_name
    else:
        uri = target_server.frontend_url + "/" + target_workspace_name

    values = {
        "name": target_workspace_name,
        "description": target_workspace_name + " ws",
        "uri": uri,
        "wms_endpoint": target_server.getWmsEndpoint(target_workspace_name),
        "wfs_endpoint": target_server.getWfsEndpoint(target_workspace_name),
        "wcs_endpoint": target_server.getWcsEndpoint(target_workspace_name),
        "wmts_endpoint": target_server.getWmtsEndpoint(target_workspace_name),
        "cache_endpoint": target_server.getCacheEndpoint(target_workspace_name)
    }
    try:
        target_workspace = None
        datastore = None
        new_project = None
        target_workspace = services_utils.create_workspace(target_server.id, target_workspace_name, uri, values, username)
        if not target_workspace:
            raise Exception('Error creating target workspace')
        datastore = services_utils.create_datastore(username, target_datastore_name, target_workspace)
        new_project = project.clone(target_datastore=datastore, name=new_project_name, title=title, clone_conf=clone_conf)
        server = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server.id)
        server.reload_nodes()
        return new_project
    except Exception as e:
        if clone_conf.clean_on_failure:
            try:
                if target_workspace:
                    if datastore:
                        services_utils._workspace_delete(target_workspace, delete_data=True)
                    else:
                        services_utils._workspace_delete(target_workspace, delete_data=False)
                    if datastore:
                        gs = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server.id)
                    else:
                        gs = None
                
                    if new_project:
                        lyr_groups = [prj_lg.layer_group for prj_lg in new_project.projectlayergroup_set.filter(baselayer_group=False)]
                        new_project.delete()
                        for lyr_group in lyr_groups:
                            if gs:
                                gs.deleteGeoserverLayerGroup(lyr_group)
                            lyr_group.delete()

                        gs.setDataRules()
                    gs.reload_nodes()
            except:
                logger.exception("Could not clean_on_failure")
                pass
        raise

@login_required()
@superuser_required
def project_clone(request, pid):
    try:
        if request.user.is_superuser:
            project = Project.objects.get(id=int(pid))
        else:
            project = Project.objects.get(id=int(pid), created_by__exact=request.user.username)
    except:
        project = None
    if request.method == 'POST':
        form = CloneProjectForm(request.POST)
        if form.is_valid():
            if not project:
                form.add_error(None, _('Operation not allowed on project: ')+str(pid))
            name = form.cleaned_data.get('project_name')
            title = form.cleaned_data.get('project_title')
            target_workspace_name = form.cleaned_data.get('target_workspace')
            target_datastore_name = form.cleaned_data.get('target_datastore')
            target_server = form.cleaned_data.get('target_server')
            copy_data = form.cleaned_data.get('copy_data')
            permission_choice = form.cleaned_data.get('permission_choice')

            clone_conf = CloneConf(copy_data=copy_data, permissions=permission_choice)

            if _project_clone(project,
                           name,
                           title,
                           target_server,
                           target_workspace_name,
                           target_datastore_name,
                           request.user.username,
                           clone_conf):
                messages.add_message(request, messages.INFO, _('The project was successfully cloned.'))
                return redirect('project_update', pid=project.id)
    else:
        form = CloneProjectForm()
        if not project:
            form.add_error(None, _('Operation not allowed on project: ')+str(pid))
    servers = Server.objects.all()
    return render(request, 'project_clone.html', {'form': form, 'servers': servers})

@superuser_required
def project_permissions_to_layer(request, pid):
    """
    Add read permissions on all the layers belonging to the layer groups of the project
    for all the user groups of the project.
    """
    if request.POST:
        try:
            print(request.POST.get("usergroups[]"))
            print(request.POST.get("is_public"))
            project = Project.objects.get(pk=pid)
            roles = project.projectrole_set.all().values_list('role', flat=True)
            last_server_id = None
            for prlg in project.projectlayergroup_set.all():
                for layer in prlg.layer_group.layer_set.filter(external=False):
                    for role in roles:
                        if not LayerReadRole.objects.filter(layer=layer, role=role).exists():
                            lyr_role = LayerReadRole()
                            lyr_role.layer = layer
                            lyr_role.role = role
                            lyr_role.save()
                    if layer.datastore.workspace.server_id != last_server_id:
                        last_server_id = layer.datastore.workspace.server_id
                        server = geographic_servers.get_instance().get_server_by_id(last_server_id)
                    read_roles = LayerReadRole.objects.filter(layer=layer).values_list('role', flat=True)
                    server.setLayerDataRules(layer, read_roles, None)
            return JsonResponse({"status": "success"})
        except Project.DoesNotExist:
            return JsonResponse({"status": "error"}, status=404)
        except:
            return JsonResponse({"status": "error"}, status=500)
    return JsonResponse({"status": "error"}, status=400)

@superuser_required
def extend_permissions_to_layer(request):
    """
    Add read permissions on all the layers belonging to the provided layer groups
    for all the provided user groups.
    """
    if request.POST:
        try:
            assigned_read_roles = []
            public_project = (request.POST.get("is_public") == 'true')
            for key in request.POST.getlist("usergroups[]", []):
                assigned_read_roles.append(key[len('usergroup-'):])
            assigned_layergroups = request.POST.getlist("layergroups[]", [])
            # not used for the moment
            #is_public = request.POST.get("is_public")
            last_server_id = None
            for layergroup in LayerGroup.objects.filter(pk__in=assigned_layergroups):
                for layer in layergroup.layer_set.filter(external=False):
                    if public_project:
                        layer.public = True
                        layer.save()
                    for role in assigned_read_roles:
                        if not LayerReadRole.objects.filter(layer=layer, role=role).exists():
                            lyr_read_role = LayerReadRole()
                            lyr_read_role.layer = layer
                            lyr_read_role.role = role
                            lyr_read_role.save()
                    if layer.datastore.workspace.server_id != last_server_id:
                        last_server_id = layer.datastore.workspace.server_id
                        server = geographic_servers.get_instance().get_server_by_id(last_server_id)
                    read_roles = LayerReadRole.objects.filter(layer=layer).values_list('role', flat=True).distinct()
                    server.setLayerDataRules(layer, read_roles, None)
            return JsonResponse({"status": "success"})
        except Project.DoesNotExist:
            return JsonResponse({"status": "error"}, status=404)
        except:
            logger.exception("")
            return JsonResponse({"status": "error"}, status=500)
    return JsonResponse({"status": "error"}, status=400)

@login_required()
@staff_required
def application_list(request):

    application_list = None
    if request.user.is_superuser:
        application_list = Application.objects.all()
    else:
        application_list = Application.objects.filter(created_by__exact=request.user.username)

    applications = []
    for app in application_list:
        application = {}
        application['id'] = app.id
        application['name'] = app.name
        application['title'] = app.title
        application['description'] = app.description
        application['url'] = app.url
        application['is_public'] = app.is_public
        applications.append(application)

    response = {
        'applications': applications
    }
    return render(request, 'application_list.html', response)

@login_required()
@staff_required
def application_add(request):
    if request.method == 'POST':
        name = request.POST.get('application-name')

        name = re.sub(r'[^a-zA-Z0-9 ]',r'',name) #for remove all characters
        name = re.sub(' ','',name)

        title = request.POST.get('application-title')
        description = request.POST.get('application-description')
        url = request.POST.get('application-url')
        conf = request.POST.get('application-conf')

        is_public = False
        if 'is_public' in request.POST:
            is_public = True

        has_image = False
        if 'application-image' in request.FILES:
            has_image = True

        assigned_roles = []
        for key in request.POST:
            if 'usergroup-' in key:
                assigned_roles.append(key[len('usergroup-'):])

        groups = None
        if request.user.is_superuser:
            groups = auth_backend.get_all_roles_details(exclude_system=True)
        else:
            groups = get_primary_user_role_details(request)

        if name == '':
            message = _('You must enter an application name')
            return render(request, 'application_add.html', {'message': message, 'groups': groups})

        if _valid_projectname_regex.search(name) == None:
            message = _("Invalid application name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
            return render(request, 'application_add.html', {'message': message, 'groups': groups})

        if Application.objects.filter(name=name).exists():
            message = _('Application name already exists')
            return render(request, 'application_add.html', {'message': message, 'groups': groups})

        app = Application(
            name = name,
            title = title,
            description = description,
            url = url,
            conf = conf,
            created_by = request.user.username,
            is_public = is_public
        )
        app.save()
        
        if has_image:
            app.image = request.FILES['application-image']
            app.save()

        roles = auth_backend.get_all_roles()
        for assigned_role in assigned_roles:
            if assigned_role in roles:
                app_role = ApplicationRole(
                    application = app,
                    role = assigned_role
                )
                app_role.save()

        app_role = ApplicationRole(
            application = app,
            role = 'admin'
        )
        app_role.save()

        return redirect('application_list')

    else:
        roles = None
        if request.user.is_superuser:
            roles = auth_backend.get_all_roles_details(exclude_system=True)
        else:
            roles = get_primary_user_role_details(request)

        return render(request, 'application_add.html', {'groups': roles})


@login_required()
@staff_required
def application_update(request, appid):
    if request.method == 'POST':
        name = request.POST.get('application-name')
        title = request.POST.get('application-title')
        description = request.POST.get('application-description')
        url = request.POST.get('application-url')
        conf = request.POST.get('application-conf')

        is_public = False
        if 'is_public' in request.POST:
            is_public = True

        assigned_roles = []
        for key in request.POST:
            if 'usergroup-' in key:
                assigned_roles.append(key[len('usergroup-'):])

        has_image = False
        if 'application-image' in request.FILES:
            has_image = True

        app = Application.objects.get(id=int(appid))

        name = re.sub(r'[^a-zA-Z0-9 ]',r'',name) #for remove all characters
        name = re.sub(' ','',name)

        app.name = name
        app.title = title
        app.description = description
        app.url = url
        app.conf = conf
        app.is_public = is_public
        
        if has_image:
            app.image = request.FILES['application-image']

        app.save()

        ApplicationRole.objects.filter(application_id=app.id).delete()
        roles = auth_backend.get_all_roles()
        for role in assigned_roles:
            if role in roles:
                app_role = ApplicationRole(
                    application = app,
                    role = role
                )
                app_role.save()

        app_role = ApplicationRole(
            application = app,
            role = 'admin'
        )
        app_role.save()

        return redirect('application_list')

    else:
        app = Application.objects.get(id=int(appid))
        roles = core_utils.get_all_roles_checked_by_application(app)
        
        return render(request, 'application_update.html', {
            'appid': appid, 
            'application': app,
            'groups': roles,
            'superuser' : is_superuser(request.user)
        })


@login_required()
@staff_required
def application_delete(request, appid):
    if request.method == 'POST':
        try:
            if request.user.is_superuser:
                app = Application.objects.get(id=int(appid))
            else:
                app = Application.objects.get(id=int(appid), created_by__exact=request.user.username)
            app.delete()
            response = {
                'deleted': True
            }
            return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
        except:
            logger.exception("Error deleting application")
            return HttpResponseForbidden({"deleted": False, "error": "Not allowed"})


def default_index(request, template="index.html", response={}):
    if settings.USE_SPA_PROJECT_LINKS and settings.FRONTEND_REDIRECT_URL:    
        return redirect(settings.FRONTEND_REDIRECT_URL)
    else:
        return render(request, 'index.html', response)
