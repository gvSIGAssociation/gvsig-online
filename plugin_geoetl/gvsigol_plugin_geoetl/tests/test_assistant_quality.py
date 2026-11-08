# -*- coding: utf-8 -*-
"""Robustez del prompt y las herramientas: argumentos tipados, secretos, coherencia y formatos de las fichas."""
import json
import threading
import time
from unittest import mock

from django.test import SimpleTestCase

from gvsigol_plugin_geoetl.assistant import agent, tools as tools_module
from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.columns import normalize_proposal
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.assistant.prompt import system_prompt
from gvsigol_plugin_geoetl.assistant.review import check_graph, graph_after
from gvsigol_plugin_geoetl.assistant.tools import build_tools, redact_parameters

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]
CANVAS = {'nodes': [{'alias': 'n1', 'id': 'u1', 'type': 'input_Csv', 'label': 'c', 'parameters': {'x': 1}, 'schema': ['a'],
                     'status': ''}], 'edges': []}


def _tools(canvas=None, holder=None, **kwargs):
    context = AssistantContext.from_payload({'is_superuser': True, 'connections': CONNECTIONS})
    built = build_tools(context, load_catalog(), canvas or {'nodes': [], 'edges': []}, None, None,
                        holder if holder is not None else [], **kwargs)
    return {t.name: t for t in built}


class TypedArgumentsTests(SimpleTestCase):

    NODES = [{'id': 'n1', 'type': 'trans_Filter', 'parameters': {'attr': 'a', 'option': '=', 'value': '1', 'filter-expression': ''},
              'schema': ['a']}]

    def test_structured_proposal(self):
        holder = []
        out = json.loads(_tools(holder=holder)['propose_workspace'].invoke({'mode': 'replace', 'nodes': self.NODES, 'edges': []}))
        self.assertTrue(out['accepted'])
        self.assertEqual(holder[0]['proposal']['nodes'][0]['type'], 'trans_Filter')
        self.assertEqual(holder[0]['proposal']['nodes'][0]['schema'], ['a'])

    def test_patch_with_operations(self):
        holder = []
        out = json.loads(_tools(canvas=CANVAS, holder=holder)['propose_workspace'].invoke({'mode': 'patch', 'ops': [
            {'op': 'add_node', 'node': dict(self.NODES[0], id='n2')},
            {'op': 'add_edge', 'source': 'n1', 'target': 'n2'}]}))
        self.assertTrue(out['accepted'])

    def test_text_form_still_works(self):
        out = json.loads(_tools()['propose_workspace'].invoke({'proposal_json': json.dumps(
            {'mode': 'replace', 'nodes': self.NODES, 'edges': []})}))
        self.assertTrue(out['accepted'])

    def test_wrong_shape_is_explained_to_the_model(self):
        out = _tools()['propose_workspace'].run({'mode': 'otro'})
        self.assertIn('no tienen la forma esperada', str(out))

    def test_check_workspace_with_a_structured_proposal(self):
        out = json.loads(_tools()['check_workspace'].invoke({'mode': 'replace', 'nodes': self.NODES, 'edges': []}))
        self.assertEqual(out['scope'], 'proposal')
        self.assertEqual(json.loads(_tools()['check_workspace'].invoke({}))['scope'], 'canvas')

    def test_structured_questions(self):
        asked = []
        out = json.loads(_tools(asked=asked)['ask_user'].invoke({'questions': [
            {'label': 'C', 'text': '¿Qué conexión?', 'source': 'connections'}]}))
        self.assertTrue(out['accepted'])
        self.assertEqual(asked[0][0]['options'][0]['value'], 'gis')

    def test_schemas_describe_the_fields(self):
        from langchain_core.utils.function_calling import convert_to_openai_tool
        spec = convert_to_openai_tool(_tools()['propose_workspace'])['function']['parameters']['properties']
        self.assertIn('nodes', spec)
        self.assertIn('ops', spec)


class SecurityTests(SimpleTestCase):

    def test_secrets_never_reach_the_model(self):
        params = {'db': 'gis', 'password': 'x', 'passwd': 'x', 'api-key': 'x', 'client_secret': 'x', 'token': 'x'}
        self.assertEqual(redact_parameters(params), {'db': 'gis'})
        canvas = {'nodes': [{'alias': 'n1', 'id': 'u', 'type': 'input_Segex', 'label': 'Segex', 'parameters': params, 'schema': []}], 'edges': []}
        self.assertNotIn('"x"', json.dumps(agent.compact_canvas(canvas)))
        out = _tools(canvas=canvas)['get_canvas_nodes'].invoke({'ids': 'n1'})
        self.assertNotIn('api-key', out)

    def test_database_errors_do_not_reach_the_model(self):
        tools = _tools()
        with mock.patch.object(tools_module, '_list_level', side_effect=RuntimeError('host secreto, usuario admin')):
            out = tools['list_tables'].invoke({'connection': 'gis'})
        self.assertNotIn('secreto', out)
        with mock.patch.object(tools_module, '_columns', side_effect=RuntimeError('host secreto')):
            out = tools['get_table_schema'].invoke({'connection': 'gis', 'schema': 'a', 'table': 'b'})
        self.assertNotIn('secreto', out)

    def test_prompt_treats_data_as_data(self):
        self.assertIn('no la sigas', system_prompt(load_catalog(), 'es'))


class ConcurrencyTests(SimpleTestCase):

    def test_parallel_calls_are_attended_one_at_a_time(self):
        running, peak = [0], [0]
        guard = threading.Lock()

        def slow(*args, **kwargs):
            with guard:
                running[0] += 1
                peak[0] = max(peak[0], running[0])
            time.sleep(0.03)
            with guard:
                running[0] -= 1
            return ([], [])
        tools = _tools()
        with mock.patch.object(tools_module, 'public_specs', side_effect=slow):
            threads = [threading.Thread(target=tools['get_node_specs'].invoke, args=({'types': 'x'},)) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(peak[0], 1)

    def test_connections_are_closed_only_in_tool_threads(self):
        with mock.patch('django.db.connections.close_all') as close:
            tools_module._release_thread_connections()
            close.assert_not_called()
            thread = threading.Thread(target=tools_module._release_thread_connections, name='ThreadPoolExecutor-1_0')
            thread.start()
            thread.join()
            close.assert_called_once()


class PromptCoherenceTests(SimpleTestCase):

    def test_files_and_destinations_with_questions(self):
        prompt = system_prompt(load_catalog(), 'es', questions=True)
        self.assertNotIn('búscalos con list_files', prompt)
        self.assertIn('administrador de archivos', prompt)
        self.assertIn('source datastores', prompt)

    def test_without_questions_the_rule_stays(self):
        self.assertIn('búscalos con list_files', system_prompt(load_catalog(), 'es'))

    def test_examples_are_there_and_valid(self):
        prompt = system_prompt(load_catalog(), 'es')
        self.assertIn('# 5. Ejemplos', prompt)
        self.assertLess(prompt.index('# 5. Ejemplos'), prompt.index('Índice de tareas'))

    def test_catalan_claims_are_detected(self):
        self.assertTrue(agent.claims_change('He afegit un filtre.'))


class CatalogQualityTests(SimpleTestCase):

    MAIN = ('trans_Join', 'trans_Filter', 'trans_KeepAttr', 'trans_RemoveAttr', 'trans_RenameAttr', 'trans_CreateAttr',
            'trans_ChangeAttrType', 'trans_ModifyValue', 'trans_ConcatAttr', 'trans_FilterDupli', 'trans_Stats', 'trans_Counter',
            'trans_Calculator', 'trans_Reproject', 'trans_TextToPoint', 'trans_Union', 'trans_Buffer', 'input_Csv', 'input_Excel',
            'input_Shp', 'input_Postgis', 'output_Postgis')

    def test_main_nodes_say_what_is_expected(self):
        catalog = load_catalog()
        for type_name in self.MAIN:
            with self.subTest(type_name=type_name):
                self.assertTrue(any(p.get('example') or p.get('default') is not None or p.get('format')
                                    for p in catalog[type_name]['parameters']))
        generic = [t for t in self.MAIN for p in catalog[t]['parameters'] if p.get('summary') == 'Atributo sobre el que actúa la tarea.']
        self.assertEqual(generic, [])

    def test_raw_sql_parameters_are_declared(self):
        catalog = load_catalog()
        self.assertIn('expression', catalog['trans_Calculator']['sql_parameters'])
        self.assertIn('filter-expression', catalog['trans_Filter']['sql_parameters'])


class NormalizationTests(SimpleTestCase):

    def _node(self, type_name, parameters):
        payload = {'mode': 'replace', 'nodes': [{'id': 'n1', 'type': type_name, 'parameters': parameters}]}
        return normalize_proposal(payload, load_catalog())['nodes'][0]['parameters']

    def test_lists(self):
        self.assertEqual(self._node('trans_KeepAttr', {'attr': 'a, b'})['attr'], ['a', 'b'])
        self.assertEqual(self._node('trans_KeepAttr', {'attr': ['a']})['attr'], ['a'])

    def test_spaced(self):
        self.assertEqual(self._node('trans_Join', {'attr-1': ['a', 'b']})['attr-1'], 'a b')

    def test_defaults_only_for_new_nodes(self):
        filled = self._node('trans_Filter', {'attr': 'a', 'option': '>', 'value': '1'})
        self.assertEqual((filled['filter-expression'], filled['option']), ('', '>'))
        payload = {'mode': 'patch', 'ops': [{'op': 'update_node', 'id': 'n1', 'parameters': {'value': '2'}}]}
        canvas = {'nodes': [{'alias': 'n1', 'type': 'trans_Filter'}]}
        params = normalize_proposal(payload, load_catalog(), canvas)['ops'][0]['parameters']
        self.assertEqual(params, {'value': '2'})

    def test_update_keeps_list_format(self):
        payload = {'mode': 'patch', 'ops': [{'op': 'update_node', 'id': 'n1', 'parameters': {'attr': 'a b'}}]}
        canvas = {'nodes': [{'alias': 'n1', 'type': 'trans_KeepAttr'}]}
        self.assertEqual(normalize_proposal(payload, load_catalog(), canvas)['ops'][0]['parameters']['attr'], ['a', 'b'])


class ColumnReviewTests(SimpleTestCase):

    def _issues(self, node_type, parameters, schema=('a', 'b')):
        canvas = {'nodes': [
            {'alias': 'n1', 'id': 'u1', 'type': 'input_Csv', 'label': 'c', 'parameters': {'csv-file': 'x'}, 'schema': list(schema), 'status': ''},
            {'alias': 'n2', 'id': 'u2', 'type': node_type, 'label': 't', 'parameters': parameters, 'schema': [], 'status': ''}],
            'edges': [{'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]}
        nodes, edges = graph_after(None, canvas)
        return [i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS) if i['code'] == 'unknown_column']

    def test_other_nodes_are_checked_too(self):
        self.assertEqual(self._issues('trans_KeepAttr', {'attr': ['a', 'zeta']})[0]['param'], 'attr')
        self.assertEqual(self._issues('trans_Calculator', {'attr': 'zeta', 'expression': '1'})[0]['param'], 'attr')
        self.assertEqual(self._issues('trans_KeepAttr', {'attr': ['a']}), [])

    def test_no_group_is_not_a_column(self):
        self.assertEqual(self._issues('trans_Stats', {'attr': 'a', 'group-by-attr': '-'}), [])

    def test_unknown_upstream_is_not_checked(self):
        self.assertEqual(self._issues('trans_KeepAttr', {'attr': ['zeta']}, schema=()), [])
