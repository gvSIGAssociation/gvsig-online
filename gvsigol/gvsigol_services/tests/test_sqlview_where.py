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
