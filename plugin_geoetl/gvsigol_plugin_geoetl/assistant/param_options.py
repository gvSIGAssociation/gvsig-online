# -*- coding: utf-8 -*-
"""Opciones para completar un parámetro desde el chat (usabilidad, fase 4: ETL_ASSISTANT_PARAM_PICKER).

Dado un tipo de nodo y un parámetro se decide de dónde salen sus valores y se
leen con los permisos del usuario. Solo los parámetros con una lista cerrada
de valores: una conexión, una opción de la ficha, un fichero, un esquema o una
tabla de entrada, un workspace o un grupo de capas donde publicar. Los ficheros
se eligen en el administrador de archivos (el panel lo abre sin pedir nada
aquí). Lo demás (textos libres, SQL, columnas) se completa en el engranaje del
nodo. La tabla de una salida tampoco, porque puede ser nueva.
"""

import logging

from .graph import is_protected
from .questions import MAX_OPTIONS, _real_options, _text

LOGGER = logging.getLogger('gvsigol')

SOURCE_CONNECTIONS = 'connections'
SOURCE_CHOICES = 'choices'
SOURCE_DATASTORES = 'datastores'
SOURCE_SHEETS = 'sheets'
SOURCE_FILES = 'files'
SOURCE_SCHEMAS = 'schemas'
SOURCE_TABLES = 'tables'

NEEDS_CONNECTION = 'connection'
NEEDS_SCHEMA = 'schema'

# Parámetro de fichero: extensiones que se ofrecen
FILE_EXTENSIONS = {
    'csv-file': 'csv,txt',
    'excel-file': 'xls,xlsx',
    'shp-file': 'shp',
    'kml-kmz-file': 'kml,kmz',
    'json-file': 'json',
    'xml-file': 'xml',
    'raster-file': 'tif,tiff',
}
SCHEMA_PARAMS = ('schema-name', 'owner-name', 'schema-name-option')
TABLE_PARAMS = ('tablename', 'table-name')
PUBLISH_PARAMS = {
    'output_RasterPublish': {'workspace': 'workspaces', 'layer-group': 'layer_groups'},
    'output_LayerPublish': {'datastore': 'publish_datastores', 'layer-group': 'layer_groups'},
}


def picker_enabled():
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_PARAM_PICKER', False))
    except Exception:
        return False


def picker_source(spec, type_name, param):
    """De dónde salen los valores de un parámetro, o None si no se puede elegir de una lista."""
    if not spec or not param:
        return None
    item = next((p for p in spec.get('parameters') or [] if p.get('name') == param), None)
    if item is None or param in (spec.get('sql_parameters') or []):
        return None
    connection_parameter = spec.get('connection_parameter')
    if param == connection_parameter:
        # En una salida a PostGIS se elige un almacén: aporta la conexión y el esquema
        return SOURCE_DATASTORES if type_name == 'output_Postgis' else SOURCE_CONNECTIONS
    if item.get('choices'):
        return SOURCE_CHOICES
    if param in FILE_EXTENSIONS:
        return SOURCE_FILES
    if type_name == 'input_Excel' and param == 'sheet-name':
        return SOURCE_SHEETS
    if param in PUBLISH_PARAMS.get(type_name, {}):
        return PUBLISH_PARAMS[type_name][param]
    if connection_parameter and param in SCHEMA_PARAMS:
        return SOURCE_SCHEMAS
    if connection_parameter and param in TABLE_PARAMS and not (type_name or '').startswith('output_'):
        return SOURCE_TABLES
    return None


def can_pick(catalog, type_name, param, restricted):
    """True si el panel puede ofrecer Elegir: la edición restringida no toca entradas, salidas ni SQL."""
    if restricted and is_protected(type_name):
        return False
    return picker_source(catalog.get(type_name), type_name, param) is not None


def _parameter(parameters, name):
    return _text(parameters.get(name), 200) if isinstance(parameters, dict) else ''


def options_for(catalog, type_name, param, parameters, context):
    """(opciones, qué falta antes de poder listarlas o None)."""
    spec = catalog.get(type_name)
    source = picker_source(spec, type_name, param)
    if source == SOURCE_SHEETS:
        from .columns import read_columns
        read = read_columns(type_name, {'excel-file': _parameter(parameters, 'excel-file')}, context) or {}
        sheets = read.get('sheets') or (read.get('params') or {}).get('get_sheet-name') or []
        return [{'value': sheet, 'label': sheet} for sheet in sheets], None
    question = {'type': type_name, 'param': param}
    if source in (SOURCE_SCHEMAS, SOURCE_TABLES):
        connection = _parameter(parameters, spec.get('connection_parameter'))
        if not connection:
            return [], NEEDS_CONNECTION
        question['connection'] = connection
        if source == SOURCE_TABLES:
            schema = next((value for value in (_parameter(parameters, name) for name in SCHEMA_PARAMS) if value), '')
            if not schema:
                return [], NEEDS_SCHEMA
            question['schema'] = schema
    # Esquemas y tablas salen del mismo listado: sin esquema, los esquemas
    origin = SOURCE_TABLES if source == SOURCE_SCHEMAS else source
    return _real_options(question, origin, catalog, None, None, context)[:MAX_OPTIONS], None
