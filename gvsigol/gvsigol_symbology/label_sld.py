# -*- coding: utf-8 -*-
'''
SLD de las etiquetas NUEVAS (TextSymbolizer con options; ver label_options.py).

sld_builder solo llama aquí cuando la etiqueta tiene opciones; las etiquetas
antiguas siguen el código de siempre y su SLD no cambia.

Orden de elementos del TextSymbolizer (SLD 1.0 + extensiones de GeoServer):
Geometry, Label, Font, LabelPlacement, Halo, Fill, Graphic, Priority, VendorOption*.
Todos los valores que vienen del usuario entran como texto de un nodo lxml (se
escapan); los nombres de campo ya vienen validados por label_options.normalize.
'''
from lxml import etree

from gvsigol_symbology.sld import TextSymbolizer, SLDNode

SLD = SLDNode._nsmap['sld']
OGC = SLDNode._nsmap['ogc']

# Posición de la etiqueta respecto al punto -> AnchorPoint (x, y) de la etiqueta.
# p. ej. «top» (encima del punto) ancla la etiqueta por su borde inferior central.
ANCHORS = {
    'top-left': (1.0, 0.0), 'top': (0.5, 0.0), 'top-right': (0.0, 0.0),
    'left': (1.0, 0.5), 'center': (0.5, 0.5), 'right': (0.0, 0.5),
    'bottom-left': (1.0, 1.0), 'bottom': (0.5, 1.0), 'bottom-right': (0.0, 1.0),
}
LINE_TYPES = ('LINESTRING', 'MULTILINESTRING')
POLYGON_TYPES = ('POLYGON', 'MULTIPOLYGON')


def _el(parent, ns, tag, text=None, **attrs):
    elem = etree.SubElement(parent, '{%s}%s' % (ns, tag))
    for k, v in attrs.items():
        elem.set(k, v)
    if text is not None:
        elem.text = text
    return elem


def _fmt(n):
    '''Número -> texto sin decimales innecesarios (15.0 -> "15").'''
    n = float(n)
    return str(int(n)) if n == int(n) else repr(n)


def _css(parent, name, value):
    _el(parent, SLD, 'CssParameter', value, name=name)


def _vendor(parent, name, value):
    _el(parent, SLD, 'VendorOption', value, name=name)


def _function(parent, name):
    return _el(parent, OGC, 'Function', name=name)


def _number_pattern(decimals, thousands):
    pattern = '0' if not decimals else '0.' + '0' * decimals
    return ('#,##' + pattern) if thousands else pattern


def _append_part_expression(parent, part):
    if part['type'] == 'text':
        _el(parent, OGC, 'Literal', part['value'])
        return
    if 'number' in part:
        fn = _function(parent, 'numberFormat')
        _el(fn, OGC, 'Literal', _number_pattern(part['number']['decimals'], part['number']['thousands']))
        _el(fn, OGC, 'PropertyName', part['name'])
        # idioma explícito: mismo separador de miles/decimal en GeoServer y en el SPA
        _el(fn, OGC, 'Literal', part['number'].get('locale', 'en'))
    elif 'date' in part:
        fn = _function(parent, 'dateFormat')
        _el(fn, OGC, 'Literal', part['date'])
        _el(fn, OGC, 'PropertyName', part['name'])
    else:
        _el(parent, OGC, 'PropertyName', part['name'])


def _label(node, text_symbolizer, options):
    parts = options['content'].get('parts') or (
        [{'type': 'field', 'name': text_symbolizer.label}] if text_symbolizer.label else [])
    label = _el(node, SLD, 'Label')
    case = options['content'].get('case', 'none')
    target = label
    if case in ('upper', 'lower'):
        target = _function(label, 'strToUpperCase' if case == 'upper' else 'strToLowerCase')
    if len(parts) > 1:
        target = _function(target, 'Concatenate')
    for part in parts:
        _append_part_expression(target, part)


def _font(node, s):
    font = _el(node, SLD, 'Font')
    _css(font, 'font-family', s.font_family)
    _css(font, 'font-size', str(s.font_size))
    _css(font, 'font-style', s.font_style)
    _css(font, 'font-weight', str(s.font_weight))


def _rotation(placement_elem, rotation):
    if rotation.get('field'):
        rot = _el(placement_elem, SLD, 'Rotation')
        _el(rot, OGC, 'PropertyName', rotation['field'])
    elif rotation.get('angle'):
        _el(placement_elem, SLD, 'Rotation', _fmt(rotation['angle']))


def _point_placement(lp, anchor, dx, dy, rotation):
    pp = _el(lp, SLD, 'PointPlacement')
    ap = _el(pp, SLD, 'AnchorPoint')
    _el(ap, SLD, 'AnchorPointX', _fmt(anchor[0]))
    _el(ap, SLD, 'AnchorPointY', _fmt(anchor[1]))
    if dx or dy:
        disp = _el(pp, SLD, 'Displacement')
        _el(disp, SLD, 'DisplacementX', _fmt(dx))
        _el(disp, SLD, 'DisplacementY', _fmt(dy))
    _rotation(pp, rotation)


def box_layout(kind, placement):
    '''
    Cómo dibujar el recuadro de fondo en GeoServer -> 'independent', 'label' o 'single_line'.

    Fallo de GeoTools (LabelPainter.paintStraightLabel, también en su rama principal): con el
    texto partido en varias líneas, el recuadro se desplaza con la sangría de la ÚLTIMA línea.
    Si las líneas van centradas o alineadas a la derecha y la última es más corta, el texto se
    sale del recuadro. No pasa con una sola línea ni con el texto alineado a la izquierda.
    - Texto centrado en el punto (polígonos, o puntos «centro» sin desplazamiento) y sin
      rotación: graphicPlacement=independent centra el recuadro en el punto y encaja siempre.
    - Texto alineado a la izquierda (posiciones «a la derecha», ancla X = 0): no le afecta.
    - Resto (encima/debajo/izquierda del punto, rotación, líneas): sin autoWrap, en una línea.
    '''
    rotated = bool(placement['rotation'].get('field') or placement['rotation'].get('angle'))
    if kind == 'line':
        return 'single_line'
    if kind == 'polygon':
        return 'single_line' if rotated else 'independent'
    pt = placement['point']
    anchor_x = ANCHORS[pt['position']][0]
    if pt['position'] == 'center' and not pt['dx'] and not pt['dy'] and not rotated:
        return 'independent'
    return 'label' if anchor_x == 0.0 else 'single_line'


def geometry_kind(geom_field):
    gtype = (geom_field or {}).get('field_type', '') if isinstance(geom_field, dict) else ''
    if gtype in LINE_TYPES:
        return 'line'
    if gtype in POLYGON_TYPES:
        return 'polygon'
    return 'point'


def build_text_symbolizer(rule, s, geom_field, options):
    '''
    Añade al Rule del SLD el TextSymbolizer de una etiqueta nueva.
    rule: sld.Rule; s: modelo TextSymbolizer; geom_field: dict de get_geometry_field o '';
    options: dict normalizado (label_options.normalize).
    '''
    # Como en las etiquetas antiguas, no se mira is_actived: el editor no lo guarda (queda
    # False en BD) y una etiqueta desactivada no llega a guardarse como regla «_text».
    symbolizer = TextSymbolizer(rule)
    node = symbolizer._node
    kind = geometry_kind(geom_field)
    placement = options['placement']

    # Geometry: polígonos en su punto interior (o centroide) para que la etiqueta caiga dentro
    if kind == 'polygon' and isinstance(geom_field, dict) and geom_field.get('field_name'):
        geom = _el(node, SLD, 'Geometry')
        fn = _function(geom, 'interiorPoint' if placement['polygon']['mode'] == 'interior' else 'centroid')
        _el(fn, OGC, 'PropertyName', geom_field['field_name'])

    _label(node, s, options)
    _font(node, s)

    lp = _el(node, SLD, 'LabelPlacement')
    if kind == 'line':
        line = placement['line']
        lpl = _el(lp, SLD, 'LinePlacement')
        if line['offset']:
            _el(lpl, SLD, 'PerpendicularOffset', _fmt(line['offset']))
    elif kind == 'polygon':
        _point_placement(lp, ANCHORS['center'], 0, 0, placement['rotation'])
    else:
        pt = placement['point']
        _point_placement(lp, ANCHORS[pt['position']], pt['dx'], pt['dy'], placement['rotation'])

    if options['style']['halo'] and s.halo_radius:
        halo = _el(node, SLD, 'Halo')
        _el(halo, SLD, 'Radius', _fmt(s.halo_radius))
        hfill = _el(halo, SLD, 'Fill')
        _css(hfill, 'fill', s.halo_fill)
        _css(hfill, 'fill-opacity', str(s.halo_fill_opacity))

    fill = _el(node, SLD, 'Fill')
    _css(fill, 'fill', s.fill)
    _css(fill, 'fill-opacity', str(s.fill_opacity))

    bg = options['background']
    if bg['type'] == 'box':
        graphic = _el(node, SLD, 'Graphic')
        mark = _el(graphic, SLD, 'Mark')
        _el(mark, SLD, 'WellKnownName', 'square')
        mfill = _el(mark, SLD, 'Fill')
        _css(mfill, 'fill', bg['fill'])
        _css(mfill, 'fill-opacity', _fmt(bg['fill_opacity']))
        if bg['stroke_width']:
            mstroke = _el(mark, SLD, 'Stroke')
            _css(mstroke, 'stroke', bg['stroke'])
            _css(mstroke, 'stroke-width', _fmt(bg['stroke_width']))

    if options['priority']['field']:
        prio = _el(node, SLD, 'Priority')
        _el(prio, OGC, 'PropertyName', options['priority']['field'])

    # Opciones de GeoServer (todas tienen equivalente en el SPA salvo «partials» y «group»,
    # que se mantienen como en las etiquetas antiguas)
    bg = options['background']
    layout = box_layout(kind, placement) if bg['type'] == 'box' else None
    _vendor(node, 'conflictResolution', 'false' if options['priority']['allow_overlap'] else 'true')
    if placement['wrap'] and layout != 'single_line':
        _vendor(node, 'autoWrap', str(placement['wrap']))
    _vendor(node, 'spaceAround', str(options['priority']['space_around']))
    _vendor(node, 'partials', 'true')
    if options['style']['letter_spacing']:
        _vendor(node, 'charSpacing', _fmt(options['style']['letter_spacing']))
    if bg['type'] == 'box':
        _vendor(node, 'graphic-resize', 'stretch')
        _vendor(node, 'graphic-margin', str(bg['padding']))
        if layout == 'independent':
            _vendor(node, 'graphicPlacement', 'independent')
    if kind == 'line':
        line = placement['line']
        _vendor(node, 'followLine', 'true' if line['follow'] else 'false')
        if line['follow']:
            _vendor(node, 'maxAngleDelta', str(line['max_angle']))
        if line['repeat']:
            _vendor(node, 'repeat', str(line['repeat']))
        _vendor(node, 'group', 'yes')
        _vendor(node, 'forceLeftToRight', 'true')
    return symbolizer


# ---------------------------------------------------------------------------
# Importación de SLD: reconstruir las opciones de una etiqueta nueva
# ---------------------------------------------------------------------------
# Al importar un SLD, un TextSymbolizer solo se convierte en etiqueta nueva si
# es EXACTAMENTE lo que generaría build_text_symbolizer con las opciones leídas
# (se regenera y se compara). Cualquier otro TextSymbolizer (etiquetas antiguas,
# SLD escritos a mano, opciones que el modelo no representa) se importa como
# siempre, como etiqueta antigua.

_ANCHOR_TO_POSITION = dict((v, k) for k, v in ANCHORS.items())


def _q(elem):
    return etree.QName(elem)


def _children(elem, ns=None, tag=None):
    out = []
    for c in elem:
        if not isinstance(c.tag, str):
            continue
        q = _q(c)
        if (ns is None or q.namespace == ns) and (tag is None or q.localname == tag):
            out.append(c)
    return out


def _child(elem, ns, tag):
    found = _children(elem, ns, tag)
    return found[0] if found else None


def _text(elem, ns, tag):
    c = _child(elem, ns, tag) if elem is not None else None
    return c.text if c is not None and c.text is not None else None


def _parse_part(expr):
    q = _q(expr)
    if q.namespace != OGC:
        raise ValueError('expresión no soportada')
    if q.localname == 'Literal':
        return {'type': 'text', 'value': expr.text or ''}
    if q.localname == 'PropertyName':
        return {'type': 'field', 'name': (expr.text or '').strip()}
    if q.localname == 'Function':
        args = _children(expr)
        name = expr.get('name')
        if name == 'numberFormat' and len(args) == 3:
            pattern = args[0].text or ''
            decimals = len(pattern.split('.', 1)[1]) if '.' in pattern else 0
            return {'type': 'field', 'name': (args[1].text or '').strip(),
                    'number': {'decimals': decimals, 'thousands': pattern.startswith('#,##'),
                               'locale': (args[2].text or '').strip()}}
        if name == 'dateFormat' and len(args) == 2:
            return {'type': 'field', 'name': (args[1].text or '').strip(), 'date': args[0].text or ''}
    raise ValueError('expresión no soportada')


def _parse_label(label, content):
    exprs = _children(label)
    if len(exprs) != 1:
        raise ValueError('etiqueta no soportada')
    expr = exprs[0]
    if _q(expr).localname == 'Function' and expr.get('name') in ('strToUpperCase', 'strToLowerCase'):
        content['case'] = 'upper' if expr.get('name') == 'strToUpperCase' else 'lower'
        inner = _children(expr)
        if len(inner) != 1:
            raise ValueError('etiqueta no soportada')
        expr = inner[0]
    if _q(expr).localname == 'Function' and expr.get('name') == 'Concatenate':
        content['parts'] = [_parse_part(e) for e in _children(expr)]
    else:
        content['parts'] = [_parse_part(expr)]


def parse_options(node):
    '''
    TextSymbolizer (lxml) -> opciones v1 sin normalizar (lo que haya en el SLD).
    Lanza ValueError si contiene algo que las opciones no pueden representar.
    '''
    content, placement, priority, style, background = {}, {}, {}, {'halo': False}, {'type': 'none'}
    geometry = _child(node, SLD, 'Geometry')
    if geometry is not None:
        fn = _child(geometry, OGC, 'Function')
        if fn is None or fn.get('name') not in ('interiorPoint', 'centroid'):
            raise ValueError('geometría no soportada')
        placement['polygon'] = {'mode': 'interior' if fn.get('name') == 'interiorPoint' else 'centroid'}
    label = _child(node, SLD, 'Label')
    if label is None:
        raise ValueError('sin Label')
    _parse_label(label, content)

    lp = _child(node, SLD, 'LabelPlacement')
    line = _child(lp, SLD, 'LinePlacement') if lp is not None else None
    point = _child(lp, SLD, 'PointPlacement') if lp is not None else None
    if line is not None:
        placement['line'] = {'offset': float(_text(line, SLD, 'PerpendicularOffset') or 0)}
    elif point is not None:
        ap = _child(point, SLD, 'AnchorPoint')
        anchor = (float(_text(ap, SLD, 'AnchorPointX')), float(_text(ap, SLD, 'AnchorPointY')))
        if anchor not in _ANCHOR_TO_POSITION:
            raise ValueError('anclaje no soportado')
        disp = _child(point, SLD, 'Displacement')
        placement['point'] = {'position': _ANCHOR_TO_POSITION[anchor],
                              'dx': float(_text(disp, SLD, 'DisplacementX') or 0) if disp is not None else 0,
                              'dy': float(_text(disp, SLD, 'DisplacementY') or 0) if disp is not None else 0}
        rot = _child(point, SLD, 'Rotation')
        if rot is not None:
            prop = _child(rot, OGC, 'PropertyName')
            placement['rotation'] = ({'field': (prop.text or '').strip()} if prop is not None
                                     else {'angle': float(rot.text)})
    if _child(node, SLD, 'Halo') is not None:
        style['halo'] = True

    graphic = _child(node, SLD, 'Graphic')
    if graphic is not None:
        mark = _child(graphic, SLD, 'Mark')
        background = {'type': 'box'}
        for part, keys in (('Fill', (('fill', 'fill'), ('fill-opacity', 'fill_opacity'))),
                           ('Stroke', (('stroke', 'stroke'), ('stroke-width', 'stroke_width')))):
            elem = _child(mark, SLD, part) if mark is not None else None
            if elem is None:
                if part == 'Stroke':
                    background['stroke_width'] = 0
                continue
            for css in _children(elem, SLD, 'CssParameter'):
                for name, key in keys:
                    if css.get('name') == name:
                        background[key] = css.text if key in ('fill', 'stroke') else float(css.text)
    prio = _child(node, SLD, 'Priority')
    if prio is not None:
        prop = _child(prio, OGC, 'PropertyName')
        priority['field'] = (prop.text or '').strip() if prop is not None else None

    vendor = dict((v.get('name'), (v.text or '').strip()) for v in _children(node, SLD, 'VendorOption'))
    priority['allow_overlap'] = vendor.get('conflictResolution') == 'false'
    placement['wrap'] = int(vendor.get('autoWrap') or 0)
    priority['space_around'] = int(vendor.get('spaceAround') or 0)
    style['letter_spacing'] = float(vendor.get('charSpacing') or 0)
    if 'graphic-margin' in vendor:
        background['padding'] = int(vendor['graphic-margin'])
    if line is not None:
        follow = vendor.get('followLine') == 'true'
        placement['line'].update({'follow': follow, 'repeat': int(vendor.get('repeat') or 0)})
        if follow and 'maxAngleDelta' in vendor:
            placement['line']['max_angle'] = int(vendor['maxAngleDelta'])
    return {'v': 1, 'content': content, 'placement': placement, 'priority': priority,
            'style': style, 'background': background}


def _canonical(elem):
    '''Árbol comparable: sin prefijos, sin espacios de formato y sin comentarios.'''
    text = elem.text or ''
    if not text.strip():
        text = ''
    return (elem.tag, tuple(sorted(elem.attrib.items())), text,
            tuple(_canonical(c) for c in elem if isinstance(c.tag, str)))


class _RuleHolder(object):
    def __init__(self):
        self._node = etree.Element('{%s}Rule' % SLD, nsmap=SLDNode._nsmap)


def options_from_sld(node, text_symbolizer, geom_field):
    '''
    Opciones normalizadas si `node` es exactamente el SLD de una etiqueta nueva para este
    simbolizador (con sus valores de fuente, color y halo) y esta geometría; si no, None.
    '''
    try:
        options = normalize_options(parse_options(node))
        if options is None:
            return None
        holder = _RuleHolder()
        build_text_symbolizer(holder, text_symbolizer, geom_field, options)
        rebuilt = _children(holder._node, SLD, 'TextSymbolizer')
        if len(rebuilt) == 1 and _canonical(rebuilt[0]) == _canonical(node):
            return options
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    return None


def normalize_options(raw):
    from gvsigol_symbology import label_options
    return label_options.normalize(raw)
