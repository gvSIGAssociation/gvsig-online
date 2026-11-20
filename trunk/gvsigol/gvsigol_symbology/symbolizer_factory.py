# -*- coding: utf-8 -*-
'''
Creación de simbolizadores a partir del JSON que envía el editor de simbología.

Sustituye a la cadena if/elif que estaba copiada en create_style/update_style de
cada tipo de leyenda vectorial. El mapeo de campos
es exactamente el que tenían esas copias (cubierto por los tests de caracterización).
'''
import json

from . import label_options
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
    symbolizer = model(rule=rule, order=int(sym.get('order')), **kwargs)
    symbolizer.save()
    return symbolizer
