import itertools
import json
import os
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from gvsigol_plugin_geoetl import views  # antes que tasks: tasks y views se importan entre sí
from gvsigol_plugin_geoetl import etl_cancel, etl_tasks, models, tasks


class _Row(SimpleNamespace):
    def save(self, update_fields=None):
        pass

    def refresh_from_db(self, fields=None):
        pass


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def exists(self):
        return bool(self.rows)

    def update(self, **values):
        for row in self.rows:
            for key, value in values.items():
                setattr(row, key, value)
        return len(self.rows)


class _Manager:
    """Lo justo del ORM de ETLstatus que usan el motor y la parada."""

    def __init__(self):
        self.rows = []
        self._ids = itertools.count(1)

    def create(self, **values):
        base = {'status': '', 'message': '', 'id_ws': None, 'celery_task_id': '', 'visualizer_session_id': None}
        base.update(values)
        row = _Row(pk=next(self._ids), **base)
        self.rows.append(row)
        return row

    def filter(self, **criteria):
        return _Query([r for r in self.rows if all(getattr(r, k, None) == v for k, v in criteria.items())])

    def all(self):
        return list(self.rows)

    def get(self, **criteria):
        return self.filter(**criteria).first()

    def get_or_create(self, defaults=None, **criteria):
        row = self.filter(**criteria).first()
        if row:
            return row, False
        return self.create(**criteria, **(defaults or {})), True

    def update_or_create(self, defaults=None, **criteria):
        row, created = self.get_or_create(defaults=defaults, **criteria)
        if not created:
            _Query([row]).update(**(defaults or {}))
        return row, created


class _StatusTestCase(SimpleTestCase):

    def setUp(self):
        self.status = _Manager()
        fake_model = SimpleNamespace(objects=self.status)
        for target in (models, tasks, views):
            patcher = mock.patch.object(target, 'ETLstatus', fake_model)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(etl_cancel.end)

    def row(self, username='ana'):
        return self.status.filter(name='current_canvas.' + username).first()


def _node(node_type, node_id):
    return {'type': node_type, 'id': node_id, 'entities': [{'parameters': [{}]}], 'ports': []}


def _run(canvas, task=None):
    tasks._run_canvas_background_impl({
        'jsonCanvas': canvas, 'id_ws': None, 'username': 'ana',
        'parameters': None, 'concat': False,
    }, task=task)


class RequestStopTests(_StatusTestCase):

    @mock.patch.object(etl_cancel, 'cancel_queries', return_value=0)
    def test_running_becomes_stopping(self, cancel):
        sm = self.status.create(name='current_canvas.ana', status='Running')
        self.assertTrue(etl_cancel.request_stop(sm))
        self.assertEqual(sm.status, etl_cancel.STOPPING)
        cancel.assert_called_once_with(sm.pk)

    @mock.patch.object(etl_cancel, 'cancel_queries', return_value=0)
    def test_finished_run_is_not_touched(self, cancel):
        sm = self.status.create(name='current_canvas.ana', status='Success')
        self.assertFalse(etl_cancel.request_stop(sm))
        self.assertEqual(sm.status, 'Success')
        cancel.assert_not_called()


class CheckTests(_StatusTestCase):

    def test_check_raises_only_when_stopping(self):
        sm = self.status.create(name='current_canvas.ana', status='Running')
        etl_cancel.begin(sm.pk)
        etl_cancel.check(force=True)
        sm.status = etl_cancel.STOPPING
        with self.assertRaises(etl_cancel.EtlCancelled):
            etl_cancel.check(force=True)

    def test_check_without_force_is_throttled(self):
        sm = self.status.create(name='current_canvas.ana', status='Running')
        etl_cancel.begin(sm.pk)
        etl_cancel.check(force=True)
        sm.status = etl_cancel.STOPPING
        etl_cancel.check()

    def test_check_outside_a_run_does_nothing(self):
        etl_cancel.check(force=True)

    def test_begin_labels_connections_and_end_restores(self):
        previous = os.environ.get('PGAPPNAME')
        etl_cancel.begin(42)
        self.assertEqual(os.environ['PGAPPNAME'], 'geoetl-run-42')
        self.assertEqual(etl_cancel.current_app_name(), 'geoetl-run-42')
        etl_cancel.end()
        self.assertEqual(os.environ.get('PGAPPNAME'), previous)
        self.assertIsNone(etl_cancel.current_app_name())


@mock.patch.object(tasks, 'delete_tables')
class EngineTests(_StatusTestCase):

    def _stop(self):
        self.row().status = etl_cancel.STOPPING

    def test_stop_between_nodes_skips_the_rest(self, delete_tables):
        calls = []

        def node(params):
            calls.append(params['id'])
            self._stop()
            return ['t_' + params['id']]
        with mock.patch.object(etl_tasks, 'input_StopA', node, create=True), \
                mock.patch.object(etl_tasks, 'input_StopB', node, create=True):
            _run([_node('input_StopA', 'a'), _node('input_StopB', 'b')])
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.row().status, etl_cancel.CANCELLED)
        self.assertEqual(self.row().message, etl_cancel.CANCELLED_MESSAGE)
        delete_tables.assert_called_once()

    def test_cancelled_query_counts_as_stop_not_error(self, delete_tables):
        def cancelled(params):
            self._stop()
            raise RuntimeError('canceling statement due to user request')
        with mock.patch.object(etl_tasks, 'input_StopA', cancelled, create=True):
            _run([_node('input_StopA', 'a')])
        self.assertEqual(self.row().status, etl_cancel.CANCELLED)

    def test_real_error_is_still_error(self, delete_tables):
        def broken(params):
            raise RuntimeError('boom')
        with mock.patch.object(etl_tasks, 'input_StopA', broken, create=True):
            _run([_node('input_StopA', 'a')])
        self.assertEqual(self.row().status, 'Error')
        self.assertIn('boom', self.row().message)

    def test_run_without_stop_succeeds(self, delete_tables):
        with mock.patch.object(etl_tasks, 'input_StopA', mock.Mock(return_value=['t1']), create=True):
            _run([_node('input_StopA', 'a')])
        self.assertEqual(self.row().status, 'Success')

    def test_stopped_while_queued_never_starts(self, delete_tables):
        self.status.create(name='current_canvas.ana', status=etl_cancel.STOPPING, celery_task_id='abc')
        node = mock.Mock(return_value=['t1'])
        task = mock.Mock()
        task.request.id = 'abc'
        with mock.patch.object(etl_tasks, 'input_StopA', node, create=True):
            _run([_node('input_StopA', 'a')], task=task)
        node.assert_not_called()
        self.assertEqual(self.row().status, etl_cancel.CANCELLED)

    def test_old_stopping_does_not_block_a_new_run(self, delete_tables):
        self.status.create(name='current_canvas.ana', status=etl_cancel.STOPPING, celery_task_id='old')
        node = mock.Mock(return_value=['t1'])
        task = mock.Mock()
        task.request.id = 'new'
        with mock.patch.object(etl_tasks, 'input_StopA', node, create=True):
            _run([_node('input_StopA', 'a')], task=task)
        node.assert_called_once()
        self.assertEqual(self.row().status, 'Success')


@mock.patch.object(etl_cancel, 'cancel_queries', return_value=1)
class StopViewTests(_StatusTestCase):

    def _post(self, data=None):
        request = RequestFactory().post('/gvsigonline/etl/etl_stop_canvas/', data or {})
        request.user = SimpleNamespace(username='ana', is_authenticated=True, is_staff=True, is_superuser=True)
        return views.etl_stop_canvas(request)

    def test_stops_the_users_unsaved_canvas(self, cancel):
        self.status.create(name='current_canvas.ana', status='Running')
        response = self._post()
        self.assertEqual(json.loads(response.content), {'stopped': True, 'status': etl_cancel.STOPPING})

    def test_nothing_running(self, cancel):
        response = self._post()
        self.assertFalse(json.loads(response.content)['stopped'])
        cancel.assert_not_called()

    def test_unknown_workspace(self, cancel):
        workspaces = mock.Mock()
        workspaces.DoesNotExist = type('DoesNotExist', (Exception,), {})
        workspaces.objects.get.side_effect = workspaces.DoesNotExist
        with mock.patch.object(views, 'ETLworkspaces', workspaces):
            response = self._post({'id_ws': '999'})
        self.assertEqual(response.status_code, 404)

    def test_workspace_without_permission(self, cancel):
        ws = mock.Mock(id=5)
        ws.can_execute.return_value = ws.can_edit.return_value = ws.can_edit_restrictedly.return_value = False
        workspaces = mock.Mock()
        workspaces.objects.get.return_value = ws
        self.status.create(name='flujo', id_ws=5, status='Running')
        with mock.patch.object(views, 'ETLworkspaces', workspaces):
            response = self._post({'id_ws': '5'})
        self.assertEqual(response.status_code, 403)
        cancel.assert_not_called()
