# -*- coding: utf-8 -*-
'''
SLD de los simbolizadores de punto, línea y polígono NUEVOS (con options; ver symbol_options.py).

sld_builder solo llama aquí cuando el simbolizador tiene opciones; los antiguos siguen el
código de siempre y su SLD no cambia.

Un simbolizador nuevo puede generar varios simbolizadores SLD seguidos:
  - polígono con trama y fondo: PolygonSymbolizer (fondo) + PolygonSymbolizer (trama + borde)
  - línea: LineSymbolizer (trazo) + LineSymbolizer (marcas a lo largo) + PointSymbolizer (inicio/fin)
El primero lleva la VendorOption «gvsigol-symbol» con los valores del simbolizador (columnas y
opciones) para poder recuperarlo al importar el SLD. Al importar se vuelve a generar el SLD con
esos valores y solo se acepta si sale idéntico (ver import_group); si no, se importa como siempre.
GeoServer ignora las VendorOption que no conoce (comprobado en 2.28).

Orden de elementos (SLD 1.0 + extensiones de GeoServer):
  LineSymbolizer:    Geometry, Stroke, PerpendicularOffset, VendorOption*
  PolygonSymbolizer: Geometry, Fill, Stroke, VendorOption*
  PointSymbolizer:   Geometry, Graphic, VendorOption*
  Graphic:           Mark | ExternalGraphic, Opacity, Size, Rotation, Displacement
  Stroke / Fill:     GraphicStroke | GraphicFill, CssParameter*
Todos los valores entran como texto de nodos lxml (se escapan) y vienen normalizados.
'''
import json

from lxml import etree

from gvsigol_symbology.sld import SLDNode
from gvsigol_symbology import symbol_options

SLD = SLDNode._nsmap['sld']
OGC = SLDNode._nsmap['ogc']

MARKER = 'gvsigol-symbol'
MARKER_VERSION = 1

# Columnas del modelo que se guardan en el marcador (las mismas que usa el editor)
COLUMNS = {
    'mark': ('opacity', 'size', 'rotation', 'well_known_name', 'fill', 'fill_opacity', 'stroke',
             'stroke_width', 'stroke_opacity', 'stroke_dash_array'),
    'line': ('stroke', 'stroke_width', 'stroke_opacity', 'stroke_dash_array'),
    'polygon': ('fill', 'fill_opacity', 'stroke', 'stroke_width', 'stroke_opacity', 'stroke_dash_array'),
}
SLD_TAG = {'mark': 'PointSymbolizer', 'line': 'LineSymbolizer', 'polygon': 'PolygonSymbolizer'}

# Trama -> forma de GeoServer (los puntos son círculos: shape://dot no pinta nada como trama)
HATCH_SHAPES = {'slash': 'shape://slash', 'backslash': 'shape://backslash', 'horline': 'shape://horline',
                'vertline': 'shape://vertline', 'plus': 'shape://plus', 'times': 'shape://times', 'dots': 'circle'}


def _el(parent, ns, tag, text=None, **attrs):
    elem = etree.SubElement(parent, '{%s}%s' % (ns, tag))
    for k, v in attrs.items():
        elem.set(k, v)
    if text is not None:
        elem.text = text
    return elem


def fmt(n):
    '''Número -> texto sin decimales innecesarios (15.0 -> "15", 0.5 -> "0.5").'''
    n = float(n)
    return str(int(n)) if n == int(n) else repr(round(n, 6))


def _css(parent, name, value):
    _el(parent, SLD, 'CssParameter', value, name=name)


def _vendor(parent, name, value):
    _el(parent, SLD, 'VendorOption', value, name=name)


def _dash(value):
    value = (value or '').strip()
    return None if not value or value == 'none' else value


def _fill(parent, color, opacity):
    fill = _el(parent, SLD, 'Fill')
    _css(fill, 'fill', color)
    _css(fill, 'fill-opacity', str(opacity))
    return fill


def _stroke(parent, s, stroke_opts):
    '''
    Stroke con los valores de las columnas (mismo formato de texto que el SLD antiguo:
    color, ancho, opacidad, guiones) y después los parámetros nuevos, solo si no son los
    valores por defecto de SLD (los lectores antiguos leen los cuatro primeros por posición).
    '''
    stroke = _el(parent, SLD, 'Stroke')
    _css(stroke, 'stroke', s.stroke)
    _css(stroke, 'stroke-width', str(s.stroke_width))
    _css(stroke, 'stroke-opacity', str(s.stroke_opacity))
    dash = _dash(s.stroke_dash_array)
    if dash:
        _css(stroke, 'stroke-dasharray', dash)
    if stroke_opts['linecap'] != 'butt':
        _css(stroke, 'stroke-linecap', stroke_opts['linecap'])
    if stroke_opts['linejoin'] != 'miter':
        _css(stroke, 'stroke-linejoin', stroke_opts['linejoin'])
    if dash and stroke_opts['dash_offset']:
        _css(stroke, 'stroke-dashoffset', fmt(stroke_opts['dash_offset']))
    return stroke


def _mark(parent, shape, fill, stroke, stroke_width, fill_opacity=None, stroke_opacity=None, dash=None):
    mark = _el(parent, SLD, 'Mark')
    _el(mark, SLD, 'WellKnownName', shape)
    if fill and shape not in symbol_options.LINE_SHAPES:
        f = _el(mark, SLD, 'Fill')
        _css(f, 'fill', fill)
        if fill_opacity is not None:
            _css(f, 'fill-opacity', str(fill_opacity))
    if stroke and stroke_width:
        st = _el(mark, SLD, 'Stroke')
        _css(st, 'stroke', stroke)
        _css(st, 'stroke-width', fmt(stroke_width))
        if stroke_opacity is not None:
            _css(st, 'stroke-opacity', str(stroke_opacity))
        if dash:
            _css(st, 'stroke-dasharray', dash)
    return mark


def _geometry_function(parent, name, geom_name):
    geom = _el(parent, SLD, 'Geometry')
    fn = _el(geom, OGC, 'Function', name=name)
    _el(fn, OGC, 'PropertyName', geom_name)


def _marker(node, kind, s, options, parts):
    data = {'v': MARKER_VERSION, 'kind': kind, 'parts': parts,
            'columns': dict((c, getattr(s, c)) for c in COLUMNS[kind]), 'options': options}
    _vendor(node, MARKER, json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')))


# --------------------------------------------------------------------------- marcas

def _build_mark(rule_node, s, options):
    node = _el(rule_node, SLD, 'PointSymbolizer')
    graphic = _el(node, SLD, 'Graphic')
    _mark(graphic, options['shape'], s.fill if options['fill'] else None, s.stroke, s.stroke_width,
          s.fill_opacity, s.stroke_opacity, _dash(s.stroke_dash_array))
    _el(graphic, SLD, 'Opacity', str(s.opacity))
    _el(graphic, SLD, 'Size', str(s.size))
    if options['rotation_field']:
        rot = _el(graphic, SLD, 'Rotation')
        add = _el(rot, OGC, 'Add')
        _el(add, OGC, 'PropertyName', options['rotation_field'])
        _el(add, OGC, 'Literal', str(s.rotation))
    else:
        _el(graphic, SLD, 'Rotation', str(s.rotation))
    d = options['displacement']
    if d['x'] or d['y']:
        disp = _el(graphic, SLD, 'Displacement')
        _el(disp, SLD, 'DisplacementX', fmt(d['x']))
        _el(disp, SLD, 'DisplacementY', fmt(d['y']))
    return [node]


# --------------------------------------------------------------------------- líneas

def _decoration_graphic(parent, g):
    graphic = _el(parent, SLD, 'Graphic')
    _mark(graphic, g['shape'], g['fill'], g['stroke'], g['stroke_width'])
    _el(graphic, SLD, 'Size', fmt(g['size']))
    return graphic


def _end_point(rule_node, which, g, geom_name):
    node = _el(rule_node, SLD, 'PointSymbolizer')
    _geometry_function(node, 'startPoint' if which == 'start' else 'endPoint', geom_name)
    graphic = _decoration_graphic(node, g)
    rot = _el(graphic, SLD, 'Rotation')
    angle = _el(rot, OGC, 'Function', name='startAngle' if which == 'start' else 'endAngle')
    _el(angle, OGC, 'PropertyName', geom_name)
    if which == 'start':
        # la forma apunta hacia fuera de la línea en los dos extremos
        add = _el(rot, OGC, 'Add')
        rot.remove(angle)
        add.append(angle)
        _el(add, OGC, 'Literal', '180')
    return node


def _build_line(rule_node, s, options, geom_name):
    nodes = []
    st = options['stroke']
    if options['line']:
        node = _el(rule_node, SLD, 'LineSymbolizer')
        _stroke(node, s, st)
        if st['offset']:
            _el(node, SLD, 'PerpendicularOffset', fmt(st['offset']))
        nodes.append(node)
    m = options['marks']
    if m:
        node = _el(rule_node, SLD, 'LineSymbolizer')
        stroke = _el(node, SLD, 'Stroke')
        gs = _el(stroke, SLD, 'GraphicStroke')
        _decoration_graphic(gs, m)
        # GraphicStroke + guiones: una marca cada (tamaño + separación) px, empezando en «start»
        _css(stroke, 'stroke-dasharray', '%s %s' % (fmt(m['size']), fmt(m['spacing'])))
        if m['start']:
            _css(stroke, 'stroke-dashoffset', fmt(m['start']))
        nodes.append(node)
    # Los extremos necesitan el nombre de la geometría (los símbolos de biblioteca no lo tienen)
    if geom_name:
        for which in ('start', 'end'):
            if options[which]:
                nodes.append(_end_point(rule_node, which, options[which], geom_name))
    return nodes


# --------------------------------------------------------------------------- polígonos

def _hatch_graphic(fill, h):
    gf = _el(fill, SLD, 'GraphicFill')
    graphic = _el(gf, SLD, 'Graphic')
    if h['pattern'] == 'dots':
        diameter = max(1, h['width'] * 2)
        _mark(graphic, 'circle', h['color'], None, 0)
        _el(graphic, SLD, 'Size', fmt(diameter))
        return max(0, (h['spacing'] - diameter) / 2.0)
    _mark(graphic, HATCH_SHAPES[h['pattern']], None, h['color'], h['width'])
    _el(graphic, SLD, 'Size', fmt(h['spacing']))
    return 0


def _build_polygon(rule_node, s, options):
    nodes = []
    f = options['fill']
    ftype = f['type']
    background = ftype == 'hatch' and f['hatch']['background']
    if background:
        bg = _el(rule_node, SLD, 'PolygonSymbolizer')
        _fill(bg, s.fill, s.fill_opacity)
        nodes.append(bg)
    node = _el(rule_node, SLD, 'PolygonSymbolizer')
    margin = 0
    if ftype == 'solid':
        _fill(node, s.fill, s.fill_opacity)
    elif ftype == 'hatch':
        margin = _hatch_graphic(_el(node, SLD, 'Fill'), f['hatch'])
    # ftype == 'none': sin Fill
    if s.stroke_width:
        _stroke(node, s, options['stroke'])
    if margin:
        _vendor(node, 'graphic-margin', fmt(margin))
    nodes.append(node)
    return nodes


# --------------------------------------------------------------------------- API

def build_symbolizer(rule, s, options, geom_field=None):
    '''
    Añade al Rule del SLD (sld.Rule) los simbolizadores SLD de un simbolizador nuevo.
    s: modelo MarkSymbolizer / LineSymbolizer / PolygonSymbolizer; options: dict normalizado.
    geom_field: dict de get_geometry_field (o None); solo se usa para los extremos de línea.
    Devuelve la lista de nodos creados (el primero lleva el marcador).
    '''
    kind = symbol_options.kind_of(s)
    rule_node = rule._node
    if kind == 'mark':
        nodes = _build_mark(rule_node, s, options)
    elif kind == 'line':
        geom_name = geom_field.get('field_name') if isinstance(geom_field, dict) else None
        nodes = _build_line(rule_node, s, options, geom_name or None)
    elif kind == 'polygon':
        nodes = _build_polygon(rule_node, s, options)
    else:
        raise ValueError('Tipo de simbolizador no soportado')
    _marker(nodes[0], kind, s, options, len(nodes))
    # el marcador va al final de los hijos del primer nodo (después de las VendorOption propias)
    return nodes


# --------------------------------------------------------------------------- importación

def _q(elem):
    return etree.QName(elem)


def _canonical(elem):
    '''Árbol comparable: sin prefijos, sin espacios de formato y sin comentarios.'''
    text = elem.text or ''
    if not text.strip():
        text = ''
    attrs = tuple(sorted((k, v) for k, v in elem.attrib.items()))
    return (elem.tag, attrs, text.strip() if text else '',
            tuple(_canonical(c) for c in elem if isinstance(c.tag, str)))


class _RuleHolder(object):
    def __init__(self):
        self._node = etree.Element('{%s}Rule' % SLD, nsmap=SLDNode._nsmap)


def read_marker(node):
    '''Datos del marcador gvsigol-symbol de un simbolizador SLD, o None.'''
    for c in node:
        if (isinstance(c.tag, str) and _q(c).namespace == SLD and _q(c).localname == 'VendorOption'
                and c.get('name') == MARKER):
            try:
                data = json.loads(c.text or '')
            except (TypeError, ValueError):
                return None
            if (isinstance(data, dict) and data.get('v') == MARKER_VERSION and data.get('kind') in COLUMNS
                    and isinstance(data.get('columns'), dict) and isinstance(data.get('parts'), int)
                    and 1 <= data['parts'] <= 4 and _q(node).localname == SLD_TAG[data['kind']]):
                return data
            return None
    return None


def import_group(nodes, model_class, geom_field=None):
    '''
    nodes: simbolizadores SLD seguidos, empezando por el que lleva el marcador.
    Si el marcador describe exactamente esos nodos (al regenerarlos salen iguales), devuelve
    (instancia sin guardar de model_class con columnas y opciones, número de nodos usados).
    Si no, None: se importan como siempre, uno a uno.
    '''
    try:
        data = read_marker(nodes[0])
        if data is None or symbol_options.kind_of(model_class.__name__) != data['kind']:
            return None
        count = data['parts']
        if len(nodes) < count:
            return None
        kind = data['kind']
        options = symbol_options.normalize(kind, data.get('options'))
        if options is None:
            return None
        columns = dict((c, data['columns'].get(c)) for c in COLUMNS[kind])
        instance = model_class(options=symbol_options.dumps(options), **columns)
        holder = _RuleHolder()
        rebuilt = build_symbolizer(holder, instance, options, geom_field)
        if len(rebuilt) == count and all(_canonical(a) == _canonical(b) for a, b in zip(rebuilt, nodes[:count])):
            return instance, count
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    return None


SYMBOLIZER_TAGS = ('PointSymbolizer', 'LineSymbolizer', 'PolygonSymbolizer', 'TextSymbolizer', 'RasterSymbolizer')


def plan_groups(sym_nodes, models_by_tag, geom_field=None):
    '''
    Para una lista de simbolizadores SLD de una regla (en orden), los grupos de simbolizadores
    nuevos reconocidos: {índice inicial: (instancia sin guardar, nodos que ocupa)}.
    '''
    plan = {}
    index = 0
    while index < len(sym_nodes):
        node = sym_nodes[index]
        model = models_by_tag.get(_q(node).localname)
        found = None
        if model is not None and read_marker(node) is not None:
            found = import_group(sym_nodes[index:], model, geom_field)
        if found is not None:
            plan[index] = found
            index += found[1]
        else:
            index += 1
    return plan
