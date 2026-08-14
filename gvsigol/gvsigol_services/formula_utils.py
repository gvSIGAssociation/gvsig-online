# -*- coding: utf-8 -*-
"""
Safe arithmetic formula parsing/compilation for calculated attributes.

Expressions may only contain numbers, field identifiers (optionally
qualified as alias.field), parentheses, the + - * / ** operators and a
closed whitelist of mathematical and aggregate functions
(see FUNCTION_SIGNATURES / AGGREGATE_FUNCTIONS).

When ``join_sources`` is provided, fields from related aliases are compiled
as correlated subqueries keyed by the join. One-to-many joins require an
aggregate (sum/avg/min/max/count) so each base row receives a single value.
"""
from __future__ import unicode_literals

import ast
import re

from django.utils.translation import gettext as _

from gvsigol_services.unit_catalog import (
    apply_result_unit,
    combine_dimensions,
    power_dimension,
    resolve_unit_meta,
)

_FIELD_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_QUALIFIED_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$')

# Operators allowed in AST
_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_UNARYOPS = (ast.UAdd, ast.USub)

# Simple dimension algebra for unit coherence checks
_DIM_COMPATIBLE_OPS = {
    ast.Add: 'same',
    ast.Sub: 'same',
    ast.Mult: 'product',
    ast.Div: 'quotient',
}

# Aggregate functions for 1:N joins (compiled as correlated subqueries)
AGGREGATE_FUNCTIONS = frozenset({'sum', 'avg', 'min', 'max', 'count'})

# name -> (min_args, max_args or None for variadic)
FUNCTION_SIGNATURES = {
    'sqrt': (1, 1),
    'abs': (1, 1),
    'round': (1, 2),
    'floor': (1, 1),
    'ceil': (1, 1),
    'power': (2, 2),
    'ln': (1, 1),
    'log10': (1, 1),
    'exp': (1, 1),
    'greatest': (2, None),
    'least': (2, None),
    'sum': (1, 1),
    'avg': (1, 1),
    'min': (1, 1),
    'max': (1, 1),
    'count': (1, 1),
}

# Functions whose argument and result must be dimensionless
_DIMENSIONLESS_FUNCTIONS = ('ln', 'log10', 'exp')
# Functions that keep the dimension of their single argument
_DIMENSION_PRESERVING_FUNCTIONS = ('abs', 'round', 'floor', 'ceil')
_AGGREGATE_DIMENSION_PRESERVING = frozenset({'sum', 'avg', 'min', 'max'})


def _as_double(sql):
    return '({0})::double precision'.format(sql)


def _quote_ident(name):
    if not name or not _FIELD_RE.match(name):
        raise FormulaError(_('Invalid identifier: {0}').format(name))
    return '"{0}"'.format(name)


def _literal_number(node):
    """Return the numeric value of a literal node (allowing a unary sign), else None."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _UNARYOPS):
        value = _literal_number(node.operand)
        if value is None:
            return None
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            return None
        return float(node.value)
    if isinstance(node, ast.Num):  # pragma: no cover - older Python ast
        return float(node.n)
    return None


def _power_dimension(base_dim, exponent_node, exponent_dim):
    if exponent_dim is not None:
        raise FormulaError(_('The exponent must be dimensionless'))
    if base_dim is None:
        return None
    exponent = _literal_number(exponent_node)
    if exponent is None:
        raise FormulaError(
            _('The exponent must be a numeric literal when the base has units'))
    return power_dimension(base_dim, exponent)


class FormulaError(ValueError):
    """Raised when a formula cannot be validated or compiled."""
    pass


class _FormulaCompiler(ast.NodeVisitor):
    """
    Compile a restricted arithmetic AST into a SQL expression fragment
    and collect referenced fields.

    Field values with a known unit are converted to the catalogue base for
    their dimension before arithmetic; the caller may then convert the
    result into a requested unit.

    When ``join_sources`` is set, joined fields become correlated subqueries
    (scalar for 1:1, aggregate for 1:N).
    """

    def __init__(self, allowed_fields, field_sql_resolver, field_units=None,
                 join_sources=None, base_alias='t1'):
        """
        Parameters
        ----------
        allowed_fields : set[str]
            Allowed identifiers, either bare field names or "alias.field".
        field_sql_resolver : callable(str) -> sqlbuilder composable or str
            Maps an identifier to a SQL fragment (already validated).
        field_units : dict[str, unit_meta] | None
        join_sources : dict[str, dict] | None
            alias -> {schema, table, join_self, join_other, is_many}
        base_alias : str
            Alias of the layer that owns each result row (usually t1).
        """
        self.allowed_fields = allowed_fields
        self.field_sql_resolver = field_sql_resolver
        self.field_units = field_units or {}
        self.join_sources = join_sources or {}
        self.base_alias = base_alias
        self.referenced_fields = set()
        self.result_dimension = None
        self._aggregate_depth = 0
        self.used_aggregates = False

    def compile(self, expression):
        expression = (expression or '').strip()
        if not expression:
            raise FormulaError(_('Empty formula'))
        if len(expression) > 2000:
            raise FormulaError(_('Formula is too long'))
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as exc:
            raise FormulaError(_('Invalid formula syntax: {0}').format(str(exc)))
        sql_fragment, dimension = self.visit(tree.body)
        self.result_dimension = dimension
        return sql_fragment

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_BinOp(self, node):
        if not isinstance(node.op, _BINOPS):
            raise FormulaError(_('Operator not allowed'))
        left_sql, left_dim = self.visit(node.left)
        right_sql, right_dim = self.visit(node.right)
        if isinstance(node.op, ast.Pow):
            dim = _power_dimension(left_dim, node.right, right_dim)
            return '(power({0}, {1}))'.format(
                _as_double(left_sql), _as_double(right_sql)), dim
        op_kind = _DIM_COMPATIBLE_OPS[type(node.op)]
        dim = combine_dimensions(left_dim, right_dim, op_kind)
        if isinstance(node.op, ast.Add):
            op = '+'
        elif isinstance(node.op, ast.Sub):
            op = '-'
        elif isinstance(node.op, ast.Mult):
            op = '*'
        else:
            op = '/'
            # Guard division by zero at SQL level with NULLIF when right is a plain field/number is hard;
            # wrap divisor.
            right_sql = 'NULLIF(({0})::double precision, 0)'.format(right_sql)
        return '(({0}) {1} ({2}))'.format(left_sql, op, right_sql), dim

    def visit_UnaryOp(self, node):
        if not isinstance(node.op, _UNARYOPS):
            raise FormulaError(_('Unary operator not allowed'))
        operand_sql, dim = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return '(-({0}))'.format(operand_sql), dim
        return '({0})'.format(operand_sql), dim

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise FormulaError(_('Invalid function call'))
        name = node.func.id.lower()
        signature = FUNCTION_SIGNATURES.get(name)
        if signature is None:
            raise FormulaError(_('Function not allowed: {0}').format(node.func.id))
        if node.keywords or getattr(node, 'starargs', None) or getattr(node, 'kwargs', None):
            raise FormulaError(_('Function arguments must be positional'))
        min_args, max_args = signature
        if len(node.args) < min_args or (max_args is not None and len(node.args) > max_args):
            raise FormulaError(
                _('Wrong number of arguments for "{0}"').format(name))
        if name in AGGREGATE_FUNCTIONS:
            return self._compile_aggregate(name, node.args[0])
        args = [self.visit(arg) for arg in node.args]
        return self._compile_function(name, node, args)

    def _qualified_field_from_node(self, node):
        """Require a single field reference (bare or alias.field) as aggregate arg."""
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if not _FIELD_RE.match(node.value.id) or not _FIELD_RE.match(node.attr):
                raise FormulaError(_('Invalid field reference'))
            return '{0}.{1}'.format(node.value.id, node.attr)
        if isinstance(node, ast.Name):
            if not _FIELD_RE.match(node.id):
                raise FormulaError(_('Invalid field reference'))
            return node.id
        raise FormulaError(
            _('Aggregation arguments must be a single field reference '
              '(e.g. sum(t2.attribute))'))

    def _correlated_subquery(self, alias, select_sql, limit_one=False):
        meta = self.join_sources[alias]
        schema = _quote_ident(meta['schema'])
        table = _quote_ident(meta['table'])
        alias_q = _quote_ident(alias)
        join_other = _quote_ident(meta['join_other'])
        join_self = _quote_ident(meta['join_self'])
        base = _quote_ident(self.base_alias)
        limit = ' LIMIT 1' if limit_one else ''
        return (
            '(SELECT {select_sql} FROM {schema}.{table} AS {alias} '
            'WHERE {alias}.{join_other} = {base}.{join_self}{limit})'
        ).format(
            select_sql=select_sql,
            schema=schema,
            table=table,
            alias=alias_q,
            join_other=join_other,
            base=base,
            join_self=join_self,
            limit=limit,
        )

    def _compile_aggregate(self, name, arg_node):
        if self._aggregate_depth:
            raise FormulaError(_('Nested aggregations are not allowed'))
        if not self.join_sources:
            raise FormulaError(
                _('Aggregations ({0}) can only be used with a JOIN').format(name))

        qualified = self._qualified_field_from_node(arg_node)
        if qualified not in self.allowed_fields:
            raise FormulaError(_('Unknown or disallowed field: {0}').format(qualified))
        if '.' not in qualified:
            raise FormulaError(
                _('Aggregations must target a field from a joined layer '
                  '(e.g. {0}(t2.campo))').format(name))

        alias, _field = qualified.split('.', 1)
        if alias == self.base_alias:
            raise FormulaError(
                _('Aggregations must target a field from a joined layer, not {0}').format(
                    self.base_alias))
        if alias not in self.join_sources:
            raise FormulaError(
                _('Unknown join alias in aggregation: {0}').format(alias))

        self.used_aggregates = True
        self._aggregate_depth += 1
        try:
            # Resolve the field as a local column inside the subquery
            # (alias.field → "alias"."field"), not as an outer reference.
            field_sql, field_dim = self._resolve_field(qualified)
        finally:
            self._aggregate_depth -= 1

        pg_fn = name.upper()
        if name == 'count':
            inner = 'COUNT({0})'.format(field_sql)
            out_dim = None
        else:
            inner = '{0}({1})'.format(pg_fn, _as_double(field_sql))
            out_dim = field_dim if name in _AGGREGATE_DIMENSION_PRESERVING else None

        return self._correlated_subquery(alias, inner), out_dim

    def _compile_function(self, name, node, args):
        first_sql, first_dim = args[0]
        value = _as_double(first_sql)

        if name in _DIMENSION_PRESERVING_FUNCTIONS:
            if name == 'round':
                if len(args) == 2:
                    decimals = _literal_number(node.args[1])
                    if decimals is None or decimals < 0 or not float(decimals).is_integer():
                        raise FormulaError(
                            _('The number of decimals must be a non-negative integer literal'))
                    return '(round({0}::numeric, {1})::double precision)'.format(
                        value, int(decimals)), first_dim
                return '(round({0}::numeric)::double precision)'.format(value), first_dim
            return '({0}({1}))'.format(name, value), first_dim

        if name == 'sqrt':
            # Avoid aborting the whole statement on negative values
            out_dim = power_dimension(first_dim, 0.5) if first_dim else None
            return ('(CASE WHEN {0} >= 0 THEN sqrt({0}) ELSE NULL END)'.format(value),
                    out_dim)

        if name in _DIMENSIONLESS_FUNCTIONS:
            if first_dim is not None:
                raise FormulaError(
                    _('"{0}" requires a dimensionless argument, got "{1}"').format(
                        name, first_dim))
            if name == 'exp':
                return '(exp({0}))'.format(value), None
            # ln/log10 are undefined for values <= 0
            return '(CASE WHEN {0} > 0 THEN {1}({0}) ELSE NULL END)'.format(value, name), None

        if name == 'power':
            exponent_sql, exponent_dim = args[1]
            dim = _power_dimension(first_dim, node.args[1], exponent_dim)
            return '(power({0}, {1}))'.format(value, _as_double(exponent_sql)), dim

        # greatest/least: all operands must share the same dimension
        dim = first_dim
        for arg_sql, arg_dim in args[1:]:
            dim = combine_dimensions(dim, arg_dim, 'same')
        operands = ', '.join(_as_double(arg_sql) for arg_sql, _arg_dim in args)
        return '({0}({1}))'.format(name, operands), dim

    def _resolve_field(self, name):
        self.referenced_fields.add(name)
        sql = self.field_sql_resolver(name)
        unit_info = resolve_unit_meta(self.field_units.get(name))
        if unit_info is None:
            return sql, None
        factor = unit_info['factor']
        if factor != 1.0:
            sql = '(({0}) * {1})'.format(_as_double(sql), repr(factor))
        else:
            sql = _as_double(sql)
        return sql, unit_info['dimension']

    def _resolve_joined_or_local(self, qualified_or_bare):
        """
        Resolve a field. Joined aliases (when join_sources is active) become
        correlated scalar subqueries, unless we are already inside an aggregate
        (the aggregate builds its own subquery).
        """
        name = qualified_or_bare
        if '.' in name and self.join_sources and not self._aggregate_depth:
            alias, _field = name.split('.', 1)
            if alias in self.join_sources:
                meta = self.join_sources[alias]
                if meta.get('is_many'):
                    raise FormulaError(
                        _('Field "{0}" comes from a one-to-many join; wrap it in '
                          'sum(), avg(), min(), max() or count()').format(name))
                field_sql, field_dim = self._resolve_field(name)
                return self._correlated_subquery(
                    alias, _as_double(field_sql), limit_one=True), field_dim
        return self._resolve_field(name)

    def visit_Name(self, node):
        name = node.id
        if name not in self.allowed_fields:
            raise FormulaError(_('Unknown or disallowed field: {0}').format(name))
        return self._resolve_joined_or_local(name)

    def visit_Attribute(self, node):
        # alias.field → Name(alias).attr
        if not isinstance(node.value, ast.Name):
            raise FormulaError(_('Invalid field reference'))
        qualified = '{0}.{1}'.format(node.value.id, node.attr)
        if qualified not in self.allowed_fields:
            raise FormulaError(_('Unknown or disallowed field: {0}').format(qualified))
        if not _FIELD_RE.match(node.value.id) or not _FIELD_RE.match(node.attr):
            raise FormulaError(_('Invalid field reference'))
        return self._resolve_joined_or_local(qualified)

    def visit_Num(self, node):  # py2/older ast
        return repr(float(node.n)), None

    def visit_Constant(self, node):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaError(_('Only numeric literals are allowed'))
        return repr(float(node.value)), None

    def generic_visit(self, node):
        raise FormulaError(_('Unsupported expression element: {0}').format(type(node).__name__))


def validate_identifier(name):
    if not name or not _FIELD_RE.match(name):
        raise FormulaError(_('Invalid identifier: {0}').format(name))
    return name.lower()


def compile_formula(expression, allowed_fields, field_sql_resolver, field_units=None,
                    result_unit=None, join_sources=None, base_alias='t1'):
    """
    Compile expression to a SQL fragment and return metadata.

    Field values are converted to catalogue base units before arithmetic.
    If ``result_unit`` is provided and matches the resulting dimension, the
    SQL is converted from the base into that unit.

    When ``join_sources`` is provided, related fields are emitted as
    correlated subqueries so 1:N joins can be reduced with aggregates.

    Returns
    -------
    dict with keys: sql, referenced_fields, result_dimension, result_unit,
    used_aggregates
    """
    allowed = set(allowed_fields)
    compiler = _FormulaCompiler(
        allowed, field_sql_resolver, field_units=field_units,
        join_sources=join_sources, base_alias=base_alias)
    sql = compiler.compile(expression)
    sql, dimension, unit_code = apply_result_unit(
        sql, compiler.result_dimension, result_unit)
    return {
        'sql': sql,
        'referenced_fields': sorted(compiler.referenced_fields),
        'result_dimension': dimension,
        'result_unit': unit_code,
        'used_aggregates': compiler.used_aggregates,
    }


def preview_units(expression, allowed_fields, field_units, result_unit=None):
    """Validate units without producing SQL (resolver returns placeholders)."""
    def resolver(name):
        return '1'
    return compile_formula(
        expression, allowed_fields, resolver,
        field_units=field_units, result_unit=result_unit)
