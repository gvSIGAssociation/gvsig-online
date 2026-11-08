# -*- coding: utf-8 -*-
"""Pasos en vivo y Detener real (fase 4): callbacks, cancelación, eventos del stream y vistas SSE/cancel."""
import importlib.util
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, cancellation, execution, streaming
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.tests.test_assistant_engine import GOOD_PATCH, scripted_model
from gvsigol_plugin_geoetl.tests.test_assistant_execution import SHARED_CACHES, FakeBroker

HAS_LANGGRAPH = importlib.util.find_spec('langgraph') is not None

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]
CANVAS = {'nodes': [{'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Postgis', 'label': 'input_Postgis',
                     'parameters': {'x': 1}, 'schema': [], 'x': 100, 'y': 100}], 'edges': []}


def _context():
    return AssistantContext.from_payload({'user_id': 7, 'username': 'ana', 'is_superuser': True,
                                          'is_staff': True, 'connections': CONNECTIONS, 'language': 'es'})


def _patches(model, engine='langgraph'):
    return [mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', engine, create=True),
            mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_MAX_SECONDS', 120, create=True),
            mock.patch.object(agent, '_build_llm', return_value=model)]


def _run(patches, fn):
    for patch in patches:
        patch.start()
    try:
        return fn()
    finally:
        for patch in reversed(patches):
            patch.stop()


class StepDetailTests(SimpleTestCase):

    def test_only_safe_short_arguments(self):
        self.assertEqual(streaming.step_detail('get_table_schema', {
            'connection': 'gis', 'schema': 'public', 'table': 'municipios'}),
            {'connection': 'gis', 'schema': 'public', 'table': 'municipios'})
        self.assertEqual(streaming.step_detail('propose_workspace', {'proposal_json': '{"sql": "x"}'}), {})
        self.assertEqual(streaming.step_detail('check_workspace', {'proposal_json': '{}'}), {})
        self.assertEqual(len(streaming.step_detail('get_node_specs', {'types': 'x' * 500})['types']), 80)
        self.assertEqual(streaming.step_detail('list_files', 'texto'), {})

    def test_a_failing_emit_does_not_break_the_turn(self):
        handler = streaming.StepCallbackHandler(mock.Mock(side_effect=RuntimeError('cola cerrada')))
        handler.on_tool_start({'name': 'list_connections'}, '', inputs={})                 # no lanza


@override_settings(CACHES=SHARED_CACHES, LANGUAGE_CODE='es')
class RunWithEventsTests(SimpleTestCase):
    """run_assistant con on_event y query_id, con los dos motores."""

    def _run(self, turns, engine, on_event=None, query_id=None):
        model = scripted_model(turns)
        return _run(_patches(model, engine), lambda: agent.run_assistant(
            _context(), 'añade un filtro', [], CANVAS, None, None, on_event=on_event, query_id=query_id))

    def _steps_in_order(self, engine):
        events = []
        result = self._run([[('get_node_specs', {'types': 'trans_Filter'})],
                            [('propose_workspace', {'proposal_json': GOOD_PATCH})],
                            'Filtro añadido.'], engine, on_event=events.append, query_id='q-steps-' + engine)
        self.assertIsNotNone(result['proposal'])
        self.assertEqual([(e['type'], e['tool']) for e in events],
                         [('step', 'get_node_specs'), ('step', 'propose_workspace')])
        self.assertEqual(events[0]['detail'], {'types': 'trans_Filter'})
        self.assertEqual(events[1]['detail'], {})

    @unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
    def test_steps_langgraph(self):
        self._steps_in_order('langgraph')

    def test_steps_legacy(self):
        self._steps_in_order('legacy')

    def _stopped_mid_turn(self, engine):
        query_id = 'q-stop-' + engine

        def on_event(event):
            if event['tool'] == 'propose_workspace':
                cancellation.cancel(query_id)                 # el usuario pulsa Detener aquí
        result = self._run([[('propose_workspace', {'proposal_json': GOOD_PATCH})], 'No debería llegar.'],
                           engine, on_event=on_event, query_id=query_id)
        self.assertEqual(result['reply'], agent.CANCELLED_REPLY)
        self.assertIsNone(result['proposal'])                 # Detener: el canvas no cambia
        self.assertTrue(result['error'])

    @unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
    def test_stop_mid_turn_langgraph(self):
        self._stopped_mid_turn('langgraph')

    def test_stop_mid_turn_legacy(self):
        self._stopped_mid_turn('legacy')

    def test_stop_before_the_first_call(self):
        cancellation.cancel('q-early')
        model = scripted_model(['Hola.'])
        result = _run(_patches(model), lambda: agent.run_assistant(
            _context(), 'x', [], {}, None, None, query_id='q-early'))
        self.assertEqual(result['reply'], agent.CANCELLED_REPLY)
        self.assertEqual(model.seen, [])                       # no se ha gastado ni una llamada


@unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
@override_settings(CACHES=SHARED_CACHES, LANGUAGE_CODE='es')
class StreamEventsTests(SimpleTestCase):

    TURNS = [[('get_node_specs', {'types': 'trans_Filter'})],
             [('propose_workspace', {'proposal_json': GOOD_PATCH})], 'Filtro añadido.']

    def test_inline(self):
        model = scripted_model(list(self.TURNS))
        patches = _patches(model) + [
            mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_EXECUTION', 'inline', create=True)]
        events = _run(patches, lambda: list(execution.stream_events(_context(), 'x', [], CANVAS, 'q-in')))
        self.assertEqual([e['type'] for e in events], ['start', 'step', 'step', 'result'])
        self.assertEqual(events[0]['query_id'], 'q-in')
        self.assertIsNotNone(events[-1]['payload']['proposal'])

    def test_celery(self):
        model = scripted_model(list(self.TURNS))
        broker = FakeBroker()
        patches = _patches(model) + broker.patches() + [
            mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_EXECUTION', 'celery', create=True)]
        events = _run(patches, lambda: list(execution.stream_events(_context(), 'x', [], CANVAS, 'q-cel')))
        self.assertEqual([e['type'] for e in events], ['start', 'step', 'step', 'result'])   # sin 'started'
        self.assertTrue(broker.sent[0]['data']['steps'])
        self.assertEqual(broker.sent[0]['data']['query_id'], 'q-cel')

    def test_wait_result_does_not_ask_for_steps(self):
        model = scripted_model(['Hola.'])
        broker = FakeBroker()
        _run(_patches(model) + broker.patches(), lambda: execution.wait_result(_context(), 'x', [], {}))
        self.assertFalse(broker.sent[0]['data']['steps'])


def _user(uid=7):
    return SimpleNamespace(id=uid, username='u%d' % uid, is_authenticated=True, is_staff=True, is_superuser=True)


@override_settings(CACHES=SHARED_CACHES, LANGUAGE_CODE='es')
class StreamViewTests(SimpleTestCase):

    def _request(self, url, body, user=None):
        request = RequestFactory().post(url, data=json.dumps(body), content_type='application/json')
        request.user = user or _user()
        return request

    def _view_patches(self, streaming_on=True):
        from gvsigol_plugin_geoetl.assistant import views
        return [mock.patch.object(views, 'assistant_feature_enabled', return_value=True),
                mock.patch('gvsigol_plugin_geoetl.views.get_etl_connections_list', return_value=CONNECTIONS),
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_STREAMING', streaming_on, create=True),
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_EXECUTION', 'inline', create=True)]

    def test_disabled_by_default(self):
        from django.http import Http404
        from gvsigol_plugin_geoetl.assistant import views
        request = self._request('/s/', {'message': 'hola'})
        with self.assertRaises(Http404):
            _run(self._view_patches(False), lambda: views.etl_assistant_stream(request))
        with self.assertRaises(Http404):
            _run(self._view_patches(False), lambda: views.etl_assistant_cancel(request))

    @unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
    def test_sse_frames_with_the_public_json(self):
        from gvsigol_plugin_geoetl.assistant import views
        model = scripted_model([[('get_node_specs', {'types': 'trans_Filter'})], 'Vale.'])
        request = self._request('/s/', {'message': 'hola', 'canvas': CANVAS, 'query_id': 'qabcdef123'})

        def call():
            response = views.etl_assistant_stream(request)
            return response, b''.join(response.streaming_content).decode('utf-8')
        response, body = _run(self._view_patches() + _patches(model), call)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['X-Accel-Buffering'], 'no')
        frames = [json.loads(f[len('data: '):]) for f in body.split('\n\n') if f.startswith('data: ')]
        self.assertEqual([f['type'] for f in frames], ['start', 'step', 'result'])
        self.assertEqual(frames[0]['query_id'], 'qabcdef123')
        self.assertEqual(sorted(frames[-1]['payload']), sorted(['reply', 'warnings', 'assumptions', 'summary',
                                                                'needs_confirmation', 'proposal', 'error']))
        self.assertEqual(cancellation.owner('qabcdef123'), 7)

    def test_bad_query_id_is_replaced(self):
        from gvsigol_plugin_geoetl.assistant import views
        request = self._request('/s/', {'message': 'hola', 'query_id': '../x'})
        with mock.patch.object(execution, 'stream_events', return_value=iter([])) as events:
            _run(self._view_patches(), lambda: views.etl_assistant_stream(request))
        self.assertRegex(events.call_args[0][4], r'^[0-9a-f]{32}$')

    def test_cancel_only_by_the_owner(self):
        from gvsigol_plugin_geoetl.assistant import views
        cancellation.set_owner('qowner0001', 7)
        other = _run(self._view_patches(), lambda: views.etl_assistant_cancel(
            self._request('/c/', {'query_id': 'qowner0001'}, user=_user(8))))
        self.assertEqual(other.status_code, 404)
        self.assertFalse(cancellation.is_cancelled('qowner0001'))
        bad = _run(self._view_patches(), lambda: views.etl_assistant_cancel(self._request('/c/', {'query_id': 'x'})))
        self.assertEqual(bad.status_code, 400)
        mine = _run(self._view_patches(), lambda: views.etl_assistant_cancel(
            self._request('/c/', {'query_id': 'qowner0001'})))
        self.assertEqual(json.loads(mine.content), {'cancelled': True})
        self.assertTrue(cancellation.is_cancelled('qowner0001'))

    def test_browser_gone_cancels_the_turn(self):
        from gvsigol_plugin_geoetl.assistant import views

        def events():
            yield {'type': 'start', 'query_id': 'qgone00001'}
            yield {'type': 'ping'}
        frames = views._sse(events(), 'qgone00001')
        next(frames)
        frames.close()                                          # el servidor cierra al fallar la escritura
        self.assertTrue(cancellation.is_cancelled('qgone00001'))

    def test_closing_after_the_result_does_not_cancel(self):
        from gvsigol_plugin_geoetl.assistant import views

        def events():
            yield {'type': 'result', 'payload': {'reply': 'ok'}}
            yield {'type': 'ping'}
        frames = views._sse(events(), 'qdone00001')
        next(frames)
        frames.close()
        self.assertFalse(cancellation.is_cancelled('qdone00001'))

    def test_template_context_has_the_flag(self):
        from gvsigol_plugin_geoetl import views as editor_views
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_STREAMING', True, create=True):
            self.assertTrue(editor_views._ctx()['etl_assistant_streaming'])
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_STREAMING', False, create=True):
            self.assertFalse(editor_views._ctx({'x': 1})['etl_assistant_streaming'])
