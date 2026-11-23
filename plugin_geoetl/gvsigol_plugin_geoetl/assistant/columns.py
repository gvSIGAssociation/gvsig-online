# -*- coding: utf-8 -*-
"""Columnas de las entradas de un flujo (ETL_ASSISTANT_COLUMNS).

Un nodo de entrada solo lee las columnas de su origen al pulsar Aceptar en su
diálogo, así que los nodos que configura el asistente se quedaban sin ellas y
los nodos siguientes (por ejemplo, el cruce) no tenían campos que ofrecer. Aquí
se leen con los mismos lectores del editor, comprobando antes que el usuario
puede acceder al fichero o a la conexión.

No se usa el botón Aceptar del nodo: guardaría también lo que haya en el
formulario, como un EPSG por defecto que el usuario no ha elegido.
"""

import csv
import logging
import os
import re

LOGGER = logging.getLogger('gvsigol')

FILE_PARAMS = {
    'input_Shp': 'shp-file',
    'input_Csv': 'csv-file',
    'input_Excel': 'excel-file',
    'input_Kml': 'kml-kmz-file',
}
# Parámetros (esquema, tabla) de las entradas de base de datos
DATABASE_TABLES = {
    'input_Postgis': ('schema-name', 'tablename'),
    'input_Oracle': ('owner-name', 'table-name'),
    'input_SqlServer': ('schema-name', 'table-name'),
}
READABLE_TYPES = tuple(FILE_PARAMS) + tuple(DATABASE_TABLES)
TYPE_BY_EXTENSION = {
    '.shp': 'input_Shp', '.csv': 'input_Csv', '.txt': 'input_Csv', '.xls': 'input_Excel', '.xlsx': 'input_Excel',
    '.kml': 'input_Kml', '.kmz': 'input_Kml',
}
# Los que admite el nodo CSV
_SEPARATORS = ';,'
READ_ERROR = 'No se han podido leer las columnas.'
NO_ACCESS = 'No tienes acceso a ese fichero.'


def columns_enabled():
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_COLUMNS', False))
    except Exception:
        return False


def file_allowed(path, context):
    """True si la ruta está dentro del gestor de ficheros y el usuario puede verla."""
    from django.conf import settings

    if not isinstance(path, str) or not path:
        return False
    local = path[7:] if path.startswith('file://') else path
    root = os.path.abspath(getattr(settings, 'FILEMANAGER_DIRECTORY', '') or '')
    full = os.path.abspath(local)
    if not root or not full.startswith(root + os.sep):
        return False
    return bool(context.can_browse(os.path.relpath(full, root)))


def _texts(values):
    return [str(value) for value in values]


def _sniff_separator(path, codec):
    with open(path, 'r', encoding=codec, errors='replace') as handle:
        sample = handle.read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=_SEPARATORS).delimiter
    except csv.Error:
        # El Sniffer falla con comillas o filas irregulares: gana el que más aparece en la cabecera
        header = sample.splitlines()[0] if sample else ''
        return max(_SEPARATORS, key=header.count)


def _read_excel(path, params):
    from gvsigol_plugin_geoetl import etl_schema

    sheets = _texts(etl_schema.get_sheets_excel(path, 'single'))
    sheet = params.get('sheet-name') or (sheets[0] if len(sheets) == 1 else '')
    extra = {'get_sheet-name': sheets}
    if not sheet:
        return {'schema': None, 'sheets': sheets, 'params': extra}
    extra.update({'sheet-name': sheet, 'reading': 'single', 'usecols': params.get('usecols') or '',
                  'header': params.get('header') or '0', 'move': params.get('move') or '',
                  'folder': params.get('folder') or ''})
    reading = dict(params, **extra)
    return {'schema': _texts(etl_schema.get_schema_excel(reading)), 'sheets': sheets, 'params': extra}


def _local(path):
    return path[7:] if path.startswith('file://') else path


def _with_corrections(read, corrected, notes):
    if corrected:
        read['corrected'] = corrected
        read['notes'] = notes
    return read


def _pick_encoding(given, detected, corrected, notes):
    """La codificación indicada, salvo si es UTF-8 y el fichero no lo es (la ejecución fallaría)."""
    if not detected:
        return given or 'UTF-8'
    if not given:
        return detected
    if given.upper().replace('-', '') == 'UTF8' and detected != 'UTF-8':
        corrected['encode'] = detected
        notes.append('el fichero no está en UTF-8: uso la codificación %s' % detected)
        return detected
    return given


def _read_shp(path, params):
    from gvsigol_plugin_geoetl import etl_schema

    corrected, notes = {}, []
    encode = _pick_encoding(params.get('encode'), etl_schema.detect_shp_encoding(_local(path)), corrected, notes)
    # EPSG vacío: la ejecución lo toma del propio shapefile
    extra = {'epsg': params.get('epsg') or '', 'encode': encode}
    read = {'schema': ['ogc_fid'] + _texts(etl_schema.get_schema_shape(path)), 'params': extra}
    return _with_corrections(read, corrected, notes)


def _missing_file(type_name, path, context):
    """Error de un fichero que no existe, con los del usuario que se llaman parecido."""
    from . import tools
    from .param_options import FILE_EXTENSIONS

    listed = tools._list_files(context, '', FILE_EXTENSIONS.get(FILE_PARAMS[type_name], ''))
    by_name = {}
    for item in listed.get('files') or []:
        by_name.setdefault(os.path.basename(item['path']), item['value'])
    similar = tools._similar(os.path.basename(_local(path)), list(by_name))
    return {'schema': None, 'params': {}, 'error': 'El fichero %s no existe.' % os.path.basename(_local(path)),
            'similar_files': [by_name[name] for name in similar]}


def _read_csv(path, params):
    """Lee la cabecera con el separador y la codificación del fichero.

    El modelo no ve el fichero, así que un separador o una codificación que no
    encajan con él se corrigen (en 'corrected', con su nota) en lugar de dejar
    que el nodo falle al ejecutarse.
    """
    from gvsigol_plugin_geoetl import etl_schema

    local_path = _local(path)
    corrected, notes = {}, []
    encode = _pick_encoding(params.get('encode'), etl_schema.detect_csv_encoding(local_path), corrected, notes)
    detected_separator = _sniff_separator(local_path, encode)
    extra = {'separator': params.get('separator') or detected_separator,
             'encode': encode,
             'header': params.get('header') or '0',
             'schema-option': params.get('schema-option') or 'has-schema',
             'reading': 'single'}
    local = dict(params, **extra)
    local['csv-file'] = local_path
    schema = _texts(etl_schema.get_schema_csv(local))
    if len(schema) <= 1 and extra['separator'] != detected_separator:
        retry = _texts(etl_schema.get_schema_csv(dict(local, separator=detected_separator)))
        if len(retry) > 1:
            notes.append("con el separador '%s' sale una sola columna: uso '%s', el del fichero"
                         % (extra['separator'], detected_separator))
            extra['separator'] = corrected['separator'] = detected_separator
            schema = retry
    return _with_corrections({'schema': schema, 'params': extra}, corrected, notes)


def _read_database(type_name, params, context):
    from . import tools
    from .questions import _name

    if str(params.get('checkbox')).lower() == 'true':
        return None                       # consulta SQL libre: no hay una tabla que leer
    schema_key, table_key = DATABASE_TABLES[type_name]
    name, schema, table = params.get('db'), params.get(schema_key), params.get(table_key)
    found = context.find_connection(name) if name else None
    if not found or not schema or not table or tools._bad_ident(schema) or tools._bad_ident(table):
        return None
    # La ejecución consulta checkbox siempre: sin él, el nodo falla
    extra = {'checkbox': params.get('checkbox') or 'false'}
    schema_columns = [c for c in (_name(item) for item in tools._columns(found, name, schema, table)) if c]
    if not schema_columns:
        missing = tools._not_found(found, name, schema, table, context.connections)
        if missing:
            missing.pop('hint', None)
            return dict(missing, schema=None, params=extra)
    return {'schema': schema_columns, 'params': extra}


def read_columns(type_name, params, context):
    """{'schema': [...] o None, 'params': {...}, 'sheets'?, 'error'?}, o None si aún no se puede leer."""
    from gvsigol_plugin_geoetl import etl_schema

    params = params if isinstance(params, dict) else {}
    if type_name not in READABLE_TYPES or params.get('reading') == 'multiple':
        return None
    try:
        if type_name in DATABASE_TABLES:
            return _read_database(type_name, params, context)
        path = params.get(FILE_PARAMS[type_name])
        if not path:
            return None
        if not file_allowed(path, context):
            return {'schema': None, 'params': {}, 'error': NO_ACCESS}
        if not os.path.exists(_local(path)):
            return _missing_file(type_name, path, context)
        if type_name == 'input_Shp':
            return _read_shp(path, params)
        if type_name == 'input_Kml':
            return {'schema': _texts(etl_schema.get_schema_kml(path)), 'params': {}}
        if type_name == 'input_Excel':
            return _read_excel(path, params)
        return _read_csv(path, params)
    except Exception:
        LOGGER.exception('etl_assistant: no se pudieron leer las columnas de un nodo %s', type_name)
        return {'schema': None, 'params': {}, 'error': READ_ERROR}


def read_file(path, sheet, context):
    """Columnas de un fichero por su extensión (herramienta get_file_columns y ask_user)."""
    if not isinstance(path, str):
        return {'schema': None, 'params': {}, 'error': READ_ERROR}
    type_name = TYPE_BY_EXTENSION.get(os.path.splitext(path)[1].lower())
    if not type_name:
        return {'schema': None, 'params': {}, 'error': 'Ese tipo de fichero no se puede leer.'}
    params = {FILE_PARAMS[type_name]: path}
    if sheet:
        params['sheet-name'] = sheet
    return read_columns(type_name, params, context)


# Desplegables que se llenan con un botón: la lista se guarda con el nodo, y sin ella el valor
# no se vería al reabrir el diálogo
OPTION_LISTS = {
    'output_Postgis': {'schema-name-option': 'get_schema-name-option', 'tablename': 'get_tablename'},
    'input_Postgis': {'schema-name': 'get_schema-name', 'tablename': 'get_tablename'},
    'input_SqlServer': {'schema-name': 'get_schema-name', 'table-name': 'get_table-name'},
}


def _canvas_type(alias, canvas):
    for node in (canvas or {}).get('nodes') or []:
        if isinstance(node, dict) and alias in (node.get('alias'), node.get('id')):
            return node.get('type')
    return None


def _normalize_parameters(params, spec, new_node):
    for item in spec.get('parameters') or []:
        name, kind = item.get('name'), item.get('format')
        if new_node and name not in params and 'default' in item:
            params[name] = item['default']
        value = params.get(name)
        if kind == 'list' and isinstance(value, str):
            params[name] = [part for part in re.split(r'[,\s]+', value) if part]
        elif kind == 'spaced' and isinstance(value, list):
            params[name] = ' '.join(str(part) for part in value)
    for name, list_name in OPTION_LISTS.get(spec.get('type'), {}).items():
        if isinstance(params.get(name), str) and params[name] and not params.get(list_name):
            params[list_name] = [params[name]]
    if spec.get('type') == 'trans_Join':
        # El cruce se ejecuta con attr-1 y attr-2: si el modelo solo manda attr1 y attr2, se copian
        for short, full in (('attr1', 'attr-1'), ('attr2', 'attr-2')):
            if params.get(short) and not params.get(full):
                params[full] = params[short]


def normalize_proposal(payload, catalog, canvas=None):
    """Deja los parámetros como los espera la ejecución: listas, valores por defecto y el cruce."""
    if not isinstance(payload, dict):
        return payload
    entries = [(node, node.get('type'), True) for node in payload.get('nodes') or [] if isinstance(node, dict)]
    for op in payload.get('ops') or []:
        if not isinstance(op, dict):
            continue
        if isinstance(op.get('node'), dict):
            entries.append((op['node'], op['node'].get('type'), True))
        elif op.get('op') == 'update_node':
            entries.append((op, _canvas_type(op.get('id') or op.get('alias'), canvas), False))
    for holder, type_name, new_node in entries:
        spec = catalog.get(type_name)
        if not spec:
            continue
        if new_node and not isinstance(holder.get('parameters'), dict):
            holder['parameters'] = {}
        if isinstance(holder.get('parameters'), dict):
            _normalize_parameters(holder['parameters'], spec, new_node)
    return payload


def _proposal_nodes(proposal):
    for node in proposal.get('nodes') or []:
        yield node.get('alias'), node
    for op in proposal.get('ops') or []:
        if op.get('op') == 'add_node' and op.get('node'):
            yield op['node'].get('alias'), op['node']
        elif op.get('op') == 'update_node':
            yield op.get('alias'), op


def enrich_proposal(result, context):
    """Lee las columnas de las entradas de una propuesta validada. Devuelve {alias: columnas}."""
    proposal = result.get('proposal') or {}
    found = {}
    for alias, node in _proposal_nodes(proposal):
        type_name = node.get('type')
        if type_name not in READABLE_TYPES or node.get('schema'):
            continue
        read = read_columns(type_name, node.get('parameters'), context)
        if not read:
            continue
        for key, value in (read.get('params') or {}).items():
            if not node['parameters'].get(key):
                node['parameters'][key] = value
        node['parameters'].update(read.get('corrected') or {})
        for note in read.get('notes') or []:
            result.setdefault('warnings', []).append('%s: %s' % (alias, note))
        if read.get('schema'):
            node['schema'] = read['schema']
            found[alias] = read['schema']
        elif read.get('error'):
            result.setdefault('warnings', []).append('%s: %s%s' % (alias, read['error'], _similar_text(read)))
    return found


SIMILAR_KEYS = ('similar_files', 'similar_schemas', 'similar_tables', 'similar_connections')


def _similar_text(read):
    """' Parecidos: a, b. Pregunta al usuario si se refiere a alguno.' si la lectura trae nombres parecidos.

    Las suggestions (esquema.tabla comprobados) van antes que los esquemas sueltos.
    """
    similar = read.get('suggestions') or [name for key in SIMILAR_KEYS for name in read.get(key) or []]
    if not similar:
        return ''
    return ' Parecidos: %s. Pregunta al usuario si se refiere a alguno.' % ', '.join(similar)
