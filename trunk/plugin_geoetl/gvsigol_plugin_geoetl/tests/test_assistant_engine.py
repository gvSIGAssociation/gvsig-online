# -*- coding: utf-8 -*-
"""Motor LangGraph del asistente (fase 2): el mismo bucle que con AgentExecutor, con un modelo simulado."""
import importlib.util
import json
import sys
import time
import unittest
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, engine
from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.context import AssistantContext

HAS_LANGGRAPH = importlib.util.find_spec('langgraph') is not None

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]
CANVAS = {'nodes': [{'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Postgis', 'label': 'input_Postgis',
                     'parameters': {'x': 1}, 'schema': [], 'x': 100, 'y': 100}], 'edges': []}
GOOD_PATCH = json.dumps({'mode': 'patch', 'ops': [
    {'op': 'add_node', 'node': {'id': 'n2', 'type': 'trans_Filter', 'parameters': {}}},
    {'op': 'add_edge', 'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]})


def scripted_model(turns, delay=0.0):
    """Modelo que responde, llamada a llamada, con lo que diga turns.

    Cada elemento de turns es una lista de (herramienta, argumentos), un texto
    final o una excepción. Guarda en .seen los mensajes que recibe.
    """
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    pending = list(turns)
    seen = []

    class ScriptedModel(BaseChatModel):
        @property
        def _llm_type(self):
            return 'scripted'

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            seen.append(list(messages))
            if delay:
                time.sleep(delay)
            turn = pending.pop(0) if pending else 'Fin.'
            if isinstance(turn, Exception):
                raise turn
            if isinstance(turn, list):
                calls = [{'name': name, 'args': args, 'id': 'c%d_%d' % (len(seen), i)}
                         for i, (name, args) in enumerate(turn)]
                message = AIMessage(content='', tool_calls=calls)
            else:
                message = AIMessage(content=turn)
            return ChatResult(generations=[ChatGeneration(message=message)])

    model = ScriptedModel()
    model.__dict__['seen'] = seen
    return model


def propose():
    return [('propose_workspace', {'proposal_json': GOOD_PATCH})]


@unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
@override_settings(LANGUAGE_CODE='es')
class LangGraphLoopTests(SimpleTestCase):
    """Los casos de AgentLoopTests (test_assistant_agent.py), con el motor LangGraph de verdad."""

    def run_with(self, turns, history=None, seconds=120, iterations=None):
        model = scripted_model(turns)
        context = AssistantContext.from_payload({'is_superuser': True, 'is_staff': True,
                                                 'connections': CONNECTIONS, 'language': 'es'})
        patches = [
            mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', 'langgraph', create=True),
            mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_MAX_SECONDS', seconds, create=True),
            mock.patch.object(agent, '_build_llm', return_value=model),
        ]
        if iterations:
            patches.append(mock.patch.object(agent, '_max_iterations', return_value=iterations))
        for patch in patches:
            patch.start()
        try:
            result = agent.run_assistant(context, 'añade un filtro', history or [], CANVAS, None, None)
        finally:
            for patch in reversed(patches):
                patch.stop()
        return result, model.seen

    def test_proposal_and_reply(self):
        result, _ = self.run_with([propose(), 'Listo: filtro añadido.'])
        self.assertIsNotNone(result['proposal'])
        self.assertEqual(result['reply'], 'Listo: filtro añadido.')
        self.assertFalse(result['error'])

    def test_claim_without_proposal_is_retried_and_fixed(self):
        result, seen = self.run_with(['He añadido un filtro después de n1.', propose(), 'Listo: filtro añadido.'])
        self.assertIsNotNone(result['proposal'])
        self.assertEqual(result['reply'], 'Listo: filtro añadido.')
        # La segunda pasada lleva el aviso y la conversación anterior
        second = seen[1]
        self.assertIn('propose_workspace', second[-1].content)
        self.assertEqual(second[-2].content, 'He añadido un filtro después de n1.')

    def test_claim_confirmed_as_no_change_keeps_reply(self):
        result, _ = self.run_with(['He añadido... no, solo explico: n1 lee la tabla.', 'SIN_CAMBIOS'])
        self.assertIsNone(result['proposal'])
        self.assertEqual(result['warnings'], [])
        self.assertIn('n1 lee la tabla', result['reply'])

    def test_claim_still_without_proposal_warns_the_user(self):
        result, _ = self.run_with(['He conectado los nodos.', 'Ya está hecho.'])
        self.assertIsNone(result['proposal'])
        self.assertIn(agent.NO_CHANGE_WARNING, result['warnings'])

    def test_iteration_limit_without_proposal(self):
        looping = [[('get_node_specs', {'types': 'trans_Filter'})]] * 50
        result, seen = self.run_with(looping, iterations=3)
        self.assertEqual(result['reply'], agent.LIMIT_REPLY)
        self.assertLessEqual(len(seen), 4)

    def test_iteration_limit_keeps_a_valid_proposal(self):
        looping = [propose()] + [[('get_node_specs', {'types': 'trans_Filter'})]] * 50
        result, _ = self.run_with(looping, iterations=3)
        self.assertIsNotNone(result['proposal'])
        self.assertNotIn('Agent stopped', result['reply'])
        self.assertIn('n2', result['reply'])                                # resumen de los cambios

    def test_llm_failure_after_proposal_keeps_it(self):
        result, _ = self.run_with([propose(), RuntimeError('timed out')])
        self.assertIsNotNone(result['proposal'])
        self.assertFalse(result['error'])
        self.assertIn('tardado', ' '.join(result['warnings']))

    def test_llm_failure_without_proposal(self):
        result, _ = self.run_with([RuntimeError('401 invalid_api_key')])
        self.assertTrue(result['error'])
        self.assertIn('clave', result['reply'])

    def test_history_reaches_the_model(self):
        history = [{'role': 'user', 'content': 'hola'},
                   {'role': 'assistant', 'content': 'Te escucho.', 'summary': ['Añado Filter (n2).'],
                    'status': 'discarded'}]
        _, seen = self.run_with(['Vale.'], history=history)
        contents = [m.content for m in seen[0]]
        self.assertEqual(contents[1], 'hola')
        self.assertIn('la descartó', contents[2])
        self.assertIn('Canvas actual', contents[3])

    def test_system_prompt_without_escaped_braces(self):
        _, seen = self.run_with(['Vale.'])
        system = seen[0][0]
        self.assertEqual(system.type, 'system')
        self.assertNotIn('{{', system.content)
        self.assertNotIn('}}', system.content)
        expected = agent._prompt(load_catalog(), 'es').format_messages(
            input='x', chat_history=[], agent_scratchpad=[])[0].content
        self.assertEqual(system.content, expected)

    def test_trace_records_the_engine(self):
        records = []
        with mock.patch.object(agent, '_trace_enabled', return_value=True), \
                mock.patch.object(agent.LOGGER, 'info', side_effect=lambda fmt, data: records.append(data)):
            self.run_with(['Vale.'])
        self.assertEqual(json.loads(records[-1])['engine'], 'langgraph')


@unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
class TimeLimitTests(SimpleTestCase):

    def test_slow_turn_stops_with_the_limit_text(self):
        from langchain_core.tools import tool

        @tool
        def slow() -> str:
            """Herramienta lenta."""
            time.sleep(0.3)
            return 'ok'

        model = scripted_model([[('slow', {})]] * 20)
        executor = engine.LangGraphExecutor(model, [slow], 'Prueba', max_iterations=20, seconds=1)
        started = time.monotonic()
        out = executor.invoke({'input': 'hola', 'chat_history': []})
        self.assertEqual(out['output'], engine.STOPPED_OUTPUT)
        self.assertTrue(agent.hit_iteration_limit(out['output']))
        self.assertLess(time.monotonic() - started, 3)

    def test_responses_api_content_blocks(self):
        # La API Responses devuelve el texto como lista de bloques: llega tal cual a output_text
        from langchain_core.messages import AIMessage
        blocks = [{'type': 'text', 'text': 'Hola '}, {'type': 'text', 'text': 'mundo'}]
        self.assertEqual(engine._final_content([AIMessage(content=blocks)]), blocks)
        self.assertEqual(agent.output_text(blocks), 'Hola mundo')


class EngineSelectionTests(SimpleTestCase):

    def test_legacy_by_default(self):
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', 'legacy', create=True):
            self.assertEqual(engine.selected_engine(), engine.ENGINE_LEGACY)
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', '', create=True):
            self.assertEqual(engine.selected_engine(), engine.ENGINE_LEGACY)

    @unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
    def test_langgraph_when_requested(self):
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', ' LangGraph ', create=True):
            self.assertEqual(engine.selected_engine(), engine.ENGINE_LANGGRAPH)

    def test_falls_back_to_legacy_without_langgraph(self):
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', 'langgraph', create=True), \
                mock.patch.dict(sys.modules, {'langgraph.prebuilt': None}):
            self.assertEqual(engine.selected_engine(), engine.ENGINE_LEGACY)

    def test_max_seconds(self):
        for value, expected in ((120, 120), (0, None), (-5, None), ('x', engine.DEFAULT_MAX_SECONDS)):
            with self.subTest(value=value), \
                    mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_MAX_SECONDS', value, create=True):
                self.assertEqual(engine.max_seconds(), expected)

    def test_legacy_executor_is_unchanged(self):
        from langchain.agents import AgentExecutor
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

        class Model(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        prompt = agent._prompt(load_catalog(), 'es')
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', 'legacy', create=True):
            executor = agent._executor(Model(responses=[]), [], prompt)
        self.assertIsInstance(executor, AgentExecutor)
        self.assertGreaterEqual(executor.max_iterations, 20)
        self.assertIsNone(executor.max_execution_time)
