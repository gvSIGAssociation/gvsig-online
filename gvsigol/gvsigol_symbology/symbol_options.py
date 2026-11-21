# -*- coding: utf-8 -*-
'''
Opciones avanzadas de los simbolizadores de punto, línea y polígono
(MarkSymbolizer.options, LineSymbolizer.options, PolygonSymbolizer.options).

Se guardan como JSON en un TextField (compatible con Django 2), igual que las
opciones de etiquetado (label_options.py). Un simbolizador sin opciones (NULL,
vacío o JSON inválido) es un simbolizador "antiguo": se genera exactamente igual
que siempre, en el SLD y en el estilo del SPA.

Las columnas del modelo siguen siendo la fuente de los valores básicos (colores,
opacidades, grosor, tamaño, rotación y patrón de guiones en stroke_dash_array);
las opciones solo añaden lo que las columnas no pueden expresar.

Esquema v1 (todas las claves son opcionales; lo que falte toma el valor por defecto):

Marca:
{
  "v": 1,
  "shape": "qgis://diamond",          # forma de SHAPES; sustituye a well_known_name en el SLD nuevo
  "fill": true,                        # false = marca sin relleno (solo contorno)
  "displacement": {"x": 0, "y": 0},    # px; x a la derecha, y hacia arriba (como en SLD)
  "rotation_field": null               # campo numérico; ángulo = campo + columna rotation
}

Línea:
{
  "v": 1,
  "line": true,                        # false = solo decoraciones (sin trazo base)
  "stroke": {"linecap": "butt", "linejoin": "miter", "dash_offset": 0, "offset": 0},
  "marks": {"shape": "shape://vertline", "size": 10, "spacing": 20, "start": 0, "fill": "#000000" | null,
            "stroke": "#000000", "stroke_width": 1},               # o null
  "start": {"shape": "circle", "size": 8, "fill": "#000000" | null, "stroke": "#000000", "stroke_width": 1},
  "end":   {...}                                                  # flechas o marcas en los extremos (o null)
}

Polígono:
{
  "v": 1,
  "fill": {
    "type": "solid" | "none" | "hatch",
    "hatch": {"pattern": "slash", "color": "#000000", "width": 1, "spacing": 10, "background": true}
  },
  "stroke": {"linecap": "butt", "linejoin": "miter", "dash_offset": 0}
}
Con "background" true el relleno de fondo usa las columnas fill / fill_opacity.
No hay relleno con imagen (GraphicFill + ExternalGraphic): GeoServer 2.28 no lo pinta (fase 2,
ni SVG ni PNG, ni file:// ni http, sin aviso en el log). Un tipo desconocido se guarda como 'solid'.

La normalización es estricta: solo claves conocidas, números dentro de límites, valores de
enumeración válidos, colores #rrggbb y nombres de campo con forma de identificador. Lo inválido se descarta, nunca se usa tal cual. La lista de formas está
validada contra GeoServer 2.28: un nombre desconocido hace fallar la capa ENTERA en GeoServer.
'''
import json
import re

SCHEMA_VERSION = 1

KINDS = ('mark', 'line', 'polygon')

# Formas comprobadas en GeoServer 2.28 (fase 0). No añadir ninguna sin validarla antes:
# qgis://octagon, quarter_circle, third_circle, cross_fill... lanzan una excepción.
SHAPES = (
    'circle', 'square', 'triangle', 'star', 'cross', 'x',
    'qgis://diamond', 'qgis://pentagon', 'qgis://hexagon', 'qgis://rectangle', 'qgis://semicircle',
    'qgis://equilateral_triangle', 'qgis://arrowhead',
    'extshape://narrow', 'extshape://sarrow',
    'shape://vertline', 'shape://slash', 'shape://backslash', 'shape://plus', 'shape://times',
    'shape://oarrow', 'shape://carrow',
)
# Formas que son solo trazo (el relleno no se pinta)
LINE_SHAPES = ('shape://vertline', 'shape://slash', 'shape://backslash', 'shape://plus', 'shape://times',
               'shape://oarrow')
# Forma clásica que se guarda en well_known_name (consumidores que no conocen las opciones)
LEGACY_SHAPE = {
    'shape://plus': 'cross', 'shape://times': 'cross',
    'qgis://diamond': 'square', 'qgis://rectangle': 'square',
    'qgis://pentagon': 'circle', 'qgis://hexagon': 'circle', 'qgis://semicircle': 'circle',
    'qgis://equilateral_triangle': 'triangle', 'qgis://arrowhead': 'triangle',
    'extshape://narrow': 'triangle', 'extshape://sarrow': 'triangle',
    'shape://oarrow': 'triangle', 'shape://carrow': 'triangle',
}
# 'x' también es clásica: el editor antiguo ya la ofrecía (SymbologyUtils.shapes)
LEGACY_SHAPES = ('circle', 'square', 'triangle', 'star', 'cross', 'x')

LINECAPS = ('butt', 'round', 'square')
LINEJOINS = ('miter', 'round', 'bevel')
FILL_TYPES = ('solid', 'none', 'hatch')
HATCH_PATTERNS = ('slash', 'backslash', 'horline', 'vertline', 'plus', 'times', 'dots')

_FIELD_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')
_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


def _num(value, lo, hi, default, integer=False):
    if isinstance(value, bool):
        return default
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if n != n or n in (float('inf'), float('-inf')):  # NaN / infinito
        return default
    n = max(lo, min(hi, n))
    if integer:
        return int(round(n))
    return int(n) if n == int(n) else round(n, 3)


def _bool(value, default):
    return value if isinstance(value, bool) else default


def _enum(value, allowed, default):
    return value if value in allowed else default


def _color(value, default):
    return value.lower() if isinstance(value, str) and _COLOR_RE.match(value) else default


def _field(value, allowed_fields):
    if not isinstance(value, str) or not _FIELD_RE.match(value):
        return None
    if allowed_fields is not None and value not in allowed_fields:
        return None
    return value


def _dict(value):
    return value if isinstance(value, dict) else {}


def loads(raw):
    '''Texto guardado -> dict, o None si es un simbolizador antiguo (vacío o JSON inválido).'''
    if not raw:
        return None
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return None
    return data if isinstance(data, dict) and data else None


def _stroke(data, with_offset):
    s = _dict(data)
    out = {'linecap': _enum(s.get('linecap'), LINECAPS, 'butt'),
           'linejoin': _enum(s.get('linejoin'), LINEJOINS, 'miter'),
           'dash_offset': _num(s.get('dash_offset'), 0, 1000, 0)}
    if with_offset:
        out['offset'] = _num(s.get('offset'), -100, 100, 0)
    return out


def _graphic(data, default_shape, default_size):
    '''Marca usada como decoración de línea (a lo largo o en los extremos).'''
    g = _dict(data)
    shape = _enum(g.get('shape'), SHAPES, default_shape)
    fill = None if shape in LINE_SHAPES else _color(g.get('fill'), None)
    return {'shape': shape,
            'size': _num(g.get('size'), 1, 100, default_size),
            'fill': fill,
            'stroke': _color(g.get('stroke'), '#000000'),
            'stroke_width': _num(g.get('stroke_width'), 0, 20, 1)}


def _normalize_mark(data, allowed_fields):
    d = _dict(data.get('displacement'))
    return {'v': SCHEMA_VERSION,
            'shape': _enum(data.get('shape'), SHAPES, 'circle'),
            'fill': _bool(data.get('fill'), True),
            'displacement': {'x': _num(d.get('x'), -200, 200, 0), 'y': _num(d.get('y'), -200, 200, 0)},
            'rotation_field': _field(data.get('rotation_field'), allowed_fields)}


def _normalize_line(data, allowed_fields):
    out = {'v': SCHEMA_VERSION,
           'line': _bool(data.get('line'), True),
           'stroke': _stroke(data.get('stroke'), with_offset=True),
           'marks': None, 'start': None, 'end': None}
    if isinstance(data.get('marks'), dict):
        m = _dict(data.get('marks'))
        marks = _graphic(m, 'shape://vertline', 10)
        marks['spacing'] = _num(m.get('spacing'), 1, 1000, 20)
        marks['start'] = _num(m.get('start'), 0, 1000, 0)
        out['marks'] = marks
    for end in ('start', 'end'):
        if isinstance(data.get(end), dict):
            out[end] = _graphic(data.get(end), 'shape://carrow' if end == 'end' else 'circle', 10)
    if not out['line'] and not (out['marks'] or out['start'] or out['end']):
        out['line'] = True  # sin trazo ni decoraciones no se vería nada
    return out


def _normalize_polygon(data, allowed_fields):
    f = _dict(data.get('fill'))
    ftype = _enum(f.get('type'), FILL_TYPES, 'solid')
    fill = {'type': ftype}
    if ftype == 'hatch':
        h = _dict(f.get('hatch'))
        fill['hatch'] = {'pattern': _enum(h.get('pattern'), HATCH_PATTERNS, 'slash'),
                         'color': _color(h.get('color'), '#000000'),
                         'width': _num(h.get('width'), 0.25, 10, 1),
                         'spacing': _num(h.get('spacing'), 2, 100, 10),
                         'background': _bool(h.get('background'), True)}
    return {'v': SCHEMA_VERSION, 'fill': fill, 'stroke': _stroke(data.get('stroke'), with_offset=False)}


_NORMALIZERS = {'mark': _normalize_mark, 'line': _normalize_line, 'polygon': _normalize_polygon}


def normalize(kind, raw, allowed_fields=None):
    '''
    kind: 'mark' | 'line' | 'polygon'.
    Devuelve un dict v1 completo y seguro, o None si no hay opciones (simbolizador antiguo).
    allowed_fields: nombres de campo de la capa (si se conocen) para validar las referencias.
    '''
    if kind not in _NORMALIZERS:
        raise ValueError('Tipo de simbolizador no soportado: %r' % (kind,))
    data = loads(raw)
    if data is None:
        return None
    if allowed_fields is not None:
        allowed_fields = set(allowed_fields)
    return _NORMALIZERS[kind](data, allowed_fields)


def dumps(options):
    '''dict normalizado -> texto para guardar (None si no hay opciones).'''
    if not options:
        return None
    return json.dumps(options, sort_keys=True, ensure_ascii=False)


_KIND_BY_MODEL = {'MarkSymbolizer': 'mark', 'LineSymbolizer': 'line', 'PolygonSymbolizer': 'polygon'}


def kind_of(symbolizer):
    '''Tipo de opciones de un simbolizador (instancia o nombre de clase), o None.'''
    name = symbolizer if isinstance(symbolizer, str) else type(symbolizer).__name__
    return _KIND_BY_MODEL.get(name)


def of(symbolizer, allowed_fields=None):
    '''Opciones normalizadas de un simbolizador, o None si es antiguo (o de otro tipo).'''
    kind = kind_of(symbolizer)
    if kind is None:
        return None
    return normalize(kind, getattr(symbolizer, 'options', None), allowed_fields)


def legacy_shape(shape):
    '''Forma clásica equivalente (para well_known_name) de una forma de SHAPES.'''
    if shape in LEGACY_SHAPES:
        return shape
    return LEGACY_SHAPE.get(shape, 'circle')
