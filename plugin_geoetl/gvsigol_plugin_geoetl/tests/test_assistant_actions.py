# -*- coding: utf-8 -*-
"""Usabilidad, fase 1: problemas del flujo estructurados para los botones Configurar / Arreglar del panel."""
import json
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent
from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.assistant.review import check_graph, graph_from_canvas

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]
GOOD_PATCH = json.dumps({'mode': 'patch', 'ops': [
    {'op': 'add_node', 'node': {'id': 'n2', 'type': 'trans_Filter', 'parameters': {}}},
    {'op': 'add_edge', 'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]})


def node(alias, type_name, parameters=None, status=''):
    return {'alias': alias, 'id': 'uuid-' + alias, 'type': type_name, 'label': type_name,
            'parameters': parameters if parameters is not None else {'x': 1}, 'schema': [], 'status': status}


CANVAS = {'nodes': [node('n1', 'input_Postgis'), node('n2', 'trans_Filter', status='unconfigured')], 'edges': []}


class ScriptedExecutor(object):
    """Llama a las herramientas indicadas y responde con un texto."""

    def __init__(self, tools, calls, output='Hecho.'):
        self.tools = {t.name: t for t in tools}
        self.calls = calls
        self.output = output

    def invoke(self, payload, config=None):
        for name, args in self.calls:
            self.tools[name].invoke(args)
        return {'output': self.output}


@override_settings(LANGUAGE_CODE='es')
class IssuesTests(SimpleTestCase):

    def _run(self, calls, actions=True, canvas=CANVAS):
        context = AssistantContext.from_payload({'is_superuser': True, 'connections': CONNECTIONS})
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ACTIONS', actions, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor',
                                  side_effect=lambda llm, tools, prompt: ScriptedExecutor(tools, calls)):
            return agent.run_assistant(context, 'revisa', [], canvas, None, None)

    def test_off_by_default_the_response_does_not_change(self):
        result = self._run([('check_workspace', {})], actions=False)
        self.assertNotIn('issues', result)

    def test_review_of_the_canvas(self):
        result = self._run([('check_workspace', {})])
        codes = [(i['node'], i['code']) for i in result['issues']]
        self.assertIn(('n2', 'unconfigured'), codes)
        self.assertIn(('n2', 'unconnected_input'), codes)
        levels = [i['level'] for i in result['issues']]
        self.assertEqual(levels, sorted(levels, key=lambda level: 0 if level == 'error' else 1))  # errores primero
        json.dumps(result)

    def test_review_of_a_proposal_is_not_shown(self):
        result = self._run([('check_workspace', {'proposal_json': GOOD_PATCH})])
        self.assertNotIn('issues', result)

    def test_without_review_nor_proposal(self):
        result = self._run([('list_connections', {})])
        self.assertNotIn('issues', result)

    def test_with_a_proposal_the_flow_as_it_will_be(self):
        canvas = {'nodes': [node('n1', 'input_Postgis')], 'edges': []}
        result = self._run([('propose_workspace', {'proposal_json': GOOD_PATCH})], canvas=canvas)
        self.assertIsNotNone(result['proposal'])
        codes = [(i['node'], i['code']) for i in result['issues']]
        # los del flujo tal como quedará: la conexión n1 → n2 ya viene en la propuesta
        self.assertIn(('n1', 'missing_parameter'), codes)
        self.assertIn(('n2', 'dead_end'), codes)
        self.assertIn((None, 'no_output'), codes)
        self.assertNotIn('unconnected_input', [c for _, c in codes])
        missing = [i for i in result['issues'] if i['code'] == 'missing_parameter'][0]
        self.assertTrue(missing['param'])

    def test_a_failure_preparing_issues_keeps_the_answer(self):
        with mock.patch('gvsigol_plugin_geoetl.assistant.review.graph_after', side_effect=RuntimeError('x')):
            result = self._run([('propose_workspace', {'proposal_json': GOOD_PATCH})],
                               canvas={'nodes': [node('n1', 'input_Postgis')], 'edges': []})
        self.assertIsNotNone(result['proposal'])
        self.assertNotIn('issues', result)


class ParamFieldTests(SimpleTestCase):

    def test_param_only_in_parameter_issues(self):
        catalog = load_catalog()
        canvas = {'nodes': [node('n1', 'input_Csv', {'separator': '|'})], 'edges': []}
        nodes, edges = graph_from_canvas(canvas)
        issues = check_graph(nodes, edges, catalog, CONNECTIONS)
        by_code = {i['code']: i for i in issues}
        self.assertEqual(by_code['missing_parameter']['param'], 'csv-file')
        self.assertEqual(by_code['invalid_choice']['param'], 'separator')
        self.assertNotIn('param', by_code['no_output'])


class PublicJsonTests(SimpleTestCase):

    def test_issues_only_when_present(self):
        from gvsigol_plugin_geoetl.assistant.views import _public
        self.assertNotIn('issues', _public({'reply': 'x'}))
        issues = [{'level': 'error', 'node': 'n2', 'code': 'unconfigured', 'message': 'm'}]
        self.assertEqual(_public({'reply': 'x', 'issues': issues})['issues'], issues)
