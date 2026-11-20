# -*- coding: utf-8 -*-
'''
Opciones avanzadas de etiquetado (TextSymbolizer.options).

Se guardan como JSON en un TextField (compatible con Django 2). Una etiqueta sin
opciones (NULL, vacío o JSON inválido) es una etiqueta "antigua" y se genera
exactamente igual que siempre, tanto en el SLD como en el estilo del SPA.

Esquema v1 (todas las claves son opcionales; lo que falte toma el valor por defecto):

{
  "v": 1,
  "content": {
    "parts": [ {"type": "field", "name": "nombre", "number": {"decimals": 0, "thousands": true, "locale": "es"}, "date": "dd/MM/yyyy"},
               {"type": "text", "value": " hab."} ],
    "case": "none" | "upper" | "lower"
  },
  "placement": {
    "point":   {"position": "top", "dx": 0, "dy": 0},     # dx a la derecha, dy hacia arriba (px)
    "line":    {"follow": true, "repeat": 0, "offset": 0, "max_angle": 25},
    "polygon": {"mode": "interior" | "centroid"},
    "rotation": {"angle": 0, "field": null},              # grados, sentido horario
    "wrap": 120                                           # ancho de salto de línea (px); 0 = sin salto
  },
  "priority": {"field": null, "allow_overlap": false, "space_around": 0},
  "style": {"letter_spacing": 0, "halo": true},
  "background": {"type": "none" | "box", "fill": "#ffffff", "fill_opacity": 1, "stroke": "#000000",
                 "stroke_width": 1, "padding": 2}
}

La normalización es estricta: solo claves conocidas, números dentro de límites, valores
de enumeración válidos y nombres de campo con forma de identificador (y, si se indican
los campos de la capa, que existan). Lo inválido se descarta, nunca se usa tal cual.
'''
import json
import re

SCHEMA_VERSION = 1

POSITIONS = ('top-left', 'top', 'top-right', 'left', 'center', 'right', 'bottom-left', 'bottom', 'bottom-right')
CASES = ('none', 'upper', 'lower')
POLYGON_MODES = ('interior', 'centroid')
BACKGROUND_TYPES = ('none', 'box')
NUMBER_LOCALES = ('en', 'es', 'ca', 'de', 'fr', 'it', 'pt')
DATE_FORMATS = ('dd/MM/yyyy', 'dd-MM-yyyy', 'yyyy-MM-dd', 'MM/yyyy', 'yyyy', 'dd/MM/yyyy HH:mm')
MAX_PARTS = 10
MAX_TEXT = 100

_FIELD_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')
_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')

DEFAULTS = {
    'content': {'case': 'none'},
    'placement': {
        'point': {'position': 'top', 'dx': 0, 'dy': 0},
        'line': {'follow': True, 'repeat': 0, 'offset': 0, 'max_angle': 25},
        'polygon': {'mode': 'interior'},
        'rotation': {'angle': 0, 'field': None},
        'wrap': 120,
    },
    'priority': {'field': None, 'allow_overlap': False, 'space_around': 0},
    'style': {'letter_spacing': 0, 'halo': True},
    'background': {'type': 'none', 'fill': '#ffffff', 'fill_opacity': 1.0, 'stroke': '#000000',
                   'stroke_width': 1, 'padding': 2},
}


def _num(value, lo, hi, default, integer=False):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if n != n:  # NaN
        return default
    n = max(lo, min(hi, n))
    return int(round(n)) if integer else n


def _bool(value, default):
    return value if isinstance(value, bool) else default


def _enum(value, allowed, default):
    return value if value in allowed else default


def _color(value, default):
    return value if isinstance(value, str) and _COLOR_RE.match(value) else default


def _field(value, allowed_fields):
    if not isinstance(value, str) or not _FIELD_RE.match(value):
        return None
    if allowed_fields is not None and value not in allowed_fields:
        return None
    return value


def _dict(value):
    return value if isinstance(value, dict) else {}


def loads(raw):
    '''Texto guardado -> dict, o None si es una etiqueta antigua (vacío o JSON inválido).'''
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


def normalize(raw, allowed_fields=None):
    '''
    Devuelve un dict v1 completo y seguro, o None si no hay opciones.
    allowed_fields: nombres de campo de la capa (si se conocen) para validar las referencias.
    '''
    data = loads(raw)
    if data is None:
        return None
    if allowed_fields is not None:
        allowed_fields = set(allowed_fields)

    content_in = _dict(data.get('content'))
    parts = []
    for p in content_in.get('parts') or []:
        if len(parts) >= MAX_PARTS or not isinstance(p, dict):
            continue
        if p.get('type') == 'field':
            name = _field(p.get('name'), allowed_fields)
            if not name:
                continue
            part = {'type': 'field', 'name': name}
            num = p.get('number')
            if isinstance(num, dict):
                part['number'] = {'decimals': _num(num.get('decimals'), 0, 6, 0, integer=True),
                                  'thousands': _bool(num.get('thousands'), False),
                                  'locale': _enum(num.get('locale'), NUMBER_LOCALES, 'en')}
            elif p.get('date') in DATE_FORMATS:
                part['date'] = p['date']
            parts.append(part)
        elif p.get('type') == 'text' and isinstance(p.get('value'), str) and p['value']:
            parts.append({'type': 'text', 'value': p['value'][:MAX_TEXT]})
    content = {'case': _enum(content_in.get('case'), CASES, 'none')}
    if parts:
        content['parts'] = parts

    pl_in = _dict(data.get('placement'))
    pt = _dict(pl_in.get('point'))
    ln = _dict(pl_in.get('line'))
    pg = _dict(pl_in.get('polygon'))
    rot = _dict(pl_in.get('rotation'))
    d = DEFAULTS['placement']
    placement = {
        'point': {'position': _enum(pt.get('position'), POSITIONS, d['point']['position']),
                  'dx': _num(pt.get('dx'), -200, 200, 0, integer=True),
                  'dy': _num(pt.get('dy'), -200, 200, 0, integer=True)},
        'line': {'follow': _bool(ln.get('follow'), d['line']['follow']),
                 'repeat': _num(ln.get('repeat'), 0, 5000, 0, integer=True),
                 'offset': _num(ln.get('offset'), -100, 100, 0, integer=True),
                 'max_angle': _num(ln.get('max_angle'), 0, 90, d['line']['max_angle'], integer=True)},
        'polygon': {'mode': _enum(pg.get('mode'), POLYGON_MODES, d['polygon']['mode'])},
        'rotation': {'angle': _num(rot.get('angle'), -360, 360, 0),
                     'field': _field(rot.get('field'), allowed_fields)},
        'wrap': _num(pl_in.get('wrap'), 0, 2000, d['wrap'], integer=True),
    }

    pr_in = _dict(data.get('priority'))
    priority = {'field': _field(pr_in.get('field'), allowed_fields),
                'allow_overlap': _bool(pr_in.get('allow_overlap'), False),
                'space_around': _num(pr_in.get('space_around'), -20, 200, 0, integer=True)}

    st_in = _dict(data.get('style'))
    style = {'letter_spacing': _num(st_in.get('letter_spacing'), -5, 30, 0),
             'halo': _bool(st_in.get('halo'), True)}

    bg_in = _dict(data.get('background'))
    db = DEFAULTS['background']
    background = {'type': _enum(bg_in.get('type'), BACKGROUND_TYPES, 'none'),
                  'fill': _color(bg_in.get('fill'), db['fill']),
                  'fill_opacity': _num(bg_in.get('fill_opacity'), 0, 1, db['fill_opacity']),
                  'stroke': _color(bg_in.get('stroke'), db['stroke']),
                  'stroke_width': _num(bg_in.get('stroke_width'), 0, 10, db['stroke_width']),
                  'padding': _num(bg_in.get('padding'), 0, 50, db['padding'], integer=True)}

    return {'v': SCHEMA_VERSION, 'content': content, 'placement': placement, 'priority': priority,
            'style': style, 'background': background}


def dumps(options):
    '''dict normalizado -> texto para guardar (None si no hay opciones).'''
    if not options:
        return None
    return json.dumps(options, sort_keys=True, ensure_ascii=False)


def of(text_symbolizer, allowed_fields=None):
    '''Opciones normalizadas de un TextSymbolizer, o None si es una etiqueta antigua.'''
    return normalize(getattr(text_symbolizer, 'options', None), allowed_fields)
