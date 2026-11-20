# -*- coding: utf-8 -*-
"""Pasos en vivo y cancelación de un turno del asistente (fase 4).

- StepCallbackHandler entrega un evento 'step' cada vez que el agente usa una
  herramienta. Lleva el nombre de la herramienta y solo datos cortos y sin
  riesgo (conexión, esquema, tabla, tipos de nodo, carpeta): nunca la
  propuesta, SQL ni rutas completas. El texto lo compone el navegador, que lo
  traduce como el resto del panel.
- CancelCallbackHandler corta el turno si está marcado como cancelado
  (Detener o desconexión del navegador), antes de cada llamada al modelo y a
  cada herramienta.
"""

import logging

from langchain_core.callbacks import BaseCallbackHandler

from . import cancellation

LOGGER = logging.getLogger('gvsigol')

# Argumentos que se pueden enseñar de cada herramienta
_SAFE_ARGS = {
    'list_tables': ('connection', 'schema'),
    'get_table_schema': ('connection', 'schema', 'table'),
    'get_node_specs': ('types',),
    'list_files': ('folder', 'extensions'),
    'get_canvas_nodes': ('ids',),
}
_MAX_VALUE = 80


class AssistantCancelled(Exception):
    """El usuario ha detenido el turno (o el navegador se ha ido)."""


def _tool_name(serialized, kwargs):
    name = kwargs.get('name')
    if not name and isinstance(serialized, dict):
        name = serialized.get('name')
    return str(name or '')


def step_detail(tool, inputs):
    """Argumentos que se pueden mostrar al usuario, recortados."""
    detail = {}
    if not isinstance(inputs, dict):
        return detail
    for key in _SAFE_ARGS.get(tool, ()):
        value = inputs.get(key)
        if isinstance(value, str) and value.strip():
            detail[key] = value.strip()[:_MAX_VALUE]
    return detail


class StepCallbackHandler(BaseCallbackHandler):
    """Entrega {'type': 'step', 'tool', 'detail'} al empezar cada herramienta."""

    def __init__(self, emit):
        self.emit = emit

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool = _tool_name(serialized, kwargs)
        try:
            self.emit({'type': 'step', 'tool': tool, 'detail': step_detail(tool, kwargs.get('inputs'))})
        except Exception:
            LOGGER.debug('etl_assistant: no se pudo entregar un paso', exc_info=True)


class CancelCallbackHandler(BaseCallbackHandler):
    """Corta el turno marcado como cancelado."""

    # Para que LangChain propague la excepción en vez de solo registrarla
    raise_error = True

    def __init__(self, query_id):
        self.query_id = query_id

    def _check(self):
        if cancellation.is_cancelled(self.query_id):
            LOGGER.info('etl_assistant: turno %s detenido', self.query_id)
            raise AssistantCancelled(self.query_id)

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self._check()

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._check()

    def on_tool_start(self, serialized, input_str, **kwargs):
        self._check()


def callbacks_for(on_event=None, query_id=None):
    callbacks = []
    if on_event is not None:
        callbacks.append(StepCallbackHandler(on_event))
    if query_id:
        callbacks.append(CancelCallbackHandler(query_id))
    return callbacks
