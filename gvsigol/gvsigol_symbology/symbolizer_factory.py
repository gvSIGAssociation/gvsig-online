# -*- coding: utf-8 -*-
'''
Creación de simbolizadores a partir del JSON que envía el editor de simbología.

Sustituye a la cadena if/elif que estaba copiada en create_style/update_style de
cada tipo de leyenda vectorial. El mapeo de campos
es exactamente el que tenían esas copias (cubierto por los tests de caracterización).
'''
import json

from . import label_options, symbol_options
from .models import (PolygonSymbolizer, LineSymbolizer, MarkSymbolizer,
                     ExternalGraphicSymbolizer, TextSymbolizer)

_FIELDS = {
    'PolygonSymbolizer': (PolygonSymbolizer, (
        'fill', 'fill_opacity', 'stroke', 'stroke_width', 'stroke_opacity', 'stroke_dash_array')),
    'LineSymbolizer': (LineSymbolizer, (
        'stroke', 'stroke_width', 'stroke_opacity', 'stroke_dash_array')),
    'MarkSymbolizer': (MarkSymbolizer, (
        'opacity', 'size', 'rotation', 'well_known_name', 'fill', 'fill_opacity',
        'stroke', 'stroke_width', 'stroke_opacity', 'stroke_dash_array')),
    'ExternalGraphicSymbolizer': (ExternalGraphicSymbolizer, (
        'opacity', 'size', 'rotation', 'online_resource', 'format')),
    'TextSymbolizer': (TextSymbolizer, (
        'label', 'font_family', 'font_size', 'font_weight', 'font_style',
        'halo_fill', 'halo_fill_opacity', 'halo_radius', 'fill', 'fill_opacity')),
}

# Puntos agrupados guarda también el anclaje de la etiqueta; el resto
# de tipos deja los valores por defecto del modelo.
_TEXT_ANCHOR_FIELDS = ('anchor_point_x', 'anchor_point_y')


def create_symbolizer_from_json(rule, sym, text_anchor=False):
    '''
    Crea y guarda el simbolizador descrito por `sym` ({'type', 'order', 'json'}) en `rule`.
    Devuelve el simbolizador, o None si el tipo no está soportado (se ignora, como antes).
    '''
    sym_type = sym.get('type')
    if sym_type not in _FIELDS:
        return None
    model, fields = _FIELDS[sym_type]
    if sym_type == 'TextSymbolizer' and text_anchor:
        fields = fields + _TEXT_ANCHOR_FIELDS
    json_sym = json.loads(sym.get('json'))
    kwargs = {name: json_sym.get(name) for name in fields}
    if sym_type == 'TextSymbolizer' and json_sym.get('options'):
        # Etiqueta nueva: se guardan las opciones normalizadas (nunca el JSON tal cual llega).
        # Si el editor no las envía, la etiqueta queda como antigua (options = NULL).
        kwargs['options'] = label_options.dumps(label_options.normalize(json_sym.get('options')))
    kwargs.update(geometry_options_kwargs(sym_type, json_sym))
    symbolizer = model(rule=rule, order=int(sym.get('order')), **kwargs)
    symbolizer.save()
    return symbolizer


def geometry_options_kwargs(sym_type, json_sym):
    '''
    Opciones avanzadas de marca, línea o polígono que envía el editor ({} si no hay).
    Se guardan normalizadas, nunca tal cual llegan. Sin opciones el simbolizador queda
    como antiguo (options = NULL) y se genera exactamente igual que siempre.
    En las marcas, well_known_name guarda la forma clásica equivalente para los
    consumidores que no conocen las opciones (exportaciones, versiones anteriores).
    '''
    kind = symbol_options.kind_of(sym_type)
    raw = symbol_options.loads(json_sym.get('options'))
    if kind is None or raw is None:
        return {}
    if kind == 'mark' and not raw.get('shape'):
        raw = dict(raw, shape=json_sym.get('well_known_name'))  # sin forma nueva: la de la columna
    options = symbol_options.normalize(kind, raw)
    if options is None:
        return {}
    kwargs = {'options': symbol_options.dumps(options)}
    if kind == 'mark':
        kwargs['well_known_name'] = symbol_options.legacy_shape(options['shape'])
    return kwargs


def create_library_geometry_symbolizer(rule, sym_type, json_sym, order):
    '''
    Marca, línea o polígono de un símbolo de biblioteca (services_library.add_symbol/update_symbol).
    Mismo mapeo de campos que tenían sus copias (el orden lo decide quien llama), más las opciones.
    '''
    model, fields = _FIELDS[sym_type]
    kwargs = {name: json_sym.get(name) for name in fields}
    kwargs.update(geometry_options_kwargs(sym_type, json_sym))
    symbolizer = model(rule=rule, order=order, **kwargs)
    symbolizer.save()
    return symbolizer


def build_geometry_symbolizer(sym_type, json_sym):
    '''
    Marca, línea o polígono SIN guardar a partir del JSON del editor (vista previa, symbol_preview.py).
    Mismo mapeo de campos y opciones que al guardar; None si el tipo no es uno de esos tres.
    '''
    if sym_type not in ('MarkSymbolizer', 'LineSymbolizer', 'PolygonSymbolizer'):
        return None
    model, fields = _FIELDS[sym_type]
    kwargs = {name: json_sym.get(name) for name in fields}
    kwargs.update(geometry_options_kwargs(sym_type, json_sym))
    return model(**kwargs)
