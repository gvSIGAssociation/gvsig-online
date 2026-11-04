# -*- coding: utf-8 -*-
"""Asistente: revisión de flujos, herramientas nuevas, canvas compacto y bucle del agente (modelo simulado)."""
import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl.assistant import agent
from gvsigol_plugin_geoetl.assistant.catalog import first_sentence, index_lines, load_catalog
from gvsigol_plugin_geoetl.assistant.graph import validate_proposal
from gvsigol_plugin_geoetl.assistant.review import check_graph, graph_after, graph_from_canvas
from gvsigol_plugin_geoetl.assistant.tools import build_tools

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]


def canvas_node(alias, type_name, parameters=None, x=None, y=None, status=None):
    return {'alias': alias, 'id': 'uuid-' + alias, 'type': type_name, 'label': type_name,
            'parameters': parameters if parameters is not None else {'x': 1}, 'schema': [],
            'x': x, 'y': y, 'status': status}


def codes(issues, node=None):
    return sorted(i['code'] for i in issues if node is None or i['node'] == node)


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def check(self, nodes, edges):
        canvas = {'nodes': nodes, 'edges': edges}
        n, e = graph_from_canvas(canvas)
        return check_graph(n, e, self.catalog, CONNECTIONS)

    def test_complete_flow_has_no_errors(self):
        issues = self.check(
            [canvas_node('n1', 'input_Postgis', {'db': 'gis', 'schema-name': 's', 'table-name': 't'}),
             canvas_node('n2', 'output_Postgis', {'db': 'gis', 'schema-name': 's', 'tablename': 'r'})],
            [{'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}])
        self.assertEqual([i for i in issues if i['level'] == 'error'
                          and i['code'] not in ('missing_parameter',)], [])

    def test_unconnected_input_unconfigured_and_no_output(self):
        issues = self.check([canvas_node('n1', 'trans_Join', {}), canvas_node('n2', 'trans_Filter', status='unconfigured')], [])
        self.assertIn('unconnected_input', codes(issues, 'n1'))
        self.assertIn('unconfigured', codes(issues, 'n1'))           # sin parámetros = rueda roja
        self.assertIn('unconfigured', codes(issues, 'n2'))
        self.assertIn('no_output', codes(issues))

    def test_kind_mismatch_duplicated_input_and_cycle(self):
        nodes = [canvas_node('n1', 'input_Raster'), canvas_node('n2', 'trans_Filter'),
                 canvas_node('n3', 'trans_Filter'), canvas_node('n4', 'trans_Filter')]
        edges = [{'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0},   # ráster → tabla
                 {'source': 'n3', 'target': 'n4', 'source_port': 0, 'target_port': 0},
                 {'source': 'n4', 'target': 'n3', 'source_port': 0, 'target_port': 0},
                 {'source': 'n2', 'target': 'n4', 'source_port': 0, 'target_port': 0}]
        issues = self.check(nodes, edges)
        self.assertIn('kind_mismatch', codes(issues, 'n2'))
        self.assertIn('duplicated_input', codes(issues, 'n4'))
        self.assertIn('cycle', codes(issues))

    def test_optional_ports_and_unknown_connection(self):
        nodes = [canvas_node('n1', 'input_Raster'), canvas_node('n2', 'input_Raster'),
                 canvas_node('n3', 'trans_RasterStack'), canvas_node('n4', 'input_Postgis', {'db': 'otra'})]
        edges = [{'source': 'n1', 'target': 'n3', 'source_port': 0, 'target_port': 0},
                 {'source': 'n2', 'target': 'n3', 'source_port': 0, 'target_port': 1}]
        issues = self.check(nodes, edges)
        self.assertNotIn('unconnected_input', codes(issues, 'n3'))   # Raster 3 y 4 son opcionales
        self.assertIn('unknown_connection', codes(issues, 'n4'))

    def test_graph_after_patch_applies_ops(self):
        canvas = {'nodes': [canvas_node('n1', 'input_Postgis'), canvas_node('n2', 'output_Postgis')],
                  'edges': [{'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]}
        payload = {'mode': 'patch', 'ops': [
            {'op': 'remove_edge', 'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0},
            {'op': 'add_node', 'node': {'id': 'n3', 'type': 'trans_Filter', 'parameters': {}}},
            {'op': 'add_edge', 'source': 'n1', 'target': 'n3', 'source_port': 0, 'target_port': 0},
            {'op': 'add_edge', 'source': 'n3', 'target': 'n2', 'source_port': 0, 'target_port': 0}]}
        result = validate_proposal(payload, self.catalog, CONNECTIONS, canvas=canvas)
        nodes, edges = graph_after(result['proposal'], canvas)
        self.assertEqual(sorted(nodes), ['n1', 'n2', 'n3'])
        self.assertEqual(sorted((e['source'], e['target']) for e in edges), [('n1', 'n3'), ('n3', 'n2')])


class LayoutTests(unittest.TestCase):
    def test_inserted_node_goes_next_to_its_source_without_overlapping(self):
        catalog = load_catalog()
        canvas = {'nodes': [canvas_node('n1', 'input_Postgis', x=100, y=100),
                            canvas_node('n2', 'output_Postgis', x=380, y=100)],
                  'edges': [{'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]}
        payload = {'mode': 'patch', 'ops': [
            {'op': 'add_node', 'node': {'id': 'n3', 'type': 'trans_Filter', 'parameters': {}}},
            {'op': 'add_node', 'node': {'id': 'n4', 'type': 'trans_Filter', 'parameters': {}}},
            {'op': 'add_edge', 'source': 'n1', 'target': 'n3', 'source_port': 0, 'target_port': 0},
            {'op': 'add_edge', 'source': 'n3', 'target': 'n4', 'source_port': 0, 'target_port': 0}]}
        ops = validate_proposal(payload, catalog, CONNECTIONS, canvas=canvas)['proposal']['ops']
        added = {op['node']['id']: op['node'] for op in ops if op['op'] == 'add_node'}
        self.assertEqual(added['n3']['x'], 380)                          # a la derecha de n1
        self.assertNotEqual(added['n3']['y'], 100)                       # bajado: n2 ocupa ese sitio
        self.assertEqual(added['n4']['x'], 660)                          # sigue la cadena
        boxes = [(100, 100), (380, 100)] + [(n['x'], n['y']) for n in added.values()]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertFalse(abs(a[0] - b[0]) < 240 and abs(a[1] - b[1]) < 140, (a, b))


class CanvasForPromptTests(unittest.TestCase):
    def test_compact_canvas_is_always_valid_json_within_budget(self):
        nodes = [canvas_node('n%d' % i, 'trans_Filter', {'sql': 'x' * 2000, 'empty': ''}) for i in range(1, 40)]
        for node in nodes:
            node['schema'] = ['col_%d' % k for k in range(200)]
        canvas = {'nodes': nodes, 'edges': []}
        for budget in (1000000, 60000, 20000, 500):
            out = agent.compact_canvas(canvas, budget=budget)
            text = json.dumps({'nodes': out['nodes'], 'edges': out['edges']})
            json.loads(text)
            self.assertEqual(len(out['nodes']), 39)                       # nunca se pierden nodos
            self.assertNotIn('empty', json.dumps(out['nodes']))           # valores vacíos fuera
        self.assertIn('schema', agent.compact_canvas(canvas, budget=10 ** 7)['nodes'][0])
        self.assertTrue(agent.compact_canvas(canvas, budget=500)['parameters_omitted'])

    def test_next_free_alias_and_user_input(self):
        canvas = {'nodes': [canvas_node('n2', 'trans_Filter'), canvas_node('n9', 'trans_Filter')],
                  'edges': [], 'selected': 'n2', 'next_alias': 'n12'}
        self.assertEqual(agent.next_free_alias(canvas), 'n12')            # el editor no reutiliza ids borrados
        self.assertEqual(agent.next_free_alias({'nodes': []}), 'n1')
        text = agent._user_input('hola', canvas)
        self.assertIn('Nodo seleccionado: n2.', text)
        self.assertIn('Siguiente id libre para tareas nuevas: n12.', text)
        json.loads(text.split('Canvas actual:\n', 1)[1])

    def test_history_carries_proposal_outcome(self):
        msgs = agent._history([
            {'role': 'user', 'content': 'añade un filtro'},
            {'role': 'assistant', 'content': 'Hecho.', 'summary': ['Añado Filter (n3).'], 'status': 'discarded'},
            {'role': 'assistant', 'content': '', 'summary': [], 'status': 'applied'},   # vacío: se omite
        ])
        self.assertEqual(len(msgs), 2)
        self.assertIn('Añado Filter (n3).', msgs[1].content)
        self.assertIn('descartó', msgs[1].content)

    def test_index_uses_first_sentence(self):
        self.assertEqual(first_sentence('Uno dos. Tres cuatro.'), 'Uno dos.')
        line = [item for item in index_lines(load_catalog()) if item.startswith('trans_RasterIndex ')][0]
        self.assertLess(len(line), 220)

    def test_claims_and_limit_detection(self):
        self.assertTrue(agent.claims_change('He añadido un filtro después de n3.'))
        self.assertTrue(agent.claims_change("I've added a filter."))
        self.assertFalse(agent.claims_change('n2 filtra las filas y n3 las guarda.'))
        self.assertTrue(agent.hit_iteration_limit('Agent stopped due to max iterations.'))


class FakeExecutor(object):
    """Simula el AgentExecutor: cada invoke ejecuta un guion de llamadas a herramientas y devuelve un texto."""

    def __init__(self, tools, scripts):
        self.tools = {t.name: t for t in tools}
        self.scripts = list(scripts)
        self.inputs = []

    def invoke(self, payload):
        self.inputs.append(payload)
        script = self.scripts.pop(0)
        if isinstance(script, Exception):
            raise script
        calls, output = script
        for name, args in calls:
            self.tools[name].invoke(args)
        return {'output': output}


GOOD_PATCH = json.dumps({'mode': 'patch', 'ops': [
    {'op': 'add_node', 'node': {'id': 'n2', 'type': 'trans_Filter', 'parameters': {}}},
    {'op': 'add_edge', 'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]})


@override_settings(LANGUAGE_CODE='es')
class AgentLoopTests(SimpleTestCase):
    canvas = {'nodes': [canvas_node('n1', 'input_Postgis', x=100, y=100)], 'edges': []}

    def run_with(self, scripts, history=None):
        made = {}

        def fake_executor(llm, tools, prompt):
            made['executor'] = FakeExecutor(tools, scripts)
            return made['executor']
        request = SimpleNamespace(user=SimpleNamespace(is_superuser=True, is_staff=True))
        with mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor', side_effect=fake_executor):
            result = agent.run_assistant(request, 'añade un filtro', history or [], self.canvas, False, CONNECTIONS)
        return result, made['executor']

    def test_claim_without_proposal_is_retried_and_fixed(self):
        result, executor = self.run_with([
            ([], 'He añadido un filtro después de n1.'),
            ([('propose_workspace', {'proposal_json': GOOD_PATCH})], 'Listo: filtro añadido.'),
        ])
        self.assertIsNotNone(result['proposal'])
        self.assertEqual(result['reply'], 'Listo: filtro añadido.')
        self.assertIn('propose_workspace', executor.inputs[1]['input'])

    def test_claim_confirmed_as_no_change_keeps_reply(self):
        result, _ = self.run_with([([], 'He añadido... no, solo explico: n1 lee la tabla.'), ([], 'SIN_CAMBIOS')])
        self.assertIsNone(result['proposal'])
        self.assertEqual(result['warnings'], [])
        self.assertIn('n1 lee la tabla', result['reply'])

    def test_claim_still_without_proposal_warns_the_user(self):
        result, _ = self.run_with([([], 'He conectado los nodos.'), ([], 'Ya está hecho.')])
        self.assertIsNone(result['proposal'])
        self.assertIn(agent.NO_CHANGE_WARNING, result['warnings'])

    def test_iteration_limit_keeps_a_valid_proposal(self):
        result, _ = self.run_with([([('propose_workspace', {'proposal_json': GOOD_PATCH})],
                                    'Agent stopped due to max iterations.')])
        self.assertIsNotNone(result['proposal'])
        self.assertNotIn('Agent stopped', result['reply'])
        self.assertIn('n2', result['reply'])                                # resumen de los cambios

    def test_iteration_limit_without_proposal(self):
        result, _ = self.run_with([([], 'Agent stopped due to max iterations.')])
        self.assertEqual(result['reply'], agent.LIMIT_REPLY)

    def test_llm_failure_after_proposal_keeps_it(self):
        class Boom(FakeExecutor):
            def invoke(self, payload):
                self.tools['propose_workspace'].invoke({'proposal_json': GOOD_PATCH})
                raise RuntimeError('timed out')

        request = SimpleNamespace(user=SimpleNamespace(is_superuser=True))
        with mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor', side_effect=lambda llm, tools, prompt: Boom(tools, [])):
            result = agent.run_assistant(request, 'x', [], self.canvas, False, CONNECTIONS)
        self.assertIsNotNone(result['proposal'])
        self.assertFalse(result['error'])
        self.assertIn('tardado', ' '.join(result['warnings']))


class ToolTests(SimpleTestCase):
    def tools(self, canvas=None, holder=None, user=None):
        request = SimpleNamespace(user=user or SimpleNamespace(is_superuser=True, is_staff=True))
        built = build_tools(request, load_catalog(), canvas or {'nodes': [], 'edges': []}, CONNECTIONS,
                            False, holder if holder is not None else [])
        return {t.name: t for t in built}

    def test_rejected_proposal_tells_the_model_how_to_fix_it(self):
        out = json.loads(self.tools()['propose_workspace'].invoke(
            {'proposal_json': json.dumps({'mode': 'replace', 'nodes': [{'id': 'n1', 'type': 'nope'}]})}))
        self.assertFalse(out['accepted'])
        self.assertTrue(out['errors'])
        self.assertIn('Corrige', out['instruction'])

    def test_accepted_proposal_reports_structural_issues(self):
        holder = []
        payload = {'mode': 'replace', 'nodes': [{'id': 'n1', 'type': 'trans_Join', 'parameters': {}}], 'edges': []}
        out = json.loads(self.tools(holder=holder)['propose_workspace'].invoke({'proposal_json': json.dumps(payload)}))
        self.assertTrue(out['accepted'])
        self.assertTrue(any('no está conectada' in m for m in out['issues']))
        self.assertEqual(len(holder), 1)

    def test_attempts_are_capped(self):
        tools = self.tools()
        bad = json.dumps({'mode': 'replace', 'nodes': []})
        outs = [json.loads(tools['propose_workspace'].invoke({'proposal_json': bad})) for _ in range(3)]
        self.assertIn('No reintentes', outs[-1]['instruction'])

    def test_check_workspace_and_canvas_nodes(self):
        canvas = {'nodes': [canvas_node('n1', 'trans_Filter', {'sql': 'a > 1'})], 'edges': []}
        tools = self.tools(canvas=canvas)
        out = json.loads(tools['check_workspace'].invoke({}))
        self.assertEqual(out['scope'], 'canvas')
        self.assertIn('unconnected_input', [i['code'] for i in out['issues']])
        nodes = json.loads(tools['get_canvas_nodes'].invoke({'ids': 'n1,n7'}))
        self.assertEqual(nodes['nodes'][0]['parameters'], {'sql': 'a > 1'})
        self.assertEqual(nodes['unknown'], ['n7'])

    def test_a_failing_tool_does_not_break_the_turn(self):
        tools = self.tools()
        with mock.patch('gvsigol_plugin_geoetl.assistant.tools.public_specs', side_effect=RuntimeError('x')):
            out = json.loads(tools['get_node_specs'].invoke({'types': 'trans_Filter'}))
        self.assertIn('ha fallado', out['error'])


class ListFilesTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        for rel in ('rol_a/datos/municipios.csv', 'rol_a/orto.tif', 'rol_b/secreto.csv',
                    'rol_a/.oculto/x.csv', '.geoetl_models/m.joblib', 'suelto.csv'):
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'w').close()

    def list(self, user, **args):
        request = SimpleNamespace(user=user)
        tools = {t.name: t for t in build_tools(request, {}, {}, [], False, [])}

        def manage(req, path):
            return req.user.is_superuser or path.split('/')[0] in getattr(req.user, 'roles', ())
        with self.settings(FILEMANAGER_DIRECTORY=self.root), \
                mock.patch('gvsigol_filemanager.views.can_manage_path', side_effect=manage), \
                mock.patch('gvsigol_filemanager.views.can_browse_path',
                           side_effect=lambda req, path: path == '' or manage(req, path)):
            return json.loads(tools['list_files'].invoke(args))

    def test_staff_sees_only_its_role_folders_and_no_hidden_files(self):
        out = self.list(SimpleNamespace(is_superuser=False, is_staff=True, roles=('rol_a',)))
        paths = [f['path'] for f in out['files']]
        self.assertEqual(paths, ['rol_a/orto.tif', 'rol_a/datos/municipios.csv'])
        self.assertTrue(out['files'][0]['value'].startswith('file://' + self.root))

    def test_extension_filter_folder_and_traversal(self):
        admin = SimpleNamespace(is_superuser=True, is_staff=True)
        out = self.list(admin, extensions='csv')
        self.assertEqual(sorted(f['path'] for f in out['files']),
                         ['rol_a/datos/municipios.csv', 'rol_b/secreto.csv', 'suelto.csv'])
        self.assertEqual([f['path'] for f in self.list(admin, folder='rol_a/datos')['files']],
                         ['rol_a/datos/municipios.csv'])
        self.assertIn('error', self.list(admin, folder='../etc'))
        staff = SimpleNamespace(is_superuser=False, is_staff=True, roles=('rol_a',))
        self.assertIn('error', self.list(staff, folder='rol_b'))


@override_settings(LANGUAGE_CODE='es')
class WiringTests(SimpleTestCase):
    def test_prompt_formats_and_tools_have_valid_schemas(self):
        from langchain_core.utils.function_calling import convert_to_openai_tool
        catalog = load_catalog()
        messages = agent._prompt(catalog).format_messages(input='hola {x}', chat_history=[], agent_scratchpad=[])
        system = messages[0].content
        self.assertIn('check_workspace', system)
        self.assertIn('trans_Join (', system)
        request = SimpleNamespace(user=SimpleNamespace(is_superuser=True))
        tools = build_tools(request, catalog, {}, CONNECTIONS, False, [])
        names = []
        for item in tools:
            spec = convert_to_openai_tool(item)
            names.append(spec['function']['name'])
            self.assertTrue(spec['function']['description'])
        self.assertEqual(sorted(names), sorted([
            'list_connections', 'get_node_specs', 'list_tables', 'get_table_schema', 'list_files',
            'get_canvas_nodes', 'check_workspace', 'propose_workspace']))
