# -*- coding: utf-8 -*-
'''
Ficheros de los gráficos externos de las bibliotecas de símbolos (PNG y SVG).

- PNG: se guarda exactamente como siempre (mismo nombre .png, mismo contenido).
- SVG: se admite desde ahora. Como los ficheros se sirven desde /media, en el mismo
  dominio que la aplicación, un SVG con código podría ejecutarse con la sesión del
  usuario si alguien lo abre directamente. Por eso se limpia con una lista blanca
  estricta antes de guardarlo: solo elementos y atributos de dibujo, sin scripts,
  manejadores de eventos, referencias externas ni DOCTYPE/entidades.
- Si el SVG no se puede limpiar con garantías, se rechaza con un mensaje claro.

Además se asegura un tamaño propio (width/height): GeoServer (Batik) y el visor SPA
(canvas) lo necesitan para escalar el símbolo sin deformarlo.
'''
import re

from django.core.files.base import ContentFile
from django.utils.translation import gettext as _
from lxml import etree

SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
MAX_SVG_BYTES = 1024 * 1024   # 1 MB: un símbolo no necesita más

FORMAT_PNG = 'image/png'
FORMAT_SVG = 'image/svg+xml'

# Elementos de dibujo permitidos (SVG 1.1 estático). Todo lo demás se elimina:
# script, foreignObject, animaciones (pueden reescribir href), iframe, etc.
ALLOWED_ELEMENTS = {
    'svg', 'g', 'defs', 'symbol', 'use', 'title', 'desc', 'metadata',
    'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon',
    'text', 'tspan', 'textPath',
    'linearGradient', 'radialGradient', 'stop', 'pattern', 'clipPath', 'mask', 'marker',
    'filter', 'feGaussianBlur', 'feOffset', 'feBlend', 'feColorMatrix', 'feMerge', 'feMergeNode',
    'feFlood', 'feComposite', 'feMorphology', 'feDropShadow',
    'image', 'style',
}

# Atributos permitidos (sin espacio de nombres, salvo xlink:href / xml:space).
ALLOWED_ATTRIBUTES = {
    'id', 'class', 'style', 'transform', 'viewBox', 'preserveAspectRatio', 'width', 'height',
    'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'fx', 'fy', 'd', 'points',
    'fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity',
    'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray',
    'stroke-dashoffset', 'opacity', 'color', 'display', 'visibility', 'overflow',
    'clip-path', 'clip-rule', 'clipPathUnits', 'mask', 'maskUnits', 'maskContentUnits',
    'filter', 'filterUnits', 'primitiveUnits', 'in', 'in2', 'result', 'stdDeviation', 'dx', 'dy',
    'mode', 'type', 'values', 'operator', 'k1', 'k2', 'k3', 'k4', 'radius',
    'flood-color', 'flood-opacity',
    'gradientUnits', 'gradientTransform', 'spreadMethod', 'offset', 'stop-color', 'stop-opacity',
    'patternUnits', 'patternContentUnits', 'patternTransform',
    'markerWidth', 'markerHeight', 'markerUnits', 'orient', 'refX', 'refY',
    'marker-start', 'marker-mid', 'marker-end',
    'font-family', 'font-size', 'font-weight', 'font-style', 'text-anchor',
    'dominant-baseline', 'alignment-baseline', 'letter-spacing', 'word-spacing',
    'text-decoration', 'startOffset', 'lengthAdjust', 'textLength', 'rotate',
    'version', 'baseProfile', 'enable-background', 'xml:space', 'href',
    'vector-effect', 'shape-rendering', 'image-rendering', 'color-interpolation-filters',
}

# href permitido: solo referencias internas (#id) o imágenes rasterizadas embebidas.
_SAFE_HREF = re.compile(r'^\s*(#[A-Za-z_][\w.\-:]*|data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+)\s*$')
# En CSS (atributo style o <style>) solo se permiten url(#id).
_CSS_URL = re.compile(r'url\(\s*([\'"]?)(.*?)\1\s*\)', re.I | re.S)
_CSS_FORBIDDEN = re.compile(r'(javascript:|expression\s*\(|@import|behavior\s*:|-moz-binding)', re.I)
_LENGTH = re.compile(r'^\s*([0-9]*\.?[0-9]+)\s*(px)?\s*$')


class ExternalGraphicError(ValueError):
    '''Fichero no válido como gráfico externo (el mensaje se muestra al usuario).'''


def _local(tag):
    return etree.QName(tag).localname if isinstance(tag, str) else None


def _css_is_safe(css):
    if _CSS_FORBIDDEN.search(css):
        return False
    for _quote, target in _CSS_URL.findall(css):
        if not target.strip().startswith('#'):
            return False
    return True


def is_png(data):
    return data[:8] == PNG_SIGNATURE


def looks_like_svg(data, filename=''):
    head = data[:2048].lstrip(b'\xef\xbb\xbf \t\r\n').lower()
    return (filename or '').lower().endswith('.svg') or head.startswith(b'<svg') or (
        head.startswith(b'<?xml') and b'<svg' in data[:4096].lower())


def sanitize_svg(data):
    '''
    SVG (bytes) -> SVG limpio (bytes). Lanza ExternalGraphicError si no es un SVG válido.
    '''
    if len(data) > MAX_SVG_BYTES:
        raise ExternalGraphicError(_('The SVG file is too large (maximum 1 MB).'))
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                             dtd_validation=False, huge_tree=False, remove_comments=True,
                             remove_pis=True, recover=False)
    try:
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError:
        raise ExternalGraphicError(_('The SVG file is not valid.'))
    if root is None or _local(root.tag) != 'svg' or etree.QName(root.tag).namespace != SVG_NS:
        raise ExternalGraphicError(_('The SVG file is not valid.'))

    # 1) Elementos: fuera todo lo que no sea de dibujo (y lo que no sea del espacio SVG,
    #    salvo los metadatos de editores como Inkscape, que también se quitan).
    for elem in list(root.iter()):
        if elem is root:
            continue
        if not isinstance(elem.tag, str):
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
            continue
        q = etree.QName(elem.tag)
        if q.namespace != SVG_NS or q.localname not in ALLOWED_ELEMENTS:
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)

    # 2) Atributos y CSS
    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        for attr in list(elem.attrib):
            q = etree.QName(attr)
            value = elem.attrib[attr]
            if q.namespace == XLINK_NS and q.localname == 'href':
                name = 'href'
            elif q.namespace == 'http://www.w3.org/XML/1998/namespace' and q.localname == 'space':
                name = 'xml:space'
            elif q.namespace:
                name = None          # sodipodi:, inkscape:, etc. -> fuera
            else:
                name = q.localname
            if name is None or name not in ALLOWED_ATTRIBUTES or name.lower().startswith('on'):
                del elem.attrib[attr]
            elif name == 'href' and not _SAFE_HREF.match(value):
                del elem.attrib[attr]
            elif name == 'style' and not _css_is_safe(value):
                del elem.attrib[attr]
            elif name != 'href' and re.search(r'javascript:', value, re.I):
                del elem.attrib[attr]
        if _local(elem.tag) == 'style':
            if len(elem):
                for child in list(elem):
                    elem.remove(child)
            if elem.text and not _css_is_safe(elem.text):
                elem.getparent().remove(elem)
        if _local(elem.tag) == 'image' and not elem.get('href') and not elem.get('{%s}href' % XLINK_NS):
            # <image> sin una imagen embebida segura no aporta nada
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)

    # 3) Tamaño propio a partir del viewBox si falta (o si es relativo, p. ej. 100%)
    width, height = root.get('width'), root.get('height')
    if not (width and _LENGTH.match(width) and height and _LENGTH.match(height)):
        vb = (root.get('viewBox') or '').replace(',', ' ').split()
        try:
            vb_w, vb_h = float(vb[2]), float(vb[3])
        except (IndexError, ValueError):
            vb_w = vb_h = 0
        if vb_w > 0 and vb_h > 0:
            root.set('width', ('%g' % vb_w))
            root.set('height', ('%g' % vb_h))
        else:
            raise ExternalGraphicError(_('The SVG file must define its size (width and height, or a viewBox).'))

    # Fuera las declaraciones de espacios de nombres que ya no se usan (inkscape, sodipodi...)
    etree.cleanup_namespaces(root)
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8')


def prepare_upload(uploaded):
    '''
    Fichero subido -> (extensión, fichero a guardar, formato o None).
    - SVG: limpio, con extensión .svg y formato image/svg+xml.
    - Cualquier otro: igual que siempre (.png, el fichero tal cual y sin forzar formato).
    '''
    data = uploaded.read()
    uploaded.seek(0)
    if not is_png(data) and looks_like_svg(data, getattr(uploaded, 'name', '')):
        clean = sanitize_svg(data)
        return '.svg', ContentFile(clean), FORMAT_SVG
    return '.png', uploaded, None


def sanitize_svg_file(path):
    '''Limpia en el sitio un .svg ya guardado (importación de bibliotecas). False si se descarta.'''
    try:
        with open(path, 'rb') as f:
            clean = sanitize_svg(f.read())
    except (ExternalGraphicError, OSError):
        return False
    with open(path, 'wb') as f:
        f.write(clean)
    return True
