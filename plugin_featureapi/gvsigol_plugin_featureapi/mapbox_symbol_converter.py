# -*- coding: utf-8 -*-
'''
Conversión a Mapbox GL (SPA, teselas vectoriales) de los simbolizadores de punto, línea y
polígono NUEVOS (con options; ver gvsigol_symbology/symbol_options.py y symbol_sld.py).

mapbox_style_converter solo llama aquí cuando el simbolizador tiene opciones; los antiguos
siguen su conversión de siempre.

Lo que ol-mapbox-style sabe pintar va en propiedades Mapbox normales:
  - marcas: capa symbol con un icono SVG generado (forma, relleno, borde), icon-offset,
    icon-rotate (también por campo) e icon-opacity;
  - líneas y bordes: line-cap, line-join, line-dasharray (en múltiplos del grosor, como Mapbox).
Lo que ol-mapbox-style no pinta viaja en metadata["gvsigol:symbol"] de la capa (con la URL data: de
los iconos de las decoraciones, para no depender de la carga de iconos) y lo dibuja el
SPA (apps/common/src/project/symbolExtras.js): desplazamiento lateral, desfase del guion, marcas
a lo largo de la línea, marcas en los extremos y tramas de relleno. Sin ese módulo se ve el trazo
o el fondo normal.

OpenLayers no crea estilo para una capa con opacidad 0, y el SPA necesita ese estilo para
engancharse: cuando no hay trazo base (solo marcas) o la trama no tiene fondo, la capa lleva
opacidad CARRIER_OPACITY (prácticamente invisible) y metadata hideLine / hideFill.
'''
import base64
import hashlib
import math

from gvsigol_symbology import symbol_options

METADATA_KEY = 'gvsigol:symbol'
CARRIER_OPACITY = 0.01


def _rgb(hex_color):
    from .mapbox_style_converter import hex_to_rgba
    return hex_to_rgba(hex_color)


def _num(value, default=0.0):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    return n if n == n else default


def _clean(n):
    '''15.0 -> 15 (JSON más limpio y estable).'''
    n = round(float(n), 4)
    return int(n) if n == int(n) else n


def dash_in_width_units(dash_text, width):
    '''
    stroke-dasharray de SLD (px) -> line-dasharray de Mapbox, que va en múltiplos del grosor
    (ol-mapbox-style lo multiplica por line-width). Con grosor 0 o sin grosor, se deja en px.
    '''
    from .mapbox_style_converter import parse_dash_array
    dash = parse_dash_array(dash_text)
    if not dash:
        return None
    w = _num(width, 0)
    if w <= 0:
        return [_clean(v) for v in dash]
    return [_clean(v / w) for v in dash]


# --------------------------------------------------------------------------- iconos SVG

def _regular(n, r, start_deg=-90):
    return [(r * math.cos(math.radians(start_deg + i * 360.0 / n)),
             r * math.sin(math.radians(start_deg + i * 360.0 / n))) for i in range(n)]


def _poly(points):
    return ' '.join('%s%s,%s' % ('M' if i == 0 else 'L', _clean(x), _clean(y))
                    for i, (x, y) in enumerate(points)) + ' Z'


def _lines(*segments):
    return ' '.join('M%s,%s L%s,%s' % tuple(_clean(v) for v in seg) for seg in segments)


def shape_path(shape, size):
    '''
    (path SVG centrado en (0, 0) con y hacia abajo, solo_trazo) de una forma de symbol_options.SHAPES.
    Las flechas apuntan a la derecha (eje x): en las líneas se giran según el tramo, como GeoServer.
    '''
    r = size / 2.0
    if shape == 'circle':
        return 'M%s,0 A%s,%s 0 1 0 %s,0 A%s,%s 0 1 0 %s,0 Z' % (
            _clean(-r), _clean(r), _clean(r), _clean(r), _clean(r), _clean(r), _clean(-r)), False
    if shape in ('square',):
        return _poly([(-r, -r), (r, -r), (r, r), (-r, r)]), False
    if shape in ('triangle', 'qgis://equilateral_triangle'):
        return _poly(_regular(3, r)), False
    if shape == 'star':
        pts = []
        for i in range(10):
            radius = r if i % 2 == 0 else r * 0.382
            a = math.radians(-90 + i * 36)
            pts.append((radius * math.cos(a), radius * math.sin(a)))
        return _poly(pts), False
    if shape in ('cross', 'x'):
        t = size * 0.125
        pts = [(-t, -r), (t, -r), (t, -t), (r, -t), (r, t), (t, t), (t, r), (-t, r), (-t, t), (-r, t),
               (-r, -t), (-t, -t)]
        if shape == 'x':
            c, s = math.cos(math.radians(45)), math.sin(math.radians(45))
            pts = [(x * c - y * s, x * s + y * c) for x, y in pts]
        return _poly(pts), False
    if shape == 'qgis://diamond':
        return _poly([(0, -r), (r, 0), (0, r), (-r, 0)]), False
    if shape == 'qgis://pentagon':
        return _poly(_regular(5, r)), False
    if shape == 'qgis://hexagon':
        return _poly(_regular(6, r)), False
    if shape == 'qgis://rectangle':
        return _poly([(-r, -r / 2), (r, -r / 2), (r, r / 2), (-r, r / 2)]), False
    if shape == 'qgis://semicircle':
        return 'M%s,0 A%s,%s 0 0 1 %s,0 Z' % (_clean(-r), _clean(r), _clean(r), _clean(r)), False
    if shape in ('qgis://arrowhead', 'shape://carrow'):
        return _poly([(-r, -r), (r, 0), (-r, r)]), False
    if shape in ('extshape://narrow', 'extshape://sarrow'):
        pts = [(0, -r), (0.5 * r, -0.2 * r), (0.15 * r, -0.2 * r), (0.15 * r, r), (-0.15 * r, r),
               (-0.15 * r, -0.2 * r), (-0.5 * r, -0.2 * r)]
        if shape == 'extshape://sarrow':
            pts = [(x, -y) for x, y in pts]
        return _poly(pts), False
    if shape == 'shape://vertline':
        return _lines((0, -r, 0, r)), True
    if shape == 'shape://slash':
        return _lines((-r, r, r, -r)), True
    if shape == 'shape://backslash':
        return _lines((-r, -r, r, r)), True
    if shape == 'shape://plus':
        return _lines((0, -r, 0, r), (-r, 0, r, 0)), True
    if shape == 'shape://times':
        return _lines((-r, -r, r, r), (-r, r, r, -r)), True
    if shape == 'shape://oarrow':
        return 'M%s,%s L%s,0 L%s,%s' % (_clean(-r), _clean(-r), _clean(r), _clean(-r), _clean(r)), True
    return None, False


def icon_spec(shape, size, fill=None, stroke=None, stroke_width=0, fill_opacity=1.0, stroke_opacity=1.0,
              dash=None):
    '''
    (nombre, {"url": data URI SVG, "size": px}) de un icono, o None si la forma no se conoce.
    El nombre depende solo del aspecto: iconos iguales se comparten.
    '''
    from .mapbox_style_converter import _svg_color, parse_dash_array
    size = max(1.0, _num(size, 8))
    path, stroke_only = shape_path(shape, size)
    if path is None:
        return None
    fill = None if stroke_only else _svg_color(fill)
    stroke = _svg_color(stroke)
    stroke_width = max(0.0, _num(stroke_width, 0)) if stroke else 0.0
    if stroke_only and not stroke_width:
        return None  # una forma de solo trazo sin trazo no se ve
    canvas = int(math.ceil(size + stroke_width))
    c = canvas / 2.0
    attrs = ['d="%s"' % path, 'transform="translate(%s %s)"' % (_clean(c), _clean(c)),
             'fill="%s"' % (fill or 'none')]
    if fill:
        attrs.append('fill-opacity="%s"' % _clean(min(1.0, max(0.0, _num(fill_opacity, 1.0)))))
    if stroke and stroke_width > 0:
        attrs += ['stroke="%s"' % stroke, 'stroke-width="%s"' % _clean(stroke_width),
                  'stroke-opacity="%s"' % _clean(min(1.0, max(0.0, _num(stroke_opacity, 1.0)))),
                  'stroke-linejoin="round"']
        dash_list = parse_dash_array(dash) if dash else None
        if dash_list:
            attrs.append('stroke-dasharray="%s"' % ' '.join(str(_clean(v)) for v in dash_list))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
           '<path %s/></svg>') % (canvas, canvas, canvas, canvas, ' '.join(attrs))
    url = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')).decode('ascii')
    name = 'gvsigol-sym-' + hashlib.sha1(svg.encode('utf-8')).hexdigest()[:12]
    return name, {"url": url, "size": canvas}


def _mark_icon(sym, options):
    return icon_spec(options['shape'], sym.size, fill=sym.fill if options['fill'] else None, stroke=sym.stroke,
                     stroke_width=sym.stroke_width, fill_opacity=sym.fill_opacity,
                     stroke_opacity=sym.stroke_opacity, dash=sym.stroke_dash_array)


def _decoration_icon(g):
    return icon_spec(g['shape'], g['size'], fill=g['fill'], stroke=g['stroke'], stroke_width=g['stroke_width'])


def icons_for(sym, options):
    '''Iconos {nombre: {url, size}} que necesita un simbolizador nuevo (para la respuesta "icons").'''
    icons = {}
    kind = symbol_options.kind_of(sym)
    specs = []
    if kind == 'mark':
        specs.append(_mark_icon(sym, options))
    elif kind == 'line':
        for key in ('marks', 'start', 'end'):
            if options.get(key):
                specs.append(_decoration_icon(options[key]))
    for spec in specs:
        if spec:
            icons[spec[0]] = spec[1]
    return icons


# --------------------------------------------------------------------------- capas

def _base_id(layer_id, rule_name, sym, suffix):
    # id único por simbolizador: en una regla puede haber varios del mismo tipo
    return '%s_%s_s%s_%s' % (layer_id, rule_name, getattr(sym, 'id', None) or getattr(sym, 'pk', 0), suffix)


def _stroke_paint_layout(sym, stroke_opts, layer):
    color = _rgb(sym.stroke)
    if color:
        layer['paint']['line-color'] = color
    width = _num(sym.stroke_width, 0)
    if width > 0:
        layer['paint']['line-width'] = _clean(width)
    opacity = _num(sym.stroke_opacity, 1.0)
    if opacity < 1.0:
        layer['paint']['line-opacity'] = opacity
    dash = dash_in_width_units(sym.stroke_dash_array, width)
    if dash:
        layer['paint']['line-dasharray'] = dash
    layer['layout']['line-cap'] = stroke_opts['linecap']
    layer['layout']['line-join'] = stroke_opts['linejoin']


def convert_mark(sym, options, layer_id, rule_name, source_layer):
    icon = _mark_icon(sym, options)
    if icon is None:
        return []
    layout = {"icon-image": icon[0], "icon-size": 1,
              # como las marcas antiguas: nunca se ocultan por colisión
              "icon-allow-overlap": True, "icon-ignore-placement": True}
    rotation = _num(sym.rotation, 0)
    if options['rotation_field']:
        layout["icon-rotate"] = ["+", ["to-number", ["get", options['rotation_field']], 0], _clean(rotation)]
    elif rotation:
        layout["icon-rotate"] = _clean(rotation)
    d = options['displacement']
    if d['x'] or d['y']:
        # SLD: y hacia arriba; Mapbox: y hacia abajo
        layout["icon-offset"] = [_clean(d['x']), _clean(-d['y'])]
    paint = {}
    opacity = _num(sym.opacity, 1.0)
    if opacity < 1.0:
        paint["icon-opacity"] = opacity
    return [{"id": _base_id(layer_id, rule_name, sym, 'point'), "type": "symbol", "source": "gvsigol",
             "source-layer": source_layer, "layout": layout, "paint": paint}]


def convert_line(sym, options, layer_id, rule_name, source_layer):
    layer = {"id": _base_id(layer_id, rule_name, sym, 'line'), "type": "line", "source": "gvsigol",
             "source-layer": source_layer, "paint": {}, "layout": {}}
    _stroke_paint_layout(sym, options['stroke'], layer)
    extras = {}
    st = options['stroke']
    if st['offset']:
        extras['offset'] = _clean(st['offset'])  # px, positivo a la izquierda (como PerpendicularOffset de SLD)
    if st['dash_offset'] and layer['paint'].get('line-dasharray'):
        extras['dashOffset'] = _clean(st['dash_offset'])
    if options['marks']:
        m = options['marks']
        icon = _decoration_icon(m)
        if icon:
            extras['marks'] = {"icon": icon[0], "url": icon[1]['url'], "iconSize": icon[1]['size'],
                               "size": _clean(m['size']), "interval": _clean(m['size'] + m['spacing']),
                               "start": _clean(m['start'])}
    for end in ('start', 'end'):
        if options[end]:
            icon = _decoration_icon(options[end])
            if icon:
                extras[end] = {"icon": icon[0], "url": icon[1]['url'], "iconSize": icon[1]['size'],
                               "size": _clean(options[end]['size'])}
    if not options['line']:
        # sin trazo base: capa portadora casi invisible para las decoraciones
        extras['hideLine'] = True
        layer['paint']['line-opacity'] = CARRIER_OPACITY
        layer['paint'].pop('line-dasharray', None)
    if extras:
        layer['metadata'] = {METADATA_KEY: extras}
    return [layer]


def convert_polygon(sym, options, layer_id, rule_name, source_layer):
    layers = []
    f = options['fill']
    if f['type'] in ('solid', 'hatch'):
        fill_layer = {"id": _base_id(layer_id, rule_name, sym, 'fill'), "type": "fill", "source": "gvsigol",
                      "source-layer": source_layer, "paint": {}}
        if f['type'] == 'solid' or f['hatch']['background']:
            color = _rgb(sym.fill)
            if color:
                fill_layer['paint']['fill-color'] = color
            opacity = _num(sym.fill_opacity, 1.0)
            if opacity < 1.0:
                fill_layer['paint']['fill-opacity'] = opacity
        if f['type'] == 'hatch':
            h = f['hatch']
            extras = {"hatch": {"pattern": h['pattern'], "color": h['color'], "width": _clean(h['width']),
                                "spacing": _clean(h['spacing'])}}
            if not h['background']:
                # sin fondo: capa portadora casi invisible (el SPA pinta solo la trama)
                fill_layer['paint']['fill-color'] = _rgb(h['color'])
                fill_layer['paint']['fill-opacity'] = CARRIER_OPACITY
                extras['hideFill'] = True
            fill_layer['metadata'] = {METADATA_KEY: extras}
        layers.append(fill_layer)
    if _num(sym.stroke_width, 0) > 0 and sym.stroke:
        stroke_layer = {"id": _base_id(layer_id, rule_name, sym, 'stroke'), "type": "line", "source": "gvsigol",
                        "source-layer": source_layer, "paint": {}, "layout": {}}
        _stroke_paint_layout(sym, options['stroke'], stroke_layer)
        if options['stroke']['dash_offset'] and stroke_layer['paint'].get('line-dasharray'):
            stroke_layer['metadata'] = {METADATA_KEY: {"dashOffset": _clean(options['stroke']['dash_offset'])}}
        layers.append(stroke_layer)
    return layers


def convert_new_geometry_symbolizer(sym, options, layer_id, rule_name, source_layer):
    '''Capas Mapbox de un simbolizador nuevo (lista, en orden de dibujo).'''
    kind = symbol_options.kind_of(sym)
    if kind == 'mark':
        return convert_mark(sym, options, layer_id, rule_name, source_layer)
    if kind == 'line':
        return convert_line(sym, options, layer_id, rule_name, source_layer)
    if kind == 'polygon':
        return convert_polygon(sym, options, layer_id, rule_name, source_layer)
    return []
