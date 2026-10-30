# -*- coding: utf-8 -*-
"""POST /etl/etl_assistant/."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST

from gvsigol_plugin_geoetl.assistant.access import (
    assistant_feature_enabled,
    user_may_use,
    workspace_edit_mode,
)
from gvsigol_plugin_geoetl.models import ETLworkspaces

LOGGER = logging.getLogger('gvsigol')


def _body(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return None
    return None


@login_required
@require_POST
def etl_assistant(request):
    if not assistant_feature_enabled():
        raise Http404
    user = request.user
    if not user_may_use(user.is_authenticated, user.is_staff, user.is_superuser):
        return JsonResponse({'error': 'No autorizado.'}, status=403)

    payload = _body(request)
    if payload is None:
        return JsonResponse({'error': 'El cuerpo tiene que ser JSON.'}, status=400)

    message = payload.get('message')
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({'error': 'Falta el mensaje.'}, status=400)

    restricted = False
    workspace_id = payload.get('workspace_id')
    if workspace_id not in (None, '', 0, '0'):
        try:
            workspace = ETLworkspaces.objects.get(id=int(workspace_id))
        except (ETLworkspaces.DoesNotExist, TypeError, ValueError):
            return JsonResponse({'error': 'El workspace no existe.'}, status=404)
        mode = workspace_edit_mode(
            workspace.can_edit(request),
            workspace.can_edit_restrictedly(request),
        )
        if mode == 'forbidden':
            return JsonResponse({'error': 'No puedes editar este workspace.'}, status=403)
        restricted = mode == 'restricted'

    from gvsigol_plugin_geoetl.assistant.agent import run_assistant
    from gvsigol_plugin_geoetl.views import get_etl_connections_list

    try:
        result = run_assistant(
            request,
            message,
            payload.get('history') if isinstance(payload.get('history'), list) else [],
            payload.get('canvas') if isinstance(payload.get('canvas'), dict) else {},
            restricted,
            get_etl_connections_list(request),
        )
    except Exception:
        LOGGER.exception('etl_assistant: error al atender la petición')
        return JsonResponse({
            'reply': 'No se ha podido consultar el asistente. Inténtalo de nuevo.',
            'warnings': [],
            'assumptions': [],
            'summary': [],
            'needs_confirmation': False,
            'proposal': None,
            'error': True,
        }, status=200)

    return JsonResponse({
        'reply': result.get('reply') or '',
        'warnings': result.get('warnings') or [],
        'assumptions': result.get('assumptions') or [],
        'summary': result.get('summary') or [],
        'needs_confirmation': bool(result.get('needs_confirmation')),
        'proposal': result.get('proposal'),
        'error': bool(result.get('error')),
    })
