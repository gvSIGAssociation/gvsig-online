# -*- coding: utf-8 -*-
"""Motor LangGraph del asistente ETL (interruptor ETL_ASSISTANT_ENGINE).

LangGraphExecutor tiene la interfaz de AgentExecutor que usa run_assistant:
invoke({'input', 'chat_history'}) -> {'output'}. Así la segunda pasada, la
propuesta (holder), la traza y la respuesta al navegador no cambian.

Diferencias con AgentExecutor que se cubren aquí:

- max_iterations -> recursion_limit (cada iteración son dos pasos del grafo:
  el modelo y las herramientas).
- Plazo máximo (ETL_ASSISTANT_MAX_SECONDS): AgentExecutor no tenía. Un
  callback lo comprueba antes de cada llamada al modelo y a cada herramienta.
- Al agotar cualquiera de los dos límites se devuelve el texto de parada de
  AgentExecutor, que run_assistant ya reconoce (hit_iteration_limit) y
  convierte en LIMIT_REPLY, conservando la propuesta si ya la había.
- El prompt de sistema llega ya resuelto: sin las llaves duplicadas que
  necesita ChatPromptTemplate.

langgraph solo se importa al usarse: con el motor legacy no hace falta.
"""

import logging

LOGGER = logging.getLogger('gvsigol')

ENGINE_LEGACY = 'legacy'
ENGINE_LANGGRAPH = 'langgraph'

# Mismo texto que AgentExecutor al parar: lo reconoce agent.hit_iteration_limit
STOPPED_OUTPUT = 'Agent stopped due to iteration limit or time limit.'

# Lo que responde create_react_agent cuando se queda sin pasos antes de
# llegar a recursion_limit (no lanza GraphRecursionError)
REACT_OUT_OF_STEPS = 'Sorry, need more steps to process this request.'

DEFAULT_MAX_SECONDS = 120


def _setting(name, default):
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return getattr(geoetl_settings, name, default)
    except Exception:
        return default


def selected_engine():
    """'langgraph' si se pide y está instalado; si no, 'legacy'."""
    engine = str(_setting('ETL_ASSISTANT_ENGINE', ENGINE_LEGACY) or ENGINE_LEGACY).strip().lower()
    if engine != ENGINE_LANGGRAPH:
        return ENGINE_LEGACY
    try:
        import langgraph.prebuilt  # noqa: F401
    except ImportError:
        LOGGER.warning('etl_assistant: ETL_ASSISTANT_ENGINE=langgraph pero langgraph no está instalado: '
                       'se usa legacy')
        return ENGINE_LEGACY
    return ENGINE_LANGGRAPH


def max_seconds():
    """Plazo de un turno en segundos; None (0 o negativo) = sin plazo."""
    try:
        value = int(_setting('ETL_ASSISTANT_MAX_SECONDS', DEFAULT_MAX_SECONDS))
    except (TypeError, ValueError):
        value = DEFAULT_MAX_SECONDS
    return value if value > 0 else None


def system_prompt_text(prompt_template):
    """Texto del mensaje de sistema de un ChatPromptTemplate, como lo ve el modelo."""
    for message in prompt_template.messages:
        prompt = getattr(message, 'prompt', None)
        if prompt is not None and message.__class__.__name__ == 'SystemMessagePromptTemplate':
            return prompt.format()
    raise ValueError('El prompt no tiene mensaje de sistema')


def _deadline_handler(seconds):
    from gvsigol_plugin_geocopilot.services.langgraph_engine import DeadlineCallbackHandler
    return DeadlineCallbackHandler(seconds)


def _is_time_limit(exc):
    from gvsigol_plugin_geocopilot.services.langgraph_engine import AgentTimeLimitExceeded
    return isinstance(exc, AgentTimeLimitExceeded)


def _ran_out_of_steps(messages):
    """True si el grafo terminó sin respuesta final por falta de pasos."""
    from langchain_core.messages import AIMessage, ToolMessage

    if not messages:
        return False
    last = messages[-1]
    if isinstance(last, AIMessage) and not last.tool_calls:
        return isinstance(last.content, str) and last.content.strip() == REACT_OUT_OF_STEPS
    return isinstance(last, ToolMessage)


def _final_content(messages):
    """Contenido del último mensaje del modelo sin llamadas a herramientas."""
    from langchain_core.messages import AIMessage

    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            return message.content
    return ''


def token_streaming_enabled():
    """Texto de la respuesta en vivo (fase 5): ETL_ASSISTANT_TOKEN_STREAMING."""
    return bool(_setting('ETL_ASSISTANT_TOKEN_STREAMING', False))


def _chunk_text(content):
    """Texto de un fragmento: cadena, o bloques de texto (API Responses)."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        content = [content]
    if isinstance(content, (list, tuple)):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get('type', 'text') == 'text' and \
                    isinstance(block.get('text'), str):
                parts.append(block['text'])
        return ''.join(parts)
    return ''


class AnswerTextStreamer(object):
    """Convierte los fragmentos del modelo en eventos 'answer_delta' {delta, reset}.

    Solo el texto de los mensajes del modelo (no las llamadas a herramientas ni
    sus resultados). El primer fragmento de cada mensaje nuevo lleva reset:
    si el modelo escribe algo antes de llamar a una herramienta, la respuesta
    final lo sustituye en el navegador. Un fallo al entregar no corta el turno.
    """

    def __init__(self, emit):
        self.emit = emit
        self.current = None

    def feed(self, chunk, metadata=None):
        from langchain_core.messages import AIMessage, AIMessageChunk

        if not isinstance(chunk, (AIMessage, AIMessageChunk)):
            return
        if getattr(chunk, 'tool_calls', None) and not isinstance(chunk, AIMessageChunk):
            return
        text = _chunk_text(chunk.content)
        if not text:
            return
        # Sin id (algún proveedor), el paso del grafo distingue un mensaje de otro
        message_id = getattr(chunk, 'id', None) or 'step-%s' % (metadata or {}).get('langgraph_step', '')
        reset = message_id != self.current
        self.current = message_id
        try:
            self.emit({'type': 'answer_delta', 'delta': text, 'reset': reset})
        except Exception:
            LOGGER.debug('etl_assistant: no se pudo entregar un fragmento del texto', exc_info=True)


class LangGraphExecutor(object):
    """Agente ReAct de LangGraph con la interfaz de AgentExecutor que usa run_assistant."""

    engine = ENGINE_LANGGRAPH
    # Con una función, el texto de la respuesta se entrega mientras se genera (fase 5)
    on_answer_delta = None

    def __init__(self, llm, tools, system_prompt, max_iterations, seconds=None, callbacks=None):
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        self.graph = create_react_agent(model=llm, tools=tools, prompt=SystemMessage(content=system_prompt))
        self.recursion_limit = 2 * int(max_iterations) + 1
        self.seconds = seconds
        self.callbacks = list(callbacks or [])

    def invoke(self, payload, config=None):
        from langchain_core.messages import HumanMessage
        from langgraph.errors import GraphRecursionError

        messages = list(payload.get('chat_history') or []) + [HumanMessage(content=payload.get('input') or '')]
        callbacks = list(self.callbacks) + list((config or {}).get('callbacks') or [])
        if self.seconds:
            callbacks.append(_deadline_handler(self.seconds))
        config = {'callbacks': callbacks, 'recursion_limit': self.recursion_limit}

        last_state = None
        stopped = False
        streamer = AnswerTextStreamer(self.on_answer_delta) if self.on_answer_delta else None
        # 'values' conserva los pasos hechos si se agota un límite; 'messages',
        # además, da los fragmentos del modelo para el texto en vivo
        modes = ['values', 'messages'] if streamer else ['values']
        try:
            for mode, data in self.graph.stream({'messages': messages}, config, stream_mode=modes):
                if mode == 'values':
                    last_state = data
                elif streamer is not None:
                    streamer.feed(data[0], data[1] if len(data) > 1 else None)
        except GraphRecursionError:
            LOGGER.warning('etl_assistant: límite de iteraciones alcanzado (LangGraph)')
            stopped = True
        except Exception as exc:
            if not _is_time_limit(exc):
                raise
            LOGGER.warning('etl_assistant: tiempo máximo del turno agotado (%ss)', self.seconds)
            stopped = True

        new_messages = (last_state or {}).get('messages', [])[len(messages):]
        if not stopped and _ran_out_of_steps(new_messages):
            LOGGER.warning('etl_assistant: el agente se ha quedado sin pasos (LangGraph)')
            stopped = True
        return {'output': STOPPED_OUTPUT if stopped else _final_content(new_messages)}
