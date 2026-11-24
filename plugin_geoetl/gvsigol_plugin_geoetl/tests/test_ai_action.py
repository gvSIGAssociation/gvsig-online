# -*- coding: utf-8 -*-
"""Nodo Procesar datos: contrato E/S, sandbox SQL y ejecución."""
import json
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from gvsigol_plugin_geoetl import etl_ai_action, views
from gvsigol_plugin_geoetl.assistant.catalog import available, load_catalog
from gvsigol_plugin_geoetl.assistant import schemas


class ParamsTests(SimpleTestCase):

    def test_output_schema_and_inputs(self):
        inputs_count, outputs_count, instruction, schema, sql_text, sqls = etl_ai_action.check_params({
            'inputs_count': 2,
            'outputs_count': 1,
            'instruction': 'join espacial',
            'output_schema': [{'name': 'a', 'type': 'text'}, {'name': 'b', 'type': 'double'}],
            'sql': 'SELECT a, b FROM input_0',
        })
        self.assertEqual((inputs_count, outputs_count, instruction), (2, 1, 'join espacial'))
        self.assertEqual([c['name'] for c in schema[0]], ['a', 'b'])
        self.assertIn('SELECT', sql_text)
        self.assertEqual(sqls, [sql_text])

    def test_per_output_schemas(self):
        _, outputs_count, _, schema, _, sqls = etl_ai_action.check_params({
            'inputs_count': 1,
            'outputs_count': 2,
            'instruction': 'parte en dos',
            'output_schemas': [
                [{'name': 'a', 'type': 'text'}],
                [{'name': 'b', 'type': 'double'}],
            ],
            'sql': 'SELECT a, b FROM input_0',
        })
        self.assertEqual(outputs_count, 2)
        self.assertEqual([c['name'] for c in schema[0]], ['a'])
        self.assertEqual([c['name'] for c in schema[1]], ['b'])
        self.assertEqual(len(sqls), 2)

    def test_per_output_sqls(self):
        _, outputs_count, _, schema, sql_text, sqls = etl_ai_action.check_params({
            'inputs_count': 2,
            'outputs_count': 2,
            'instruction': 'join y no unidos',
            'output_schemas': [
                [{'name': 'preid', 'type': 'integer'}, {'name': 'id', 'type': 'integer'}],
                [{'name': 'preid', 'type': 'integer'}],
            ],
            'sqls': [
                'SELECT a.preid, b.id FROM input_0 a INNER JOIN input_1 b ON a.preid = b.id',
                'SELECT a.preid FROM input_0 a WHERE NOT EXISTS (SELECT 1 FROM input_1 b WHERE b.id = a.preid)',
            ],
        })
        self.assertEqual(outputs_count, 2)
        self.assertEqual(sql_text, sqls[0])
        self.assertIn('INNER JOIN', sqls[0])
        self.assertIn('NOT EXISTS', sqls[1])
        self.assertEqual([c['name'] for c in schema[0]], ['preid', 'id'])

    def test_partial_accept_allows_empty_sql(self):
        inputs_count, outputs_count, instruction, schema, sql_text, sqls = etl_ai_action.check_params({
            'inputs_count': 2,
            'outputs_count': 2,
            'instruction': '',
            'output_schema': [],
            'sql': '',
        }, for_run=False)
        self.assertEqual((inputs_count, outputs_count, instruction, sql_text), (2, 2, '', ''))
        self.assertEqual(schema, [[], []])
        self.assertEqual(sqls, ['', ''])

    def test_rejects_bad_contract_on_run(self):
        with self.assertRaisesRegex(ValueError, 'salida'):
            etl_ai_action.check_params({
                'inputs_count': 1,
                'instruction': 'x',
                'output_schema': [],
                'sql': 'SELECT 1 AS x FROM input_0',
            }, for_run=True)

    def test_limits(self):
        self.assertEqual(etl_ai_action.MAX_INPUTS, 5)
        self.assertEqual(etl_ai_action.MAX_OUTPUTS, 10)
        with self.assertRaisesRegex(ValueError, 'inputs_count'):
            etl_ai_action.check_params({
                'inputs_count': 6,
                'outputs_count': 1,
                'instruction': 'x',
                'output_schema': [{'name': 'a', 'type': 'text'}],
                'sql': 'SELECT 1 AS a FROM input_0',
            }, for_run=False)

    def test_infer_outputs_from_instruction(self):
        self.assertEqual(
            etl_ai_action.infer_outputs_count(
                'Une las tablas y da dos salidas, una con unidos y otra con no unidos',
                1,
            ),
            2,
        )
        self.assertEqual(
            etl_ai_action.infer_outputs_count('calcula centroides', 1),
            1,
        )
        self.assertEqual(
            etl_ai_action.infer_outputs_count('tres salidas distintas', 1),
            3,
        )
        self.assertEqual(
            etl_ai_action.infer_outputs_count('dos salidas', 4),
            4,
        )
        self.assertEqual(
            etl_ai_action.parse_outputs_from_instruction('dos salidas distintas'),
            2,
        )
        self.assertEqual(
            etl_ai_action.parse_outputs_from_instruction('calcula centroides'),
            0,
        )
        self.assertEqual(
            etl_ai_action.count_outputs_from_sqls([
                'SELECT 1 AS a FROM input_0',
                'SELECT 1 AS a FROM input_0',
                'SELECT 2 AS b FROM input_0',
                '',
            ]),
            2,
        )

    def test_suggest_schemas_from_instruction(self):
        def fake_invoke(system, user):
            return json.dumps({
                'outputs_count': 2,
                'output_schemas': [
                    [{'name': 'a', 'type': 'text'}],
                    [{'name': 'b', 'type': 'integer'}],
                ],
            })
        count, schemas = etl_ai_action.suggest_schemas_from_instruction(
            'dos salidas: una con a y otra con b',
            [[{'name': 'id', 'type': 'integer'}]],
            outputs_count=1,
            invoke=fake_invoke,
        )
        self.assertEqual(count, 2)
        self.assertEqual(schemas[0][0]['name'], 'a')
        self.assertEqual(schemas[1][0]['name'], 'b')


class SandboxTests(SimpleTestCase):

    def test_sanitize_allows_select(self):
        self.assertTrue(etl_ai_action.sanitize_sql('SELECT a FROM input_0').startswith('SELECT'))

    def test_sanitize_rejects_drop(self):
        with self.assertRaisesRegex(ValueError, 'SELECT/WITH'):
            etl_ai_action.sanitize_sql('DROP TABLE input_0')

    def test_sanitize_rejects_multiple_statements(self):
        with self.assertRaisesRegex(ValueError, 'una sentencia'):
            etl_ai_action.sanitize_sql('SELECT 1 FROM input_0; SELECT 2')

    def test_alias_range(self):
        with self.assertRaisesRegex(ValueError, 'no declaradas'):
            etl_ai_action.assert_only_input_aliases('SELECT * FROM input_2', 2)

    def test_bind_replaces_aliases(self):
        bound = etl_ai_action.bind_sql(
            'SELECT a FROM input_0 JOIN input_1 USING (a)',
            ['t0', 't1'],
            schema='ds_plugin_geoetl',
        )
        self.assertIn('"ds_plugin_geoetl"."t0"', bound)
        self.assertIn('"ds_plugin_geoetl"."t1"', bound)
        self.assertNotIn('input_0', bound)

    def test_columns_match(self):
        schema = [{'name': 'x', 'type': 'double'}, {'name': 'y', 'type': 'double'}]
        etl_ai_action.assert_columns_match(['x', 'y'], schema)
        with self.assertRaisesRegex(ValueError, 'no coinciden'):
            etl_ai_action.assert_columns_match(['x'], schema)

    def test_columns_subset(self):
        etl_ai_action.assert_columns_subset(
            ['a', 'b', 'c'],
            [{'name': 'a', 'type': 'text'}, {'name': 'c', 'type': 'text'}],
        )
        with self.assertRaisesRegex(ValueError, 'faltan'):
            etl_ai_action.assert_columns_subset(['a'], [{'name': 'b', 'type': 'text'}])


class GenerateTests(SimpleTestCase):

    def test_parse_json_sql(self):
        sql_text = etl_ai_action.parse_generated_sql('{"sql":"SELECT a AS out FROM input_0"}')
        self.assertIn('SELECT', sql_text)

    def test_parse_json_sqls(self):
        sqls = etl_ai_action.parse_generated_sqls(
            json.dumps({
                'sqls': [
                    'SELECT a.preid FROM input_0 a INNER JOIN input_1 b ON a.preid = b.id',
                    'SELECT a.preid FROM input_0 a WHERE NOT EXISTS (SELECT 1 FROM input_1 b WHERE b.id = a.preid)',
                ],
            }),
            outputs_count=2,
        )
        self.assertEqual(len(sqls), 2)
        self.assertIn('INNER JOIN', sqls[0])
        self.assertIn('NOT EXISTS', sqls[1])

    def test_generate_calls_invoke_and_dry_run(self):
        invoke = mock.Mock(return_value=json.dumps({
            'sql': 'SELECT calle AS direccion FROM input_0',
        }))
        with mock.patch.object(
            etl_ai_action, 'dry_run_schema',
            return_value=[{'name': 'direccion', 'type': 'text'}],
        ):
            sql_text, schema = etl_ai_action.generate_sql(
                'unifica en direccion',
                [['calle', 'numero']],
                [{'name': 'direccion', 'type': 'text'}],
                invoke=invoke,
            )
        self.assertIn('direccion', sql_text)
        self.assertEqual(schema[0]['name'], 'direccion')
        invoke.assert_called_once()

    def test_generate_multi_outputs(self):
        invoke = mock.Mock(return_value=json.dumps({
            'sqls': [
                'SELECT a.preid, b.id FROM input_0 a INNER JOIN input_1 b ON a.preid = b.id',
                'SELECT a.preid FROM input_0 a WHERE NOT EXISTS (SELECT 1 FROM input_1 b WHERE b.id = a.preid)',
            ],
        }))
        schemas_side = [
            [{'name': 'preid', 'type': 'integer'}, {'name': 'id', 'type': 'integer'}],
            [{'name': 'preid', 'type': 'integer'}],
        ]
        with mock.patch.object(
            etl_ai_action, 'dry_run_schema', side_effect=schemas_side,
        ):
            sqls, schemas = etl_ai_action.generate_sql(
                'une por preid/id; salida 1 unidos, salida 2 no unidos del primer input',
                [[{'name': 'preid', 'type': 'integer'}], [{'name': 'id', 'type': 'integer'}]],
                outputs_count=2,
                output_schemas=[[], []],
                invoke=invoke,
            )
        self.assertEqual(len(sqls), 2)
        self.assertEqual(schemas[0][0]['name'], 'preid')
        self.assertEqual(schemas[1][0]['name'], 'preid')
        system, user = invoke.call_args[0]
        self.assertIn('sqls', system)
        self.assertIn('jsonb_agg', system.lower())
        self.assertIn('outputs_count', user)

    def test_generate_prompt_prioritizes_instruction(self):
        system, user = etl_ai_action.build_generate_messages(
            'crea id10 = id + 10',
            [[{'name': 'id', 'type': 'integer'}]],
            [{'name': 'id', 'type': 'integer'}],
        )
        self.assertIn('prioridad', system.lower())
        self.assertIn('id10', user)
        self.assertIn('output_schema_hint', user)

    def test_suggest_schema_from_sql(self):
        with mock.patch.object(
            etl_ai_action, 'dry_run_schema',
            return_value=[{'name': 'x', 'type': 'double'}, {'name': 'y', 'type': 'double'}],
        ):
            cols = etl_ai_action.suggest_schema_from_sql(
                'SELECT 1::float AS x, 2::float AS y FROM input_0',
                [['id']],
            )
        self.assertEqual([c['name'] for c in cols], ['x', 'y'])


class ExecuteTests(SimpleTestCase):

    def test_disabled(self):
        with mock.patch.object(etl_ai_action, 'feature_enabled', return_value=False):
            with self.assertRaisesRegex(ValueError, 'desactivado'):
                etl_ai_action.trans_AIAction({
                    'id': 't', 'data': ['s'], 'inputs_count': 1,
                    'instruction': 'x', 'output_schema': [{'name': 'a', 'type': 'text'}],
                    'sql': 'SELECT 1 AS a FROM input_0',
                })

    def test_execute_creates_table(self):
        cur = mock.MagicMock()
        cur.description = [('a',), ('b',)]
        conn = mock.MagicMock()
        conn.cursor.return_value = cur
        with mock.patch.object(etl_ai_action, 'feature_enabled', return_value=True), \
                mock.patch.object(etl_ai_action, '_connect', return_value=conn):
            result = etl_ai_action.trans_AIAction({
                'id': 'out', 'data': ['src'], 'inputs_count': 1,
                'instruction': 'pasa a y b',
                'output_schema': [{'name': 'a', 'type': 'text'}, {'name': 'b', 'type': 'text'}],
                'sql': 'SELECT a, b FROM input_0',
            })
        self.assertEqual(result, ['out'])
        self.assertTrue(cur.execute.called)

    def test_execute_projects_per_output(self):
        cur = mock.MagicMock()
        cur.description = [('a',), ('b',), ('c',)]
        conn = mock.MagicMock()
        conn.cursor.return_value = cur
        with mock.patch.object(etl_ai_action, 'feature_enabled', return_value=True), \
                mock.patch.object(etl_ai_action, '_connect', return_value=conn):
            result = etl_ai_action.trans_AIAction({
                'id': 'out', 'data': ['src'], 'inputs_count': 1, 'outputs_count': 2,
                'instruction': 'dos proyecciones',
                'output_schemas': [
                    [{'name': 'a', 'type': 'text'}],
                    [{'name': 'b', 'type': 'text'}, {'name': 'c', 'type': 'text'}],
                ],
                'sql': 'SELECT a, b, c FROM input_0',
            })
        self.assertEqual(result, ['out', 'out_o1'])

    def test_execute_per_output_sqls(self):
        cur = mock.MagicMock()
        cur.description = [('preid',), ('id',)]
        conn = mock.MagicMock()
        conn.cursor.return_value = cur
        with mock.patch.object(etl_ai_action, 'feature_enabled', return_value=True), \
                mock.patch.object(etl_ai_action, '_connect', return_value=conn):
            result = etl_ai_action.trans_AIAction({
                'id': 'out', 'data': ['t0', 't1'], 'inputs_count': 2, 'outputs_count': 2,
                'instruction': 'join y no unidos',
                'output_schemas': [
                    [{'name': 'preid', 'type': 'integer'}, {'name': 'id', 'type': 'integer'}],
                    [{'name': 'preid', 'type': 'integer'}],
                ],
                'sqls': [
                    'SELECT a.preid, b.id FROM input_0 a INNER JOIN input_1 b ON a.preid = b.id',
                    'SELECT a.preid FROM input_0 a WHERE NOT EXISTS (SELECT 1 FROM input_1 b WHERE b.id = a.preid)',
                ],
            })
        self.assertEqual(result, ['out', 'out_o1'])
        executed = ' '.join(str(c) for c in [args[0] for args, _ in cur.execute.call_args_list])
        self.assertIn('INNER JOIN', executed)
        self.assertIn('NOT EXISTS', executed)


class SchemaHandlerTests(SimpleTestCase):

    def test_schemas_handler_uses_contract(self):
        compute, _ = schemas.HANDLERS['trans_AIAction']
        self.assertEqual(
            compute([['id']], {'output_schema': [{'name': 'x', 'type': 'double'}, {'name': 'y', 'type': 'double'}]}),
            ['x', 'y'],
        )

    def test_schemas_handler_per_output(self):
        compute, _ = schemas.HANDLERS['trans_AIAction']
        self.assertEqual(
            compute(
                [['id']],
                {
                    'outputs_count': 2,
                    'output_schemas': [
                        [{'name': 'a', 'type': 'text'}],
                        [{'name': 'b', 'type': 'text'}],
                    ],
                },
            ),
            [['a'], ['b']],
        )


class CatalogTests(SimpleTestCase):

    def test_both_ai_nodes_hidden_together(self):
        catalog = load_catalog()
        self.assertIn('trans_AIAction', catalog)
        with mock.patch('gvsigol_plugin_geoetl.etl_ai.feature_enabled', return_value=False):
            hidden = available(catalog)
            self.assertNotIn('trans_AIText', hidden)
            self.assertNotIn('trans_AIAction', hidden)
        with mock.patch('gvsigol_plugin_geoetl.etl_ai.feature_enabled', return_value=True):
            shown = available(catalog)
            self.assertIn('trans_AIText', shown)
            self.assertIn('trans_AIAction', shown)


class ViewTests(SimpleTestCase):

    def test_generate_endpoint(self):
        request = RequestFactory().post(
            '/gvsigonline/etl/etl_ai_action_generate/',
            data=json.dumps({
                'instruction': 'unifica',
                'output_schema': [{'name': 'direccion', 'type': 'text'}],
                'input_schemas': [['calle']],
            }),
            content_type='application/json',
        )
        request.user = mock.Mock(is_authenticated=True, is_staff=True, is_superuser=True)
        with mock.patch('gvsigol_plugin_geoetl.etl_ai_action.feature_enabled', return_value=True), \
                mock.patch('gvsigol_plugin_geoetl.etl_ai_action.generate_sql',
                           return_value=('SELECT calle AS direccion FROM input_0',
                                         [{'name': 'direccion', 'type': 'text'}])):
            response = views.etl_ai_action_generate(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertIn('sql', body)
        self.assertEqual(body['sqls'][0], body['sql'])
        self.assertEqual(body['output_schema'][0]['name'], 'direccion')

    def test_generate_endpoint_multi(self):
        request = RequestFactory().post(
            '/gvsigonline/etl/etl_ai_action_generate/',
            data=json.dumps({
                'instruction': 'join y no unidos',
                'outputs_count': 2,
                'output_schemas': [[], []],
                'input_schemas': [['preid'], ['id']],
            }),
            content_type='application/json',
        )
        request.user = mock.Mock(is_authenticated=True, is_staff=True, is_superuser=True)
        with mock.patch('gvsigol_plugin_geoetl.etl_ai_action.feature_enabled', return_value=True), \
                mock.patch(
                    'gvsigol_plugin_geoetl.etl_ai_action.generate_sql',
                    return_value=(
                        ['SELECT 1 AS preid FROM input_0', 'SELECT 2 AS preid FROM input_0'],
                        [[{'name': 'preid', 'type': 'integer'}], [{'name': 'preid', 'type': 'integer'}]],
                    ),
                ):
            response = views.etl_ai_action_generate(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(len(body['sqls']), 2)
        self.assertEqual(len(body['output_schemas']), 2)

    def test_suggest_schema_endpoint(self):
        request = RequestFactory().post(
            '/gvsigonline/etl/etl_ai_action_suggest_schema/',
            data=json.dumps({
                'sql': 'SELECT 1 AS x FROM input_0',
                'input_schemas': [['id']],
            }),
            content_type='application/json',
        )
        request.user = mock.Mock(is_authenticated=True, is_staff=True, is_superuser=True)
        with mock.patch('gvsigol_plugin_geoetl.etl_ai_action.feature_enabled', return_value=True), \
                mock.patch('gvsigol_plugin_geoetl.etl_ai_action.suggest_schema_from_sql',
                           return_value=[{'name': 'x', 'type': 'integer'}]):
            response = views.etl_ai_action_suggest_schema(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['output_schema'][0]['name'], 'x')

    def test_generate_disabled(self):
        request = RequestFactory().post(
            '/gvsigonline/etl/etl_ai_action_generate/',
            data='{}',
            content_type='application/json',
        )
        request.user = mock.Mock(is_authenticated=True, is_staff=True, is_superuser=True)
        with mock.patch('gvsigol_plugin_geoetl.etl_ai_action.feature_enabled', return_value=False):
            response = views.etl_ai_action_generate(request)
        self.assertEqual(response.status_code, 403)

    def test_suggest_from_instruction_endpoint(self):
        request = RequestFactory().post(
            '/gvsigonline/etl/etl_ai_action_suggest_from_instruction/',
            data=json.dumps({
                'instruction': 'dos salidas',
                'input_schemas': [[{'name': 'id', 'type': 'integer'}]],
                'suggest_outputs': True,
                'suggest_schemas': True,
            }),
            content_type='application/json',
        )
        request.user = mock.Mock(is_authenticated=True, is_staff=True, is_superuser=True)
        with mock.patch('gvsigol_plugin_geoetl.etl_ai_action.feature_enabled', return_value=True), \
                mock.patch(
                    'gvsigol_plugin_geoetl.etl_ai_action.suggest_schemas_from_instruction',
                    return_value=(2, [[{'name': 'a', 'type': 'text'}], [{'name': 'b', 'type': 'text'}]]),
                ):
            response = views.etl_ai_action_suggest_from_instruction(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body['outputs_count'], 2)
        self.assertEqual(len(body['output_schemas']), 2)
