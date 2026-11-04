# -*- coding: utf-8 -*-
"""Ejecuta el agente. La importación de LangChain y de build_llm es perezosa."""

import json
import logging
import re
import time

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .catalog import load_catalog
from .prompt import NO_CHANGE_TOKEN, no_change_nudge, system_prompt
from .tools import build_tools

LOGGER = logging.getLogger('gvsigol')

_HISTORY_LIMIT = 16
_MESSAGE_LIMIT = 8000
_CANVAS_BUDGET = 24000
_LONG_VALUE = 300

LIMIT_REPLY = ('No he podido terminar: la petición necesita demasiados pasos. '
               'Prueba a dividirla en partes más pequeñas.')
NO_CHANGE_WARNING = 'El asistente no ha propuesto ningún cambio: el canvas sigue igual.'

# Frases con las que el modelo afirma haber cambiado el canvas.
_CLAIM_RE = re.compile(
    r'\b(?:he|hemos|ya)\s+(?:añadido|creado|conectado|eliminado|borrado|cambiado|modificado|actualizado|'
    r'quitado|puesto|sustituido|insertado|aplicado|configurado|rellenado|incorporado)\b'
    r'|\b(?:añado|conecto|elimino|actualizo|sustituyo|inserto|incorporo)\b'
    r'|\bI(?:\'ve| have)\s+(?:added|created|connected|removed|deleted|updated|changed|inserted|replaced)\b',
    re.IGNORECASE)
_LIMIT_MARKERS = ('agent stopped due to', 'max iterations', 'iteration limit', 'time limit')

_STATUS_TEXT = {
    'applied': 'el usuario la aplicó',
    'discarded': 'el usuario la descartó; el canvas no cambió',
    'undone': 'el usuario la deshizo; el canvas volvió a como estaba',
    'pending': 'el usuario aún no la ha aplicado ni descartado',
}


class Trace(object):
    """Traza de un turno para el log (setting ETL_ASSISTANT_TRACE). Sin textos ni datos del usuario."""

    def __init__(self, enabled):
        self.enabled = bool(enabled)
        self.began = time.time()
        self.steps = []
        self.notes = {}

    def start(self, name):
        return {'tool': name, 't': time.time()}

    def finish(self, started, ok=True, error=None):
        if not started:
            return
        step = {'tool': started['tool'], 'ms': int((time.time() - started['t']) * 1000), 'ok': ok}
        if error:
            step['error'] = error
        self.steps.append(step)

    def note(self, key, value):
        self.notes[key] = value

    def emit(self, **extra):
        if not self.enabled:
            return
        record = {'ms': int((time.time() - self.began) * 1000), 'steps': self.steps}
        record.update(self.notes)
        record.update(extra)
        LOGGER.info('etl_assistant trace %s', json.dumps(record, ensure_ascii=False))


def output_text(output):
    """Texto de la salida del agente: cadena, o lista de bloques de contenido (API Responses)."""
    if output is None:
        return ''
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, dict):
        output = [output]
    if isinstance(output, (list, tuple)):
        parts = []
        for block in output:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get('type', 'text') == 'text':
                text = block.get('text')
                if isinstance(text, str):
                    parts.append(text)
        return ''.join(parts).strip()
    return str(output).strip()


def public_llm_error(exc):
    text = str(exc).lower()
    if 'timeout' in text or 'timed out' in text:
        return 'El asistente ha tardado demasiado. Inténtalo de nuevo.'
    if '401' in text or 'invalid_api_key' in text or 'incorrect api key' in text or 'authentication' in text:
        return 'La clave del proveedor de IA no es válida o ha caducado.'
    if '429' in text or 'quota' in text or 'rate limit' in text or 'insufficient_quota' in text:
        return 'Se ha superado la cuota del proveedor de IA.'
    if 'context length' in text or 'maximum context' in text or 'too many tokens' in text:
        return 'La conversación es demasiado larga. Bórrala (icono de la papelera) y vuelve a preguntar.'
    return 'No se ha podido consultar el asistente. Inténtalo de nuevo.'


def claims_change(text):
    return bool(text) and bool(_CLAIM_RE.search(text))


def hit_iteration_limit(text):
    low = (text or '').lower()
    return any(marker in low for marker in _LIMIT_MARKERS)


def run_assistant(request, message, history, canvas, restricted, connections):
    catalog = load_catalog()
    holder = []
    trace = Trace(_trace_enabled())
    canvas = canvas or {}
    tools = build_tools(request, catalog, canvas, connections, restricted, holder, trace)
    executor = _executor(_build_llm(), tools, _prompt(catalog))
    user_input = _user_input(message, canvas)
    chat_history = _history(history)
    warnings = []
    try:
        result = executor.invoke({'input': user_input, 'chat_history': chat_history})
    except Exception as exc:
        LOGGER.exception('etl_assistant: fallo al invocar el agente')
        trace.emit(error=type(exc).__name__, proposal=bool(holder))
        if holder:
            # La propuesta ya validada se conserva aunque falle la respuesta final.
            return _with_proposal(holder[-1], '', [public_llm_error(exc)])
        return _empty(public_llm_error(exc), error=True)

    reply = output_text(result.get('output'))
    limited = hit_iteration_limit(reply)
    if limited:
        reply = ''
    guard = None
    if not holder and not limited and claims_change(reply):
        guard = 'nudged'
        try:
            second = executor.invoke({
                'input': no_change_nudge(),
                'chat_history': chat_history + [HumanMessage(content=user_input), AIMessage(content=reply)],
            })
            second_reply = output_text(second.get('output'))
        except Exception:
            LOGGER.exception('etl_assistant: fallo en la segunda pasada')
            second_reply = ''
        if holder:
            guard = 'fixed'
            if second_reply and NO_CHANGE_TOKEN not in second_reply and not hit_iteration_limit(second_reply):
                reply = second_reply
        elif NO_CHANGE_TOKEN in second_reply:
            guard = 'no_change'
        else:
            guard = 'warned'
            warnings.append(NO_CHANGE_WARNING)
    trace.emit(proposal=bool(holder), limit=limited, guard=guard)

    if holder:
        return _with_proposal(holder[-1], reply, warnings)
    if limited:
        return _empty(LIMIT_REPLY, warnings=warnings)
    return _empty(reply or '¿Puedes concretar un poco más qué quieres hacer?', warnings=warnings)


def _with_proposal(result, reply, extra_warnings):
    payload = dict(result)
    payload['reply'] = reply or '\n'.join(payload.get('summary') or [])
    payload['warnings'] = list(payload.get('warnings') or []) + list(extra_warnings or [])
    payload['error'] = False
    return payload


def _empty(reply, warnings=None, error=False):
    return {
        'reply': reply,
        'warnings': warnings or [],
        'assumptions': [],
        'summary': [],
        'needs_confirmation': False,
        'proposal': None,
        'error': error,
    }


def _prompt(catalog):
    return ChatPromptTemplate.from_messages([
        ('system', system_prompt(catalog, _language())),
        MessagesPlaceholder(variable_name='chat_history', optional=True),
        ('human', '{input}'),
        MessagesPlaceholder(variable_name='agent_scratchpad'),
    ])


def _language():
    from django.utils import translation
    return translation.get_language()


def _trace_enabled():
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_TRACE', False))
    except Exception:
        return False


def _build_llm():
    from gvsigol_plugin_geocopilot.services.llm_factory import build_llm
    from gvsigol_plugin_geoetl import settings as geoetl_settings
    model = (geoetl_settings.GEOETL_LLM_MODEL or '').strip() or None
    return build_llm(llm_model=model)


def _executor(llm, tools, prompt):
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    try:
        from gvsigol_plugin_geocopilot.settings import LANGCHAIN_SETTINGS
        iterations = LANGCHAIN_SETTINGS.get('AGENT_MAX_ITERATIONS', 15)
    except Exception:
        iterations = 15
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=max(int(iterations or 20), 20),
        handle_parsing_errors=True,
        return_intermediate_steps=False,
    )


def _history(history):
    """Historial para el modelo. Cada respuesta lleva qué propuso y qué hizo el usuario con ello."""
    messages = []
    for item in (history or [])[-_HISTORY_LIMIT:]:
        if not isinstance(item, dict):
            continue
        content = item.get('content')
        content = content.strip() if isinstance(content, str) else ''
        if item.get('role') == 'assistant':
            note = _proposal_note(item)
            if note:
                content = (content + '\n\n' + note).strip()
            if content:
                messages.append(AIMessage(content=content[:_MESSAGE_LIMIT]))
        elif item.get('role') == 'user' and content:
            messages.append(HumanMessage(content=content[:_MESSAGE_LIMIT]))
    return messages


def _proposal_note(item):
    summary = [line for line in item.get('summary') or [] if isinstance(line, str)][:12]
    status = item.get('status') if item.get('status') in _STATUS_TEXT else None
    if not summary:
        return ''
    text = '[Cambios que propuse: %s' % ' '.join(summary)
    if status:
        text += ' Estado: %s.' % _STATUS_TEXT[status]
    return text + ']'


def _user_input(message, canvas):
    text = (message or '').strip()[:_MESSAGE_LIMIT]
    nodes = compact_canvas(canvas or {})
    selected = (canvas or {}).get('selected') or ''
    lines = [text, '']
    lines.append('Nodo seleccionado: %s.' % selected if selected else 'No hay ningún nodo seleccionado.')
    lines.append('Siguiente id libre para tareas nuevas: %s.' % next_free_alias(canvas or {}))
    if nodes.get('parameters_omitted'):
        lines.append('El canvas es grande: se envía sin parámetros; pídelos con get_canvas_nodes.')
    lines.append('Canvas actual:')
    lines.append(json.dumps({'nodes': nodes['nodes'], 'edges': nodes['edges']}, ensure_ascii=False))
    return '\n'.join(lines)


def next_free_alias(canvas):
    top = 0
    for node in canvas.get('nodes') or []:
        if isinstance(node, dict):
            match = re.match(r'^n([1-9]\d*)$', str(node.get('alias') or ''))
            if match:
                top = max(top, int(match.group(1)))
    hint = re.match(r'^n([1-9]\d*)$', str(canvas.get('next_alias') or ''))
    if hint:
        top = max(top, int(hint.group(1)) - 1)
    return 'n%d' % (top + 1)


def compact_canvas(canvas, budget=_CANVAS_BUDGET):
    """
    Canvas para el modelo en JSON siempre válido: primero completo; si no cabe, sin esquemas; luego
    con los textos largos recortados; y, en último caso, solo tipos, títulos y conexiones.
    """
    edges = canvas.get('edges') if isinstance(canvas.get('edges'), list) else []
    raw = [node for node in canvas.get('nodes') or [] if isinstance(node, dict)]

    def build(level):
        nodes = []
        for node in raw:
            entry = {'id': node.get('alias') or node.get('id'), 'type': node.get('type'),
                     'label': node.get('label')}
            if node.get('status'):
                entry['status'] = node.get('status')
            params = node.get('parameters') if isinstance(node.get('parameters'), dict) else {}
            params = {k: v for k, v in params.items() if v not in (None, '', [], {})}
            if level < 3:
                if level >= 2:
                    params = {k: _shorten(v) for k, v in params.items()}
                entry['parameters'] = params
            schema = node.get('schema') if isinstance(node.get('schema'), list) else []
            if level == 0:
                entry['schema'] = schema
            elif schema:
                entry['schema_columns'] = len(schema)
            nodes.append(entry)
        return nodes

    for level in range(4):
        nodes = build(level)
        size = len(json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False))
        if size <= budget or level == 3:
            return {'nodes': nodes, 'edges': edges, 'parameters_omitted': level == 3}
    return {'nodes': [], 'edges': edges, 'parameters_omitted': True}


def _shorten(value):
    if isinstance(value, str) and len(value) > _LONG_VALUE:
        return value[:_LONG_VALUE] + '…'
    if isinstance(value, list) and len(value) > 30:
        return value[:30] + ['…']
    return value
