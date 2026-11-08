# -*- coding: utf-8 -*-
"""Usabilidad, fase 5: sugerencias de siguiente paso por reglas y opciones para el arranque guiado."""
import json
from types import SimpleNamespace
from unittest import mock

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, views
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.assistant.next_steps import attach_next_steps, compute_steps

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]
NODES = {'n1': {}}


def issue(code, level='warning'):
    return {'code': code, 'level': level}


def _context(restricted=False):
    return AssistantContext.from_payload({'is_superuser': True, 'is_staff': True, 'connections': CONNECTIONS,
                                          'restricted': restricted, 'language': 'es'})


class RulesTests(SimpleTestCase):

    def test_empty_canvas(self):
        self.assertEqual(compute_steps({}, []), [])

    def test_clean_flow(self):
        self.assertEqual(compute_steps(NODES, []), ['explain', 'review'])

    def test_without_output(self):
        self.assertEqual(compute_steps(NODES, [issue('no_output'), issue('dead_end')]),
                         ['add_output', 'explain', 'review'])

    def test_restricted_edition_does_not_add_outputs(self):
        self.assertEqual(compute_steps(NODES, [issue('no_output')], restricted=True), ['explain', 'review'])

    def test_structure_problems_come_first(self):
        for code in ('unconnected_input', 'duplicated_input', 'cycle', 'kind_mismatch', 'bad_port'):
            with self.subTest(code=code):
                self.assertEqual(compute_steps(NODES, [issue(code, 'error'), issue('no_output')]), [])

    def test_configuration_errors_only_offer_the_review(self):
        self.assertEqual(compute_steps(NODES, [issue('missing_parameter', 'error')]), ['review'])
        self.assertEqual(compute_steps(NODES, [issue('unconfigured', 'error'), issue('no_output')]),
                         ['add_output', 'review'])


CANVAS = {'nodes': [{'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Csv', 'label': 'CSV',
                     'parameters': {'csv-file': 'file:///a.csv'}, 'schema': []}], 'edges': []}


class AttachTests(SimpleTestCase):

    def _attach(self, payload, flag=True, canvas=CANVAS, context=None):
        from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_NEXT_STEPS', flag, create=True):
            return attach_next_steps(payload, [], canvas, load_catalog(), context or _context())

    def test_off_by_default(self):
        self.assertNotIn('next_steps', self._attach({'reply': 'x'}, flag=False))

    def test_on(self):
        self.assertEqual(self._attach({'reply': 'x'})['next_steps'],
                         [{'code': 'add_output'}, {'code': 'explain'}, {'code': 'review'}])

    def test_not_while_waiting_for_the_user_or_after_an_error(self):
        for extra in ({'error': True}, {'needs_confirmation': True}, {'questions': [{'id': 'q1'}]}):
            with self.subTest(extra=extra):
                self.assertNotIn('next_steps', self._attach(dict(extra, reply='x')))

    def test_empty_canvas_has_no_steps(self):
        self.assertNotIn('next_steps', self._attach({'reply': 'x'}, canvas={'nodes': [], 'edges': []}))

    def test_a_failure_keeps_the_answer(self):
        with mock.patch('gvsigol_plugin_geoetl.assistant.next_steps.check_graph', side_effect=RuntimeError('x')):
            self.assertNotIn('next_steps', self._attach({'reply': 'x'}))


class Executor(object):
    def invoke(self, payload, config=None):
        return {'output': 'Hola.'}


@override_settings(LANGUAGE_CODE='es')
class RunTests(SimpleTestCase):

    def test_reaches_the_public_json(self):
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_NEXT_STEPS', True, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor', side_effect=lambda llm, tools, prompt: Executor()):
            result = agent.run_assistant(_context(), 'hola', [], CANVAS, None, None)
        self.assertEqual(views._public(result)['next_steps'][0], {'code': 'add_output'})

    def test_public_json_without_steps(self):
        self.assertNotIn('next_steps', views._public({'reply': 'x'}))


class EndpointTests(SimpleTestCase):

    def _post(self, picker, next_steps):
        request = RequestFactory().post('/o/', data=json.dumps({'type': 'output_Postgis', 'param': 'db-option'}),
                                        content_type='application/json')
        request.user = SimpleNamespace(id=7, username='ana', is_authenticated=True, is_staff=True, is_superuser=True)
        with mock.patch.object(views, 'assistant_feature_enabled', return_value=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_PARAM_PICKER', picker, create=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_NEXT_STEPS', next_steps, create=True), \
                mock.patch('gvsigol_plugin_geoetl.views.get_etl_connections_list', return_value=CONNECTIONS), \
                mock.patch('gvsigol_plugin_geoetl.assistant.context.usable_datastores', return_value=[
                    {'name': 'ds', 'description': '', 'workspace': 'ws', 'connection': 'gis', 'schema': 's'}]):
            return views.etl_assistant_options(request)

    def test_options_for_the_guided_start(self):
        data = json.loads(self._post(False, True).content)
        self.assertEqual(data['options'][0]['params'], {'db-option': 'gis', 'schema-name-option': 's'})
        self.assertTrue(data['create_datastore'])

    def test_closed_with_both_flags_off(self):
        with self.assertRaises(Http404):
            self._post(False, False)

    def test_template_context_has_the_flag(self):
        from gvsigol_plugin_geoetl import views as editor_views
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_NEXT_STEPS', True, create=True):
            self.assertTrue(editor_views._ctx()['etl_assistant_next_steps'])
