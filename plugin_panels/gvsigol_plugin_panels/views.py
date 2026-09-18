# -*- coding: utf-8 -*-
import logging
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from gvsigol_auth import auth_backend
from gvsigol_auth import signals
from gvsigol_auth.utils import staff_required
from gvsigol_core.models import Project
from gvsigol_core.utils import can_read_project
from gvsigol_services.models import Layer
from gvsigol_services import utils as services_utils

from .models import Panel, PanelDataset, PanelRole, PanelWidget
from . import utils

logger = logging.getLogger(__name__)


def _role_deleted_handler(sender, **kwargs):
    PanelRole.objects.filter(role=kwargs.get('role')).delete()


signals.role_deleted.connect(
    _role_deleted_handler,
    dispatch_uid='gvsigol_plugin_panels_role_deleted',
)


def _resolve_token_user(request):
    """Resuelve el usuario a partir del token que envía el frontend.

    Estas vistas son vistas Django planas y solo ven la sesión, mientras que el
    SPA se autentica con un token Bearer que únicamente interpretan las clases
    de autenticación de DRF.
    """
    from rest_framework.request import Request
    from rest_framework.settings import api_settings
    try:
        authenticators = [cls() for cls in api_settings.DEFAULT_AUTHENTICATION_CLASSES]
        user = Request(request, authenticators=authenticators).user
    except Exception:
        logger.debug('unable to authenticate panels request with a token', exc_info=True)
        return
    if user is not None and user.is_authenticated:
        request.user = user


def api_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not getattr(request.user, 'is_authenticated', False):
            _resolve_token_user(request)
        return view_func(request, *args, **kwargs)
    return wrapper


def _json_error(message, status=400):
    return JsonResponse({'success': False, 'error': message}, status=status)


def _json_ok(payload=None, status=200):
    data = {'success': True}
    if payload is not None:
        data.update(payload)
    return JsonResponse(data, status=status)


def _get_project(project_id=None, project_name=None):
    if project_id:
        return get_object_or_404(Project, pk=project_id)
    return get_object_or_404(Project, name=project_name)


def _can_edit(request, project):
    if not request.user.is_authenticated:
        return False
    return bool(project.can_manage(request)) or request.user.is_superuser


def _selected_project(request):
    project_id = request.POST.get('project_id')
    if not project_id:
        return None
    project = get_object_or_404(Project, pk=project_id)
    if not project.can_manage(request) and not request.user.is_superuser:
        return None
    return project


def _dataset_belongs_to_panel(dataset, panel):
    if dataset.panel_id:
        return dataset.panel_id == panel.id
    if panel.project_id and dataset.project_id == panel.project_id:
        return True
    return dataset.panelwidget_set.filter(panel=panel).exists()


def _private_layers(layer_ids):
    return list(Layer.objects.select_for_update().filter(
        pk__in=set(layer_ids), public=False))


def _reassignable_roles(queryset, skip_roles=()):
    """Roles que se pueden reenviar a set_layer_permissions sin duplicarlos.

    set_layer_permissions borra y recrea los permisos no externos y añade por su
    cuenta el rol de administración, así que hay que quitar duplicados y el rol
    de administración para no violar la restricción de unicidad.
    """
    roles = dict.fromkeys(queryset.values_list('role', flat=True))
    return [role for role in roles if role not in skip_roles]


def _publish_layers(request, layers):
    if any(not services_utils.can_manage_layer(request, layer) for layer in layers):
        return False
    from gvsigol_services.models import LayerManageRole, LayerReadRole, LayerWriteRole
    admin_roles = (auth_backend.get_admin_role(),)
    for layer in layers:
        read_roles = _reassignable_roles(
            LayerReadRole.objects.filter(layer=layer, external=False), admin_roles)
        write_roles = _reassignable_roles(
            LayerWriteRole.objects.filter(layer=layer, external=False), admin_roles)
        manage_roles = _reassignable_roles(LayerManageRole.objects.filter(layer=layer))
        try:
            # Savepoint propio para que un fallo no invalide la transacción del guardado.
            with transaction.atomic():
                services_utils.set_layer_permissions(
                    layer, True, read_roles, write_roles, manage_roles)
        except Exception:
            logger.exception('Unable to publish layers required by a public panel')
            return False
        layer.refresh_from_db()
    return True


def _payload_layer_ids(panel, widgets_payload):
    ids = set()
    dataset_ids = set()
    for item in widgets_payload or []:
        if not isinstance(item, dict):
            continue
        config = item.get('config') if isinstance(item.get('config'), dict) else {}
        if config.get('layer_id'):
            ids.add(config['layer_id'])
        if item.get('dataset_id'):
            dataset_ids.add(item['dataset_id'])
    ids.update(PanelDataset.objects.filter(
        pk__in=dataset_ids, layer_id__isnull=False).values_list('layer_id', flat=True))
    return ids


def _rescope_panel_datasets(panel, new_project):
    """Preserve imported data when a panel changes or drops its project."""
    replacements = {}
    widgets = panel.widgets.select_related('dataset').exclude(dataset_id=None)
    for widget in widgets:
        dataset = widget.dataset
        already_valid = (
            dataset.panel_id == panel.id
            or (new_project is not None and dataset.project_id == new_project.id)
        )
        if already_valid:
            continue
        if dataset.id not in replacements:
            clone = PanelDataset.objects.create(
                project=new_project,
                panel=None if new_project is not None else panel,
                name=dataset.name,
                source_type=dataset.source_type,
                layer=dataset.layer,
                file=dataset.file.name if dataset.file else None,
                column_mapping=dataset.column_mapping,
                rows=dataset.rows,
            )
            replacements[dataset.id] = clone
        widget.dataset = replacements[dataset.id]
        widget.save(update_fields=['dataset'])


def _can_view_panel(request, panel):
    return panel.can_read(request)


def _can_manage_panel(request, panel):
    return panel.can_manage(request)


def _require_edit(request, project):
    if not _can_edit(request, project):
        return _json_error('forbidden', 403)
    return None


def _require_panel_edit(request, panel):
    if not _can_manage_panel(request, panel):
        return _json_error('forbidden', 403)
    return None


def _manageable_projects(request):
    return [
        project for project in Project.objects.all().order_by('title')
        if project.can_manage(request)
    ]


def _panel_roles(panel=None):
    read = set()
    manage = set()
    if panel:
        read = set(panel.panelrole_set.filter(
            permission=PanelRole.PERM_READ,
        ).values_list('role', flat=True))
        manage = set(panel.panelrole_set.filter(
            permission=PanelRole.PERM_MANAGE,
        ).values_list('role', flat=True))
    roles = []
    for role in auth_backend.get_all_roles_details(exclude_system=True):
        item = dict(role)
        item['read_checked'] = item.get('name') in read
        item['manage_checked'] = item.get('name') in manage
        roles.append(item)
    return roles


def _save_panel_roles(request, panel):
    known = set(auth_backend.get_all_roles())
    read = {
        key[len('read-role-'):]
        for key in request.POST
        if key.startswith('read-role-')
    }
    manage = {
        key[len('manage-role-'):]
        for key in request.POST
        if key.startswith('manage-role-')
    }
    # Nadie que gestiona un panel debe perder la capacidad de leerlo.
    read.update(manage)
    admin_role = auth_backend.get_admin_role()
    if admin_role:
        manage.add(admin_role)
        read.add(admin_role)
    if panel.created_by:
        creator_role = auth_backend.get_primary_role(panel.created_by)
        if creator_role:
            manage.add(creator_role)
            read.add(creator_role)

    panel.panelrole_set.all().delete()
    rows = [
        PanelRole(panel=panel, role=role, permission=permission)
        for permission, selected in (
            (PanelRole.PERM_READ, read),
            (PanelRole.PERM_MANAGE, manage),
        )
        for role in selected
        if role in known
    ]
    PanelRole.objects.bulk_create(rows, ignore_conflicts=True)


def _admin_panel_context(request, panel=None):
    return {
        'panel': panel,
        'projects': _manageable_projects(request),
        'roles': _panel_roles(panel),
    }


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def dashboard_panels(request):
    panels = [
        panel for panel in Panel.objects.select_related('project').all()
        if panel.can_manage(request)
    ]
    return render(request, 'panels_list.html', {'panels': panels})


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def dashboard_panel_add(request):
    projects = _manageable_projects(request)
    if request.method == 'POST':
        project = _selected_project(request)
        if request.POST.get('project_id') and project is None:
            return _json_error('forbidden', 403)
        name = (request.POST.get('name') or '').strip()
        title = (request.POST.get('title') or '').strip()
        if not name or not title:
            messages.error(request, _('Name and title are required'))
            return render(request, 'panels_form.html', _admin_panel_context(request))
        panel = Panel.objects.create(
            project=project,
            name=name,
            title=title,
            description=(request.POST.get('description') or '').strip(),
            slug=utils.unique_slug(name),
            is_public=request.POST.get('is_public') == 'on',
            created_by=request.user.username,
        )
        _save_panel_roles(request, panel)
        messages.success(request, _('Panel created successfully'))
        return redirect('panels_dashboard_list')
    return render(request, 'panels_form.html', _admin_panel_context(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@transaction.atomic
def dashboard_panel_update(request, panel_id):
    panel = get_object_or_404(Panel.objects.select_related('project'), pk=panel_id)
    if not panel.can_manage(request):
        return _json_error('forbidden', 403)
    if request.method == 'POST':
        project = _selected_project(request)
        if request.POST.get('project_id') and project is None:
            return _json_error('forbidden', 403)
        name = (request.POST.get('name') or '').strip()
        title = (request.POST.get('title') or '').strip()
        if not name or not title:
            messages.error(request, _('Name and title are required'))
            return render(request, 'panels_form.html', _admin_panel_context(request, panel))
        panel.name = name
        panel.title = title
        panel.description = (request.POST.get('description') or '').strip()
        project_changed = panel.project_id != (project.id if project else None)
        panel.project = project
        panel.slug = utils.unique_slug(name, exclude_id=panel.id)
        wants_public = request.POST.get('is_public') == 'on'
        private_layers = _private_layers(utils.panel_layer_ids(panel)) if wants_public else []
        if private_layers and request.POST.get('confirm_public_layers') != 'yes':
            panel.is_public = True
            context = _admin_panel_context(request, panel)
            context['private_layers'] = private_layers
            return render(request, 'panels_form.html', context)
        if private_layers and not _publish_layers(request, private_layers):
            messages.error(
                request,
                _('You cannot publish this panel because you cannot manage all its private layers.'))
            context = _admin_panel_context(request, panel)
            context['private_layers_forbidden'] = private_layers
            return render(request, 'panels_form.html', context)
        if project_changed:
            _rescope_panel_datasets(panel, project)
        panel.is_public = wants_public
        panel.save()
        _save_panel_roles(request, panel)
        messages.success(request, _('Panel updated successfully'))
        return redirect('panels_dashboard_list')
    return render(request, 'panels_form.html', _admin_panel_context(request, panel))


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@require_http_methods(['POST'])
def dashboard_panel_delete(request, panel_id):
    panel = get_object_or_404(Panel, pk=panel_id)
    if not panel.can_manage(request):
        return _json_error('forbidden', 403)
    panel.delete()
    messages.success(request, _('Panel deleted successfully'))
    return redirect('panels_dashboard_list')


@api_auth
@require_http_methods(['GET'])
def readable_panels(request):
    """Todos los paneles que el usuario puede abrir, con o sin proyecto."""
    panels = []
    qs = Panel.objects.select_related('project').prefetch_related('widgets')
    for panel in qs:
        if not panel.can_read(request):
            continue
        data = utils.serialize_panel(panel, include_widgets=False)
        data['can_edit'] = bool(panel.can_manage(request))
        # La misma imagen que identifica a los paneles en la portada de Django.
        data['image'] = settings.STATIC_URL + 'panels/panel.svg'
        panels.append(data)
    return _json_ok({'panels': panels})


@api_auth
@ensure_csrf_cookie
@require_http_methods(['GET', 'POST'])
def project_panels(request, project_id):
    project = _get_project(project_id=project_id)
    if request.method == 'GET':
        if not can_read_project(request, project) and not project.is_public:
            return _json_error('forbidden', 403)
        qs = [
            panel for panel in Panel.objects.filter(project=project)
            if panel.can_read(request)
        ]
        can_edit = _can_edit(request, project)
        is_staff = bool(getattr(request.user, 'is_staff', False))
        panels = []
        for panel in qs:
            data = utils.serialize_panel(panel, include_widgets=False)
            data['can_edit'] = bool(panel.can_manage(request))
            # La ficha del panel de control exige perfil de staff, además de gestión.
            data['can_configure'] = is_staff and bool(panel.can_manage(request))
            panels.append(data)
        return _json_ok({'panels': panels, 'can_edit': can_edit, 'project_id': project.id, 'project_name': project.name})

    err = _require_edit(request, project)
    if err:
        return err
    body = utils.parse_json_body(request)
    title = (body.get('title') or '').strip()
    if not title:
        return _json_error('title_required')
    panel = Panel.objects.create(
        project=project,
        name=(body.get('name') or title).strip(),
        title=title,
        description=(body.get('description') or '').strip(),
        slug=utils.unique_slug(title),
        layout=body.get('layout') if isinstance(body.get('layout'), dict) else {},
        created_by=getattr(request.user, 'username', '') or '',
    )
    return _json_ok({'panel': utils.serialize_panel(panel)}, status=201)


@api_auth
@require_http_methods(['GET', 'PUT', 'PATCH', 'DELETE'])
def panel_detail(request, panel_id):
    panel = get_object_or_404(Panel.objects.select_related('project'), pk=panel_id)
    if request.method == 'GET':
        if not _can_view_panel(request, panel):
            return _json_error('forbidden', 403)
        return _json_ok({
            'panel': utils.serialize_panel(panel),
            'can_edit': _can_manage_panel(request, panel),
        })

    err = _require_panel_edit(request, panel)
    if err:
        return err
    if request.method == 'DELETE':
        panel.delete()
        return _json_ok()

    body = utils.parse_json_body(request)
    if 'title' in body and body.get('title'):
        panel.title = body['title'].strip()
    if 'description' in body:
        panel.description = (body.get('description') or '').strip()
    if body.get('slug'):
        panel.slug = utils.unique_slug(body['slug'], exclude_id=panel.id)
    elif 'title' in body and body.get('title'):
        panel.slug = utils.unique_slug(panel.title, exclude_id=panel.id)
    if isinstance(body.get('layout'), dict):
        panel.layout = body['layout']
    panel.save()
    return _json_ok({'panel': utils.serialize_panel(panel)})


@api_auth
@require_http_methods(['POST'])
@transaction.atomic
def panel_save(request, panel_id):
    panel = get_object_or_404(Panel.objects.select_related('project'), pk=panel_id)
    err = _require_panel_edit(request, panel)
    if err:
        return err
    body = utils.parse_json_body(request)
    widgets_payload = body.get('widgets')
    if panel.is_public and isinstance(widgets_payload, list):
        private_layers = _private_layers(_payload_layer_ids(panel, widgets_payload))
        if private_layers and not body.get('publish_private_layers'):
            return JsonResponse({
                'success': False,
                'error': 'private_layers_confirmation',
                'private_layers': [
                    {'id': layer.id, 'title': layer.title or layer.name}
                    for layer in private_layers
                ],
                'can_publish': all(
                    services_utils.can_manage_layer(request, layer)
                    for layer in private_layers
                ),
            }, status=409)
        if private_layers and not _publish_layers(request, private_layers):
            return _json_error('private_layers_forbidden', 403)
    if body.get('title'):
        panel.title = body['title'].strip()
    if 'description' in body:
        panel.description = (body.get('description') or '').strip()
    if isinstance(body.get('layout'), dict):
        panel.layout = body['layout']
    panel.save()

    if isinstance(widgets_payload, list):
        keep_ids = []
        for index, item in enumerate(widgets_payload):
            if not isinstance(item, dict):
                continue
            widget_id = item.get('id')
            widget = None
            if widget_id:
                widget = panel.widgets.filter(pk=widget_id).first()
            if widget is None:
                widget = PanelWidget(panel=panel)
            utils.apply_widget_payload(widget, item, index=index)
            if widget.dataset_id:
                ds = PanelDataset.objects.filter(pk=widget.dataset_id).first()
                widget.dataset = ds if ds and _dataset_belongs_to_panel(ds, panel) else None
            if widget.layer_id:
                layer = Layer.objects.filter(pk=widget.layer_id).first()
                if not layer or not utils.is_vector_layer(layer) or not services_utils.can_read_layer(request, layer):
                    return _json_error('layer_forbidden', 403)
            widget.save()
            keep_ids.append(widget.id)
        panel.widgets.exclude(pk__in=keep_ids).delete()
    return _json_ok({'panel': utils.serialize_panel(panel)})


@api_auth
@require_http_methods(['GET'])
def panel_by_slug(request, project_name, slug):
    panel = get_object_or_404(
        Panel.objects.select_related('project'),
        project__name=project_name,
        slug=slug,
    )
    if not _can_view_panel(request, panel):
        return _json_error('forbidden', 403)
    return _json_ok({
        'panel': utils.serialize_panel(panel),
        'can_edit': _can_manage_panel(request, panel),
    })


@api_auth
@require_http_methods(['GET'])
def standalone_panel_by_slug(request, slug):
    panel = get_object_or_404(Panel.objects.select_related('project'), slug=slug)
    if not _can_view_panel(request, panel):
        return _json_error('forbidden', 403)
    return _json_ok({
        'panel': utils.serialize_panel(panel),
        'can_edit': _can_manage_panel(request, panel),
    })


@api_auth
@require_http_methods(['GET'])
def panel_project_config(request, project_name, slug):
    """Project configuration needed by the standalone panel route.

    It deliberately authorizes against the panel instead of the viewer project:
    a public panel may be opened even when the viewer itself is not public. The
    public serializer still limits layer metadata to public layers.
    """
    panel = get_object_or_404(
        Panel.objects.select_related('project'),
        project__name=project_name,
        slug=slug,
    )
    if not panel.can_read(request):
        return _json_error('forbidden', 403)
    from gvsigol_plugin_projectapi.infoserializer import InfoSerializer, PublicInfoSerializer
    lang = request.GET.get('lang') or 'es'
    if panel.is_public:
        serializer = PublicInfoSerializer(panel.project, context={'lang': lang})
    else:
        serializer = InfoSerializer(panel.project, context={
            'request': request,
            'user': getattr(request.user, 'username', ''),
            'lang': lang,
            'user_profile': None,
        })
    return JsonResponse({'projects': [serializer.data]})


@api_auth
@require_http_methods(['GET'])
def standalone_panel_config(request, slug):
    """Configuración de mapa del panel, tenga proyecto o no.

    Se autoriza contra el panel, no contra el visor: un panel público se abre
    aunque su proyecto no lo sea. Si hay proyecto se reutiliza su configuración
    (capas base, plugins); si no, se sintetiza una a partir de sus capas.
    """
    panel = get_object_or_404(Panel.objects.select_related('project'), slug=slug)
    if not panel.can_read(request):
        return _json_error('forbidden', 403)
    if panel.project_id:
        from gvsigol_plugin_projectapi.infoserializer import InfoSerializer, PublicInfoSerializer
        lang = request.GET.get('lang') or 'es'
        if panel.is_public:
            serializer = PublicInfoSerializer(panel.project, context={'lang': lang})
        else:
            serializer = InfoSerializer(panel.project, context={
                'request': request,
                'user': getattr(request.user, 'username', ''),
                'lang': lang,
                'user_profile': None,
            })
        data = dict(serializer.data)
        # Mismo sitio para las capas base tenga proyecto o no, que es donde las
        # busca el mapa del panel.
        data['base_layers'] = utils.base_layers_config(panel)
        return JsonResponse({'projects': [data]})
    layer_ids = utils.panel_layer_ids(panel)
    layers = Layer.objects.filter(pk__in=layer_ids).select_related('datastore__workspace')
    return JsonResponse({'projects': [utils.synthetic_panel_config(panel, layers)]})


@api_auth
@require_http_methods(['GET'])
def project_layers(request, project_id):
    project = _get_project(project_id=project_id)
    if not can_read_project(request, project) and not project.is_public:
        return _json_error('forbidden', 403)
    layers = [utils.serialize_layer(layer) for layer in utils.project_operational_layers(project)]
    return _json_ok({'layers': layers})


@api_auth
@require_http_methods(['GET'])
def panel_layers(request, panel_id):
    panel = get_object_or_404(Panel.objects.select_related('project'), pk=panel_id)
    if not panel.can_read(request):
        return _json_error('forbidden', 403)
    if panel.can_manage(request):
        layers = utils.global_operational_layers(request)
    else:
        layers = utils.vector_layers(Layer.objects.filter(
            pk__in=utils.panel_layer_ids(panel),
            external=False,
            queryable=True,
        )).select_related('datastore__workspace')
        layers = [layer for layer in layers if services_utils.can_read_layer(request, layer)]
    return _json_ok({'layers': [utils.serialize_layer(layer) for layer in layers]})


@api_auth
@require_http_methods(['GET'])
def layer_fields(request, project_id, layer_id):
    project = _get_project(project_id=project_id)
    if not can_read_project(request, project) and not project.is_public:
        return _json_error('forbidden', 403)
    layer = get_object_or_404(Layer, pk=layer_id)
    if not utils.is_vector_layer(layer):
        return _json_error('layer_not_vector', 400)
    if not utils.layer_in_project(project, layer):
        return _json_error('layer_not_in_project', 400)
    return _json_ok(utils.load_layer_fields(layer))


@api_auth
@require_http_methods(['GET'])
def panel_layer_fields(request, panel_id, layer_id):
    panel = get_object_or_404(Panel, pk=panel_id)
    if not panel.can_manage(request):
        return _json_error('forbidden', 403)
    layer = get_object_or_404(Layer, pk=layer_id, external=False, queryable=True)
    if not utils.is_vector_layer(layer):
        return _json_error('layer_not_vector', 400)
    if not services_utils.can_read_layer(request, layer):
        return _json_error('forbidden', 403)
    return _json_ok(utils.load_layer_fields(layer))


@api_auth
@require_http_methods(['GET', 'POST'])
def project_datasets(request, project_id):
    project = _get_project(project_id=project_id)
    if request.method == 'GET':
        if not can_read_project(request, project) and not project.is_public:
            return _json_error('forbidden', 403)
        datasets = [utils.serialize_dataset(d) for d in project.panel_datasets.all().order_by('-id')]
        return _json_ok({'datasets': datasets})

    err = _require_edit(request, project)
    if err:
        return err
    body = utils.parse_json_body(request)
    name = (body.get('name') or '').strip() or 'dataset'
    source_type = body.get('source_type') or PanelDataset.SOURCE_SHEET
    if source_type not in (PanelDataset.SOURCE_WFS, PanelDataset.SOURCE_SHEET, PanelDataset.SOURCE_REST):
        source_type = PanelDataset.SOURCE_SHEET
    dataset = PanelDataset(project=project, name=name, source_type=source_type)
    layer_id = body.get('layer_id')
    if layer_id:
        layer = get_object_or_404(Layer, pk=layer_id)
        if not utils.layer_in_project(project, layer):
            return _json_error('layer_not_in_project', 400)
        if not utils.is_vector_layer(layer):
            return _json_error('layer_not_vector', 400)
        dataset.layer = layer
        dataset.source_type = PanelDataset.SOURCE_WFS
    dataset.column_mapping = body.get('column_mapping') if isinstance(body.get('column_mapping'), dict) else {}
    dataset.rows = utils.normalize_rows(body.get('rows') or [])
    dataset.save()
    payload = utils.serialize_dataset(dataset)
    payload['rows'] = dataset.rows[:200]
    return _json_ok({'dataset': payload}, status=201)


@api_auth
@require_http_methods(['GET', 'POST'])
def panel_datasets(request, panel_id):
    panel = get_object_or_404(Panel, pk=panel_id)
    if request.method == 'GET':
        if not panel.can_read(request):
            return _json_error('forbidden', 403)
        scoped = PanelDataset.objects.filter(
            Q(panel=panel) | Q(panelwidget__panel=panel)).distinct().order_by('-id')
        if panel.project_id:
            scoped = PanelDataset.objects.filter(
                Q(panel=panel)
                | Q(panelwidget__panel=panel)
                | Q(project=panel.project, panel__isnull=True)
            ).distinct().order_by('-id')
        return _json_ok({'datasets': [utils.serialize_dataset(d) for d in scoped]})
    if not panel.can_manage(request):
        return _json_error('forbidden', 403)
    body = utils.parse_json_body(request)
    name = (body.get('name') or '').strip() or 'dataset'
    source_type = body.get('source_type') or PanelDataset.SOURCE_SHEET
    if source_type not in (
        PanelDataset.SOURCE_WFS, PanelDataset.SOURCE_SHEET, PanelDataset.SOURCE_REST,
    ):
        source_type = PanelDataset.SOURCE_SHEET
    dataset = PanelDataset(
        project=panel.project if panel.project_id else None,
        panel=None if panel.project_id else panel,
        name=name,
        source_type=source_type,
    )
    layer_id = body.get('layer_id')
    if layer_id:
        layer = get_object_or_404(Layer, pk=layer_id)
        if not services_utils.can_read_layer(request, layer):
            return _json_error('forbidden', 403)
        if not utils.is_vector_layer(layer):
            return _json_error('layer_not_vector', 400)
        dataset.layer = layer
        dataset.source_type = PanelDataset.SOURCE_WFS
    dataset.column_mapping = body.get('column_mapping') if isinstance(body.get('column_mapping'), dict) else {}
    dataset.rows = utils.normalize_rows(body.get('rows') or [])
    dataset.save()
    payload = utils.serialize_dataset(dataset)
    payload['rows'] = dataset.rows[:200]
    return _json_ok({'dataset': payload}, status=201)


@api_auth
@require_http_methods(['GET'])
def dataset_detail(request, dataset_id):
    dataset = get_object_or_404(
        PanelDataset.objects.select_related('project', 'panel', 'layer'), pk=dataset_id)
    panel_access = any(
        widget.panel.can_read(request)
        for widget in dataset.panelwidget_set.select_related('panel__project').all()
    )
    direct_panel_access = dataset.panel_id and dataset.panel.can_read(request)
    project_access = dataset.project_id and (
        can_read_project(request, dataset.project) or dataset.project.is_public)
    if not panel_access and not direct_panel_access and not project_access:
        return _json_error('forbidden', 403)
    data = utils.serialize_dataset(dataset)
    data['rows'] = dataset.rows or []
    if dataset.layer_id:
        data['layer'] = utils.serialize_layer(dataset.layer)
    return _json_ok({'dataset': data})
