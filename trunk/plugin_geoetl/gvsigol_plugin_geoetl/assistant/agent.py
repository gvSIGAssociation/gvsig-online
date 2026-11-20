# -*- coding: utf-8 -*-
"""Ejecuta el agente. La importación de LangChain y de build_llm es perezosa."""

import json
import logging
import re
import time

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .catalog import load_catalog
from .context import as_context
from .prompt import NO_CHANGE_TOKEN, no_change_nudge, system_prompt
from .streaming import AssistantCancelled, callbacks_for
from .tools import build_tools, redact_parameters

LOGGER = logging.getLogger('gvsigol')

_HISTORY_LIMIT = 16
_MESSAGE_LIMIT = 8000
_CANVAS_BUDGET = 24000
_LONG_VALUE = 300

LIMIT_REPLY = ('No he podido terminar: la petición necesita demasiados pasos. '
               'Prueba a dividirla en partes más pequeñas.')
NO_CHANGE_WARNING = 'El asistente no ha propuesto ningún cambio: el canvas sigue igual.'
CANCELLED_REPLY = 'Detenido. El canvas no ha cambiado.'

# Frases con las que el modelo afirma haber cambiado el canvas.
_CLAIM_RE = re.compile(
    r'\b(?:he|hemos|ya)\s+(?:añadido|creado|conectado|eliminado|borrado|cambiado|modificado|actualizado|'
    r'quitado|puesto|sustituido|insertado|aplicado|configurado|rellenado|incorporado)\b'
    r'|\b(?:añado|conecto|elimino|actualizo|sustituyo|inserto|incorporo)\b'
    r'|\bI(?:\'ve| have)\s+(?:added|created|connected|removed|deleted|updated|changed|inserted|replaced)\b'
    r'|\b(?:he|hem)\s+(?:afegit|creat|connectat|eliminat|esborrat|canviat|modificat|actualitzat)\b',
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


def run_assistant(request, message, history, canvas, restricted, connections, on_event=None, query_id=None):
    """request es el request de Django o un AssistantContext (context.py).

    on_event recibe los pasos ('step') mientras el agente trabaja; con
    query_id el turno se corta si se marca como cancelado (streaming.py).
    """
    context = as_context(request, connections, restricted)
    callbacks = callbacks_for(on_event, query_id)
    catalog = load_catalog()
    holder = []
    trace = Trace(_trace_enabled())
    canvas = canvas or {}
    reviews = []
    asking = questions_enabled()
    asked = [] if asking else None
    alternatives = alternatives_enabled()
    from .columns import columns_enabled
    columns = columns_enabled()
    tools = build_tools(context, catalog, canvas, None, None, holder, trace, reviews=reviews, asked=asked,
                        alternatives=alternatives, columns=columns)

    def finish(payload):
        if asked:
            payload['questions'] = asked[-1]
            trace.note('questions', len(asked[-1]))
        from .next_steps import attach_next_steps
        attach_next_steps(payload, holder, canvas, catalog, context)
        return _attach_issues(payload, holder, reviews, canvas, catalog, context)

    executor = _executor(_build_llm(), tools, _prompt(catalog, context.language, asking, alternatives, columns))
    trace.note('engine', getattr(executor, 'engine', 'legacy'))
    live_text = _live_text(executor, on_event)
    user_input = _user_input(message, canvas)
    chat_history = _history(history)
    warnings = []
    try:
        result = _invoke(executor, {'input': user_input, 'chat_history': chat_history}, callbacks)
    except AssistantCancelled:
        trace.emit(cancelled=True, proposal=bool(holder))
        return _empty(CANCELLED_REPLY, error=True)
    except Exception as exc:
        LOGGER.exception('etl_assistant: fallo al invocar el agente')
        trace.emit(error=type(exc).__name__, proposal=bool(holder))
        if holder:
            # La propuesta ya validada se conserva aunque falle la respuesta final.
            return finish(_with_proposal(holder[-1], '', [public_llm_error(exc)]))
        return _empty(public_llm_error(exc), error=True)

    reply = output_text(result.get('output'))
    limited = hit_iteration_limit(reply)
    if limited:
        reply = ''
    guard = None
    if not holder and not limited and claims_change(reply):
        guard = 'nudged'
        if live_text:
            # La segunda pasada no se enseña en vivo: su texto puede ser SIN_CAMBIOS.
            # El resultado final decide qué texto ve el usuario.
            executor.on_answer_delta = None
        try:
            second = _invoke(executor, {
                'input': no_change_nudge(),
                'chat_history': chat_history + [HumanMessage(content=user_input), AIMessage(content=reply)],
            }, callbacks)
            second_reply = output_text(second.get('output'))
        except AssistantCancelled:
            trace.emit(cancelled=True, proposal=bool(holder))
            return _empty(CANCELLED_REPLY, error=True)
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
        return finish(_with_proposal(holder[-1], reply, warnings))
    if limited:
        return finish(_empty(LIMIT_REPLY, warnings=warnings))
    return finish(_empty(reply or '¿Puedes concretar un poco más qué quieres hacer?', warnings=warnings))


# ============================================================================
# PROBLEMAS CON BOTONES (usabilidad, fase 1: ETL_ASSISTANT_ACTIONS)
# ============================================================================

_MAX_ISSUES = 30


def questions_enabled():
    """Preguntas con opciones (usabilidad, fase 2): ETL_ASSISTANT_QUESTIONS."""
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_QUESTIONS', False))
    except Exception:
        return False


def alternatives_enabled():
    """Suposiciones cambiables con un clic (usabilidad, fase 3): ETL_ASSISTANT_ALTERNATIVES."""
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_ALTERNATIVES', False))
    except Exception:
        return False


def actions_enabled():
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_ACTIONS', False))
    except Exception:
        return False


def _attach_issues(payload, holder, reviews, canvas, catalog, context):
    """Añade 'issues' (problemas estructurados) para que el panel ponga botones.

    Con propuesta, los del flujo tal como quedará al aplicarla; sin ella, los de
    la última revisión del canvas que hizo el agente en este turno. Sin el
    interruptor la respuesta no cambia.
    """
    if not actions_enabled():
        return payload
    try:
        from .review import check_graph, graph_after
        if holder:
            nodes, edges = graph_after(holder[-1]['proposal'], canvas)
            issues = check_graph(nodes, edges, catalog, context.connections)
        elif reviews:
            issues = reviews[-1]
        else:
            return payload
        ordered = sorted(issues, key=lambda item: 0 if item.get('level') == 'error' else 1)
        payload['issues'] = [_with_picker(dict(item), holder, canvas, catalog, context)
                             for item in ordered[:_MAX_ISSUES]]
    except Exception:
        LOGGER.exception('etl_assistant: no se pudieron preparar los problemas del flujo')
    return payload


def _with_picker(issue, holder, canvas, catalog, context):
    """Marca los problemas que se resuelven eligiendo un valor (ETL_ASSISTANT_PARAM_PICKER)."""
    from .alternatives import _canvas_node, _proposal_node
    from .param_options import FILE_EXTENSIONS, SOURCE_FILES, can_pick, picker_enabled, picker_source

    if not issue.get('param') or not issue.get('node') or not picker_enabled():
        return issue
    proposal = holder[-1]['proposal'] if holder else {}
    found = _proposal_node(issue['node'], proposal) or _canvas_node(issue['node'], canvas)
    if found and can_pick(catalog, found[0], issue['param'], context.restricted):
        issue['pick'] = {'type': found[0]}
        if picker_source(catalog.get(found[0]), found[0], issue['param']) == SOURCE_FILES:
            issue['pick']['file_picker'] = {'extensions': FILE_EXTENSIONS[issue['param']]}
    return issue


def _live_text(executor, on_event):
    """Activa el texto en vivo si hay a quién entregarlo, el motor es LangGraph y el interruptor está puesto."""
    from .engine import ENGINE_LANGGRAPH, token_streaming_enabled
    if on_event is None or getattr(executor, 'engine', None) != ENGINE_LANGGRAPH or not token_streaming_enabled():
        return False
    executor.on_answer_delta = on_event
    return True


def _invoke(executor, payload, callbacks):
    """Sin callbacks, la llamada de siempre; con ellos, en la config (AgentExecutor y LangGraphExecutor)."""
    if not callbacks:
        return executor.invoke(payload)
    return executor.invoke(payload, {'callbacks': callbacks})


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


def _prompt(catalog, language=None, questions=False, alternatives=False, columns=False):
    return ChatPromptTemplate.from_messages([
        ('system', system_prompt(catalog, language or _language(), questions=questions,
                                 alternatives=alternatives, columns=columns)),
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


def _max_iterations():
    try:
        from gvsigol_plugin_geocopilot.settings import LANGCHAIN_SETTINGS
        iterations = LANGCHAIN_SETTINGS.get('AGENT_MAX_ITERATIONS', 15)
    except Exception:
        iterations = 15
    return max(int(iterations or 20), 20)


def _executor(llm, tools, prompt):
    """AgentExecutor (legacy) o LangGraph según ETL_ASSISTANT_ENGINE (engine.py)."""
    from .engine import ENGINE_LANGGRAPH, LangGraphExecutor, max_seconds, selected_engine, system_prompt_text
    if selected_engine() == ENGINE_LANGGRAPH:
        return LangGraphExecutor(llm, tools, system_prompt_text(prompt), _max_iterations(), max_seconds())

    from langchain.agents import AgentExecutor, create_tool_calling_agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=_max_iterations(),
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
            for note in (_proposal_note(item), _questions_note(item), _changes_note(item)):
                if note:
                    content = (content + '\n\n' + note).strip()
            if content:
                messages.append(AIMessage(content=content[:_MESSAGE_LIMIT]))
        elif item.get('role') == 'user' and content:
            messages.append(HumanMessage(content=content[:_MESSAGE_LIMIT]))
    return messages


def _changes_note(item):
    """Suposiciones que el usuario cambió con un clic (ETL_ASSISTANT_ALTERNATIVES), para no deshacerlas."""
    parts = []
    for change in (item.get('changes') or [])[:12]:
        if not isinstance(change, dict):
            continue
        node = change.get('node') if isinstance(change.get('node'), str) else ''
        param = change.get('param') if isinstance(change.get('param'), str) else ''
        value = change.get('value') if isinstance(change.get('value'), str) else ''
        if node and param:
            parts.append('%s %s = %s' % (node[:20], param[:100], value[:300]))
    if not parts:
        return ''
    return '[El usuario cambió: %s]' % '; '.join(parts)


def _questions_note(item):
    """Preguntas con opciones de esa respuesta (ETL_ASSISTANT_QUESTIONS), para entender la contestación."""
    parts = []
    for question in (item.get('questions') or [])[:4]:
        if not isinstance(question, dict):
            continue
        label = question.get('label') if isinstance(question.get('label'), str) else ''
        text = question.get('text') if isinstance(question.get('text'), str) else ''
        if label or text:
            parts.append('%s: %s' % (label[:60], text[:300]) if label else text[:300])
    if not parts:
        return ''
    return '[Pregunté con opciones: %s]' % ' | '.join(parts)


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
            params = {k: v for k, v in redact_parameters(params).items() if v not in (None, '', [], {})}
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
