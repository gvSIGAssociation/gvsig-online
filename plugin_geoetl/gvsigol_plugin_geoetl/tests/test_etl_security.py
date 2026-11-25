# -*- coding: utf-8 -*-
from unittest import mock

from django.test import SimpleTestCase

from gvsigol_plugin_geoetl import etl_ai_action, etl_security, etl_tasks


class AISelectValidationTests(SimpleTestCase):

    ALLOWED = [
        'SELECT a.*, b."NOMBRE" FROM input_0 AS a INNER JOIN input_1 AS b ON a."ID" = b."ID"',
        "SELECT id, ST_Buffer(wkb_geometry, 10)::geometry(Polygon,25830) AS wkb_geometry "
        "FROM input_0 WHERE nombre ILIKE '%x%'",
        "WITH t AS (SELECT * FROM input_0) SELECT count(*) AS n FROM t",
        "SELECT a.* FROM input_0 a WHERE NOT EXISTS "
        "(SELECT 1 FROM input_1 b WHERE ST_Intersects(a.wkb_geometry, b.wkb_geometry))",
        "SELECT a.*, (SELECT b.id FROM input_1 b ORDER BY a.wkb_geometry <-> b.wkb_geometry LIMIT 1) AS near "
        "FROM input_0 a",
        "SELECT * FROM input_0 a, input_1 b WHERE a.wkb_geometry && b.wkb_geometry",
        "SELECT * FROM input_0, LATERAL ST_Dump(wkb_geometry) AS d",
        "SELECT * FROM input_0 UNION ALL SELECT * FROM input_1",
        "SELECT id, pg_typeof(id) AS t FROM input_0",
        "SELECT public.ST_AsText(wkb_geometry) AS wkt FROM input_0",
    ]

    BLOCKED = [
        "SELECT DropGeometryTable('public','auth_user')",
        "SELECT AddGeometryColumn('public','auth_user','g',4326,'POINT',2)",
        "SELECT username, password FROM public.auth_user",
        "SELECT * FROM input_0 WHERE id IN (SELECT id FROM ds_brasil.municipios)",
        "SELECT * FROM auth_user",
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity",
        "SELECT pg_sleep(1000)",
        "SELECT table_to_xml('public.auth_user', true, false, '')",
        "SELECT query_to_xml('select 1', true, false, '')",
        "SELECT nextval('s')",
        "SELECT set_config('search_path', 'public', false)",
        "SELECT lo_import('/etc/passwd')",
        "SELECT myschema.peligrosa(id) FROM input_0",
        "SELECT 1; DROP TABLE x",
    ]

    def test_legitimate_sql_passes(self):
        for text in self.ALLOWED:
            with self.subTest(sql=text):
                etl_ai_action.sanitize_sql(text)

    def test_attacks_are_blocked(self):
        for text in self.BLOCKED:
            with self.subTest(sql=text):
                with self.assertRaises(ValueError):
                    etl_ai_action.sanitize_sql(text)

    def test_bind_sql_validates_before_binding(self):
        with self.assertRaises(ValueError):
            etl_ai_action.bind_sql("SELECT DropGeometryTable('public','t')", ['tabla'])


class NodeTypeTests(SimpleTestCase):

    def test_real_node_resolves(self):
        self.assertIs(etl_security.resolve_node_function(etl_tasks, 'trans_Filter'), etl_tasks.trans_Filter)

    def test_helpers_and_garbage_are_rejected(self):
        for node_type in ('move', 'merge_tables', 'get_type_n_srid', 'os', '__import__',
                          'trans_Filter.__globals__', 'input_', None, 123, 'trans_NoExiste'):
            with self.subTest(node_type=node_type):
                with self.assertRaises(ValueError):
                    etl_security.resolve_node_function(etl_tasks, node_type)


class ConnectionPermissionTests(SimpleTestCase):

    def test_collects_node_and_workspace_connections(self):
        names = etl_security.canvas_connection_names(
            [{'db': 'pg_prod'}, {'db-option': 'salida'}, {'api': 'segex'}, {'db': ''}, 'basura'],
            {'db': 'pre_post', 'sql-before': ['select 1'], 'sql-after': []},
        )
        self.assertEqual(names, {'pg_prod', 'salida', 'segex', 'pre_post'})

    def test_workspace_db_ignored_when_unused(self):
        names = etl_security.canvas_connection_names(
            [], {'db': 'pre_post', 'sql-before': [], 'sql-after': [], 'radio-params-user': 'integer'},
        )
        self.assertEqual(names, set())

    def test_denied_connection_raises(self):
        with mock.patch.object(etl_security, 'allowed_connection_names', return_value={'mia'}):
            etl_security.assert_connections_allowed('pepe', {'mia'})
            with self.assertRaises(PermissionError) as ctx:
                etl_security.assert_connections_allowed('pepe', {'mia', 'produccion'})
            self.assertIn('produccion', str(ctx.exception))

    def test_superuser_allows_all(self):
        with mock.patch.object(etl_security, 'allowed_connection_names', return_value=None):
            etl_security.assert_connections_allowed('admin', {'cualquiera'})
