# -*- coding: utf-8 -*-
"""
REST API for persisting vector/tabular imports into a project.

Owned by gvsigol_plugin_projectapi so temporary-layer persist and file import
work without gvsigol_plugin_importvector installed.
"""
import uuid

from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gvsigol_auth import auth_backend
from gvsigol_core.models import Project, ProjectLayerGroup
from gvsigol_plugin_baseapi.validation import Validation, HttpException
from gvsigol_services import utils as services_utils
from gvsigol_services.forms_geoserver import supported_encodings, supported_srs_and_blank
from gvsigol_services.forms_services import img_formats
from gvsigol_services.models import Datastore, LayerGroup, LayerGroupRole


def _check_project_access(request, project_id):
    validator = Validation(request)
    validator.check_get_project(project_id)
    return get_object_or_404(Project, id=project_id)


def _check_project_publish_access(request, project_id):
    """
    Persisting layers into a project is allowed for staff and superusers.
    Concrete destinations are further filtered by can_use_datastore /
    can_use_layergroup on import-options and on POST.
    """
    project = _check_project_access(request, project_id)
    user = request.user
    if not (
        getattr(user, 'is_superuser', False)
        or getattr(user, 'is_staff', False)
    ):
        raise PermissionDenied(
            'Only staff or superusers can publish layers into a project')
    return project


def _request_bool(data, key, default=False):
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('1', 'true', 'yes', 'on')


def _published_layer_payload(request, project, layer, layer_group):
    """
    Enough projectconf-shaped data for the SPA to hot-add the layer without
    depending on get_layerread filters (publisher may not match ACL yet).
    """
    from gvsigol_plugin_projectapi import util as projectapi_util
    from gvsigol_plugin_projectapi.infoserializer import (
        LayerSerializer,
        _get_group_server_endpoints,
    )

    lang = request.META.get('HTTP_ACCEPT_LANGUAGE', 'es')
    context = {
        'request': request,
        'user': getattr(request.user, 'username', None),
        'lang': lang,
        'projectid': project.id,
    }
    layer_data = LayerSerializer(layer, context=context).data
    endpoints = _get_group_server_endpoints(layer_group)
    try:
        group_order = projectapi_util.get_order_in_project(
            project.id, layer_group.name)
    except Exception:
        group_order = 0
    return {
        'layer': layer_data,
        'layer_group': {
            'id': layer_group.id,
            'name': layer_group.name,
            'title': layer_group.title or layer_group.name,
            'cached': bool(layer_group.cached),
            'created_by': layer_group.created_by,
            'visible': True,
            'server_id': layer_group.server_id,
            'order': group_order,
            'allows_getmap': False,
            'wms_url': endpoints.get('wms_url'),
            'wfs_url': endpoints.get('wfs_url'),
            'cache_url': endpoints.get('cache_url'),
            'layers': [layer_data],
        },
    }


class ProjectLayerImportOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        try:
            project = _check_project_publish_access(request, project_id)
        except HttpException as exc:
            return exc.get_exception()
        except PermissionDenied as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)

        datastores = [
            datastore for datastore in
            Datastore.objects.filter(type='v_PostGIS').select_related(
                'workspace__server').order_by('name')
            if services_utils.can_use_datastore(request.user, datastore)
        ]
        project_groups = LayerGroup.objects.filter(
            projectlayergroup__project=project,
            projectlayergroup__baselayer_group=False,
        ).distinct().order_by('title', 'name')
        groups = [
            group for group in project_groups
            if services_utils.can_use_layergroup(
                request.user, group,
                permission=LayerGroupRole.PERM_INCLUDEINPROJECTS)
        ]
        roles = auth_backend.get_all_roles_details(exclude_system=True)
        try:
            from gvsigol_plugin_geocopilot.models import ProjectGeoCopilotConfig
            geocopilot_enabled = ProjectGeoCopilotConfig.objects.filter(
                project=project, enabled=True).exists()
        except (ImportError, RuntimeError):
            geocopilot_enabled = False
        return Response({
            'datastores': [{
                'id': item.id,
                'name': item.name,
                'workspace': item.workspace.name,
                'server_id': item.workspace.server_id,
            } for item in datastores],
            'layer_groups': [{
                'id': item.id,
                'name': item.name,
                'title': item.title or item.name,
                'server_id': item.server_id,
            } for item in groups],
            'roles': roles,
            'geocopilot_enabled': geocopilot_enabled,
            'supported_srs': [
                {'value': value, 'label': str(label)}
                for value, label in supported_srs_and_blank
            ],
            'supported_encodings': [
                {'value': value, 'label': str(label)}
                for value, label in supported_encodings
            ],
            'formats': [
                {'value': value, 'label': str(label)}
                for value, label in img_formats
            ],
        })


class ProjectLayerImportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = _check_project_publish_access(request, project_id)
        except HttpException as exc:
            return exc.get_exception()
        except PermissionDenied as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        upload = request.FILES.get('file')
        if not upload:
            return Response(
                {'file': ['A file is required']},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            datastore = Datastore.objects.select_related(
                'workspace__server').get(id=request.data.get('datastore'))
            layer_group = LayerGroup.objects.get(
                id=request.data.get('layer_group'))
        except (Datastore.DoesNotExist, LayerGroup.DoesNotExist, ValueError, TypeError):
            return Response(
                {'detail': 'Invalid datastore or layer group'},
                status=status.HTTP_400_BAD_REQUEST)
        if not ProjectLayerGroup.objects.filter(
                project=project, layer_group=layer_group,
                baselayer_group=False).exists():
            return Response(
                {'layer_group': ['The layer group is not part of this project']},
                status=status.HTTP_400_BAD_REQUEST)
        if not services_utils.can_use_datastore(request.user, datastore):
            raise PermissionDenied('You cannot use the selected datastore')
        if not services_utils.can_use_layergroup(
                request.user, layer_group,
                permission=LayerGroupRole.PERM_INCLUDEINPROJECTS):
            raise PermissionDenied('You cannot publish in the selected layer group')

        getlist = getattr(request.data, 'getlist', None)
        role_list = (
            lambda key: getlist(key) if getlist else request.data.get(key, [])
        )
        # Prefer explicit auto_detect_wkt from the client. Empty wkt_column may
        # be dropped by multipart parsers, so the flag is the reliable signal
        # that the user cleared geometry in the wizard.
        wkt_column = (request.data.get('wkt_column') or '').strip() or None
        if 'auto_detect_wkt' in request.data:
            auto_detect_wkt = _request_bool(request.data, 'auto_detect_wkt', True)
        else:
            # Legacy: presence of wkt_column (even empty) means "do not guess".
            auto_detect_wkt = 'wkt_column' not in request.data
        options = {
            'name': request.data.get('name'),
            'title': request.data.get('title'),
            'abstract': request.data.get('abstract', ''),
            'srs': request.data.get('srs'),
            'native_srs': request.data.get('srs') or 'EPSG:4326',
            'encoding': request.data.get('encoding', 'autodetect'),
            'format': request.data.get('format', 'image/png'),
            'delimiter': request.data.get('delimiter'),
            'wkt_column': wkt_column,
            'auto_detect_wkt': auto_detect_wkt,
            'json_root': request.data.get('json_root'),
            'visible': _request_bool(request.data, 'visible', True),
            'queryable': _request_bool(request.data, 'queryable', True),
            'cached': _request_bool(request.data, 'cached'),
            'single_image': _request_bool(request.data, 'single_image'),
            'allow_download': _request_bool(request.data, 'allow_download'),
            'max_features': request.data.get('max_features', 0),
            'is_public': _request_bool(request.data, 'is_public'),
            'add_to_geocopilot': _request_bool(
                request.data, 'add_to_geocopilot', True),
            'read_roles': role_list('read_roles'),
            'write_roles': role_list('write_roles'),
            'manage_roles': role_list('manage_roles'),
        }
        job_id = str(uuid.uuid4())
        cache_key = 'project-layer-import:{}'.format(job_id)
        cache.set(cache_key, {'status': 'running'}, timeout=86400)
        try:
            from .import_service import import_uploaded_resource
            layer, has_geometry = import_uploaded_resource(
                upload, datastore, layer_group, request.user, options)
            try:
                from gvsigol_plugin_geocopilot.models import ProjectGeoCopilotConfig
                geocopilot_config = ProjectGeoCopilotConfig.objects.filter(
                    project=project, enabled=True).first()
                if geocopilot_config:
                    if options['add_to_geocopilot']:
                        geocopilot_config.excluded_layers.remove(layer)
                    else:
                        geocopilot_config.excluded_layers.add(layer)
            except (ImportError, RuntimeError):
                pass
            result = {
                'status': 'completed',
                'layer_id': layer.id,
                'has_geometry': has_geometry,
            }
            try:
                result.update(
                    _published_layer_payload(
                        request, project, layer, layer_group))
            except Exception:
                # Hot-add payload is best-effort; import already succeeded.
                pass
            cache.set(cache_key, result, timeout=86400)
            return Response(dict(result, job_id=job_id), status=status.HTTP_201_CREATED)
        except (DjangoValidationError, ValueError) as exc:
            messages = getattr(exc, 'messages', [str(exc)])
            result = {'status': 'failed', 'errors': messages}
            cache.set(cache_key, result, timeout=86400)
            return Response(
                dict(result, job_id=job_id),
                status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            result = {'status': 'failed', 'errors': [str(exc)]}
            cache.set(cache_key, result, timeout=86400)
            return Response(
                dict(result, job_id=job_id),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectLayerImportStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, job_id):
        try:
            _check_project_access(request, project_id)
        except HttpException as exc:
            return exc.get_exception()
        result = cache.get('project-layer-import:{}'.format(job_id))
        if result is None:
            return Response(
                {'detail': 'Import job not found'},
                status=status.HTTP_404_NOT_FOUND)
        return Response(dict(result, job_id=job_id))