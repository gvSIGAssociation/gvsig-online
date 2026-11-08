# -*- coding: utf-8 -*-
"""POST /etl/etl_assistant/; con ETL_ASSISTANT_STREAMING /stream/ y /cancel/; con ETL_ASSISTANT_PARAM_PICKER /options/."""

import json
import logging
import re
import uuid

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST

from gvsigol_plugin_geoetl.assistant.access import (
    assistant_feature_enabled,
    user_may_use,
    workspace_edit_mode,
)
from gvsigol_plugin_geoetl.models import ETLworkspaces

LOGGER = logging.getLogger('gvsigol')

_QUERY_ID = re.compile(r'^[A-Za-z0-9_-]{8,64}$')

_ERROR_RESPONSE = {
    'reply': 'No se ha podido consultar el asistente. Inténtalo de nuevo.',
    'warnings': [],
    'assumptions': [],
    'summary': [],
    'needs_confirmation': False,
    'proposal': None,
    'error': True,
}


def _body(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return None
    return None


def _workspace_access(request, workspace_id):
    """(respuesta de error, None) o (None, True si la edición es restringida)."""
    if workspace_id in (None, '', 0, '0'):
        return None, False
    try:
        workspace = ETLworkspaces.objects.get(id=int(workspace_id))
    except (ETLworkspaces.DoesNotExist, TypeError, ValueError):
        return JsonResponse({'error': 'El workspace no existe.'}, status=404), None
    mode = workspace_edit_mode(
        workspace.can_edit(request),
        workspace.can_edit_restrictedly(request),
    )
    if mode == 'forbidden':
        return JsonResponse({'error': 'No puedes editar este workspace.'}, status=403), None
    return None, mode == 'restricted'


def _prepare(request):
    """Comprobaciones comunes. Devuelve (respuesta de error, None) o (None, datos del turno)."""
    if not assistant_feature_enabled():
        raise Http404
    user = request.user
    if not user_may_use(user.is_authenticated, user.is_staff, user.is_superuser):
        return JsonResponse({'error': 'No autorizado.'}, status=403), None

    payload = _body(request)
    if payload is None:
        return JsonResponse({'error': 'El cuerpo tiene que ser JSON.'}, status=400), None

    message = payload.get('message')
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({'error': 'Falta el mensaje.'}, status=400), None

    error, restricted = _workspace_access(request, payload.get('workspace_id'))
    if error is not None:
        return error, None

    return None, {
        'message': message,
        'history': payload.get('history') if isinstance(payload.get('history'), list) else [],
        'canvas': payload.get('canvas') if isinstance(payload.get('canvas'), dict) else {},
        'restricted': restricted,
        'query_id': payload.get('query_id'),
    }


def _public(result):
    public = {
        'reply': result.get('reply') or '',
        'warnings': result.get('warnings') or [],
        'assumptions': result.get('assumptions') or [],
        'summary': result.get('summary') or [],
        'needs_confirmation': bool(result.get('needs_confirmation')),
        'proposal': result.get('proposal'),
        'error': bool(result.get('error')),
    }
    # Solo con ETL_ASSISTANT_ACTIONS: problemas estructurados para los botones del panel
    if isinstance(result.get('issues'), list):
        public['issues'] = result['issues']
    # Solo con ETL_ASSISTANT_QUESTIONS: preguntas con opciones para elegir con un clic
    if isinstance(result.get('questions'), list):
        public['questions'] = result['questions']
    # Solo con ETL_ASSISTANT_ALTERNATIVES: suposiciones que se pueden cambiar con un clic
    if isinstance(result.get('assumption_choices'), list):
        public['assumption_choices'] = result['assumption_choices']
    # Solo con ETL_ASSISTANT_NEXT_STEPS: sugerencias de siguiente paso
    if isinstance(result.get('next_steps'), list):
        public['next_steps'] = result['next_steps']
    return public


@login_required
@require_POST
def etl_assistant(request):
    error, turn = _prepare(request)
    if error is not None:
        return error

    from gvsigol_plugin_geoetl.assistant.agent import run_assistant
    from gvsigol_plugin_geoetl.assistant.execution import EXECUTION_CELERY, execution_mode, wait_result
    from gvsigol_plugin_geoetl.views import get_etl_connections_list

    try:
        if execution_mode() == EXECUTION_CELERY:
            from gvsigol_plugin_geoetl.assistant.context import AssistantContext
            context = AssistantContext.from_request(request, get_etl_connections_list(request),
                                                    turn['restricted'])
            result = wait_result(context, turn['message'], turn['history'], turn['canvas'])
        else:
            result = run_assistant(
                request,
                turn['message'],
                turn['history'],
                turn['canvas'],
                turn['restricted'],
                get_etl_connections_list(request),
            )
    except Exception:
        LOGGER.exception('etl_assistant: error al atender la petición')
        return JsonResponse(dict(_ERROR_RESPONSE), status=200)

    return JsonResponse(_public(result))


# ============================================================================
# STREAMING (ETL_ASSISTANT_STREAMING)
# ============================================================================

def _sse_frame(event):
    return 'data: %s\n\n' % json.dumps(event, ensure_ascii=False, default=str)


def _sse(events, query_id):
    """Eventos en formato SSE. Si el navegador se va, el turno se cancela.

    La desconexión se detecta al escribir: como muy tarde con el siguiente ping.
    """
    from gvsigol_plugin_geoetl.assistant import cancellation

    finished = False
    try:
        for event in events:
            if event.get('type') == 'result':
                event = {'type': 'result', 'payload': _public(event.get('payload') or {})}
                finished = True
            yield _sse_frame(event)
    except GeneratorExit:
        if not finished:
            LOGGER.info('etl_assistant: el navegador se ha ido: se detiene el turno %s', query_id)
            cancellation.cancel(query_id)
        events.close()
        raise
    except Exception:
        LOGGER.exception('etl_assistant: error en el stream del turno %s', query_id)
        cancellation.cancel(query_id)
        yield _sse_frame({'type': 'result', 'payload': dict(_ERROR_RESPONSE)})


@login_required
@require_POST
def etl_assistant_stream(request):
    from gvsigol_plugin_geoetl.assistant import cancellation
    from gvsigol_plugin_geoetl.assistant.context import AssistantContext
    from gvsigol_plugin_geoetl.assistant.execution import stream_events, streaming_enabled
    from gvsigol_plugin_geoetl.views import get_etl_connections_list

    if not streaming_enabled():
        raise Http404
    error, turn = _prepare(request)
    if error is not None:
        return error

    query_id = turn['query_id'] if isinstance(turn['query_id'], str) and _QUERY_ID.match(turn['query_id']) \
        else uuid.uuid4().hex
    try:
        cancellation.set_owner(query_id, request.user.id)
        context = AssistantContext.from_request(request, get_etl_connections_list(request), turn['restricted'])
    except Exception:
        LOGGER.exception('etl_assistant: error al preparar el stream')
        return JsonResponse(dict(_ERROR_RESPONSE), status=200)

    events = stream_events(context, turn['message'], turn['history'], turn['canvas'], query_id)
    response = StreamingHttpResponse(_sse(events, query_id), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    # Sin esto un proxy acumula el flujo y se pierde el efecto
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_POST
def etl_assistant_cancel(request):
    """Detener: marca el turno como cancelado. Solo puede hacerlo quien lo lanzó."""
    from gvsigol_plugin_geoetl.assistant import cancellation
    from gvsigol_plugin_geoetl.assistant.execution import streaming_enabled

    if not streaming_enabled() or not assistant_feature_enabled():
        raise Http404
    payload = _body(request) or {}
    query_id = payload.get('query_id')
    if not isinstance(query_id, str) or not _QUERY_ID.match(query_id):
        return JsonResponse({'error': 'Falta el turno.'}, status=400)
    if cancellation.owner(query_id) != request.user.id:
        return JsonResponse({'error': 'El turno no existe.'}, status=404)
    cancellation.cancel(query_id)
    return JsonResponse({'cancelled': True})


@login_required
@require_POST
def etl_assistant_options(request):
    """Valores que se pueden elegir para un parámetro de un nodo. No llama al modelo."""
    from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
    from gvsigol_plugin_geoetl.assistant.context import AssistantContext
    from gvsigol_plugin_geoetl.assistant.param_options import (
        SOURCE_FILES, can_pick, options_for, picker_enabled, picker_source,
    )
    from gvsigol_plugin_geoetl.views import get_etl_connections_list

    from gvsigol_plugin_geoetl.assistant.next_steps import next_steps_enabled

    # El arranque guiado (ETL_ASSISTANT_NEXT_STEPS) usa también estas opciones
    from gvsigol_plugin_geoetl.assistant.agent import questions_enabled

    if not (picker_enabled() or next_steps_enabled() or questions_enabled()) or not assistant_feature_enabled():
        raise Http404
    user = request.user
    if not user_may_use(user.is_authenticated, user.is_staff, user.is_superuser):
        return JsonResponse({'error': 'No autorizado.'}, status=403)
    payload = _body(request)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'El cuerpo tiene que ser JSON.'}, status=400)
    error, restricted = _workspace_access(request, payload.get('workspace_id'))
    if error is not None:
        return error

    catalog = load_catalog()
    type_name = payload.get('type')
    param = payload.get('param')
    if not isinstance(type_name, str) or not isinstance(param, str) or not can_pick(catalog, type_name, param, False):
        return JsonResponse({'error': 'Ese parámetro no se puede elegir de una lista.'}, status=400)
    if not can_pick(catalog, type_name, param, restricted):
        return JsonResponse({'error': 'En edición restringida no se puede cambiar este nodo.'}, status=403)
    if picker_source(catalog.get(type_name), type_name, param) == SOURCE_FILES:
        return JsonResponse({'error': 'Los ficheros se eligen en el administrador de archivos.'}, status=400)

    try:
        context = AssistantContext.from_request(request, get_etl_connections_list(request), restricted)
        options, needs = options_for(catalog, type_name, param, payload.get('parameters'), context)
    except Exception:
        LOGGER.exception('etl_assistant: no se pudieron leer las opciones de %s.%s', type_name, param)
        return JsonResponse({'options': [], 'needs': None, 'error': True})
    return JsonResponse({
        'options': options,
        'needs': needs,
        'error': False,
        'create_datastore': picker_source(catalog.get(type_name), type_name, param) == 'datastores',
    })


@login_required
@require_POST
def etl_assistant_columns(request):
    """Lee las columnas de un nodo de entrada cuyo origen acaba de cambiar. No llama al modelo."""
    from gvsigol_plugin_geoetl.assistant.columns import READABLE_TYPES, columns_enabled, read_columns
    from gvsigol_plugin_geoetl.assistant.context import AssistantContext
    from gvsigol_plugin_geoetl.assistant.graph import is_protected
    from gvsigol_plugin_geoetl.views import get_etl_connections_list

    if not columns_enabled() or not assistant_feature_enabled():
        raise Http404
    user = request.user
    if not user_may_use(user.is_authenticated, user.is_staff, user.is_superuser):
        return JsonResponse({'error': 'No autorizado.'}, status=403)
    payload = _body(request)
    if not isinstance(payload, dict) or payload.get('type') not in READABLE_TYPES:
        return JsonResponse({'error': 'Ese nodo no tiene columnas que leer.'}, status=400)
    error, restricted = _workspace_access(request, payload.get('workspace_id'))
    if error is not None:
        return error
    if restricted and is_protected(payload['type']):
        return JsonResponse({'error': 'En edición restringida no se puede cambiar este nodo.'}, status=403)
    context = AssistantContext.from_request(request, get_etl_connections_list(request), restricted)
    read = read_columns(payload['type'], payload.get('parameters'), context) or {}
    return JsonResponse({'schema': read.get('schema'), 'params': read.get('params') or {},
                         'sheets': read.get('sheets'), 'error': read.get('error')})
