# -*- coding: utf-8 -*-
"""Columnas de las entradas: lectura con permisos, propuesta enriquecida, cruce y prompt."""
import json
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase

from gvsigol_plugin_geoetl import etl_schema, settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import columns, views
from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.assistant.prompt import system_prompt
from gvsigol_plugin_geoetl.assistant.questions import resolve_questions
from gvsigol_plugin_geoetl.assistant.review import check_graph, graph_after
from gvsigol_plugin_geoetl.assistant.tools import build_tools

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}]


class Base(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.settings_ctx = self.settings(FILEMANAGER_DIRECTORY=self.root)
        self.settings_ctx.enable()
        self.addCleanup(self.settings_ctx.disable)
        for rel in ('rol_a/a.shp', 'rol_a/b.xlsx', 'rol_b/c.xlsx'):
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'w').close()
        with open(os.path.join(self.root, 'rol_a/d.csv'), 'w') as handle:
            handle.write('id;nombre\n1;a\n')

    def file(self, rel):
        return 'file://' + os.path.join(self.root, rel)

    def context(self, restricted=False):
        return AssistantContext.from_payload({'is_staff': True, 'connections': CONNECTIONS, 'file_dirs': ['rol_a'],
                                              'restricted': restricted})


class ReadTests(Base):

    def test_shapefile_like_the_accept_button(self):
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id_zona', 'nombre']):
            read = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/a.shp')}, self.context())
        self.assertEqual(read['schema'], ['ogc_fid', 'id_zona', 'nombre'])
        self.assertEqual(read['params']['epsg'], '')                  # no se inventa: se toma del fichero

    def test_no_access_to_other_folders_or_outside(self):
        with mock.patch.object(etl_schema, 'get_sheets_excel') as sheets, \
                mock.patch.object(etl_schema, 'get_schema_shape') as shape:
            other = columns.read_columns('input_Excel', {'excel-file': self.file('rol_b/c.xlsx')}, self.context())
            outside = columns.read_columns('input_Shp', {'shp-file': 'file:///etc/passwd'}, self.context())
            escape = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/../../x.shp')}, self.context())
        sheets.assert_not_called()
        shape.assert_not_called()
        for read in (other, outside, escape):
            self.assertEqual(read['error'], columns.NO_ACCESS)

    def test_excel_with_one_sheet_uses_it(self):
        with mock.patch.object(etl_schema, 'get_sheets_excel', return_value=['Datos']), \
                mock.patch.object(etl_schema, 'get_schema_excel', return_value=['id', 2]) as schema:
            read = columns.read_columns('input_Excel', {'excel-file': self.file('rol_a/b.xlsx')}, self.context())
        self.assertEqual(read['schema'], ['id', '2'])
        self.assertEqual(read['params']['sheet-name'], 'Datos')
        self.assertEqual(read['params']['get_sheet-name'], ['Datos'])
        self.assertEqual(schema.call_args[0][0]['reading'], 'single')

    def test_excel_with_several_sheets_waits(self):
        with mock.patch.object(etl_schema, 'get_sheets_excel', return_value=['A', 'B']), \
                mock.patch.object(etl_schema, 'get_schema_excel') as schema:
            read = columns.read_columns('input_Excel', {'excel-file': self.file('rol_a/b.xlsx')}, self.context())
        schema.assert_not_called()
        self.assertIsNone(read['schema'])
        self.assertEqual(read['sheets'], ['A', 'B'])

    def test_csv_detects_the_separator(self):
        read = columns.read_columns('input_Csv', {'csv-file': self.file('rol_a/d.csv')}, self.context())
        self.assertEqual(read['schema'], ['id', 'nombre'])
        self.assertEqual(read['params']['separator'], ';')

    def write(self, rel, data):
        with open(os.path.join(self.root, rel), 'wb') as handle:
            handle.write(data)
        return self.file(rel)

    def test_wrong_separator_is_corrected(self):
        path = self.write('rol_a/coma.csv', b'id,nombre,poblacion\n1,a,10\n2,b,20\n')
        read = columns.read_columns('input_Csv', {'csv-file': path, 'separator': ';'}, self.context())
        self.assertEqual(read['schema'], ['id', 'nombre', 'poblacion'])
        self.assertEqual(read['params']['separator'], ',')
        self.assertEqual(read['corrected'], {'separator': ','})

    def test_separator_that_works_is_kept(self):
        path = self.write('rol_a/mixto.csv', b'id;nombre,apellido\n1;a,b\n')
        read = columns.read_columns('input_Csv', {'csv-file': path, 'separator': ';'}, self.context())
        self.assertEqual(read['schema'], ['id', 'nombre,apellido'])
        self.assertNotIn('corrected', read)

    def test_dos_encoding_is_detected(self):
        path = self.write('rol_a/dos.csv', 'id;nombre\n1;ESPAÑA\n2;Peñíscola\n'.encode('cp850'))
        read = columns.read_columns('input_Csv', {'csv-file': path}, self.context())
        self.assertEqual(read['params']['encode'], 'CP850')
        self.assertEqual(read['schema'], ['id', 'nombre'])

    def test_windows_encoding_is_detected(self):
        path = self.write('rol_a/win.csv', 'id;nombre\n1;ESPAÑA\n2;Peñíscola\n'.encode('cp1252'))
        read = columns.read_columns('input_Csv', {'csv-file': path}, self.context())
        self.assertEqual(read['params']['encode'], 'WINDOWS-1252')

    def test_utf8_given_for_a_non_utf8_file_is_corrected(self):
        path = self.write('rol_a/dos2.csv', 'id;año\n1;Ñ\n'.encode('cp850'))
        read = columns.read_columns('input_Csv', {'csv-file': path, 'encode': 'UTF-8'}, self.context())
        self.assertEqual(read['corrected'], {'encode': 'CP850'})
        self.assertEqual(read['schema'], ['id', 'año'])

    def test_corrections_reach_the_proposal_with_a_warning(self):
        path = self.write('rol_a/coma2.csv', b'id,nombre\n1,a\n')
        result = {'proposal': {'mode': 'replace', 'nodes': [
            {'alias': 'n1', 'type': 'input_Csv', 'parameters': {'csv-file': path, 'separator': ';'}}]}}
        found = columns.enrich_proposal(result, self.context())
        node = result['proposal']['nodes'][0]
        self.assertEqual(node['parameters']['separator'], ',')
        self.assertEqual(node['parameters']['encode'], 'UTF-8')
        self.assertEqual(found['n1'], ['id', 'nombre'])
        self.assertTrue(any(w.startswith('n1: ') and "','" in w for w in result['warnings']))

    def test_shapefile_encoding_from_the_cpg(self):
        self.write('rol_a/a.cpg', b'1252')
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id']):
            read = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/a.shp'), 'encode': 'UTF-8'},
                                        self.context())
        self.assertEqual(read['params']['encode'], 'WINDOWS-1252')
        self.assertEqual(read['corrected'], {'encode': 'WINDOWS-1252'})

    def test_shapefile_encoding_from_the_dbf_records(self):
        header = bytearray(32)
        header[8:10] = (33).to_bytes(2, 'little')
        self.write('rol_a/a.dbf', bytes(header) + b'\r' + ' ESPAÑA  Peñíscola'.encode('cp850'))
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id']):
            read = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/a.shp')}, self.context())
        self.assertEqual(read['params']['encode'], 'CP850')

    def test_shapefile_encoding_from_the_geoserver_cst(self):
        self.write('rol_a/a.cst', b'ISO-8859-1')
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id']):
            read = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/a.shp'), 'encode': 'UTF-8'},
                                        self.context())
        self.assertEqual(read['params']['encode'], 'LATIN1')

    def test_shapefile_accents_far_into_the_dbf_are_detected(self):
        header = bytearray(32)
        header[8:10] = (33).to_bytes(2, 'little')
        records = b' ' * (3 * 1024 * 1024 + 7) + 'Vinificación'.encode('latin1')
        self.write('rol_a/a.dbf', bytes(header) + b'\r' + records)
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id']):
            read = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/a.shp'), 'encode': 'UTF-8'},
                                        self.context())
        self.assertEqual(read['params']['encode'], 'WINDOWS-1252')

    def test_shapefile_in_utf8_keeps_the_given_encoding(self):
        self.write('rol_a/a.cpg', b'UTF-8')
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id']):
            read = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/a.shp'), 'encode': 'UTF-8'},
                                        self.context())
        self.assertEqual(read['params']['encode'], 'UTF-8')
        self.assertNotIn('corrected', read)

    def test_missing_file_offers_similar_names(self):
        self.write('rol_a/viajeros_2024.csv', b'id;a\n')
        read = columns.read_columns('input_Csv', {'csv-file': self.file('rol_a/viajeros.csv')}, self.context())
        self.assertIn('viajeros.csv no existe', read['error'])
        self.assertEqual(read['similar_files'], [self.file('rol_a/viajeros_2024.csv')])

    def test_missing_file_warning_reaches_the_model(self):
        self.write('rol_a/viajeros_2024.csv', b'id;a\n')
        result = {'proposal': {'mode': 'replace', 'nodes': [
            {'alias': 'n1', 'type': 'input_Csv', 'parameters': {'csv-file': self.file('rol_a/viajeros.csv')}}]}}
        columns.enrich_proposal(result, self.context())
        self.assertIn('viajeros_2024.csv', result['warnings'][0])

    def test_failure_does_not_show_details(self):
        with mock.patch.object(etl_schema, 'get_schema_shape', side_effect=RuntimeError('/ruta/secreta')):
            read = columns.read_columns('input_Shp', {'shp-file': self.file('rol_a/a.shp')}, self.context())
        self.assertEqual(read['error'], columns.READ_ERROR)

    def test_nothing_to_read(self):
        self.assertIsNone(columns.read_columns('input_Shp', {}, self.context()))
        self.assertIsNone(columns.read_columns('trans_Join', {'x': 1}, self.context()))
        self.assertIsNone(columns.read_columns('input_Csv', {'csv-file': 'x', 'reading': 'multiple'}, self.context()))


class DatabaseTests(Base):

    def _context(self):
        return AssistantContext.from_payload({'is_staff': True, 'connections': [
            {'name': 'gis', 'type': 'PostGIS'}, {'name': 'ora', 'type': 'Oracle'}, {'name': 'sql', 'type': 'SQLServer'}]})

    def test_each_database_uses_its_own_parameters(self):
        from gvsigol_plugin_geoetl.assistant import tools as tools_module
        for type_name, params, expected in (
                ('input_Postgis', {'db': 'gis', 'schema-name': 's', 'tablename': 't'}, ('gis', 's', 't')),
                ('input_Oracle', {'db': 'ora', 'owner-name': 'O', 'table-name': 'T'}, ('ora', 'O', 'T')),
                ('input_SqlServer', {'db': 'sql', 'schema-name': 'dbo', 'table-name': 'T'}, ('sql', 'dbo', 'T'))):
            with self.subTest(type_name=type_name), \
                    mock.patch.object(tools_module, '_columns', return_value=[['id', 'int'], 'nombre']) as read:
                out = columns.read_columns(type_name, params, self._context())
                self.assertEqual(read.call_args[0][1:], expected)
                self.assertEqual(out['schema'], ['id', 'nombre'])
                self.assertEqual(out['params']['checkbox'], 'false')    # la ejecución lo consulta siempre

    def test_missing_table_of_a_database_input_offers_similar_ones(self):
        from gvsigol_plugin_geoetl.assistant import tools as tools_module
        levels = {'': ['public', 'ds_44523361f'], 'ds_44523361f': ['viajeros']}
        with mock.patch.object(tools_module, '_columns', return_value=[]), \
                mock.patch.object(tools_module, '_list_level', side_effect=lambda c, n, s: levels.get(s, [])):
            out = columns.read_columns('input_Postgis', {'db': 'gis', 'schema-name': '44523361f',
                                                         'tablename': 'viajeros'}, self._context())
        self.assertIsNone(out['schema'])
        self.assertEqual(out['similar_schemas'], ['ds_44523361f'])
        self.assertEqual(out['params']['checkbox'], 'false')

    def test_free_sql_or_other_connections_are_not_read(self):
        from gvsigol_plugin_geoetl.assistant import tools as tools_module
        with mock.patch.object(tools_module, '_columns') as read:
            sql = columns.read_columns('input_Oracle', {'db': 'ora', 'owner-name': 'O', 'table-name': 'T', 'checkbox': 'true'}, self._context())
            other = columns.read_columns('input_Oracle', {'db': 'ajena', 'owner-name': 'O', 'table-name': 'T'}, self._context())
            bad = columns.read_columns('input_SqlServer', {'db': 'sql', 'schema-name': 'a;b', 'table-name': 'T'}, self._context())
        read.assert_not_called()
        self.assertEqual((sql, other, bad), (None, None, None))


class RequiredParametersTests(SimpleTestCase):
    """Parámetros sin los que el nodo falla o no hace nada al ejecutarse."""

    REQUIRED = {
        'trans_KeepAttr': ['attr'], 'trans_RemoveAttr': ['attr'], 'trans_RenameAttr': ['old-attr', 'new-attr'],
        'trans_CreateAttr': ['attr', 'data-type'], 'trans_Calculator': ['attr', 'expression'],
        'trans_ChangeAttrType': ['attr', 'data-type-option'], 'trans_ModifyValue': ['attr'],
        'trans_ConcatAttr': ['attr', 'new-attr'], 'trans_SplitAttr': ['attr', 'split'],
        'trans_Reproject': ['source-epsg', 'target-epsg'], 'trans_FilterDupli': ['attr'],
        'trans_TextToPoint': ['epsg', 'lat', 'lon'], 'trans_CalcArea': ['attr'],
        'output_Postgis': ['db-option', 'schema-name-option', 'tablename'], 'trans_Join': ['attr-1', 'attr-2'],
    }
    OPTIONAL = {'trans_CreateAttr': 'value', 'trans_ModifyValue': 'value', 'trans_ConcatAttr': 'separator',
                'trans_Stats': 'group-by-attr'}

    def _required(self, catalog, type_name):
        return sorted(p['name'] for p in catalog[type_name].get('parameters') or [] if p.get('required'))

    def test_marked_in_the_catalog(self):
        catalog = load_catalog()
        for type_name, names in self.REQUIRED.items():
            with self.subTest(type_name=type_name):
                self.assertEqual(self._required(catalog, type_name), sorted(names))

    def test_a_value_that_may_be_empty_is_not_required(self):
        catalog = load_catalog()
        for type_name, name in self.OPTIONAL.items():
            with self.subTest(type_name=type_name):
                self.assertNotIn(name, self._required(catalog, type_name))

    def test_the_review_reports_them(self):
        canvas = {'nodes': [{'alias': 'n1', 'id': 'u1', 'type': 'output_Postgis', 'label': 'x',
                             'parameters': {'db-option': 'gis', 'operation': 'CREATE'}, 'status': ''}], 'edges': []}
        nodes, edges = graph_after(None, canvas)
        missing = sorted(i['param'] for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS)
                         if i['code'] == 'missing_parameter')
        self.assertEqual(missing, ['schema-name-option', 'tablename'])


class ProposalTests(Base):

    def _propose(self, payload, flag=True):
        holder = []
        tools = {t.name: t for t in build_tools(self.context(), load_catalog(), {'nodes': [], 'edges': []}, None, None,
                                                holder, columns=flag)}
        out = json.loads(tools['propose_workspace'].invoke({'proposal_json': json.dumps(payload)}))
        return out, holder[-1] if holder else None

    def _payload(self, join):
        return {'mode': 'replace', 'nodes': [
            {'id': 'n1', 'type': 'input_Shp', 'parameters': {'shp-file': self.file('rol_a/a.shp')}},
            {'id': 'n2', 'type': 'input_Shp', 'parameters': {'shp-file': self.file('rol_a/a.shp')}},
            {'id': 'n3', 'type': 'trans_Join', 'parameters': join}],
            'edges': [{'source': 'n1', 'target': 'n3', 'source_port': 0, 'target_port': 0},
                      {'source': 'n2', 'target': 'n3', 'source_port': 0, 'target_port': 1}]}

    def test_columns_reach_the_nodes_and_the_model(self):
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id_zona']):
            out, result = self._propose(self._payload({'attr-1': 'id_zona', 'attr-2': 'id_zona'}))
        self.assertEqual(result['proposal']['nodes'][0]['schema'], ['ogc_fid', 'id_zona'])
        self.assertEqual(out['columns']['n1'], ['ogc_fid', 'id_zona'])

    def test_join_short_names_are_copied(self):
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id_zona']):
            _, result = self._propose(self._payload({'attr1': 'id_zona', 'attr2': 'id_zona'}))
        params = result['proposal']['nodes'][2]['parameters']
        self.assertEqual((params['attr-1'], params['attr-2']), ('id_zona', 'id_zona'))

    def test_column_that_does_not_arrive_is_reported(self):
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id_zona']):
            out, result = self._propose(self._payload({'attr-1': 'inventado', 'attr-2': 'id_zona'}))
        nodes, edges = graph_after(result['proposal'], {'nodes': [], 'edges': []})
        issues = check_graph(nodes, edges, load_catalog(), CONNECTIONS)
        wrong = [i for i in issues if i['code'] == 'unknown_column']
        self.assertEqual((len(wrong), wrong[0]['param']), (1, 'attr-1'))
        self.assertTrue(any('inventado' in m for m in out['issues']))

    def test_join_is_checked_against_the_columns_of_the_canvas(self):
        canvas = {'nodes': [
            {'alias': 'n1', 'id': 'u1', 'type': 'input_Shp', 'label': 'a', 'parameters': {'shp-file': 'x'}, 'schema': ['id_zona'], 'status': ''},
            {'alias': 'n2', 'id': 'u2', 'type': 'trans_Filter', 'label': 'b', 'parameters': {'x': 1}, 'schema': [['a'], ['b']], 'status': ''},
            {'alias': 'n3', 'id': 'u3', 'type': 'trans_Join', 'label': 'c', 'parameters': {'attr-1': 'otra', 'attr-2': 'b'}, 'schema': [], 'status': ''}],
            'edges': [{'source': 'n1', 'target': 'n3', 'source_port': 0, 'target_port': 0},
                      {'source': 'n2', 'target': 'n3', 'source_port': 0, 'target_port': 1}]}
        nodes, edges = graph_after(None, canvas)
        wrong = [i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS) if i['code'] == 'unknown_column']
        self.assertEqual([i['param'] for i in wrong], ['attr-1'])       # n2 no es una entrada: no se comprueba

    def test_empty_join_is_reported(self):
        catalog = load_catalog()
        with mock.patch.object(etl_schema, 'get_schema_shape', return_value=['id_zona']):
            _, result = self._propose(self._payload({}))
        nodes, edges = graph_after(result['proposal'], {'nodes': [], 'edges': []})
        found = [i.get('param') for i in check_graph(nodes, edges, catalog, CONNECTIONS) if i['code'] == 'missing_parameter']
        self.assertEqual(sorted(found), ['attr-1', 'attr-2'])

    def test_without_the_flag_nothing_is_read(self):
        with mock.patch.object(etl_schema, 'get_schema_shape') as shape:
            out, result = self._propose(self._payload({'attr-1': 'a', 'attr-2': 'b'}), flag=False)
        shape.assert_not_called()
        self.assertEqual(result['proposal']['nodes'][0]['schema'], [])
        self.assertEqual(out['columns'], {})

    def test_excel_without_sheet_can_be_chosen(self):
        with mock.patch.object(etl_schema, 'get_sheets_excel', return_value=['A', 'B']):
            _, result = self._propose({'mode': 'replace', 'nodes': [
                {'id': 'n1', 'type': 'input_Excel', 'parameters': {'excel-file': self.file('rol_a/b.xlsx')}}], 'edges': []})
        node = result['proposal']['nodes'][0]
        self.assertEqual(node['parameters']['get_sheet-name'], ['A', 'B'])
        nodes, edges = graph_after(result['proposal'], {'nodes': [], 'edges': []})
        issue = [i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS) if i.get('param') == 'sheet-name'][0]
        self.assertEqual(issue['code'], 'missing_parameter')


class ToolAndQuestionTests(Base):

    def test_tool_only_with_the_flag(self):
        names = lambda flag: [t.name for t in build_tools(self.context(), load_catalog(), {}, None, None, [], columns=flag)]
        self.assertNotIn('get_file_columns', names(False))
        self.assertIn('get_file_columns', names(True))

    def test_tool_reads(self):
        tools = {t.name: t for t in build_tools(self.context(), load_catalog(), {}, None, None, [], columns=True)}
        out = json.loads(tools['get_file_columns'].invoke({'file': self.file('rol_a/d.csv')}))
        self.assertEqual(out['columns'], ['id', 'nombre'])
        out = json.loads(tools['get_file_columns'].invoke({'file': self.file('rol_b/c.xlsx')}))
        self.assertEqual(out['error'], columns.NO_ACCESS)

    def test_question_with_the_columns_of_a_file(self):
        questions, _ = resolve_questions([{'label': 'Campo', 'text': '¿Por qué campo cruzo el CSV?', 'source': 'columns',
                                           'file': self.file('rol_a/d.csv')}], load_catalog(), {}, self.context())
        self.assertEqual([o['value'] for o in questions[0]['options']], ['id', 'nombre'])

    def test_prompt_only_with_the_flag(self):
        catalog = load_catalog()
        self.assertNotIn('get_file_columns', system_prompt(catalog, 'es'))
        self.assertIn('get_file_columns', system_prompt(catalog, 'es', columns=True))
        self.assertNotIn('ask_user', system_prompt(catalog, 'es', columns=True))
        self.assertIn('source columns', system_prompt(catalog, 'es', questions=True, columns=True))


class EndpointTests(Base):

    def _post(self, body, flag=True, access=(None, False), staff=True):
        request = RequestFactory().post('/c/', data=json.dumps(body), content_type='application/json')
        request.user = SimpleNamespace(id=1, username='ana', is_authenticated=True, is_staff=staff, is_superuser=staff)
        with mock.patch.object(views, 'assistant_feature_enabled', return_value=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_COLUMNS', flag, create=True), \
                mock.patch.object(views, '_workspace_access', return_value=access), \
                mock.patch('gvsigol_plugin_geoetl.views.get_etl_connections_list', return_value=CONNECTIONS), \
                mock.patch.object(columns, 'read_columns', return_value={'schema': ['a'], 'params': {}}):
            return views.etl_assistant_columns(request)

    def test_ok(self):
        data = json.loads(self._post({'type': 'input_Shp', 'parameters': {}}).content)
        self.assertEqual(data['schema'], ['a'])

    def test_closed_or_refused(self):
        with self.assertRaises(Http404):
            self._post({'type': 'input_Shp'}, flag=False)
        self.assertEqual(self._post({'type': 'input_Shp'}, staff=False).status_code, 403)
        self.assertEqual(self._post({'type': 'trans_Join'}).status_code, 400)
        self.assertEqual(self._post({'type': 'input_Shp'}, access=(None, True)).status_code, 403)


class PropagatedColumnsTests(SimpleTestCase):
    """Las columnas se calculan como en el editor, también detrás de nodos recién propuestos."""

    CANVAS = {'nodes': [
        {'alias': 'n1', 'id': 'u1', 'type': 'input_Postgis', 'label': 'regioes', 'status': '',
         'parameters': {'db': 'gis', 'tablename': 'regioes'}, 'schema': ['region', 'pop_2008', 'nome']},
        {'alias': 'n2', 'id': 'u2', 'type': 'trans_Union', 'label': 'Fusión', 'status': '',
         'parameters': {'group-by-attr': 'region'}, 'schema': ['region']},
        {'alias': 'n3', 'id': 'u3', 'type': 'output_Postgis', 'label': 'salida', 'status': '',
         'parameters': {'db': 'gis', 'tablename': 'r'}, 'schema': ['region']}],
        'edges': [{'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0},
                  {'source': 'n2', 'target': 'n3', 'source_port': 0, 'target_port': 0}]}

    def _issues(self, filter_attr, stats=None):
        stats = stats or {'attr': 'pop_2008', 'group-by-attr': 'region'}
        ops = [
            {'op': 'remove_edge', 'source': 'n2', 'target': 'n3'},
            {'op': 'add_node', 'node': {'alias': 'n4', 'type': 'trans_Stats', 'parameters': stats}},
            {'op': 'add_node', 'node': {'alias': 'n5', 'type': 'trans_Join',
                                        'parameters': {'attr-1': 'region', 'attr-2': 'region'}}},
            {'op': 'add_node', 'node': {'alias': 'n6', 'type': 'trans_Filter', 'parameters': {'attr': filter_attr}}},
            {'op': 'add_edge', 'source': 'n1', 'target': 'n4'},
            {'op': 'add_edge', 'source': 'n2', 'target': 'n5', 'target_port': 0},
            {'op': 'add_edge', 'source': 'n4', 'target': 'n5', 'target_port': 1},
            {'op': 'add_edge', 'source': 'n5', 'target': 'n6'},
            {'op': 'add_edge', 'source': 'n6', 'target': 'n3'},
        ]
        nodes, edges = graph_after({'mode': 'patch', 'ops': ops}, self.CANVAS)
        return [i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS) if i['code'] == 'unknown_column']

    def test_original_column_after_stats_turns_red(self):
        wrong = self._issues('pop_2008')
        self.assertEqual([(i['node'], i['param']) for i in wrong], [('n6', 'attr')])
        self.assertIn('_sum', wrong[0]['message'])

    def test_stats_columns_are_ok(self):
        self.assertEqual(self._issues('_sum'), [])

    def test_stats_on_a_missing_column(self):
        wrong = self._issues('_sum', stats={'attr': 'poblacion', 'group-by-attr': 'region'})
        self.assertEqual([(i['node'], i['param']) for i in wrong], [('n4', 'attr')])

    def test_join_key_missing_on_the_second_input(self):
        nodes, edges = graph_after({'mode': 'patch', 'ops': [
            {'op': 'add_node', 'node': {'alias': 'n4', 'type': 'trans_Stats',
                                        'parameters': {'attr': 'pop_2008', 'group-by-attr': '-'}}},
            {'op': 'add_node', 'node': {'alias': 'n5', 'type': 'trans_Join',
                                        'parameters': {'attr-1': 'region', 'attr-2': 'region'}}},
            {'op': 'add_edge', 'source': 'n1', 'target': 'n4'},
            {'op': 'add_edge', 'source': 'n1', 'target': 'n5', 'target_port': 0},
            {'op': 'add_edge', 'source': 'n4', 'target': 'n5', 'target_port': 1},
        ]}, self.CANVAS)
        wrong = [i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS) if i['code'] == 'unknown_column']
        self.assertEqual([(i['node'], i['param']) for i in wrong], [('n5', 'attr-2')])

    def test_canvas_nodes_untouched_are_not_rechecked(self):
        nodes, edges = graph_after(None, self.CANVAS)
        self.assertEqual([i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS)
                          if i['code'] == 'unknown_column'], [])

    def test_unknown_upstream_is_not_reported(self):
        nodes, edges = graph_after({'mode': 'replace', 'nodes': [
            {'alias': 'n1', 'type': 'input_Csv', 'parameters': {'csv-file': 'x'}},
            {'alias': 'n2', 'type': 'trans_Filter', 'parameters': {'attr': 'lo_que_sea'}}],
            'edges': [{'source': 'n1', 'target': 'n2', 'source_port': 0, 'target_port': 0}]}, None)
        self.assertEqual([i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS)
                          if i['code'] == 'unknown_column'], [])


class SqlPlacementTests(SimpleTestCase):

    def _issues(self, node, code):
        nodes, edges = graph_after(None, {'nodes': node, 'edges': []})
        return [i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS) if i['code'] == code]

    def _input(self, clause):
        return [{'alias': 'n1', 'id': 'u1', 'type': 'input_Postgis', 'label': 'e', 'status': '',
                 'parameters': {'db': 'gis', 'tablename': 't', 'checkbox': 'true', 'clause': clause},
                 'schema': ['ogc_fid']}]

    def test_full_query_in_the_where_is_an_error(self):
        wrong = self._issues(self._input('SELECT "ogc_fid", ST_Centroid(geom) FROM "ds_brasil"."t"'), 'invalid_where')
        self.assertEqual([i['param'] for i in wrong], ['clause'])

    def test_conditions_and_subqueries_are_fine(self):
        self.assertEqual(self._issues(self._input('"ogc_fid" IN (SELECT "id" FROM "x"."y")'), 'invalid_where'), [])
        self.assertEqual(self._issues(self._input('"pop_2008" > 1000'), 'invalid_where'), [])

    def _calculator(self, attr, expose):
        ops = [{'op': 'add_node', 'node': {'alias': 'n3', 'type': 'trans_Calculator',
                                           'parameters': {'attr': attr, 'expression': 'ST_Centroid("wkb_geometry")'}}}]
        if expose:
            ops += [{'op': 'add_node', 'node': {'alias': 'n2', 'type': 'trans_ExposeAttr', 'parameters': {'attrs': 'wkb_geometry'}}},
                    {'op': 'add_edge', 'source': 'n1', 'target': 'n2'}, {'op': 'add_edge', 'source': 'n2', 'target': 'n3'}]
        else:
            ops += [{'op': 'add_edge', 'source': 'n1', 'target': 'n3'}]
        nodes, edges = graph_after({'mode': 'patch', 'ops': ops}, {'nodes': self._input(''), 'edges': []})
        return [i for i in check_graph(nodes, edges, load_catalog(), CONNECTIONS) if i['code'] == 'unknown_column']

    def test_exposed_geometry_can_be_filled_by_the_calculator(self):
        self.assertEqual(self._calculator('wkb_geometry', expose=True), [])

    def test_hidden_geometry_must_be_exposed_first(self):
        for attr in ('wkb_geometry', 'geom'):
            wrong = self._calculator(attr, expose=False)
            self.assertEqual([i['node'] for i in wrong], ['n3'])
            self.assertIn('trans_ExposeAttr', wrong[0]['message'])
