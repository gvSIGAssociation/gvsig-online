# -*- coding: utf-8 -*-
"""Valida la propuesta del modelo antes de devolverla al canvas."""

import re

from .catalog import port_count

_ALIAS_RE = re.compile(r'\bn\d+\b')
_MAX_NODES = 40
_SQL_WARNING = 'Revisa el SQL de %s antes de guardar o ejecutar: lo ha escrito el asistente.'


def needs_confirmation(mode, canvas_occupied, ops=None):
    """Replace con el canvas ocupado, o un patch que borra nodos o aristas."""
    if mode == 'replace':
        return bool(canvas_occupied)
    for op in ops or []:
        if op.get('op') in ('remove_node', 'remove_edge'):
            return True
    return False


def is_protected(type_name):
    name = type_name or ''
    return (
        name.startswith('input_')
        or name.startswith('output_')
        or name == 'trans_ExecuteSQL'
    )


def validate_proposal(payload, catalog, connections, canvas=None, restricted=False):
    """Devuelve reply vacío, warnings, assumptions, summary, needs_confirmation y proposal.

    ``connections`` es una lista de ``{'name', 'type'}``. ``canvas`` es el
    resumen que envió el cliente, con alias ``n1`` y el id real de draw2d.
    """
    canvas = canvas or {}
    connections = connections or []
    warnings = []
    if not isinstance(payload, dict):
        return _result(warnings=['La propuesta no tiene un formato válido.'])

    mode = payload.get('mode')
    if mode not in ('replace', 'patch'):
        return _result(warnings=['La propuesta tiene que ser replace o patch.'])

    canvas_nodes = _canvas_index(canvas)
    occupied = bool(canvas_nodes)
    removed = set()

    if mode == 'replace':
        if restricted:
            warnings.append('En edición restringida no se puede sustituir el flujo.')
            return _result(warnings=warnings)
        nodes, edges = _clean_graph(
            payload.get('nodes'),
            payload.get('edges'),
            catalog,
            connections,
            warnings,
            removed,
        )
        if not nodes:
            if not warnings:
                warnings.append('La propuesta no contiene ninguna tarea válida.')
            return _result(warnings=warnings, assumptions=_filter_assumptions(payload, removed))
        layout_nodes(nodes, edges)
        _attach_counts(nodes, catalog)
        proposal = {
            'mode': 'replace',
            'name': _clip(payload.get('name'), 250),
            'description': _clip(payload.get('description'), 500),
            'nodes': nodes,
            'edges': edges,
        }
        summary = summarize_replace(nodes, edges)
        return _result(
            warnings=warnings,
            assumptions=_filter_assumptions(payload, removed),
            summary=summary,
            needs_confirmation=needs_confirmation('replace', occupied),
            proposal=proposal,
        )

    ops, removed = _clean_patch(
        payload.get('ops'),
        catalog,
        connections,
        canvas_nodes,
        restricted,
        warnings,
    )
    if not ops:
        return _result(
            warnings=warnings,
            assumptions=_filter_assumptions(payload, removed),
        )
    _layout_patch(ops, canvas_nodes)
    proposal = {
        'mode': 'patch',
        'name': _clip(payload.get('name'), 250),
        'description': _clip(payload.get('description'), 500),
        'ops': ops,
    }
    return _result(
        warnings=warnings,
        assumptions=_filter_assumptions(payload, removed),
        summary=summarize_patch(ops, canvas_nodes),
        needs_confirmation=needs_confirmation('patch', occupied, ops),
        proposal=proposal,
    )


def summarize_replace(nodes, edges):
    if not nodes:
        return []
    names = [_node_ref(node) for node in nodes]
    if len(nodes) == 1:
        lines = ['Creo un flujo con %s.' % names[0]]
    else:
        lines = ['Creo un flujo con %d tareas: %s.' % (len(nodes), ', '.join(names))]
    for edge in edges or []:
        lines.append('Conecto %s con %s.' % (
            _id_ref(edge.get('source'), nodes),
            _id_ref(edge.get('target'), nodes),
        ))
    return lines


def summarize_patch(ops, canvas_nodes):
    labels = dict(canvas_nodes)
    lines = []
    added = {}
    covered = _edges_inside_inserts(ops)
    for op in ops:
        kind = op.get('op')
        if kind == 'add_node':
            node = op.get('node') or {}
            added[node.get('id')] = node
            between = _between(node.get('id'), ops)
            if between:
                lines.append('Añado %s entre %s y %s.' % (
                    _node_ref(node),
                    _ref(between[0], labels, added),
                    _ref(between[1], labels, added),
                ))
            else:
                lines.append('Añado %s.' % _node_ref(node))
        elif kind == 'update_node':
            lines.append('Actualizo %s.' % _ref(op.get('id'), labels, added, op.get('alias')))
        elif kind == 'remove_node':
            lines.append('Elimino %s.' % _ref(op.get('id'), labels, added, op.get('alias')))
        elif kind == 'add_edge':
            if id(op) in covered:
                continue
            lines.append('Conecto %s con %s.' % (
                _ref(op.get('source'), labels, added),
                _ref(op.get('target'), labels, added),
            ))
        elif kind == 'remove_edge':
            lines.append('Quito la conexión entre %s y %s.' % (
                _ref(op.get('source'), labels, added),
                _ref(op.get('target'), labels, added),
            ))
    return lines


def layout_nodes(nodes, edges):
    """Asigna x e y por profundidad topológica. Los ciclos se quedan en la columna 0."""
    ids = [node['id'] for node in nodes]
    incoming = {node_id: [] for node_id in ids}
    for edge in edges or []:
        source = edge.get('source')
        target = edge.get('target')
        if target in incoming and source in incoming:
            incoming[target].append(source)
    depth = {}

    def walk(node_id, stack):
        if node_id in depth:
            return depth[node_id]
        if node_id in stack:
            depth[node_id] = 0
            return 0
        stack.add(node_id)
        sources = incoming.get(node_id) or []
        depth[node_id] = 0 if not sources else 1 + max(walk(item, stack) for item in sources)
        stack.remove(node_id)
        return depth[node_id]

    for node_id in ids:
        walk(node_id, set())
    buckets = {}
    for node in nodes:
        buckets.setdefault(depth.get(node['id'], 0), []).append(node)
    for column, group in buckets.items():
        for row, node in enumerate(group):
            node['x'] = 80 + column * 280
            node['y'] = 60 + row * 160


def _layout_patch(ops, canvas_nodes):
    fresh = []
    edges = []
    for op in ops:
        if op.get('op') == 'add_node':
            fresh.append(op['node'])
        elif op.get('op') == 'add_edge':
            edges.append(op)
    if not fresh:
        return
    known = set(canvas_nodes)
    only_new = []
    for edge in edges:
        if edge.get('source') in known or edge.get('target') in known:
            continue
        only_new.append({'source': edge.get('source'), 'target': edge.get('target')})
    layout_nodes(fresh, only_new)


def _clean_graph(raw_nodes, raw_edges, catalog, connections, warnings, removed):
    nodes = []
    seen = set()
    for raw in raw_nodes or []:
        if len(nodes) >= _MAX_NODES:
            warnings.append('Se han omitido tareas a partir de la %d.' % _MAX_NODES)
            break
        node = _clean_node(raw, catalog, connections, warnings, removed)
        if not node:
            continue
        if node['id'] in seen:
            warnings.append('Hay dos tareas con el id %s; me quedo con la primera.' % node['alias'])
            continue
        seen.add(node['id'])
        nodes.append(node)
    edges = _clean_edges(raw_edges, {node['id']: node for node in nodes}, catalog, warnings)
    return nodes, edges


def _clean_patch(raw_ops, catalog, connections, canvas_nodes, restricted, warnings):
    removed = set()
    ops = []
    added = {}
    if not isinstance(raw_ops, list):
        warnings.append('El patch no trae una lista de operaciones.')
        return [], removed
    for raw in raw_ops:
        if not isinstance(raw, dict):
            continue
        kind = raw.get('op')
        if kind == 'add_node':
            if len(added) >= _MAX_NODES:
                continue
            node = _clean_node(raw.get('node') or raw, catalog, connections, warnings, removed)
            if not node:
                continue
            if restricted and is_protected(node['type']):
                warnings.append('En edición restringida no se añade %s.' % node['type'])
                removed.add(node['alias'])
                continue
            if node['alias'] in canvas_nodes or node['id'] in canvas_nodes:
                warnings.append('%s ya está en el canvas; no lo vuelvo a crear.' % node['alias'])
                continue
            _attach_counts([node], catalog)
            added[node['id']] = node
            ops.append({'op': 'add_node', 'node': node})
        elif kind == 'update_node':
            op = _clean_update(raw, catalog, connections, canvas_nodes, restricted, warnings, removed)
            if op:
                ops.append(op)
        elif kind == 'remove_node':
            op = _clean_remove_node(raw, canvas_nodes, restricted, warnings, removed)
            if op:
                ops.append(op)
        elif kind in ('add_edge', 'remove_edge'):
            op = _clean_edge_op(kind, raw, catalog, canvas_nodes, added, restricted, warnings)
            if op:
                ops.append(op)
        else:
            warnings.append('Operación no reconocida: %s.' % kind)
    return ops, removed


def _clean_node(raw, catalog, connections, warnings, removed):
    if not isinstance(raw, dict):
        return None
    alias = _text_id(raw.get('id') or raw.get('alias'))
    type_name = raw.get('type')
    if not alias or not type_name:
        warnings.append('Hay una tarea sin id o sin tipo.')
        return None
    spec = catalog.get(type_name)
    if not spec:
        warnings.append('No propongo %s: no está en el catálogo.' % type_name)
        removed.add(alias)
        return None
    params = _parameters(raw.get('parameters'))
    params, param_warnings = _filter_parameters(alias, spec, params, connections)
    warnings.extend(param_warnings)
    _warn_sql(alias, spec, params, warnings)
    _warn_required(alias, spec, params, warnings)
    return {
        'id': alias,
        'alias': alias,
        'type': type_name,
        'label': _clip(raw.get('label') or spec.get('label') or type_name, 80),
        'parameters': params,
        'schema': raw.get('schema') if isinstance(raw.get('schema'), list) else [],
        'schemaold': _schemaold(raw),
    }


def _clean_update(raw, catalog, connections, canvas_nodes, restricted, warnings, removed):
    alias = _text_id(raw.get('id') or raw.get('alias'))
    current = canvas_nodes.get(alias) if alias else None
    if not current:
        warnings.append('No actualizo %s porque no está en el canvas.' % (alias or '?'))
        if alias:
            removed.add(alias)
        return None
    type_name = current.get('type')
    if restricted and is_protected(type_name):
        warnings.append('En edición restringida no se cambia %s (%s).' % (current.get('label') or type_name, alias))
        removed.add(alias)
        return None
    spec = catalog.get(type_name)
    if not spec:
        warnings.append('No modifico %s: el tipo %s no tiene ficha.' % (alias, type_name))
        return None
    params = dict(current.get('parameters') or {})
    if raw.get('parameters') is not None:
        params.update(_parameters(raw.get('parameters')))
    params, param_warnings = _filter_parameters(alias, spec, params, connections)
    warnings.extend(param_warnings)
    _warn_sql(alias, spec, params, warnings)
    label = raw.get('label')
    op = {
        'op': 'update_node',
        'id': current.get('canvas_id') or alias,
        'alias': alias,
        'type': type_name,
        'parameters': params,
    }
    if label:
        op['label'] = _clip(label, 80)
    if isinstance(raw.get('schema'), list):
        op['schema'] = raw.get('schema')
    schemaold = _schemaold(raw)
    if schemaold:
        op['schemaold'] = schemaold
    return op


def _clean_remove_node(raw, canvas_nodes, restricted, warnings, removed):
    alias = _text_id(raw.get('id') or raw.get('alias'))
    current = canvas_nodes.get(alias) if alias else None
    if not current:
        warnings.append('No elimino %s porque no está en el canvas.' % (alias or '?'))
        return None
    if restricted and is_protected(current.get('type')):
        warnings.append('En edición restringida no se elimina %s.' % alias)
        removed.add(alias)
        return None
    return {
        'op': 'remove_node',
        'id': current.get('canvas_id') or alias,
        'alias': alias,
        'type': current.get('type'),
        'label': current.get('label') or current.get('type'),
    }


def _clean_edges(raw_edges, nodes_by_id, catalog, warnings):
    edges = []
    seen = set()
    for raw in raw_edges or []:
        edge = _edge_from(raw, nodes_by_id, catalog, warnings)
        if not edge:
            continue
        key = (edge['source'], edge['target'], edge['source_port'], edge['target_port'])
        if key in seen:
            continue
        seen.add(key)
        edges.append(edge)
    return edges


def _clean_edge_op(kind, raw, catalog, canvas_nodes, added, restricted, warnings):
    source_alias = _text_id(raw.get('source'))
    target_alias = _text_id(raw.get('target'))
    source = _endpoint(source_alias, canvas_nodes, added)
    target = _endpoint(target_alias, canvas_nodes, added)
    if not source or not target:
        warnings.append('Conexión omitida: %s → %s no está en el flujo.' % (source_alias, target_alias))
        return None
    if source['id'] == target['id']:
        warnings.append('No conecto %s consigo mismo.' % source_alias)
        return None
    if restricted and (is_protected(source['type']) or is_protected(target['type'])):
        warnings.append('En edición restringida no se cambian las conexiones de entradas, salidas o SQL.')
        return None
    source_port = _port_index(raw.get('source_port', 0))
    target_port = _port_index(raw.get('target_port', 0))
    if not _ports_fit(source, target, source_port, target_port, catalog, warnings, source_alias, target_alias):
        return None
    return {
        'op': kind,
        'source': source['id'],
        'target': target['id'],
        'source_alias': source_alias,
        'target_alias': target_alias,
        'source_port': source_port,
        'target_port': target_port,
    }


def _edge_from(raw, nodes_by_id, catalog, warnings):
    if not isinstance(raw, dict):
        return None
    source_id = _text_id(raw.get('source'))
    target_id = _text_id(raw.get('target'))
    source = nodes_by_id.get(source_id)
    target = nodes_by_id.get(target_id)
    if not source or not target:
        warnings.append('Conexión omitida: %s → %s.' % (source_id, target_id))
        return None
    if source_id == target_id:
        warnings.append('No conecto %s consigo mismo.' % source_id)
        return None
    source_port = _port_index(raw.get('source_port', 0))
    target_port = _port_index(raw.get('target_port', 0))
    if not _ports_fit(source, target, source_port, target_port, catalog, warnings, source_id, target_id):
        return None
    return {
        'source': source_id,
        'target': target_id,
        'source_port': source_port,
        'target_port': target_port,
    }


def _ports_fit(source, target, source_port, target_port, catalog, warnings, source_label, target_label):
    source_spec = catalog.get(source.get('type'))
    target_spec = catalog.get(target.get('type'))
    if source_port is None or target_port is None:
        warnings.append('Puerto no válido entre %s y %s.' % (source_label, target_label))
        return False
    if source_spec and source_port >= port_count(source_spec, 'output'):
        warnings.append('%s no tiene la salida %s.' % (source_label, source_port))
        return False
    if target_spec and target_port >= port_count(target_spec, 'input'):
        warnings.append('%s no tiene la entrada %s.' % (target_label, target_port))
        return False
    # Un nodo ya presente sin ficha conserva sus conexiones: no se rechaza el puerto.
    if source_spec is None or target_spec is None:
        return True
    return True


def _endpoint(alias, canvas_nodes, added):
    if alias in added:
        node = added[alias]
        return {'id': node['id'], 'type': node['type']}
    current = canvas_nodes.get(alias)
    if not current:
        return None
    return {
        'id': current.get('canvas_id') or alias,
        'type': current.get('type'),
    }


def _filter_parameters(alias, spec, params, connections):
    warnings = []
    allowed = {item.get('name'): item for item in spec.get('parameters') or []}
    cleaned = {}
    for key, value in params.items():
        if key not in allowed:
            warnings.append('%s: quito el parámetro desconocido "%s".' % (alias, key))
            continue
        if not _value_ok(value):
            warnings.append('%s: quito "%s" porque el valor no es válido.' % (alias, key))
            continue
        choices = allowed[key].get('choices')
        if choices and isinstance(value, str) and value not in choices:
            warnings.append('%s: "%s" no admite el valor "%s".' % (alias, key, value))
            continue
        cleaned[key] = value
    _filter_connection(alias, spec, cleaned, connections, warnings)
    return cleaned, warnings


def _filter_connection(alias, spec, params, connections, warnings):
    field = spec.get('connection_parameter')
    if not field or field not in params:
        return
    name = params.get(field)
    if name in (None, ''):
        return
    name = str(name)
    found = None
    for item in connections:
        if item.get('name') == name:
            found = item
            break
    if not found:
        params.pop(field, None)
        warnings.append('%s: la conexión "%s" no está disponible para este usuario.' % (alias, name))
        return
    allowed_types = spec.get('connection_types') or []
    if allowed_types and found.get('type') not in allowed_types:
        params.pop(field, None)
        warnings.append(
            '%s: "%s" es de tipo %s y este nodo admite %s.'
            % (alias, name, found.get('type'), ', '.join(allowed_types))
        )


def _warn_sql(alias, spec, params, warnings):
    fields = spec.get('sql_parameters') or []
    if spec.get('type') == 'trans_ExecuteSQL':
        fields = list(fields) or ['query']
    for field in fields:
        value = params.get(field)
        if isinstance(value, str) and value.strip():
            warnings.append(_SQL_WARNING % alias)
            return


def _warn_required(alias, spec, params, warnings):
    for item in spec.get('parameters') or []:
        if not item.get('required'):
            continue
        value = params.get(item.get('name'))
        if value in (None, '', []):
            warnings.append('%s: falta %s. Se puede completar en el engranaje del nodo.' % (alias, item.get('name')))


def _parameters(raw):
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        return dict(raw[0])
    return {}


def _value_ok(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_value_ok(item) or isinstance(item, list) for item in value)
    return False


def _port_index(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def _schemaold(raw):
    for key in ('schemaold', 'schema-old'):
        if isinstance(raw.get(key), list):
            return raw.get(key)
    return []


def _canvas_index(canvas):
    """alias y id real apuntan a la misma ficha. canvas_id es el UUID de draw2d."""
    index = {}
    for node in canvas.get('nodes') or []:
        if not isinstance(node, dict):
            continue
        canvas_id = _text_id(node.get('id'))
        alias = _text_id(node.get('alias')) or canvas_id
        if not canvas_id or not alias:
            continue
        entry = {
            'alias': alias,
            'canvas_id': canvas_id,
            'id': canvas_id,
            'type': node.get('type'),
            'label': node.get('label') or node.get('type'),
            'parameters': node.get('parameters') if isinstance(node.get('parameters'), dict) else {},
        }
        index[alias] = entry
        index[canvas_id] = entry
    return index


def _attach_counts(nodes, catalog):
    for node in nodes:
        spec = catalog.get(node['type']) or {}
        node['input_count'] = port_count(spec, 'input')
        node['output_count'] = port_count(spec, 'output')


def _filter_assumptions(payload, removed):
    kept = []
    for item in payload.get('assumptions') or []:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        refs = set(_ALIAS_RE.findall(text))
        if refs & set(removed):
            continue
        kept.append(text)
    return kept


def _edges_inside_inserts(ops):
    """Aristas que ya quedan descritas en «Añado X entre A y B»."""
    covered = set()
    for op in ops:
        if op.get('op') != 'add_node':
            continue
        node_id = (op.get('node') or {}).get('id')
        if not _between(node_id, ops):
            continue
        for edge in ops:
            if edge.get('op') != 'add_edge':
                continue
            touches = (
                edge.get('target') == node_id
                or edge.get('target_alias') == node_id
                or edge.get('source') == node_id
                or edge.get('source_alias') == node_id
            )
            if touches:
                covered.add(id(edge))
    return covered


def _between(node_id, ops):
    incoming = []
    outgoing = []
    for op in ops:
        if op.get('op') != 'add_edge':
            continue
        if op.get('target') == node_id or op.get('target_alias') == node_id:
            incoming.append(op.get('source_alias') or op.get('source'))
        if op.get('source') == node_id or op.get('source_alias') == node_id:
            outgoing.append(op.get('target_alias') or op.get('target'))
    if len(incoming) == 1 and len(outgoing) == 1:
        return incoming[0], outgoing[0]
    return None


def _node_ref(node):
    return '%s (%s)' % (node.get('label') or node.get('type'), node.get('alias') or node.get('id'))


def _id_ref(node_id, nodes):
    for node in nodes:
        if node.get('id') == node_id or node.get('alias') == node_id:
            return _node_ref(node)
    return str(node_id)


def _ref(node_id, canvas_nodes, added, alias=None):
    if alias and node_id in canvas_nodes:
        current = canvas_nodes[node_id]
        return '%s (%s)' % (current.get('label') or current.get('type'), current.get('alias') or alias)
    if node_id in added:
        return _node_ref(added[node_id])
    current = canvas_nodes.get(node_id)
    if current:
        return '%s (%s)' % (current.get('label') or current.get('type'), current.get('alias') or node_id)
    return str(alias or node_id)


def _text_id(value):
    if value is None:
        return ''
    text = str(value).strip()
    if not text or len(text) > 80 or any(char.isspace() for char in text):
        return ''
    return text


def _clip(value, limit):
    if value is None:
        return ''
    text = str(value).strip()
    return text[:limit]


def _result(warnings=None, assumptions=None, summary=None, needs_confirmation=False, proposal=None):
    return {
        'warnings': warnings or [],
        'assumptions': assumptions or [],
        'summary': summary or [],
        'needs_confirmation': bool(needs_confirmation) if proposal else False,
        'proposal': proposal,
    }
