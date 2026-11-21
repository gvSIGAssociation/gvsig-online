# -*- coding: utf-8 -*-
'''
Vista previa de simbolizadores en el editor con el MISMO SLD que se publica (sld_builder /
symbol_sld), en lugar del SLD que genera el JavaScript del editor (que no conoce las opciones
avanzadas). La usan los simbolizadores con opciones; los antiguos siguen con su vista previa.

La imagen la pinta GeoServer con las capas de vista previa (preview_point/line/polygon), como
siempre: GetLegendGraphic. Para las líneas con decoraciones (marcas, extremos, desplazamiento)
se pide antes un GetMap con una línea quebrada, porque la leyenda dibuja una recta y no aplica
las funciones de geometría; si GeoServer no lo permite, se vuelve a GetLegendGraphic.
'''
import json
import re
from types import SimpleNamespace

from . import sld_builder, symbol_options, utils
from .sld import StyledLayerDescriptor
from .symbolizer_factory import build_geometry_symbolizer

PREVIEW_LAYERS = {'preview_point': 'mark', 'preview_line': 'line', 'preview_polygon': 'polygon'}
PREVIEW_WORKSPACE = 'preview'  # espacio de trabajo de las capas de vista previa en GeoServer
PREVIEW_GEOM_NAME = 'geom'  # columna de geometría de las tablas preview.* (docker/gvsigol-postgis/conf/init.sql)
MAX_SYMBOLIZERS = 10
SIZE_LIMITS = (16, 600)
def zigzag_frame(width, height):
    '''
    (encuadre, función geomFromWKT) de la línea quebrada para una imagen de width x height: el
    encuadre respeta la proporción de la imagen (WMS 1.1.1 deforma si no) y la línea deja margen
    en los extremos para las marcas de inicio y fin. El encuadre corta la recta (0 0, 1 1) de la
    capa preview_line, que es la que se consulta.
    '''
    span = 1.1 * float(height) / float(width)
    miny = -0.05
    low, high = miny + 0.3 * span, miny + 0.7 * span
    points = ((0.12, low), (0.31, high), (0.5, low), (0.69, high), (0.88, low))
    wkt = 'LINESTRING(%s)' % ', '.join('%.4f %.4f' % p for p in points)
    bbox = '-0.05,%.4f,1.05,%.4f' % (miny, miny + span)
    return bbox, '<ogc:Function name="geomFromWKT"><ogc:Literal>%s</ogc:Literal></ogc:Function>' % wkt


_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


class PreviewError(ValueError):
    pass


def parse_symbolizers(raw):
    '''
    JSON del editor ([{type, json}], json como texto o dict) -> instancias sin guardar.
    Solo marcas, líneas y polígonos; colores #rrggbb; opciones normalizadas.
    '''
    try:
        items = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        raise PreviewError('JSON inválido')
    if not isinstance(items, list) or not items or len(items) > MAX_SYMBOLIZERS:
        raise PreviewError('Lista de simbolizadores inválida')
    instances = []
    for item in items:
        if not isinstance(item, dict):
            raise PreviewError('Simbolizador inválido')
        data = item.get('json')
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                raise PreviewError('Simbolizador inválido')
        if not isinstance(data, dict):
            raise PreviewError('Simbolizador inválido')
        for key in ('fill', 'stroke'):
            if key in data and data[key] not in (None, '') and not _COLOR_RE.match(str(data[key])):
                raise PreviewError('Color no válido')
        instance = build_geometry_symbolizer(item.get('type'), data)
        if instance is None:
            raise PreviewError('Tipo de simbolizador no soportado')
        instances.append(instance)
    return instances


def build_sld(layer_name, instances, geom_name=PREVIEW_GEOM_NAME):
    '''SLD (bytes) de una regla con estos simbolizadores, en el orden recibido.'''
    sld = StyledLayerDescriptor()
    named_layer = sld.create_namedlayer(layer_name)
    user_style = named_layer.create_userstyle('symbol_preview', 'symbol_preview')
    fts = user_style.create_featuretypestyle()
    rule = SimpleNamespace(minscale=-1, maxscale=-1, filter='', title='preview', name='preview')
    wrappers = [SimpleNamespace(**{type(i).__name__.lower(): i}) for i in instances]
    geom_field = {'field_name': geom_name, 'field_type': 'LINESTRING'}
    sld_builder.create_rule(rule, wrappers, fts, geom_field)
    return sld.as_sld(True)


def with_zigzag(sld_text, zigzag, geom_name=PREVIEW_GEOM_NAME):
    '''Las líneas (y las funciones de sus extremos) se dibujan sobre una línea quebrada fija.'''
    text = sld_text.decode('utf-8') if isinstance(sld_text, bytes) else sld_text
    text = text.replace('<sld:LineSymbolizer>', '<sld:LineSymbolizer><sld:Geometry>%s</sld:Geometry>' % zigzag)
    return text.replace('<ogc:PropertyName>%s</ogc:PropertyName>' % geom_name, zigzag)


def needs_map(instances):
    '''True si alguna línea tiene decoraciones que la leyenda no puede mostrar.'''
    for instance in instances:
        options = symbol_options.of(instance)
        if symbol_options.kind_of(instance) == 'line' and options and (
                options['marks'] or options['start'] or options['end'] or options['stroke']['offset']):
            return True
    return False


def _size(value, default):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(SIZE_LIMITS[0], min(SIZE_LIMITS[1], n))


def requests_for(params, instances, width=None, height=None):
    '''
    Peticiones a GeoServer por orden de preferencia: [(parámetros, es_getmap), ...].
    params: parámetros de la URL de vista previa del editor (GetLegendGraphic con LAYER=preview_*).
    '''
    upper = dict((k.upper(), v) for k, v in params)
    layer = upper.get('LAYER', '')
    if layer not in PREVIEW_LAYERS:
        raise PreviewError('Capa de vista previa no permitida')
    w = _size(width, _size(upper.get('WIDTH'), 20))
    h = _size(height, _size(upper.get('HEIGHT'), 20))
    sld = utils.geoserver_sld(build_sld(layer, instances))
    legend = [('SERVICE', 'WMS'), ('VERSION', '1.0.0'), ('REQUEST', 'GetLegendGraphic'), ('FORMAT', 'image/png'),
              ('WIDTH', str(w)), ('HEIGHT', str(h)), ('LAYER', layer),
              ('LEGEND_OPTIONS', 'forceLabels:off'), ('SLD_BODY', sld)]
    result = []
    if PREVIEW_LAYERS[layer] == 'line' and needs_map(instances):
        # En GetMap el NamedLayer del SLD tiene que llevar el nombre cualificado (ws:capa): si no
        # coincide, GeoServer pinta en silencio el estilo guardado de la capa (no el del SLD). Si el
        # espacio de trabajo no existe, GeoServer da error y se usa la leyenda.
        qualified = '%s:%s' % (PREVIEW_WORKSPACE, layer)
        map_sld = utils.geoserver_sld(build_sld(qualified, instances))
        bbox, zigzag = zigzag_frame(w, h)
        result.append(([('SERVICE', 'WMS'), ('VERSION', '1.1.1'), ('REQUEST', 'GetMap'), ('LAYERS', qualified),
                        ('STYLES', ''), ('SRS', 'EPSG:4326'), ('BBOX', bbox), ('WIDTH', str(w)),
                        ('HEIGHT', str(h)), ('FORMAT', 'image/png'), ('TRANSPARENT', 'true'),
                        ('SLD_BODY', with_zigzag(map_sld, zigzag))], True))
    result.append((legend, False))
    return result
