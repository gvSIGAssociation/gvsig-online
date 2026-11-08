# -*- coding: utf-8 -*-
"""Suposiciones que el usuario puede cambiar con un clic (usabilidad, fase 3: ETL_ASSISTANT_ALTERNATIVES).

El modelo puede escribir una suposición sobre un parámetro como objeto:
    {"text": "n3: cruce por cod_mun", "node": "n3", "param": "field", "source": "columns",
     "connection": "gis", "schema": "public", "table": "padron"}

graph.validate_proposal sigue recibiendo solo textos (split_assumptions). Con
la propuesta ya validada se comprueba que el nodo y el parámetro existen, se
toma su valor y se leen las alternativas reales (questions._real_options).
El panel las enseña en un desplegable y aplica el cambio en el canvas sin
llamar al modelo.

Formato que llega al panel:
    {text, node, param, value, options: [{value, label}]}
"""

import logging

from .graph import is_protected
from .param_options import FILE_EXTENSIONS
from .questions import MAX_OPTIONS, SOURCE_ALIASES, _extensions, _inferred_from_parameter, _options, _plain, _real_options, _text

LOGGER = logging.getLogger('gvsigol')

SOURCES = ('choices', 'connections', 'publish_datastores', 'tables', 'columns', 'files', 'workspaces', 'layer_groups')
MAX_ALTERNATIVES = 8


def split_assumptions(payload):
    """(payload con las suposiciones como textos, suposiciones estructuradas)."""
    if not isinstance(payload, dict) or not isinstance(payload.get('assumptions'), list):
        return payload, []
    texts = []
    structured = []
    for item in payload['assumptions']:
        if isinstance(item, dict):
            text = _text(item.get('text'), 300)
            if text:
                texts.append(text)
                structured.append(dict(item, text=text))
        else:
            texts.append(item)
    cleaned = dict(payload)
    cleaned['assumptions'] = texts
    return cleaned, structured


def _proposal_node(alias, proposal):
    """(tipo, parámetros) de un nodo en la propuesta validada, o None."""
    for node in proposal.get('nodes') or []:
        if node.get('alias') == alias:
            return node.get('type'), node.get('parameters') or {}
    for op in proposal.get('ops') or []:
        if op.get('op') == 'add_node' and (op.get('node') or {}).get('alias') == alias:
            return op['node'].get('type'), op['node'].get('parameters') or {}
        if op.get('op') == 'update_node' and op.get('alias') == alias:
            return op.get('type'), op.get('parameters') or {}
    return None


def _canvas_node(alias, canvas):
    for node in (canvas or {}).get('nodes') or []:
        if isinstance(node, dict) and node.get('alias') == alias:
            params = node.get('parameters') if isinstance(node.get('parameters'), dict) else {}
            return node.get('type'), params
    return None


def resolve_alternatives(structured, result, canvas, catalog, context):
    """Alternativas de las suposiciones que siguen en la propuesta validada."""
    proposal = result.get('proposal') or {}
    kept_texts = set(result.get('assumptions') or [])
    choices = []
    for item in structured:
        if len(choices) >= MAX_ALTERNATIVES:
            break
        text = item.get('text')
        alias = _text(item.get('node'), 20)
        param = _text(item.get('param'), 100)
        source = _plain(_text(item.get('source'), 30))
        source = SOURCE_ALIASES.get(source, source)
        if text not in kept_texts or not alias or not param:
            continue
        found = _proposal_node(alias, proposal) or _canvas_node(alias, canvas)
        if not found:
            continue
        type_name, params = found
        if context.restricted and is_protected(type_name):
            continue                       # la edición restringida no cambia entradas, salidas ni SQL
        spec = catalog.get(type_name) or {}
        if param not in [p.get('name') for p in spec.get('parameters') or []]:
            continue
        value = params.get(param)
        if not isinstance(value, str) or not value:
            continue
        question = dict(item, node=alias, param=param, type=type_name)
        if source not in SOURCES:
            inferred = _inferred_from_parameter(question, catalog, canvas, proposal)
            source = inferred[0] if inferred else 'choices'
            if source == 'datastores':     # aquí se cambia un solo parámetro: la conexión
                source = 'connections'
        if source == 'files':
            # Se cambia en el administrador de archivos: no hay lista de alternativas
            choices.append({'text': text, 'node': alias, 'param': param, 'value': value, 'options': [],
                            'file_picker': {'extensions': _extensions(item.get('extensions'))
                                            or FILE_EXTENSIONS.get(param, '')}})
            continue
        try:
            options = _real_options(question, source, catalog, canvas, proposal, context)
        except Exception:
            LOGGER.exception('etl_assistant: no se pudieron leer las alternativas de %s.%s', alias, param)
            continue
        if value not in [o['value'] for o in options]:
            options = _options([value]) + options
        if len(options) < 2:
            continue
        choices.append({'text': text, 'node': alias, 'param': param, 'value': value,
                        'options': options[:MAX_OPTIONS]})
    return choices
