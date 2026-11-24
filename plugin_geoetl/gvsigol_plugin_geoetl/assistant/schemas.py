# -*- coding: utf-8 -*-
"""Columnas que llegan a cada nodo, calculadas como el editor (static/js/SchemaPropagator.js).

El editor pone la rueda en rojo cuando un parámetro nombra una columna que no le
llega (por ejemplo, filtrar por pop_2008 detrás de una estadística, que solo
devuelve region, _sum, _count…). Aquí se repite ese cálculo para que la revisión
lo detecte antes de aplicar la propuesta, también en cadenas de nodos nuevos que
aún no tienen columnas guardadas.

Si se cambia un manejador en SchemaPropagator.js hay que cambiarlo aquí también.
"""

import re

from .catalog import port_count

_STATS = ['_max', '_min', '_count', '_sum', '_mean', '_median', '_mode', '_desv']

# Todas las entradas renombran la geometría así y no la incluyen en las columnas: hay que exponerla
# con trans_ExposeAttr para usarla en un parámetro.
GEOMETRY_COLUMN = 'wkb_geometry'
_MAX_LISTED = 40


def _cols(inputs):
    """schemaAsColumnList: con varias entradas, la primera."""
    if inputs and isinstance(inputs[0], list):
        return list(inputs[0])
    return list(inputs or [])


def _port(inputs, index):
    if inputs and isinstance(inputs[0], list):
        return inputs[index] if index < len(inputs) else []
    return inputs if index == 0 else []


def _names(value):
    """attrsExistInSchema: lista o texto separado por espacios o comas; '-' es "ninguno"."""
    if value in (None, ''):
        return []
    items = value if isinstance(value, list) else re.split(r'[\s,]+', str(value))
    return [str(item) for item in items if item and item != '-']


def _missing(value, columns):
    return [name for name in _names(value) if name not in columns]


def _fields(*names, port=0):
    """Validación de los parámetros que nombran columnas de una entrada."""
    def check(inputs, params):
        columns = _port(inputs, port) if port else _cols(inputs)
        return [(name, _missing(params.get(name), columns), port) for name in names]
    return check


def _no_check(inputs, params):
    return []


def _same(inputs, params):
    return _cols(inputs)


def _plus(*extra):
    return lambda inputs, params: _cols(inputs) + list(extra)


def _plus_param(key):
    return lambda inputs, params: _cols(inputs) + ([params[key]] if params.get(key) else [])


def _names_from_schema_block(block):
    names = []
    items = block
    if isinstance(block, dict) and 'columns' in block:
        items = block.get('columns') or []
    for item in items or []:
        if isinstance(item, dict):
            name = (item.get('name') or '').strip()
        else:
            name = str(item).strip()
        if name:
            names.append(name)
    return names


def _output_schema_only(inputs, params):
    """Una lista de columnas por salida; si falta, el esquema de la primera entrada."""
    try:
        outs = int(params.get('outputs_count') or 1)
    except (TypeError, ValueError):
        outs = 1
    outs = max(1, outs)
    raw = params.get('output_schemas')
    if raw in (None, ''):
        raw = params.get('output_schema') or []

    per_out = []
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        for block in raw:
            per_out.append(_names_from_schema_block(block))
    elif isinstance(raw, list) and raw and isinstance(raw[0], dict) and 'columns' in raw[0]:
        for block in raw:
            per_out.append(_names_from_schema_block(block))
    else:
        shared = _names_from_schema_block(raw)
        per_out = [list(shared) for _ in range(outs)] if shared else []

    fallback = _cols(inputs)
    while len(per_out) < outs:
        per_out.append([])
    per_out = per_out[:outs]
    for i, names in enumerate(per_out):
        if not names:
            per_out[i] = list(fallback)
    if outs <= 1:
        return per_out[0] if per_out else fallback
    return per_out


def _plus_list(key, fallback=None):
    def compute(inputs, params):
        value = params.get(key)
        if value is None and fallback:
            value = params.get(fallback)
        if isinstance(value, (list, tuple)):
            names = [str(item).strip() for item in value if str(item).strip()]
        elif value:
            names = [part.strip() for part in re.split(r'[,;|]', str(value)) if part.strip()]
        else:
            names = []
        return _cols(inputs) + names
    return compute


def _without(key, add=None):
    def compute(inputs, params):
        columns = _cols(inputs)
        if params.get(key) in columns:
            columns.remove(params[key])
        if add and params.get(add):
            columns.append(params[add])
        return columns
    return compute


def _moved_to_end(inputs, params):
    columns = _cols(inputs)
    if params.get('attr') in columns:
        columns.remove(params['attr'])
        columns.append(params['attr'])
    return columns


def _remove_attr(inputs, params):
    return [c for c in _cols(inputs) if c not in (params.get('attr') if isinstance(params.get('attr'), list)
                                                   else [params.get('attr')])]


def _keep_attr(inputs, params):
    attrs = params.get('attr')
    return list(attrs) if isinstance(attrs, list) else ([attrs] if attrs else [])


def _rename(inputs, params):
    columns = _cols(inputs)
    old = params.get('old-attr')
    new = params.get('new-attr')
    if not old or new is None:
        return columns
    old_list = old if isinstance(old, list) else [old]
    new_list = str(new).split(' ')
    for index, name in enumerate(old_list):
        target = new_list[index] if index < len(new_list) else new_list[0]
        if name in columns and target:
            columns[columns.index(name)] = target
    return columns


def _rename_check(inputs, params):
    if _names(params.get('old-attr')) == []:
        return [('old-attr', ['(vacío)'], 0)]
    return _fields('old-attr')(inputs, params)


def _counter(inputs, params):
    columns = _cols(inputs) + ([params['attr']] if params.get('attr') else [])
    return columns[1:]


def _stats(inputs, params):
    return ([params['group-by-attr']] if params.get('group-by-attr') else []) + list(_STATS)


def _union_two(inputs):
    first, second = _port(inputs, 0), _port(inputs, 1)
    return first + [c for c in second if c not in first]


def _join_check(inputs, params):
    if not (inputs and isinstance(inputs[0], list)):
        return []
    found = []
    for name, port in (('attr1', 0), ('attr2', 1)):
        value = params.get(name)
        if value and value not in _port(inputs, port):
            found.append((name, [value], port))
    for name, port in (('attr-1', 0), ('attr-2', 1)):
        words = [w for w in str(params.get(name) or '').split(' ') if w]
        found.append((name, [w for w in words if w not in _port(inputs, port)], port))
    return found


def _pairs(inputs, params):
    if inputs and isinstance(inputs[0], list):
        return [_union_two(inputs), list(_port(inputs, 0)), list(_port(inputs, 1))]
    return _cols(inputs)


def _nearest_check(inputs, params):
    if inputs and isinstance(inputs[0], list) and params.get('attr') and params['attr'] not in inputs[0]:
        return [('attr', [params['attr']], 0)]
    return []


def _compare_rows(inputs, params):
    if inputs and isinstance(inputs[0], list):
        first = list(_port(inputs, 0))
        return [first, first, first, list(_port(inputs, 1))]
    return _cols(inputs)


def _intersection(inputs, params):
    multi = inputs and isinstance(inputs[0], list)
    if params.get('merge') in ('true', True) and multi:
        return _union_two(inputs)
    return list(_port(inputs, 0)) if multi else _cols(inputs)


def _expose(inputs, params):
    columns = _cols(inputs)
    for name in str(params.get('attrs') or '').split(' '):
        if name and name not in columns:
            columns.append(name)
    return columns


def _cluster(inputs, params):
    return (_cols(inputs) + ['_cluster', '_cluster_rmse', '_distance_to_centroid'])[1:]


def _mgrs(inputs, params):
    extra = ['_lon', '_lat'] if params.get('select') == 'mgrstolatlon' else ['_mgrs_grid']
    return _cols(inputs) + extra


def _mgrs_check(inputs, params):
    if params.get('select') == 'mgrstolatlon':
        return _fields('mgrs')(inputs, params)
    return _fields('lon', 'lat')(inputs, params)


def _geocoder(inputs, params):
    extra = ['_X', '_Y'] if params.get('mode-option') == 'direct' else ['_ADDRESS']
    return _cols(inputs) + extra


def _geocoder_check(inputs, params):
    if params.get('mode-option') == 'direct':
        key = 'attr-selected' if params.get('attr-selected') else 'attr'
        return _fields(key)(inputs, params)
    return _fields('x', 'y')(inputs, params)


def _union(inputs, params):
    group = params.get('group-by-attr')
    if not group or group == '-':
        return _cols(inputs)[1:]
    return [group]


def _first_port(inputs, params):
    return list(_port(inputs, 0)) if inputs and isinstance(inputs[0], list) else _cols(inputs)


def _split_attr(inputs, params):
    columns = _without('attr')(inputs, params)
    if params.get('list'):
        columns.append(params['list'])
    return columns


def _copies(count):
    return lambda inputs, params: [_cols(inputs) for _ in range(count)]


def _sink(inputs, params):
    return _cols(inputs)


# tipo -> (columnas de salida, comprobación). Los tipos que no están se tratan como el editor: pasan las columnas.
HANDLERS = {
    'trans_RemoveAttr': (_remove_attr, _fields('attr')),
    'trans_KeepAttr': (_keep_attr, _fields('attr')),
    'trans_RenameAttr': (_rename, _rename_check),
    'trans_ConcatAttr': (_plus_param('new-attr'), _fields('attr')),
    'trans_AIText': (_plus_list('new-attrs', 'new-attr'), _fields('attr')),
    'trans_AIAction': (_output_schema_only, _no_check),
    'trans_PadAttr': (_moved_to_end, _fields('attr')),
    'trans_FilterDupli': (_copies(2), _fields('attr')),
    'trans_Filter': (_same, _fields('attr')),
    'trans_ModifyValue': (_same, _fields('attr')),
    'trans_Calculator': (_same, _fields('attr')),
    'trans_Reproject': (_same, _no_check),
    'trans_CadastralGeom': (_same, _fields('attr')),
    'trans_ExplodeGeom': (_same, _no_check),
    'trans_Buffer': (_same, _fields('radius-attr', 'current-area-attr', 'area-attr-reach')),
    'trans_RemoveGeom': (_same, _no_check),
    'trans_Counter': (_counter, _fields('group-by-attr')),
    'trans_Stats': (_stats, _fields('attr', 'group-by-attr')),
    'trans_ChangeAttrType': (_moved_to_end, _fields('attr')),
    'trans_CorrectSpelling': (_plus('_corrected'), _fields('attr')),
    'trans_CreateAttr': (_plus_param('attr'), _no_check),
    'trans_Join': (_pairs, _join_check),
    'trans_NearestNeighbor': (_pairs, _nearest_check),
    'trans_CompareRows': (_compare_rows, _fields('attr')),
    'trans_Intersection': (_intersection, _no_check),
    'trans_ValGeom': (lambda inputs, params: [_cols(inputs) + ['_valid'],
                                              _cols(inputs) + ['_valid', '_reason', '_location']], _no_check),
    'trans_SimpGeom': (_copies(2), _no_check),
    'trans_ExposeAttr': (_expose, _no_check),
    'trans_ExecuteSQL': (lambda inputs, params: _cols(inputs), _no_check),
    'trans_Cluster': (_cluster, _fields('attr')),
    'trans_Voronoi': (lambda inputs, params: [], _no_check),
    'trans_MGRS': (_mgrs, _mgrs_check),
    'trans_Geocoder': (_geocoder, _geocoder_check),
    'output_Visualizer': (_sink, _no_check),
    'trans_Difference': (_first_port, _no_check),
    'trans_SpatialRel': (lambda inputs, params: _first_port(inputs, params) + ['_related'], _no_check),
    'trans_TextToPoint': (_plus('_xlon', '_ylat'), _fields('lon', 'lat')),
    'trans_WktGeom': (_without('attr'), _fields('attr')),
    'trans_SplitAttr': (_split_attr, _fields('attr')),
    'trans_ExplodeList': (lambda inputs, params: _without('list', add='attr')(inputs, params), _fields('list')),
    'trans_Union': (_union, _fields('group-by-attr')),
    'trans_FilterGeom': (_copies(6), _no_check),
    'trans_LineEndPoints': (_plus('_xini', '_yini', '_xend', '_yend'), _no_check),
    'trans_CalcLength': (_plus('_length'), _no_check),
    'trans_CalcArea': (_plus_param('attr'), _no_check),
    'trans_CurrentDate': (_plus_param('attr'), _no_check),
    'trans_IDW': (lambda inputs, params: ['id', 'x', 'y', 'interpolated_value'], _fields('value-field')),
    'trans_Kriging': (lambda inputs, params: ['id', 'x', 'y', 'kriging_value', 'kriging_variance'],
                      _fields('value-field')),
    'output_Postgis': (_sink, _no_check),
}


def _is_source(type_name):
    return (type_name or '').startswith(('input_', 'crea_'))


def _usable(inputs):
    if inputs and isinstance(inputs[0], list):
        return any(_usable(port) for port in inputs)
    return any(isinstance(c, str) and c for c in inputs or [])


def _edge_columns(output, port):
    """passSchemaToEdgeConnected: con una lista por salida, la de ese puerto; si no, la misma en todas."""
    if output and isinstance(output[0], list):
        return list(output[port]) if port < len(output) else []
    return list(output or [])


def _order(nodes, edges):
    incoming = {alias: 0 for alias in nodes}
    following = {alias: [] for alias in nodes}
    for edge in edges:
        if edge.get('source') in nodes and edge.get('target') in nodes:
            incoming[edge['target']] += 1
            following[edge['source']].append(edge['target'])
    ready = [alias for alias in nodes if not incoming[alias]]
    ordered = []
    while ready:
        alias = ready.pop(0)
        ordered.append(alias)
        for target in following[alias]:
            incoming[target] -= 1
            if not incoming[target]:
                ready.append(target)
    return ordered                       # con un ciclo faltan nodos: el ciclo ya se avisa aparte


def column_issues(nodes, edges, catalog):
    """[(alias, parámetro, columnas que faltan, puerto, columnas que llegan)] de los nodos que el editor pondría en rojo.

    Solo se revisan los nodos propuestos y los que reciben columnas de uno propuesto
    (lo que el editor vuelve a calcular al aplicar); los demás ya muestran su estado.
    """
    outputs, changed, found = {}, set(), []
    for alias in _order(nodes, edges):
        node = nodes[alias]
        type_name = node.get('type')
        stored = node.get('schema') if isinstance(node.get('schema'), list) else []
        proposed = node.get('status') == 'proposed'
        if _is_source(type_name):
            outputs[alias] = stored
            if proposed:
                changed.add(alias)
            continue
        arriving = [e for e in edges if e.get('target') == alias and e.get('source') in outputs]
        dirty = proposed or any(e['source'] in changed for e in arriving)
        if not dirty and stored:
            outputs[alias] = stored
            continue
        spec = catalog.get(type_name) or {}
        ports = max(port_count(spec, 'input'), 1)
        per_port = []
        for port in range(ports):
            columns = []
            for edge in arriving:
                if edge.get('target_port', 0) == port:
                    for column in _edge_columns(outputs[edge['source']], edge.get('source_port', 0)):
                        if column not in columns:
                            columns.append(column)
            per_port.append(columns)
        inputs = per_port[0] if ports == 1 else per_port
        if not _usable(inputs):
            outputs[alias] = stored            # el editor espera a que lleguen columnas
            continue
        params = node.get('parameters') or {}
        compute, check = HANDLERS.get(type_name, (_same, _no_check))
        try:
            outputs[alias] = compute(inputs, params)
        except Exception:
            outputs[alias] = _cols(inputs)
        if not dirty:
            continue
        changed.add(alias)
        for param, missing, port in check(inputs, params):
            if missing:
                found.append((alias, param, missing, port, _port(inputs, port) if port else _cols(inputs)))
    return found


def listed(columns):
    shown = [str(c) for c in columns[:_MAX_LISTED]]
    return ', '.join(shown) + (', …' if len(columns) > _MAX_LISTED else '')
