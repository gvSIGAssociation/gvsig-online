# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from gvsigol_services.formula_utils import FormulaError, compile_formula, preview_units


def _resolver(name):
    if '.' in name:
        a, f = name.split('.', 1)
        return '"{0}"."{1}"'.format(a, f)
    return '"{0}"'.format(name)


class FormulaUtilsTests(SimpleTestCase):

    def test_same_layer_arithmetic(self):
        result = compile_formula('a + b * 2', {'a', 'b'}, _resolver)
        self.assertIn('"a"', result['sql'])
        self.assertIn('"b"', result['sql'])
        self.assertEqual(sorted(result['referenced_fields']), ['a', 'b'])

    def test_qualified_fields_density(self):
        result = compile_formula(
            't1.pop / t2.area',
            {'t1.pop', 't2.area'},
            _resolver,
            field_units={'t1.pop': 'hab', 't2.area': 'km2'},
            result_unit='hab/km2',
        )
        self.assertIn('"t1"."pop"', result['sql'])
        self.assertIn('NULLIF', result['sql'])
        # km2 -> m2 (*1e6), then density base hab/m2, then /1e-6 to hab/km2
        self.assertEqual(result['result_dimension'], 'density')
        self.assertEqual(result['result_unit'], 'hab/km2')
        self.assertIn('1000000.0', result['sql'])

    def test_incompatible_units_on_add(self):
        with self.assertRaises(FormulaError):
            compile_formula(
                'a + b',
                {'a', 'b'},
                _resolver,
                field_units={'a': 'hab', 'b': 'km2'},
            )

    def test_compatible_units_on_add_same_dimension(self):
        result = compile_formula(
            'a + b',
            {'a', 'b'},
            _resolver,
            field_units={'a': 'hab', 'b': 'personas'},
        )
        self.assertEqual(result['result_dimension'], 'population')

    def test_auto_converts_length_before_add(self):
        result = compile_formula(
            'a + b',
            {'a', 'b'},
            _resolver,
            field_units={'a': 'km', 'b': 'm'},
            result_unit='km',
        )
        self.assertEqual(result['result_dimension'], 'length')
        self.assertEqual(result['result_unit'], 'km')
        self.assertIn('* 1000.0', result['sql'])  # km -> m
        self.assertIn('/ 1000.0', result['sql'])  # m -> km

    def test_rejects_unknown_unit(self):
        with self.assertRaises(FormulaError):
            compile_formula(
                'a + 1',
                {'a'},
                _resolver,
                field_units={'a': 'parsecs'},
            )

    def test_rejects_mismatched_result_unit(self):
        with self.assertRaises(FormulaError):
            compile_formula(
                'a + b',
                {'a', 'b'},
                _resolver,
                field_units={'a': 'm', 'b': 'm'},
                result_unit='hab',
            )

    def test_rejects_unknown_function_calls(self):
        with self.assertRaises(FormulaError):
            compile_formula('pg_sleep(a)', {'a'}, _resolver)

    def test_power_operator_length_squared_is_area(self):
        result = compile_formula('a ** 2', {'a'}, _resolver, field_units={'a': 'm'},
                                 result_unit='m2')
        self.assertIn('power', result['sql'])
        self.assertEqual(result['result_dimension'], 'area')
        self.assertEqual(result['result_unit'], 'm2')

    def test_power_requires_literal_exponent_with_units(self):
        with self.assertRaises(FormulaError):
            compile_formula('a ** b', {'a', 'b'}, _resolver, field_units={'a': 'm'})

    def test_sqrt_of_area_is_length(self):
        result = compile_formula('sqrt(a)', {'a'}, _resolver, field_units={'a': 'm2'},
                                 result_unit='m')
        self.assertIn('sqrt', result['sql'])
        self.assertEqual(result['result_dimension'], 'length')

    def test_round_with_decimals(self):
        result = compile_formula('round(a / b, 2)', {'a', 'b'}, _resolver)
        self.assertIn('round(', result['sql'])
        self.assertIn('numeric, 2', result['sql'])

    def test_round_rejects_non_literal_decimals(self):
        with self.assertRaises(FormulaError):
            compile_formula('round(a, b)', {'a', 'b'}, _resolver)

    def test_abs_preserves_dimension(self):
        result = compile_formula('abs(a - b)', {'a', 'b'}, _resolver,
                                 field_units={'a': 'hab', 'b': 'hab'})
        self.assertEqual(result['result_dimension'], 'population')

    def test_log_requires_dimensionless_argument(self):
        with self.assertRaises(FormulaError):
            compile_formula('ln(a)', {'a'}, _resolver, field_units={'a': 'hab'})

    def test_greatest_requires_same_dimension(self):
        with self.assertRaises(FormulaError):
            compile_formula('greatest(a, b)', {'a', 'b'}, _resolver,
                            field_units={'a': 'hab', 'b': 'km2'})

    def test_wrong_arity_is_rejected(self):
        with self.assertRaises(FormulaError):
            compile_formula('sqrt(a, b)', {'a', 'b'}, _resolver)

    def test_rejects_unknown_field(self):
        with self.assertRaises(FormulaError):
            compile_formula('a + c', {'a', 'b'}, _resolver)

    def test_same_dimension_division_is_dimensionless(self):
        result = preview_units(
            'a / b',
            {'a', 'b'},
            {'a': 'hab', 'b': 'hab'},
        )
        self.assertIsNone(result['result_dimension'])

    def test_unary_minus(self):
        result = compile_formula('-a + 1.5', {'a'}, _resolver)
        self.assertIn('-', result['sql'])
