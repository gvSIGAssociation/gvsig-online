# -*- coding: utf-8 -*-
"""Dónde se ejecuta un turno del asistente (interruptor ETL_ASSISTANT_EXECUTION).

- inline: en el proceso web, como siempre.
- celery: en un worker de la cola ETL_ASSISTANT_CELERY_QUEUE ('geocopilot',
  la de GeoCopilot), con la tarea geoetl.run_assistant (tasks.py).

En celery:

1. El web calcula los permisos del usuario (AssistantContext.to_payload): el
   worker no tiene request ni la sesión de Keycloak.
2. El web crea su cola de eventos en RabbitMQ (event_bus de GeoCopilot) ANTES
   de encolar la tarea, para no perder ninguno.
3. El worker publica 'started' al empezar y 'result' al terminar, con el
   mismo JSON que devuelve run_assistant.
4. Si en PICKUP_TIMEOUT_SECONDS ningún worker ha empezado, el web responde
   que el asistente no está disponible y marca el turno como cancelado (un
   worker que lo recoja tarde no lo ejecuta). Si pasa el límite de la tarea
   sin resultado, responde con un error.

Hace falta la caché compartida de GeoCopilot (GEOCOPILOT_SHARED_CACHE=True)
para la marca de cancelación. Sin ella se ejecuta inline y se avisa en el
log: mejor el comportamiento de siempre que un asistente que no responde.
"""

import logging
import time
import uuid

LOGGER = logging.getLogger('gvsigol')

EXECUTION_INLINE = 'inline'
EXECUTION_CELERY = 'celery'

DEFAULT_QUEUE = 'geocopilot'
EVENTS_PREFIX = 'etl-'

# Si en este tiempo ningún worker ha empezado el turno, no hay worker
# escuchando la cola (o están todos ocupados)
PICKUP_TIMEOUT_SECONDS = 20

# Cada cuánto se comprueba (y, en la fase 4, se manda un ping al navegador)
HEARTBEAT_SECONDS = 10

# Límite de la tarea cuando el turno no tiene plazo propio (motor legacy o
# ETL_ASSISTANT_MAX_SECONDS=0)
FALLBACK_TASK_SECONDS = 600

UNAVAILABLE_TEXT = ('El asistente no está disponible en este momento. '
                    'Inténtalo de nuevo en unos minutos.')
TIMEOUT_TEXT = 'El asistente ha tardado demasiado. Inténtalo de nuevo.'
INTERNAL_ERROR_TEXT = 'No se ha podido consultar el asistente. Inténtalo de nuevo.'


def _setting(name, default):
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return getattr(geoetl_settings, name, default)
    except Exception:
        return default


def celery_queue():
    return str(_setting('ETL_ASSISTANT_CELERY_QUEUE', DEFAULT_QUEUE) or DEFAULT_QUEUE).strip()


def task_time_limits():
    """Límites de la tarea: algo por encima del plazo del turno."""
    from .engine import max_seconds
    seconds = max_seconds() or FALLBACK_TASK_SECONDS
    return {'soft_time_limit': seconds + 30, 'time_limit': seconds + 60}


def _shared_cache_ready():
    from django.conf import settings
    try:
        from gvsigol_plugin_geocopilot.utils.shared_cache import GEOCOPILOT_CACHE_ALIAS
    except Exception:
        return False
    return GEOCOPILOT_CACHE_ALIAS in getattr(settings, 'CACHES', {})


def execution_mode():
    """'celery' si se pide y hay caché compartida; si no, 'inline'."""
    requested = str(_setting('ETL_ASSISTANT_EXECUTION', EXECUTION_INLINE) or EXECUTION_INLINE)
    if requested.strip().lower() != EXECUTION_CELERY:
        return EXECUTION_INLINE
    if not _shared_cache_ready():
        LOGGER.warning('etl_assistant: ETL_ASSISTANT_EXECUTION=celery necesita GEOCOPILOT_SHARED_CACHE=True: '
                       'se ejecuta en el proceso web')
        return EXECUTION_INLINE
    return EXECUTION_CELERY


def error_result(text):
    from .agent import _empty
    return _empty(text, error=True)


# ============================================================================
# LADO DEL WORKER
# ============================================================================

def execute(data, emit):
    """Ejecuta un turno en el worker y entrega sus eventos a emit, hasta el 'result'.

    Los permisos ya los ha calculado el web (data['context']). Cualquier error
    termina en un 'result' de error, nunca en silencio.
    """
    from . import cancellation

    query_id = data.get('query_id')
    if cancellation.is_cancelled(query_id):
        # El web ya ha dejado de esperar: no se gasta el turno
        LOGGER.info('etl_assistant: turno %s cancelado antes de empezar', query_id)
        return
    emit({'type': 'started'})
    try:
        from django.utils import translation

        from .agent import run_assistant
        from .context import AssistantContext

        context = AssistantContext.from_payload(data.get('context'))
        with translation.override(context.language or None):
            result = run_assistant(context, data.get('message') or '', data.get('history') or [],
                                   data.get('canvas') or {}, None, None,
                                   on_event=emit if data.get('steps') else None, query_id=query_id)
    except Exception:
        LOGGER.exception('etl_assistant: error al ejecutar el turno %s en el worker', query_id)
        result = error_result(INTERNAL_ERROR_TEXT)
    emit({'type': 'result', 'payload': result})


# ============================================================================
# LADO WEB: ENCOLAR Y ESPERAR
# ============================================================================

def task_payload(context, message, history, canvas, query_id, steps=False):
    return {
        'query_id': query_id,
        'steps': bool(steps),
        'context': context.to_payload(),
        'message': message,
        'history': history,
        'canvas': canvas,
    }


def relay_events(context, message, history, canvas, query_id=None, steps=False):
    """Encola el turno en Celery y devuelve sus eventos hasta el 'result'.

    Mientras no llegan eventos devuelve un 'ping' cada HEARTBEAT_SECONDS.
    Termina siempre con un 'result'.
    """
    from gvsigol_plugin_geocopilot.services import event_bus

    from . import cancellation
    from ..tasks import run_assistant_task

    query_id = query_id or uuid.uuid4().hex
    events_id = EVENTS_PREFIX + query_id
    data = task_payload(context, message, history, canvas, query_id, steps)
    started = time.monotonic()
    deadline = task_time_limits()['time_limit'] + 15
    picked_up = False
    with event_bus.subscribe(events_id) as subscription:
        run_assistant_task.apply_async(args=(data, event_bus.events_queue_name(events_id)),
                                       queue=celery_queue())
        while True:
            event = subscription.get(timeout=HEARTBEAT_SECONDS)
            elapsed = time.monotonic() - started
            if event is None:
                if not picked_up and elapsed >= PICKUP_TIMEOUT_SECONDS:
                    LOGGER.error("etl_assistant: ningún worker ha recogido el turno %s en %ss (cola '%s')",
                                 query_id, PICKUP_TIMEOUT_SECONDS, celery_queue())
                    cancellation.cancel(query_id)
                    yield {'type': 'result', 'payload': error_result(UNAVAILABLE_TEXT)}
                    return
                if elapsed >= deadline:
                    LOGGER.error('etl_assistant: el turno %s no ha terminado en %ss', query_id, deadline)
                    cancellation.cancel(query_id)
                    yield {'type': 'result', 'payload': error_result(TIMEOUT_TEXT)}
                    return
                yield {'type': 'ping'}
                continue
            picked_up = True
            yield event
            if event.get('type') == 'result':
                return


def wait_result(context, message, history, canvas):
    """Como relay_events, pero solo devuelve el resultado final."""
    for event in relay_events(context, message, history, canvas):
        if event.get('type') == 'result':
            return event.get('payload') or error_result(INTERNAL_ERROR_TEXT)
    return error_result(UNAVAILABLE_TEXT)


# ============================================================================
# STREAMING (fase 4): eventos para /etl_assistant/stream/
# ============================================================================

def streaming_enabled():
    return bool(_setting('ETL_ASSISTANT_STREAMING', False))


def _inline_events(context, message, history, canvas, query_id):
    """Ejecuta el turno en un hilo de este proceso y devuelve sus eventos.

    El agente es síncrono y el proyecto corre sobre WSGI: sin el hilo no se
    podría enviar nada hasta el final. Mientras no hay eventos, 'ping' cada
    HEARTBEAT_SECONDS.
    """
    import queue
    import threading

    events = queue.Queue()
    end = object()

    def run():
        try:
            from django.utils import translation

            from .agent import run_assistant
            with translation.override(context.language or None):
                result = run_assistant(context, message, history, canvas, None, None,
                                       on_event=events.put, query_id=query_id)
        except Exception:
            LOGGER.exception('etl_assistant: error al ejecutar el turno %s', query_id)
            result = error_result(INTERNAL_ERROR_TEXT)
        finally:
            # El hilo tiene su propia conexión de Django si ha tocado el ORM
            try:
                from django.db import connections
                connections.close_all()
            except Exception:
                pass
        events.put({'type': 'result', 'payload': result})
        events.put(end)

    thread = threading.Thread(target=run, name='etl-assistant-%s' % query_id, daemon=True)
    thread.start()
    while True:
        try:
            event = events.get(timeout=HEARTBEAT_SECONDS)
        except queue.Empty:
            yield {'type': 'ping'}
            continue
        if event is end:
            return
        yield event


def stream_events(context, message, history, canvas, query_id):
    """Eventos de un turno para el navegador: start, step, ping y result (siempre al final)."""
    yield {'type': 'start', 'query_id': query_id}
    if execution_mode() == EXECUTION_CELERY:
        events = relay_events(context, message, history, canvas, query_id=query_id, steps=True)
    else:
        events = _inline_events(context, message, history, canvas, query_id)
    try:
        for event in events:
            if event.get('type') == 'started':
                continue                              # solo le sirve al web
            yield event
            if event.get('type') == 'result':
                return
    finally:
        events.close()
