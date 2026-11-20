# -*- coding: utf-8 -*-
"""Texto de la respuesta en vivo (fase 5): eventos 'answer_delta' {delta, reset} con el motor LangGraph."""
import importlib.util
import unittest
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, engine
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.tests.test_assistant_engine import GOOD_PATCH
from gvsigol_plugin_geoetl.tests.test_assistant_execution import SHARED_CACHES

HAS_LANGGRAPH = importlib.util.find_spec('langgraph') is not None

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]
CANVAS = {'nodes': [{'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Postgis', 'label': 'input_Postgis',
                     'parameters': {'x': 1}, 'schema': [], 'x': 100, 'y': 100}], 'edges': []}


def streaming_model(turns, size=6):
    """Modelo que entrega el texto en trozos (como OpenAI con streaming).

    Cada turno es una lista de (herramienta, argumentos) o un texto, que llega
    en trozos de `size` caracteres. Las llamadas a herramientas llegan enteras.
    """
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage, AIMessageChunk
    from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

    pending = list(turns)
    counter = {'n': 0}

    class StreamingModel(BaseChatModel):
        @property
        def _llm_type(self):
            return 'streaming'

        def bind_tools(self, tools, **kwargs):
            return self

        def _next(self):
            counter['n'] += 1
            return pending.pop(0) if pending else 'Fin.', 'r%d' % counter['n']

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            turn, msg_id = self._next()
            if isinstance(turn, list):
                message = AIMessage(content='', id=msg_id, tool_calls=[
                    {'name': n, 'args': a, 'id': 'c%d' % i} for i, (n, a) in enumerate(turn)])
            else:
                message = AIMessage(content=turn, id=msg_id)
            return ChatResult(generations=[ChatGeneration(message=message)])

        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            turn, msg_id = self._next()
            if isinstance(turn, list):
                pieces = [AIMessageChunk(content='', id=msg_id, tool_call_chunks=[
                    {'name': n, 'args': __import__('json').dumps(a), 'id': 'c%d' % i, 'index': i}
                    for i, (n, a) in enumerate(turn)])]
            else:
                pieces = [AIMessageChunk(content=turn[i:i + size], id=msg_id) for i in range(0, len(turn), size)]
            for piece in pieces:
                chunk = ChatGenerationChunk(message=piece)
                if run_manager:
                    run_manager.on_llm_new_token(piece.content if isinstance(piece.content, str) else '',
                                                 chunk=chunk)
                yield chunk

    return StreamingModel()


class StreamerTests(unittest.TestCase):

    def _feed(self, chunks):
        events = []
        streamer = engine.AnswerTextStreamer(events.append)
        for chunk, meta in chunks:
            streamer.feed(chunk, meta)
        return events

    def test_text_tool_calls_and_tool_results(self):
        from langchain_core.messages import AIMessageChunk, ToolMessage
        events = self._feed([
            (AIMessageChunk(content='Miro ', id='a'), None),
            (AIMessageChunk(content='', id='a', tool_call_chunks=[{'name': 'x', 'args': '{}', 'id': 'c', 'index': 0}]),
             None),
            (ToolMessage(content='{"secreto": 1}', tool_call_id='c'), None),
            (AIMessageChunk(content='Hecho', id='b'), None),
            (AIMessageChunk(content=', n2.', id='b'), None),
        ])
        self.assertEqual([(e['delta'], e['reset']) for e in events],
                         [('Miro ', True), ('Hecho', True), (', n2.', False)])

    def test_responses_api_blocks_and_missing_ids(self):
        from langchain_core.messages import AIMessageChunk
        events = self._feed([
            (AIMessageChunk(content=[{'type': 'text', 'text': 'Ho', 'index': 0}]), {'langgraph_step': 1}),
            (AIMessageChunk(content=[{'type': 'text', 'text': 'la'}]), {'langgraph_step': 1}),
            (AIMessageChunk(content=[{'type': 'reasoning', 'summary': []}]), {'langgraph_step': 1}),
            (AIMessageChunk(content='Otra'), {'langgraph_step': 3}),
        ])
        self.assertEqual([(e['delta'], e['reset']) for e in events],
                         [('Ho', True), ('la', False), ('Otra', True)])

    def test_a_failing_emit_does_not_break_the_turn(self):
        from langchain_core.messages import AIMessageChunk
        streamer = engine.AnswerTextStreamer(mock.Mock(side_effect=RuntimeError('cola cerrada')))
        streamer.feed(AIMessageChunk(content='hola', id='a'))                  # no lanza


@unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
@override_settings(CACHES=SHARED_CACHES, LANGUAGE_CODE='es')
class LiveTextTests(SimpleTestCase):

    def _run(self, turns, token_streaming=True, engine_name='langgraph', on_event=True):
        events = []
        model = streaming_model(turns)
        context = AssistantContext.from_payload({'is_superuser': True, 'connections': CONNECTIONS,
                                                 'language': 'es'})
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', engine_name, create=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_TOKEN_STREAMING', token_streaming, create=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_MAX_SECONDS', 120, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=model):
            result = agent.run_assistant(context, 'añade un filtro', [], CANVAS, None, None,
                                         on_event=events.append if on_event else None, query_id='q-live')
        return result, events

    def test_deltas_rebuild_the_reply(self):
        text = 'He propuesto un **filtro** (n2) después de n1. Revisa la condición.'
        result, events = self._run([[('propose_workspace', {'proposal_json': GOOD_PATCH})], text])
        deltas = [e for e in events if e['type'] == 'answer_delta']
        self.assertGreater(len(deltas), 3)                                     # llega en varios trozos
        self.assertEqual(''.join(e['delta'] for e in deltas), text)
        self.assertTrue(deltas[0]['reset'])
        self.assertEqual(result['reply'], text)
        self.assertIsNotNone(result['proposal'])
        # los pasos siguen llegando, antes que el texto
        self.assertEqual(events[0]['type'], 'step')

    def test_second_pass_is_not_shown_live(self):
        first = 'He conectado los nodos.'
        result, events = self._run([first, 'SIN_CAMBIOS'])
        live = ''.join(e['delta'] for e in events if e['type'] == 'answer_delta')
        self.assertEqual(live, first)
        self.assertNotIn('SIN_CAMBIOS', live)
        self.assertEqual(result['reply'], first)

    def test_off_without_the_flag(self):
        _, events = self._run([[('get_node_specs', {'types': 'trans_Filter'})], 'Vale.'], token_streaming=False)
        self.assertEqual([e['type'] for e in events], ['step'])

    def test_off_with_the_legacy_engine(self):
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage

        class Model(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self
        events = []
        context = AssistantContext.from_payload({'is_superuser': True, 'connections': CONNECTIONS})
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', 'legacy', create=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_TOKEN_STREAMING', True, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=Model(responses=[AIMessage(content='Vale.')])):
            result = agent.run_assistant(context, 'hola', [], {}, None, None, on_event=events.append)
        self.assertEqual(result['reply'], 'Vale.')
        self.assertEqual(events, [])

    def test_off_without_a_listener(self):
        result, _ = self._run(['Vale.'], on_event=False)
        self.assertEqual(result['reply'], 'Vale.')

    def test_limit_replaces_the_live_text_in_the_result(self):
        looping = [[('get_node_specs', {'types': 'trans_Filter'})]] * 60
        with mock.patch.object(agent, '_max_iterations', return_value=2):
            result, _ = self._run(looping)
        self.assertEqual(result['reply'], agent.LIMIT_REPLY)
