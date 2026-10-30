# -*- coding: utf-8 -*-
import unittest

from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.graph import (
    is_protected,
    needs_confirmation,
    validate_proposal,
)

_SQL = 'Revisa el SQL de %s antes de guardar o ejecutar: lo ha escrito el asistente.'


class ConfirmationTests(unittest.TestCase):
    def test_replace_confirms_only_when_the_canvas_has_nodes(self):
        self.assertFalse(needs_confirmation('replace', False))
        self.assertTrue(needs_confirmation('replace', True))

    def test_patch_confirms_only_deletes(self):
        self.assertFalse(needs_confirmation('patch', True, [{'op': 'add_node'}]))
        self.assertFalse(needs_confirmation('patch', True, [{'op': 'add_edge'}, {'op': 'update_node'}]))
        self.assertTrue(needs_confirmation('patch', False, [{'op': 'remove_node'}]))
        self.assertTrue(needs_confirmation('patch', True, [{'op': 'remove_edge'}]))


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.connections = [
            {'name': 'gis', 'type': 'PostGIS'},
            {'name': 'ora', 'type': 'Oracle'},
        ]
        cls.canvas = {
            'nodes': [
                {
                    'alias': 'n1',
                    'id': 'uuid-1',
                    'type': 'input_Postgis',
                    'label': 'PostGIS',
                    'parameters': {'db': 'gis'},
                },
                {
                    'alias': 'n2',
                    'id': 'uuid-2',
                    'type': 'trans_Filter',
                    'label': 'Filtro',
                    'parameters': {'attr': 'uso'},
                },
                {
                    'alias': 'n3',
                    'id': 'uuid-3',
                    'type': 'output_Postgis',
                    'label': 'Salida',
                    'parameters': {'db-option': 'gis'},
                },
            ]
        }

    def test_unknown_type_param_port_and_connection_are_dropped(self):
        result = validate_proposal({
            'mode': 'replace',
            'assumptions': ['n1: lectura de parcelas', 'n9: este nodo no existe'],
            'nodes': [
                {
                    'id': 'n1',
                    'type': 'input_Postgis',
                    'parameters': {'db': 'desconocida', 'clause': 'select 1', 'nope': True},
                },
                {'id': 'n9', 'type': 'nope', 'parameters': {}},
            ],
            'edges': [
                {'source': 'n1', 'target': 'n1', 'source_port': 0, 'target_port': 0},
                {'source': 'n1', 'target': 'n9', 'source_port': True, 'target_port': 0},
            ],
        }, self.catalog, self.connections, {'nodes': []}, restricted=False)
        self.assertIsNotNone(result['proposal'])
        params = result['proposal']['nodes'][0]['parameters']
        self.assertNotIn('db', params)
        self.assertNotIn('nope', params)
        self.assertEqual(params.get('clause'), 'select 1')
        self.assertEqual(result['proposal']['edges'], [])
        self.assertIn(_SQL % 'n1', result['warnings'])
        self.assertTrue(any('no está en el catálogo' in line for line in result['warnings']))
        self.assertTrue(any('no está disponible' in line for line in result['warnings']))
        self.assertEqual(result['assumptions'], ['n1: lectura de parcelas'])
        self.assertFalse(result['needs_confirmation'])
        self.assertEqual(result['summary'], ['Creo un flujo con PgSQL/PostGIS (n1).'])

    def test_incompatible_connection_type_is_removed(self):
        result = validate_proposal({
            'mode': 'replace',
            'nodes': [{'id': 'n1', 'type': 'input_Postgis', 'parameters': {'db': 'ora'}}],
        }, self.catalog, self.connections, {'nodes': []})
        self.assertNotIn('db', result['proposal']['nodes'][0]['parameters'])
        self.assertTrue(any('Oracle' in line for line in result['warnings']))

    def test_occupied_replace_asks_for_confirmation(self):
        result = validate_proposal({
            'mode': 'replace',
            'nodes': [{'id': 'n4', 'type': 'trans_Filter', 'label': 'Filtro', 'parameters': {'attr': 'uso'}}],
        }, self.catalog, self.connections, self.canvas)
        self.assertTrue(result['needs_confirmation'])
        self.assertEqual(result['summary'][0], 'Creo un flujo con Filtro (n4).')

    def test_insert_between_does_not_ask_and_summarizes_once(self):
        result = validate_proposal({
            'mode': 'patch',
            'ops': [
                {
                    'op': 'add_node',
                    'node': {
                        'id': 'n4',
                        'type': 'trans_Filter',
                        'label': 'Filtro',
                        'parameters': {'attr': 'uso', 'option': '=', 'value': 'urbana'},
                    },
                },
                {'op': 'add_edge', 'source': 'n1', 'target': 'n4', 'source_port': 0, 'target_port': 0},
                {'op': 'add_edge', 'source': 'n4', 'target': 'n3', 'source_port': 0, 'target_port': 0},
            ],
        }, self.catalog, self.connections, self.canvas)
        self.assertFalse(result['needs_confirmation'])
        self.assertEqual(result['summary'], [
            'Añado Filtro (n4) entre PostGIS (n1) y Salida (n3).',
        ])
        edge = result['proposal']['ops'][1]
        self.assertEqual(edge['source'], 'uuid-1')
        self.assertEqual(edge['source_alias'], 'n1')
        self.assertEqual(edge['target'], 'n4')

    def test_update_rewrites_alias_to_canvas_uuid(self):
        result = validate_proposal({
            'mode': 'patch',
            'ops': [{'op': 'update_node', 'id': 'n2', 'parameters': {'attr': 'ine', 'option': '='}}],
        }, self.catalog, self.connections, self.canvas)
        op = result['proposal']['ops'][0]
        self.assertEqual(op['id'], 'uuid-2')
        self.assertEqual(op['alias'], 'n2')
        self.assertEqual(op['parameters']['attr'], 'ine')
        self.assertFalse(result['needs_confirmation'])
        self.assertEqual(result['summary'], ['Actualizo Filtro (n2).'])

    def test_remove_asks_for_confirmation(self):
        result = validate_proposal({
            'mode': 'patch',
            'ops': [{'op': 'remove_node', 'id': 'n2'}],
        }, self.catalog, self.connections, self.canvas)
        self.assertTrue(result['needs_confirmation'])
        self.assertEqual(result['summary'], ['Elimino Filtro (n2).'])
        self.assertEqual(result['proposal']['ops'][0]['id'], 'uuid-2')

    def test_port_out_of_range_drops_the_edge(self):
        result = validate_proposal({
            'mode': 'replace',
            'nodes': [
                {'id': 'n1', 'type': 'trans_Filter', 'parameters': {'attr': 'uso'}},
                {'id': 'n2', 'type': 'output_Visualizer', 'parameters': {}},
            ],
            'edges': [{'source': 'n1', 'target': 'n2', 'source_port': 5, 'target_port': 0}],
        }, self.catalog, self.connections, {'nodes': []})
        self.assertEqual(result['proposal']['edges'], [])
        self.assertTrue(any('no tiene la salida 5' in line for line in result['warnings']))
        boolean_port = validate_proposal({
            'mode': 'replace',
            'nodes': [
                {'id': 'n1', 'type': 'trans_Filter', 'parameters': {'attr': 'uso'}},
                {'id': 'n2', 'type': 'output_Visualizer', 'parameters': {}},
            ],
            'edges': [{'source': 'n1', 'target': 'n2', 'source_port': True, 'target_port': 0}],
        }, self.catalog, self.connections, {'nodes': []})
        self.assertEqual(boolean_port['proposal']['edges'], [])
        self.assertTrue(any('Puerto no válido' in line for line in boolean_port['warnings']))

    def test_restricted_edit_blocks_replace_and_protected_nodes(self):
        self.assertTrue(is_protected('input_Csv'))
        self.assertTrue(is_protected('output_Postgis'))
        self.assertTrue(is_protected('trans_ExecuteSQL'))
        self.assertFalse(is_protected('trans_Filter'))
        replaced = validate_proposal({
            'mode': 'replace',
            'nodes': [{'id': 'n1', 'type': 'trans_Filter', 'parameters': {}}],
        }, self.catalog, self.connections, self.canvas, restricted=True)
        self.assertIsNone(replaced['proposal'])
        patched = validate_proposal({
            'mode': 'patch',
            'ops': [
                {'op': 'add_node', 'node': {'id': 'n8', 'type': 'input_Csv', 'parameters': {}}},
                {'op': 'add_node', 'node': {'id': 'n9', 'type': 'trans_ExecuteSQL', 'parameters': {'query': 'select 1'}}},
                {'op': 'add_node', 'node': {'id': 'n4', 'type': 'trans_Filter', 'label': 'Nuevo', 'parameters': {'attr': 'a'}}},
                {'op': 'update_node', 'id': 'n1', 'parameters': {'tablename': 'otras'}},
                {'op': 'remove_node', 'id': 'n3'},
                {'op': 'add_edge', 'source': 'n1', 'target': 'n4', 'source_port': 0, 'target_port': 0},
            ],
        }, self.catalog, self.connections, self.canvas, restricted=True)
        kinds = [(op['op'], op.get('node', {}).get('type') or op.get('type')) for op in patched['proposal']['ops']]
        self.assertEqual(kinds, [('add_node', 'trans_Filter')])
        text = ' '.join(patched['warnings'])
        self.assertIn('input_Csv', text)
        self.assertIn('trans_ExecuteSQL', text)
        self.assertIn('no se cambia', text)
        self.assertIn('no se elimina', text)
        self.assertIn('no se cambian las conexiones', text)
