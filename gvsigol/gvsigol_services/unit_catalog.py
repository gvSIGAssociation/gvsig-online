# -*- coding: utf-8 -*-
"""
Curated unit catalogue for calculated attributes.

Every unit belongs to a physical dimension and carries a factor that converts
a value into the catalogue base for that dimension. Arithmetic is performed
in base units; the result is converted back to the requested unit when the
dimensions match.
"""
from __future__ import unicode_literals

from django.utils.translation import gettext as _


def _formula_error(message):
    # Lazy import avoids a circular dependency with formula_utils
    from gvsigol_services.formula_utils import FormulaError
    return FormulaError(message)


# code -> {dimension, factor_to_base, label}
UNIT_CATALOG = {
    # length (base: m)
    'm': {'dimension': 'length', 'factor': 1.0, 'label': 'm'},
    'cm': {'dimension': 'length', 'factor': 0.01, 'label': 'cm'},
    'km': {'dimension': 'length', 'factor': 1000.0, 'label': 'km'},
    # area (base: m²)
    'm2': {'dimension': 'area', 'factor': 1.0, 'label': 'm²'},
    'ha': {'dimension': 'area', 'factor': 10000.0, 'label': 'ha'},
    'km2': {'dimension': 'area', 'factor': 1000000.0, 'label': 'km²'},
    # volume (base: m³)
    'm3': {'dimension': 'volume', 'factor': 1.0, 'label': 'm³'},
    'l': {'dimension': 'volume', 'factor': 0.001, 'label': 'L'},
    # population (base: person)
    'hab': {'dimension': 'population', 'factor': 1.0, 'label': 'hab'},
    'personas': {'dimension': 'population', 'factor': 1.0, 'label': 'personas'},
    # density (base: persons / m²)
    'hab/m2': {'dimension': 'density', 'factor': 1.0, 'label': 'hab/m²'},
    'hab/ha': {'dimension': 'density', 'factor': 0.0001, 'label': 'hab/ha'},
    'hab/km2': {'dimension': 'density', 'factor': 0.000001, 'label': 'hab/km²'},
    # mass (base: kg)
    'kg': {'dimension': 'mass', 'factor': 1.0, 'label': 'kg'},
    't': {'dimension': 'mass', 'factor': 1000.0, 'label': 't'},
    # time (base: s)
    's': {'dimension': 'time', 'factor': 1.0, 'label': 's'},
    'min': {'dimension': 'time', 'factor': 60.0, 'label': 'min'},
    'h': {'dimension': 'time', 'factor': 3600.0, 'label': 'h'},
    'd': {'dimension': 'time', 'factor': 86400.0, 'label': 'd'},
    # percent / ratio
    '%': {'dimension': 'percent', 'factor': 1.0, 'label': '%'},
    # currencies are not convertible between themselves
    'EUR': {'dimension': 'currency_EUR', 'factor': 1.0, 'label': 'EUR'},
    'BRL': {'dimension': 'currency_BRL', 'factor': 1.0, 'label': 'BRL'},
    'USD': {'dimension': 'currency_USD', 'factor': 1.0, 'label': 'USD'},
}

_DIM_PRODUCT = {
    ('length', 'length'): 'area',
    ('length', 'area'): 'volume',
    ('area', 'length'): 'volume',
}

_DIM_QUOTIENT = {
    ('area', 'length'): 'length',
    ('volume', 'area'): 'length',
    ('volume', 'length'): 'area',
    ('population', 'area'): 'density',
}

_DIM_POWER = {
    ('length', 2): 'area',
    ('length', 3): 'volume',
    ('area', 0.5): 'length',
    ('volume', 1.0 / 3.0): 'length',
}


def list_units():
    """Return units ready for UI select options."""
    return [
        {
            'value': code,
            'label': meta['label'],
            'dimension': meta['dimension'],
        }
        for code, meta in UNIT_CATALOG.items()
    ]


def get_unit(code):
    if not code:
        return None
    key = str(code).strip()
    meta = UNIT_CATALOG.get(key)
    if meta is None:
        # tolerate unicode superscript aliases from older conf
        aliases = {
            'm²': 'm2', 'km²': 'km2', 'm³': 'm3',
            'hab/m²': 'hab/m2', 'hab/km²': 'hab/km2',
        }
        key = aliases.get(key, key)
        meta = UNIT_CATALOG.get(key)
    if meta is None:
        raise _formula_error(_('Unknown unit: {0}').format(code))
    return {
        'code': key,
        'dimension': meta['dimension'],
        'factor': float(meta['factor']),
        'label': meta['label'],
    }


def resolve_unit_meta(unit_meta):
    """
    Accept a catalogue code, a legacy free-text unit, or
    ``{'unit': code}`` / ``{'unit': code, 'dimension': ...}``.
    """
    if unit_meta is None or unit_meta == '':
        return None
    if isinstance(unit_meta, dict):
        code = unit_meta.get('unit') or unit_meta.get('label') or unit_meta.get('code')
    else:
        code = unit_meta
    return get_unit(code)


def combine_dimensions(left_dim, right_dim, op_kind):
    if left_dim is None and right_dim is None:
        return None
    if op_kind == 'same':
        if left_dim is None:
            return right_dim
        if right_dim is None:
            return left_dim
        if left_dim != right_dim:
            raise _formula_error(
                _('Incompatible units for addition or subtraction: "{0}" vs "{1}"').format(
                    left_dim, right_dim))
        return left_dim
    if op_kind == 'product':
        if left_dim is None:
            return right_dim
        if right_dim is None:
            return left_dim
        mapped = _DIM_PRODUCT.get((left_dim, right_dim))
        if mapped:
            return mapped
        return left_dim + '*' + right_dim
    if op_kind == 'quotient':
        if right_dim is None:
            return left_dim
        if left_dim is None:
            return '1/' + right_dim
        if left_dim == right_dim:
            return None  # dimensionless ratio
        mapped = _DIM_QUOTIENT.get((left_dim, right_dim))
        if mapped:
            return mapped
        return left_dim + '/' + right_dim
    return None


def power_dimension(base_dim, exponent):
    if base_dim is None:
        return None
    if exponent == 0:
        return None
    if exponent == 1:
        return base_dim
    mapped = _DIM_POWER.get((base_dim, float(exponent)))
    if mapped:
        return mapped
    if float(exponent) == 0.5:
        return 'sqrt({0})'.format(base_dim)
    return '{0}^{1}'.format(base_dim, int(exponent) if float(exponent).is_integer() else exponent)


def apply_result_unit(sql, result_dimension, result_unit):
    """Convert a SQL fragment from base units into ``result_unit`` when possible."""
    if not result_unit:
        return sql, result_dimension, None
    target = get_unit(result_unit)
    if result_dimension is None:
        raise _formula_error(
            _('The formula is dimensionless; a result unit cannot be applied'))
    if target['dimension'] != result_dimension:
        raise _formula_error(
            _('Result unit "{0}" does not match the formula dimension "{1}"').format(
                target['label'], result_dimension))
    if target['factor'] != 1.0:
        sql = '(({0}) / {1})'.format(sql, repr(target['factor']))
    return sql, result_dimension, target['code']
