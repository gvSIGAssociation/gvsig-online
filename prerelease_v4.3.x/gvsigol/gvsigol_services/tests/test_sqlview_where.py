# -*- coding: utf-8 -*-
from django.test import SimpleTestCase
from psycopg2 import sql as sqlbuilder

from gvsigol_services.backend_postgis import (
    build_sqlview_where,
    _sqlview_where_condition,
    SqlFrom,
    SqlField,
    SqlJoinFields,
)


def _flatten_sql(obj, acc=None):
    """Turn a psycopg2.sql composable into a readable token list for assertions."""
    acc = acc if acc is not None else []
    if isinstance(obj, sqlbuilder.Composed):
        for part in obj:
            _flatten_sql(part, acc)
    elif isinstance(obj, sqlbuilder.SQL):
        acc.append(getattr(obj, 'string', None) or str(obj))
    elif isinstance(obj, sqlbuilder.Identifier):
        acc.append('.'.join('"%s"' % s for s in obj.strings))
    elif isinstance(obj, sqlbuilder.Literal):
        acc.append(repr(obj.wrapped))
    else:
        acc.append(str(obj))
    return acc


def _sql_text(obj):
    return ''.join(_flatten_sql(obj))


class SqlViewWhereCompilerTests(SimpleTestCase):

    def test_empty_where_returns_none(self):
        self.assertIsNone(build_sqlview_where(None))
        self.assertIsNone(build_sqlview_where({}))
        self.assertIsNone(build_sqlview_where({'operator': 'AND', 'conditions': []}))

    def test_equality_condition(self):
        clause = build_sqlview_where({
            'operator': 'AND',
            'conditions': [
                {'table_alias': 't1', 'name': 'estado', 'op': '=', 'value': 'activo'},
            ],
        })
        text = _sql_text(clause)
        self.assertIn('"t1"."estado"', text)
        self.assertIn('=', text)
        self.assertIn(repr('activo'), text)

    def test_is_null_without_value(self):
        clause = build_sqlview_where({
            'operator': 'AND',
            'conditions': [
                {'table_alias': 't1', 'name': 'deleted_at', 'op': 'IS NULL'},
            ],
        })
        text = _sql_text(clause)
        self.assertIn('IS NULL', text)
        self.assertIn('"t1"."deleted_at"', text)

    def test_or_joiner(self):
        clause = build_sqlview_where({
            'operator': 'OR',
            'conditions': [
                {'table_alias': 't1', 'name': 'a', 'op': '=', 'value': '1'},
                {'table_alias': 't1', 'name': 'b', 'op': '=', 'value': '2'},
            ],
        })
        text = _sql_text(clause)
        self.assertIn(' OR ', text)
        self.assertIn('"t1"."a"', text)
        self.assertIn('"t1"."b"', text)

    def test_mixed_and_or_groups(self):
        clause = build_sqlview_where({
            'operator': 'AND',
            'conditions': [
                {'table_alias': 't1', 'name': 'region', 'op': '=', 'value': 'norte'},
                {
                    'type': 'group',
                    'operator': 'OR',
                    'conditions': [
                        {'table_alias': 't1', 'name': 'a', 'op': '=', 'value': '1'},
                        {'table_alias': 't1', 'name': 'b', 'op': '=', 'value': '2'},
                    ],
                },
            ],
        })
        text = _sql_text(clause)
        self.assertIn(' AND ', text)
        self.assertIn(' OR ', text)
        self.assertIn('"t1"."region"', text)
        self.assertIn('"t1"."a"', text)
        self.assertIn('"t1"."b"', text)

    def test_in_operator(self):
        clause = build_sqlview_where({
            'operator': 'AND',
            'conditions': [
                {'table_alias': 't1', 'name': 'code', 'op': 'IN', 'value': 'a, b, c'},
            ],
        })
        text = _sql_text(clause)
        self.assertIn('IN', text)
        self.assertIn(repr('a'), text)
        self.assertIn(repr('c'), text)

    def test_contains_operator(self):
        clause = build_sqlview_where({
            'operator': 'AND',
            'conditions': [
                {'table_alias': 't1', 'name': 'name', 'op': 'CONTAINS', 'value': 'foo'},
            ],
        })
        text = _sql_text(clause)
        self.assertIn('ILIKE', text)
        self.assertIn(repr('%foo%'), text)

    def test_invalid_operator_skipped(self):
        self.assertIsNone(_sqlview_where_condition({
            'table_alias': 't1', 'name': 'a', 'op': 'DROP TABLE',
        }))
        self.assertIsNone(build_sqlview_where({
            'operator': 'AND',
            'conditions': [
                {'table_alias': 't1', 'name': 'a', 'op': 'DROP TABLE', 'value': 'x'},
            ],
        }))

    def test_create_view_includes_where(self):
        from gvsigol_services.backend_postgis import Introspect

        captured = {}

        class FakeCursor:
            def execute(self, query, params=None):
                captured['query'] = query

        introspect = Introspect.__new__(Introspect)
        introspect.cursor = FakeCursor()

        from_tables = [
            SqlFrom('public', 'table1', 't1'),
            SqlFrom(
                'public', 'table2', 't2',
                join_fields=[SqlJoinFields(SqlField('t1', 'id'), SqlField('t2', 't1_id'))],
            ),
        ]
        fields = [
            SqlField('t1', 'id', 'id'),
            SqlField('t2', 'name', 'name'),
        ]
        where = {
            'operator': 'AND',
            'conditions': [
                {'table_alias': 't1', 'name': 'estado', 'op': '=', 'value': 'activo'},
            ],
        }
        ok = introspect.create_view('public', 'my_view', from_tables, fields, where=where)
        self.assertTrue(ok)
        text = _sql_text(captured['query'])
        self.assertIn('CREATE VIEW', text)
        self.assertIn('WHERE', text)
        self.assertIn('"t1"."estado"', text)
        self.assertIn(repr('activo'), text)

    def test_create_view_without_where(self):
        from gvsigol_services.backend_postgis import Introspect

        captured = {}

        class FakeCursor:
            def execute(self, query, params=None):
                captured['query'] = query

        introspect = Introspect.__new__(Introspect)
        introspect.cursor = FakeCursor()
        from_tables = [SqlFrom('public', 'table1', 't1')]
        fields = [SqlField('t1', 'id', 'id')]
        ok = introspect.create_view('public', 'my_view', from_tables, fields)
        self.assertTrue(ok)
        text = _sql_text(captured['query'])
        self.assertIn('CREATE VIEW', text)
        self.assertNotIn('WHERE', text)


class SqlViewSelectFieldsTests(SimpleTestCase):

    def test_main_pk_keeps_original_alias_when_joined_has_same_name(self):
        from gvsigol_services.backend_postgis import prepare_sqlview_select_fields
        fields = [
            SqlField('t1', 'ogc_fid', 'ogc_fid'),
            SqlField('t1', 'wkb_geometry', 'wkb_geometry'),
            SqlField('t2', 'ogc_fid', 'ogc_fid'),
            SqlField('t2', 'wkb_geometry', 'wkb_geometry'),
        ]
        result, pk_aliases, geom, pk_json = prepare_sqlview_select_fields(
            fields, 't1', ['ogc_fid'],
            {('t1', 'wkb_geometry'), ('t2', 'wkb_geometry')},
            geometry_choice={'table_alias': 't1', 'name': 'wkb_geometry'},
        )
        aliases = {(f.table_alias, f.field): f.alias for f in result}
        self.assertEqual(pk_aliases, ['ogc_fid'])
        self.assertEqual(pk_json['mode'], 'field')
        self.assertEqual(aliases[('t1', 'ogc_fid')], 'ogc_fid')
        self.assertEqual(aliases[('t2', 'ogc_fid')], 'ogc_fid_1')
        self.assertNotIn(('t2', 'wkb_geometry'), aliases)
        self.assertEqual(geom['alias'], 'wkb_geometry')
        self.assertEqual(geom['table_alias'], 't1')

    def test_generated_pk_adds_unique_expression(self):
        from gvsigol_services.backend_postgis import prepare_sqlview_select_fields, build_generated_pk_expression
        from psycopg2 import sql as sqlbuilder
        fields = [
            SqlField('t1', 'nome', 'nome'),
            SqlField('t2', 'nome', 'nome'),
        ]
        result, pk_aliases, geom, pk_json = prepare_sqlview_select_fields(
            fields, 't1', ['ogc_fid'],
            set(),
            pk_choice={'mode': 'generated'},
            table_pks={'t1': ['ogc_fid'], 't2': ['ogc_fid']},
        )
        self.assertEqual(pk_aliases, ['gvol_pk'])
        self.assertEqual(pk_json['mode'], 'generated')
        generated = [f for f in result if f.expression is not None]
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0].alias, 'gvol_pk')
        # source PKs are not forced into the SELECT
        names = [(f.table_alias, f.field) for f in result if f.expression is None]
        self.assertEqual(names, [('t1', 'nome'), ('t2', 'nome')])
        expr = build_generated_pk_expression([('t1', 'ogc_fid'), ('t2', 'ogc_fid')])
        text = expr.as_string(None) if hasattr(expr, 'as_string') else str(expr)
        # Fallback flatten for Composed without connection
        if 'ROW_NUMBER' not in text:
            def _flatten(obj, acc=None):
                acc = acc if acc is not None else []
                if isinstance(obj, sqlbuilder.Composed):
                    for part in obj:
                        _flatten(part, acc)
                elif isinstance(obj, sqlbuilder.SQL):
                    acc.append(getattr(obj, 'string', None) or str(obj))
                elif isinstance(obj, sqlbuilder.Identifier):
                    acc.append('.'.join('"%s"' % s for s in obj.strings))
                else:
                    acc.append(str(obj))
                return ''.join(acc)
            text = _flatten(expr)
        self.assertIn('ROW_NUMBER()', text)
        self.assertIn('ORDER BY', text)
        self.assertIn('"t1"."ogc_fid"', text)
        self.assertIn('"t2"."ogc_fid"', text)

    def test_chosen_field_pk_is_auto_included(self):
        from gvsigol_services.backend_postgis import prepare_sqlview_select_fields
        fields = [
            SqlField('t1', 'nome', 'nome'),
        ]
        result, pk_aliases, geom, pk_json = prepare_sqlview_select_fields(
            fields, 't1', ['ogc_fid'],
            set(),
            pk_choice={'mode': 'field', 'table_alias': 't1', 'name': 'ogc_fid'},
        )
        self.assertEqual(pk_aliases, ['ogc_fid'])
        self.assertIn(('t1', 'ogc_fid'), {(f.table_alias, f.field) for f in result})

    def test_multiple_geometries_without_choice_raise(self):
        from gvsigol_services.backend_postgis import prepare_sqlview_select_fields, SqlViewFieldError
        fields = [
            SqlField('t1', 'ogc_fid', 'ogc_fid'),
            SqlField('t1', 'wkb_geometry', 'wkb_geometry'),
            SqlField('t2', 'wkb_geometry', 'wkb_geometry'),
        ]
        with self.assertRaises(SqlViewFieldError) as ctx:
            prepare_sqlview_select_fields(
                fields, 't1', ['ogc_fid'],
                {('t1', 'wkb_geometry'), ('t2', 'wkb_geometry')},
            )
        self.assertEqual(ctx.exception.code, 'multiple_geometry')

    def test_single_geometry_is_auto_selected(self):
        from gvsigol_services.backend_postgis import prepare_sqlview_select_fields
        fields = [
            SqlField('t1', 'ogc_fid', 'ogc_fid'),
            SqlField('t1', 'wkb_geometry', 'wkb_geometry'),
            SqlField('t2', 'name', 'name'),
        ]
        result, pk_aliases, geom, pk_json = prepare_sqlview_select_fields(
            fields, 't1', ['ogc_fid'],
            {('t1', 'wkb_geometry')},
        )
        self.assertEqual(pk_aliases, ['ogc_fid'])
        self.assertEqual(geom['name'], 'wkb_geometry')
        self.assertEqual(len(result), 3)
