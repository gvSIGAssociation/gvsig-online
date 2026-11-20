# -*- coding: utf-8 -*-
"""Preguntas con opciones (usabilidad, fase 2: ETL_ASSISTANT_QUESTIONS).

El modelo pide un dato con la herramienta ask_user y dice de dónde salen las
opciones. Aquí se generan o se validan contra los datos reales del usuario,
con sus permisos: el modelo no puede ofrecer una conexión, tabla, columna o
fichero que no exista. Si una pregunta se queda sin opciones, pasa a ser de
respuesta libre. El panel siempre permite además escribir otra respuesta.

Formato de cada pregunta que llega al panel:
    {id, label, text, node, param, multiple, source, options: [{value, label}], file_picker?, create_datastore?, empty?}

Para el destino de una tabla PostGIS se ofrecen almacenes (datastores), que el
usuario conoce, en lugar de conexiones: un almacén aporta la conexión y el
esquema del nodo de salida.

Los ficheros no se listan: file_picker ({extensions}) hace que el panel abra el
administrador de archivos, como los nodos, con los permisos y la subida de
ficheros que ya tiene.

El modelo no siempre indica bien el origen, así que se corrige aquí: se aceptan
sinónimos y, si no hay origen útil, se deduce del parámetro o del texto de la
pregunta ("¿Qué shapefile...?", "¿En qué conexión...?"). `empty` dice que el
origen era correcto pero no hay nada que ofrecer (por ejemplo, ninguna conexión
disponible), para que el panel se lo explique al usuario.
"""

import logging
import re
import unicodedata

LOGGER = logging.getLogger('gvsigol')

MAX_QUESTIONS = 4
MAX_OPTIONS = 200
MAX_CUSTOM_OPTIONS = 8
MAX_TEXT = 300
MAX_LABEL = 60
MAX_OPTION_TEXT = 120

SOURCES = ('choices', 'connections', 'datastores', 'publish_datastores', 'tables', 'columns', 'files', 'workspaces', 'layer_groups', 'custom')


SOURCE_ALIASES = {
    'choice': 'choices', 'option': 'choices', 'options': 'choices',
    'connection': 'connections', 'conexion': 'connections', 'conexiones': 'connections',
    'datastore': 'datastores', 'almacen': 'datastores', 'almacenes': 'datastores',
    'table': 'tables', 'tabla': 'tables', 'tablas': 'tables',
    'column': 'columns', 'columna': 'columns', 'columnas': 'columns', 'field': 'columns', 'fields': 'columns',
    'file': 'files', 'fichero': 'files', 'ficheros': 'files', 'archivo': 'files', 'archivos': 'files',
    'workspace': 'workspaces', 'layer_group': 'layer_groups', 'layergroup': 'layer_groups',
    'layergroups': 'layer_groups', 'layer-group': 'layer_groups',
}

_CONNECTION_WORDS = re.compile(r'\b(conexion(es)?|connexio(ns)?|connections?)\b')
_POSTGIS_WORDS = re.compile(r'\b(postgis|postgres(ql)?)\b')
_DATASTORE_WORDS = re.compile(r'\b(datastores?|almacen(es)?( de datos)?)\b')
_DESTINATION_WORDS = re.compile(r'\b(destino|desti|destination|crear?|creo|create|guardar?|guardo|save|escribir|escribo|write|publicar?)\b')
_OTHER_DATABASE_WORDS = re.compile(r'\b(oracle|sql ?server)\b')
_WORKSPACE_WORDS = re.compile(r'\b(workspaces?|espacios? de trabajo)\b')
_LAYER_GROUP_WORDS = re.compile(r'\b(grupos? de capas|layer groups?)\b')
_FILE_WORDS = re.compile(r'\b(ficheros?|archivos?|arxius?|files?)\b')
_FILE_KINDS = (
    (re.compile(r'\b(shapefiles?|shp)\b'), 'shp'),
    (re.compile(r'\b(excel|xlsx?)\b'), 'xls,xlsx'),
    (re.compile(r'\bcsv\b'), 'csv,txt'),
    (re.compile(r'\b(kml|kmz)\b'), 'kml,kmz'),
    (re.compile(r'\bjson\b'), 'json'),
    (re.compile(r'\bxml\b'), 'xml'),
    (re.compile(r'\b(raster|geotiff|tiff?)\b'), 'tif,tiff'),
)


def _plain(text):
    """Minúsculas y sin acentos, para buscar palabras."""
    decomposed = unicodedata.normalize('NFKD', text or '')
    return ''.join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _file_extensions(words):
    for pattern, extensions in _FILE_KINDS:
        if pattern.search(words):
            return extensions
    return ''


def _extensions(raw):
    """Extensiones como texto "csv,txt", venga como venga ("*.shp", [".csv", "txt"])."""
    if isinstance(raw, (list, tuple)):
        raw = ','.join(item for item in raw if isinstance(item, str))
    if not isinstance(raw, str):
        return ''
    parts = [part.strip().lstrip('*').lstrip('.') for part in raw.split(',')]
    return ','.join(part for part in parts if part)[:100]


def _inferred_from_parameter(question, catalog, canvas, proposal):
    """(origen, datos) si la pregunta es sobre un parámetro con valores conocidos."""
    from .param_options import FILE_EXTENSIONS, picker_source

    type_name = question.get('type') or _node_type(question.get('node'), canvas, proposal)
    param = question.get('param')
    source = picker_source(catalog.get(type_name), type_name, param) if type_name and param else None
    if source == 'files':
        return 'files', {'extensions': FILE_EXTENSIONS[param]}
    if source in ('connections', 'datastores', 'publish_datastores', 'choices', 'workspaces', 'layer_groups'):
        return source, {'type': type_name}
    return None


def _inferred_from_words(label, text):
    """(origen, datos) deducidos de la pregunta, o None."""
    words = _plain(label + ' ' + text)
    if _DATASTORE_WORDS.search(words):
        return 'datastores', {}
    if _CONNECTION_WORDS.search(words):
        return 'connections', ({'type': 'output_Postgis'} if _POSTGIS_WORDS.search(words) else {})
    if _LAYER_GROUP_WORDS.search(words):
        return 'layer_groups', {}
    if _WORKSPACE_WORDS.search(words):
        return 'workspaces', {}
    extensions = _file_extensions(words)
    if extensions:
        return 'files', {'extensions': extensions}
    if _FILE_WORDS.search(words):
        return 'files', {}
    return None


def _is_destination(question, label, text, canvas, proposal):
    """True si se pregunta por una conexión donde escribir una tabla PostGIS."""
    type_name = question.get('type') or _node_type(question.get('node'), canvas, proposal)
    if type_name:
        return type_name == 'output_Postgis'
    words = _plain(label + ' ' + text)
    return bool(_DESTINATION_WORDS.search(words)) and not _OTHER_DATABASE_WORDS.search(words)


def datastore_options(datastores):
    """Opciones de almacén: value es para el modelo; params, los parámetros del nodo de salida."""
    seen = set()
    options = []
    for item in datastores:
        value = 'connection=%s; schema=%s' % (item.get('connection'), item.get('schema'))
        if value in seen:
            continue
        seen.add(value)
        name = item.get('description') or item.get('name')
        options.append({'value': value, 'label': ('%s · %s' % (name, item.get('workspace')))[:MAX_OPTION_TEXT],
                        'params': {'db-option': item.get('connection'),
                                   'schema-name-option': item.get('schema')}})
    return options


def publish_datastore_options(datastores):
    """Almacenes para el nodo Publicar capa: se guardan como workspace/nombre."""
    return [{'value': '%s/%s' % (item.get('workspace'), item.get('name')),
             'label': ('%s · %s' % (item.get('description') or item.get('name'), item.get('workspace')))[:MAX_OPTION_TEXT]}
            for item in datastores]


def _text(value, limit):
    return value.strip()[:limit] if isinstance(value, str) else ''


def _node_type(alias, canvas, proposal):
    """Tipo de un nodo del canvas o de la propuesta registrada en este turno."""
    for node in (canvas or {}).get('nodes') or []:
        if isinstance(node, dict) and node.get('alias') == alias:
            return node.get('type')
    proposal = proposal or {}
    for node in proposal.get('nodes') or []:
        if isinstance(node, dict) and (node.get('alias') or node.get('id')) == alias:
            return node.get('type')
    for op in proposal.get('ops') or []:
        node = op.get('node') if isinstance(op, dict) else None
        if isinstance(node, dict) and (node.get('alias') or node.get('id')) == alias:
            return node.get('type')
    return None


def _name(item):
    """Nombre de una tabla o columna: texto, [nombre, tipo] o {'name'}."""
    if isinstance(item, str):
        return item
    if isinstance(item, (list, tuple)) and item and isinstance(item[0], str):
        return item[0]
    if isinstance(item, dict):
        for key in ('name', 'column_name', 'table_name'):
            if isinstance(item.get(key), str):
                return item[key]
    return None


def _options(values):
    """[{value, label}] sin repetidos, a partir de textos o de pares (value, label)."""
    seen = set()
    options = []
    for item in values:
        if isinstance(item, tuple):
            value, label = item
        else:
            value = label = item
        if not isinstance(value, str) or not value or value in seen:
            continue
        seen.add(value)
        options.append({'value': value, 'label': str(label)[:MAX_OPTION_TEXT]})
    return options


def _real_options(question, source, catalog, canvas, proposal, context):
    """Opciones reales de una pregunta según su origen. Lanza si no se pueden leer."""
    from . import tools

    if source == 'choices':
        type_name = question.get('type') or _node_type(question.get('node'), canvas, proposal)
        spec = catalog.get(type_name) or {}
        for item in spec.get('parameters') or []:
            if item.get('name') == question.get('param'):
                return _options([str(c) for c in item.get('choices') or []])
        return []
    if source == 'connections':
        type_name = question.get('type') or _node_type(question.get('node'), canvas, proposal)
        allowed = (catalog.get(type_name) or {}).get('connection_types') or []
        return _options([c.get('name') for c in context.connections
                         if not allowed or c.get('type') in allowed])
    if source == 'columns' and question.get('file'):
        from .columns import read_file
        read = read_file(question.get('file'), _text(question.get('sheet'), 200), context) or {}
        return _options(read.get('schema') or [])
    if source == 'columns' and question.get('node') and not question.get('connection'):
        for node in (canvas or {}).get('nodes') or []:
            if isinstance(node, dict) and node.get('alias') == question.get('node'):
                return _options([_name(item) for item in node.get('schema') or []])
        return []
    if source in ('tables', 'columns'):
        name = _text(question.get('connection'), 200)
        found = context.find_connection(name)
        if not found:
            return []
        schema = _text(question.get('schema'), 200)
        if schema and tools._bad_ident(schema):
            return []
        if source == 'tables':
            return _options([_name(item) for item in tools._list_level(found, name, schema)])
        table = _text(question.get('table'), 200)
        if not schema or not table or tools._bad_ident(table):
            return []
        return _options([_name(item) for item in tools._columns(found, name, schema, table)])
    if source == 'datastores':
        return datastore_options(context.datastores())
    if source == 'publish_datastores':
        return publish_datastore_options(context.datastores())
    if source == 'workspaces':
        return _options([item.get('name') for item in context.publish_targets().get('workspaces') or []])
    if source == 'layer_groups':
        return _options([(item.get('name'), item.get('title') or item.get('name'))
                         for item in context.publish_targets().get('layer_groups') or []])
    return []


def _custom_options(raw):
    values = []
    for item in raw or []:
        if isinstance(item, dict):
            item = item.get('label') or item.get('value')
        text = _text(item, MAX_OPTION_TEXT)
        if text:
            values.append(text)
    return _options(values)[:MAX_CUSTOM_OPTIONS]


def _wanted(raw):
    """Valores que el modelo propone para una pregunta con opciones reales."""
    wanted = []
    for item in raw or []:
        if isinstance(item, dict):
            item = item.get('value') or item.get('label')
        if isinstance(item, str) and item.strip():
            wanted.append(item.strip())
    return wanted


def resolve_questions(raw, catalog, canvas, context, proposal=None):
    """Valida las preguntas del modelo. Devuelve (preguntas, avisos para el modelo)."""
    notes = []
    if not isinstance(raw, list):
        return [], ['questions tiene que ser una lista.']
    if len(raw) > MAX_QUESTIONS:
        notes.append('Solo se hacen las %d primeras preguntas.' % MAX_QUESTIONS)
    questions = []
    for index, question in enumerate(raw[:MAX_QUESTIONS]):
        if not isinstance(question, dict):
            notes.append('La pregunta %d no tiene un formato válido.' % (index + 1))
            continue
        text = _text(question.get('text'), MAX_TEXT)
        if not text:
            notes.append('La pregunta %d no tiene texto.' % (index + 1))
            continue
        label = _text(question.get('label'), MAX_LABEL) or text[:MAX_LABEL]
        question = dict(question)
        original = dict(question)
        source = _plain(_text(question.get('source'), 30))
        source = SOURCE_ALIASES.get(source, source)
        if source not in SOURCES or (source == 'custom' and not _custom_options(question.get('options'))):
            found = _inferred_from_parameter(question, catalog, canvas, proposal) or _inferred_from_words(label, text)
            if found:
                source = found[0]
                question.update(found[1])
                question.pop('options', None)      # lo que escribió el modelo no sirve de filtro
            else:
                source = 'custom'
        if source == 'connections' and _is_destination(original, label, text, canvas, proposal):
            source = 'datastores'
        if source == 'datastores':
            question.pop('options', None)          # el modelo no conoce los almacenes del usuario
        picker = None
        if source == 'files':
            # Se elige en el administrador de archivos: aquí no se lista nada
            picker = {'extensions': _extensions(question.get('extensions'))
                      or _file_extensions(_plain(label + ' ' + text))}
            options = []
        elif source == 'custom':
            options = _custom_options(question.get('options'))
        else:
            try:
                real = _real_options(question, source, catalog, canvas, proposal, context)
            except Exception:
                LOGGER.exception('etl_assistant: no se pudieron leer las opciones de una pregunta (%s)', source)
                real = []
                notes.append('"%s": no se han podido leer las opciones; queda como respuesta libre.' % label)
            wanted = _wanted(question.get('options'))
            if wanted:
                by_value = {o['value']: o for o in real}
                by_label = {o['label']: o for o in real}
                kept = [by_value.get(w) or by_label.get(w) for w in wanted]
                dropped = [w for w, o in zip(wanted, kept) if o is None]
                if dropped:
                    notes.append('"%s": se descartan opciones que no existen: %s.' % (label, ', '.join(dropped[:5])))
                options = _options([(o['value'], o['label']) for o in kept if o]) or real
            else:
                options = real
            options = options[:MAX_OPTIONS]
            if not options and not any(label in n for n in notes):
                notes.append('"%s": no hay opciones de %s; queda como respuesta libre.' % (label, source))
        questions.append({
            'id': 'q%d' % (len(questions) + 1),
            'label': label,
            'text': text,
            'node': _text(question.get('node'), 20) or None,
            'param': _text(question.get('param'), 100) or None,
            'multiple': bool(question.get('multiple')),
            'source': source,
            'options': options,
        })
        if picker:
            questions[-1]['file_picker'] = picker
        elif not options and source in ('connections', 'datastores', 'workspaces', 'layer_groups'):
            questions[-1]['empty'] = source
        if source == 'datastores':
            questions[-1]['create_datastore'] = True
    return questions, notes
