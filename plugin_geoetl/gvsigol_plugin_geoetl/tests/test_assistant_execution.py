# -*- coding: utf-8 -*-
"""Asistente en Celery (fase 3): tarea, espera del web, vuelta a inline y mismo JSON en los dos modos.

RabbitMQ y el worker se simulan en el mismo proceso: apply_async ejecuta la
tarea al momento y sus eventos van a la cola de la suscripción.
"""
import json
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, cancellation, execution
from gvsigol_plugin_geoetl.assistant.context import AssistantContext

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]
CANVAS = {'nodes': [{'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Postgis', 'label': 'input_Postgis',
                     'parameters': {'x': 1}, 'schema': [], 'x': 100, 'y': 100}], 'edges': []}
GOOD_PATCH = json.dumps({'mode': 'patch', 'ops': [
    {'op': 'add_node', 'node': {'id': 'n2', 'type': 'trans_Filter', 'parameters': {}}},
    {'op': 'add_edge', 'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]})

LOCMEM = 'django.core.cache.backends.locmem.LocMemCache'
SHARED_CACHES = {'default': {'BACKEND': LOCMEM, 'LOCATION': 'etl-default'},
                 'geocopilot': {'BACKEND': LOCMEM, 'LOCATION': 'etl-shared'}}


class ProposingExecutor(object):
    """Hace lo que haría el modelo: propone un filtro y responde."""

    def __init__(self, tools):
        self.tools = {t.name: t for t in tools}

    def invoke(self, payload, config=None):                 # como AgentExecutor y LangGraphExecutor
        self.tools['propose_workspace'].invoke({'proposal_json': GOOD_PATCH})
        return {'output': 'Filtro añadido después de n1.'}


def proposing_executor(llm, tools, prompt):
    return ProposingExecutor(tools)


class FakeSubscription(object):
    def __init__(self):
        self.events = []
        self.closed = False

    def get(self, timeout):
        return self.events.pop(0) if self.events else None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True


class FakeBroker(object):
    """event_bus + apply_async: el 'worker' ejecuta la tarea al encolarla (o no, si no hay worker)."""

    def __init__(self, worker=True, events=None):
        self.subscription = FakeSubscription()
        self.worker = worker
        self.events = events
        self.sent = []

    def subscribe(self, events_id):
        self.events_id = events_id
        return self.subscription

    def apply_async(self, args, queue):
        data, events_queue = args
        self.sent.append({'data': json.loads(json.dumps(data)), 'queue': queue, 'events_queue': events_queue})
        if self.events is not None:
            self.subscription.events.extend(self.events)
        elif self.worker:
            execution.execute(self.sent[-1]['data'], self.subscription.events.append)

    def patches(self):
        from gvsigol_plugin_geocopilot.services import event_bus
        from gvsigol_plugin_geoetl import tasks
        return [mock.patch.object(event_bus, 'subscribe', side_effect=self.subscribe),
                mock.patch.object(tasks.run_assistant_task, 'apply_async', side_effect=self.apply_async)]


def _context():
    return AssistantContext.from_payload({'user_id': 7, 'username': 'ana', 'is_superuser': True,
                                          'is_staff': True, 'connections': CONNECTIONS, 'language': 'es'})


def _start(patches):
    for patch in patches:
        patch.start()


def _stop(patches):
    for patch in reversed(patches):
        patch.stop()


class ExecutionModeTests(SimpleTestCase):

    def _mode(self, value, caches):
        with override_settings(CACHES=caches), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_EXECUTION', value, create=True):
            return execution.execution_mode()

    def test_inline_by_default(self):
        self.assertEqual(self._mode('inline', SHARED_CACHES), execution.EXECUTION_INLINE)
        self.assertEqual(self._mode('', SHARED_CACHES), execution.EXECUTION_INLINE)

    def test_celery_with_shared_cache(self):
        self.assertEqual(self._mode(' Celery ', SHARED_CACHES), execution.EXECUTION_CELERY)

    def test_celery_without_shared_cache_falls_back_to_inline(self):
        with self.assertLogs('gvsigol', 'WARNING') as logs:
            mode = self._mode('celery', {'default': SHARED_CACHES['default']})
        self.assertEqual(mode, execution.EXECUTION_INLINE)
        self.assertIn('GEOCOPILOT_SHARED_CACHE', logs.output[0])

    def test_queue_and_time_limits(self):
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_CELERY_QUEUE', '', create=True):
            self.assertEqual(execution.celery_queue(), 'geocopilot')
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_MAX_SECONDS', 120, create=True):
            self.assertEqual(execution.task_time_limits(), {'soft_time_limit': 150, 'time_limit': 180})
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_MAX_SECONDS', 0, create=True):
            self.assertEqual(execution.task_time_limits()['time_limit'], execution.FALLBACK_TASK_SECONDS + 60)


class TaskTests(SimpleTestCase):

    def test_task_is_registered_without_retries(self):
        from gvsigol.celery import app
        from gvsigol_plugin_geoetl.tasks import run_assistant_task
        self.assertIn('geoetl.run_assistant', app.tasks)
        self.assertFalse(run_assistant_task.acks_late)
        self.assertTrue(run_assistant_task.ignore_result)
        self.assertGreater(run_assistant_task.time_limit, run_assistant_task.soft_time_limit)

    def test_emitter_publishes_and_survives_failures(self):
        from gvsigol_plugin_geocopilot.services import event_bus
        from gvsigol_plugin_geoetl.tasks import _assistant_emitter
        with mock.patch.object(event_bus, 'publish') as publish:
            _assistant_emitter('geocopilot.events.etl-1')({'type': 'started'})
        publish.assert_called_once_with('geocopilot.events.etl-1', {'type': 'started'})
        with mock.patch.object(event_bus, 'publish', side_effect=OSError('broker caído')):
            _assistant_emitter('q')({'type': 'result'})                      # no lanza
        _assistant_emitter(None)({'type': 'result'})                          # solo al log


@override_settings(CACHES=SHARED_CACHES, LANGUAGE_CODE='es')
class WorkerTests(SimpleTestCase):

    def _data(self, query_id='q1'):
        return json.loads(json.dumps(execution.task_payload(_context(), 'añade un filtro', [], CANVAS, query_id)))

    def test_started_then_result(self):
        events = []
        with mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor', side_effect=proposing_executor):
            execution.execute(self._data(), events.append)
        self.assertEqual([e['type'] for e in events], ['started', 'result'])
        result = events[-1]['payload']
        self.assertIsNotNone(result['proposal'])
        self.assertEqual(result['reply'], 'Filtro añadido después de n1.')
        json.dumps(result)                                                    # viaja por RabbitMQ

    def test_cancelled_before_start_does_not_run(self):
        cancellation.cancel('q2')
        events = []
        with mock.patch.object(agent, 'run_assistant') as run:
            execution.execute(self._data('q2'), events.append)
        run.assert_not_called()
        self.assertEqual(events, [])

    def test_unexpected_error_ends_in_an_error_result(self):
        events = []
        with mock.patch.object(agent, 'run_assistant', side_effect=RuntimeError('boom')):
            execution.execute(self._data('q3'), events.append)
        self.assertEqual(events[-1]['type'], 'result')
        self.assertTrue(events[-1]['payload']['error'])
        self.assertEqual(events[-1]['payload']['reply'], execution.INTERNAL_ERROR_TEXT)

    def test_payload_carries_resolved_permissions_not_the_request(self):
        data = self._data()
        self.assertEqual(data['context']['connections'], CONNECTIONS)
        self.assertEqual(data['context']['language'], 'es')
        self.assertEqual(data['canvas'], CANVAS)


@override_settings(CACHES=SHARED_CACHES, LANGUAGE_CODE='es')
class RelayTests(SimpleTestCase):

    def test_result_from_the_worker(self):
        broker = FakeBroker()
        patches = broker.patches() + [mock.patch.object(agent, '_build_llm', return_value=None),
                                      mock.patch.object(agent, '_executor', side_effect=proposing_executor)]
        _start(patches)
        try:
            with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_CELERY_QUEUE', 'geocopilot', create=True):
                result = execution.wait_result(_context(), 'añade un filtro', [], CANVAS)
        finally:
            _stop(patches)
        self.assertIsNotNone(result['proposal'])
        sent = broker.sent[0]
        self.assertEqual(sent['queue'], 'geocopilot')
        self.assertTrue(broker.events_id.startswith('etl-'))
        self.assertEqual(sent['events_queue'], 'geocopilot.events.' + broker.events_id)
        self.assertTrue(broker.subscription.closed)

    def test_no_worker_answers_unavailable_and_cancels(self):
        broker = FakeBroker(worker=False)
        patches = broker.patches() + [mock.patch.object(execution, 'PICKUP_TIMEOUT_SECONDS', 0)]
        _start(patches)
        try:
            result = execution.wait_result(_context(), 'x', [], {})
        finally:
            _stop(patches)
        self.assertTrue(result['error'])
        self.assertEqual(result['reply'], execution.UNAVAILABLE_TEXT)
        self.assertTrue(cancellation.is_cancelled(broker.sent[0]['data']['query_id']))

    def test_worker_that_never_finishes_ends_in_timeout(self):
        broker = FakeBroker(events=[{'type': 'started'}])
        patches = broker.patches() + [
            mock.patch.object(execution, 'task_time_limits', return_value={'soft_time_limit': 0,
                                                                            'time_limit': -15})]
        _start(patches)
        try:
            events = list(execution.relay_events(_context(), 'x', [], {}))
        finally:
            _stop(patches)
        self.assertEqual([e['type'] for e in events], ['started', 'result'])
        self.assertEqual(events[-1]['payload']['reply'], execution.TIMEOUT_TEXT)
        self.assertTrue(cancellation.is_cancelled(broker.sent[0]['data']['query_id']))

    def test_pings_while_waiting(self):
        broker = FakeBroker(events=[{'type': 'started'}])
        original = broker.subscription.get
        calls = {'n': 0}

        def get(timeout):
            calls['n'] += 1
            if calls['n'] == 3:
                return {'type': 'result', 'payload': execution.error_result('fin')}
            return original(timeout)
        broker.subscription.get = get
        patches = broker.patches()
        _start(patches)
        try:
            events = list(execution.relay_events(_context(), 'x', [], {}))
        finally:
            _stop(patches)
        self.assertEqual([e['type'] for e in events], ['started', 'ping', 'result'])


@override_settings(CACHES=SHARED_CACHES, LANGUAGE_CODE='es')
class ViewTests(SimpleTestCase):
    """La vista devuelve el mismo JSON en inline y en celery."""

    def _post(self, mode):
        from gvsigol_plugin_geoetl.assistant import views
        request = RequestFactory().post('/gvsigonline/etl/etl_assistant/', data=json.dumps({
            'message': 'añade un filtro', 'history': [], 'canvas': CANVAS}), content_type='application/json')
        request.user = SimpleNamespace(id=7, username='ana', is_authenticated=True, is_staff=True,
                                       is_superuser=True)
        broker = FakeBroker()
        patches = broker.patches() + [
            mock.patch.object(views, 'assistant_feature_enabled', return_value=True),
            mock.patch('gvsigol_plugin_geoetl.views.get_etl_connections_list', return_value=CONNECTIONS),
            mock.patch.object(agent, '_build_llm', return_value=None),
            mock.patch.object(agent, '_executor', side_effect=proposing_executor),
            mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_EXECUTION', mode, create=True),
        ]
        _start(patches)
        try:
            response = views.etl_assistant(request)
        finally:
            _stop(patches)
        return json.loads(response.content), broker

    def test_same_json_inline_and_celery(self):
        inline, broker_inline = self._post('inline')
        celery, broker_celery = self._post('celery')
        self.assertEqual(broker_inline.sent, [])
        self.assertEqual(len(broker_celery.sent), 1)
        self.assertIsNotNone(inline['proposal'])
        self.assertEqual(inline, celery)
        self.assertEqual(broker_celery.sent[0]['data']['context']['connections'], CONNECTIONS)

    def test_broker_down_gives_the_usual_error(self):
        from gvsigol_plugin_geocopilot.services import event_bus
        with mock.patch.object(event_bus, 'subscribe', side_effect=OSError('sin RabbitMQ')):
            data, _ = self._post_without_broker()
        self.assertTrue(data['error'])
        self.assertIn('No se ha podido consultar', data['reply'])

    def _post_without_broker(self):
        from gvsigol_plugin_geoetl.assistant import views
        request = RequestFactory().post('/gvsigonline/etl/etl_assistant/', data=json.dumps({
            'message': 'hola'}), content_type='application/json')
        request.user = SimpleNamespace(id=7, username='ana', is_authenticated=True, is_staff=True,
                                       is_superuser=True)
        with mock.patch.object(views, 'assistant_feature_enabled', return_value=True), \
                mock.patch('gvsigol_plugin_geoetl.views.get_etl_connections_list', return_value=CONNECTIONS), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_EXECUTION', 'celery', create=True):
            response = views.etl_assistant(request)
        return json.loads(response.content), None
