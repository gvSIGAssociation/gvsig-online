# -*- coding: utf-8 -*-
"""Ejecuta el agente. La importación de LangChain y de build_llm es perezosa."""

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .catalog import load_catalog
from .prompt import system_prompt
from .tools import build_tools

LOGGER = logging.getLogger('gvsigol')

_HISTORY_LIMIT = 16
_MESSAGE_LIMIT = 8000


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
    return 'No se ha podido consultar el asistente. Inténtalo de nuevo.'


def run_assistant(request, message, history, canvas, restricted, connections):
    catalog = load_catalog()
    holder = []
    tools = build_tools(request, catalog, canvas or {}, connections, restricted, holder)
    llm = _build_llm()
    prompt = ChatPromptTemplate.from_messages([
        ('system', system_prompt(catalog, _language())),
        MessagesPlaceholder(variable_name='chat_history', optional=True),
        ('human', '{input}'),
        MessagesPlaceholder(variable_name='agent_scratchpad'),
    ])
    executor = _executor(llm, tools, prompt)
    try:
        result = executor.invoke({
            'input': _user_input(message, canvas),
            'chat_history': _history(history),
        })
    except Exception as exc:
        LOGGER.exception('etl_assistant: fallo al invocar el agente')
        return {
            'reply': public_llm_error(exc),
            'warnings': [],
            'assumptions': [],
            'summary': [],
            'needs_confirmation': False,
            'proposal': None,
            'error': True,
        }
    reply = output_text(result.get('output'))
    if holder:
        payload = dict(holder[-1])
        if not reply:
            payload['reply'] = '\n'.join(payload.get('summary') or [])
        else:
            payload['reply'] = reply
        payload['error'] = False
        return payload
    return {
        'reply': reply or '¿Puedes concretar un poco más el flujo?',
        'warnings': [],
        'assumptions': [],
        'summary': [],
        'needs_confirmation': False,
        'proposal': None,
        'error': False,
    }


def _language():
    from django.utils import translation
    return translation.get_language()


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
        max_iterations=iterations,
        handle_parsing_errors=True,
        return_intermediate_steps=False,
    )


def _history(history):
    messages = []
    for item in (history or [])[-_HISTORY_LIMIT:]:
        if not isinstance(item, dict):
            continue
        content = item.get('content')
        if not isinstance(content, str) or not content.strip():
            continue
        content = content.strip()[:_MESSAGE_LIMIT]
        if item.get('role') == 'assistant':
            messages.append(AIMessage(content=content))
        elif item.get('role') == 'user':
            messages.append(HumanMessage(content=content))
    return messages


def _user_input(message, canvas):
    text = (message or '').strip()[:_MESSAGE_LIMIT]
    snapshot = _canvas_for_prompt(canvas or {})
    selected = snapshot.get('selected') or ''
    body = json.dumps(
        {'nodes': snapshot.get('nodes') or [], 'edges': snapshot.get('edges') or []},
        ensure_ascii=False,
    )
    if len(body) > 24000:
        body = body[:24000] + '…'
    selected_line = 'Nodo seleccionado: %s.' % selected if selected else 'No hay ningún nodo seleccionado.'
    return '%s\n\n%s\nCanvas actual:\n%s' % (text, selected_line, body)


def _canvas_for_prompt(canvas):
    nodes = []
    for node in canvas.get('nodes') or []:
        if not isinstance(node, dict):
            continue
        nodes.append({
            'id': node.get('alias') or node.get('id'),
            'type': node.get('type'),
            'label': node.get('label'),
            'parameters': node.get('parameters') if isinstance(node.get('parameters'), dict) else {},
            'schema': node.get('schema') if isinstance(node.get('schema'), list) else [],
        })
    return {
        'selected': canvas.get('selected') or '',
        'nodes': nodes,
        'edges': canvas.get('edges') if isinstance(canvas.get('edges'), list) else [],
    }
