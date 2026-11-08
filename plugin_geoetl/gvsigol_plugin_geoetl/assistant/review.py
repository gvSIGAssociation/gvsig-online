# -*- coding: utf-8 -*-
"""Revisión exacta de un flujo: lo que se puede comprobar con el catálogo, sin el modelo.

Trabaja con alias (n1, n2…). Sirve para revisar el canvas abierto y para comprobar el resultado
de una propuesta antes de devolverla, de modo que el modelo pueda corregirla.
"""

from .catalog import port_count, port_kind

ERROR = 'error'
WARNING = 'warning'


def graph_from_canvas(canvas):
    """Nodos y aristas del resumen del canvas que envía el editor."""
    nodes = {}
    for node in (canvas or {}).get('nodes') or []:
        if not isinstance(node, dict):
            continue
        alias = node.get('alias') or node.get('id')
        if not alias:
            continue
        nodes[alias] = {
            'alias': alias,
            'type': node.get('type'),
            'label': node.get('label') or node.get('type'),
            'parameters': node.get('parameters') if isinstance(node.get('parameters'), dict) else {},
            # None: editor antiguo que no envía el estado (se deduce de si tiene parámetros)
            'status': node.get('status'),
            'schema': node.get('schema') if isinstance(node.get('schema'), list) else [],
        }
    edges = []
    for edge in (canvas or {}).get('edges') or []:
        if isinstance(edge, dict) and edge.get('source') in nodes and edge.get('target') in nodes:
            edges.append({
                'source': edge.get('source'),
                'target': edge.get('target'),
                'source_port': edge.get('source_port', 0),
                'target_port': edge.get('target_port', 0),
            })
    return nodes, edges


def graph_after(proposal, canvas):
    """Cómo quedaría el flujo si se aplicara una propuesta ya validada."""
    if not proposal:
        return graph_from_canvas(canvas)
    if proposal.get('mode') == 'replace':
        nodes = {}
        for node in proposal.get('nodes') or []:
            alias = node.get('alias') or node.get('id')
            nodes[alias] = {
                'alias': alias,
                'type': node.get('type'),
                'label': node.get('label') or node.get('type'),
                'parameters': node.get('parameters') or {},
                'schema': node.get('schema') or [],
                'status': 'proposed',
            }
        edges = [dict(edge) for edge in proposal.get('edges') or []]
        return nodes, edges

    nodes, edges = graph_from_canvas(canvas)
    by_canvas_id = {}
    for node in (canvas or {}).get('nodes') or []:
        if isinstance(node, dict) and node.get('id') and node.get('alias'):
            by_canvas_id[node.get('id')] = node.get('alias')

    def alias_of(value, fallback=None):
        return fallback or by_canvas_id.get(value) or value

    for op in proposal.get('ops') or []:
        kind = op.get('op')
        if kind == 'add_node':
            node = op.get('node') or {}
            alias = node.get('alias') or node.get('id')
            nodes[alias] = {
                'alias': alias,
                'type': node.get('type'),
                'label': node.get('label') or node.get('type'),
                'parameters': node.get('parameters') or {},
                'schema': node.get('schema') or [],
                'status': 'proposed',
            }
        elif kind == 'update_node':
            alias = alias_of(op.get('id'), op.get('alias'))
            if alias in nodes:
                nodes[alias]['parameters'] = op.get('parameters') or {}
                nodes[alias]['status'] = 'proposed'
                if op.get('schema'):
                    nodes[alias]['schema'] = op.get('schema')
                if op.get('label'):
                    nodes[alias]['label'] = op.get('label')
        elif kind == 'remove_node':
            alias = alias_of(op.get('id'), op.get('alias'))
            nodes.pop(alias, None)
            edges = [e for e in edges if e['source'] != alias and e['target'] != alias]
        elif kind in ('add_edge', 'remove_edge'):
            edge = {
                'source': alias_of(op.get('source'), op.get('source_alias')),
                'target': alias_of(op.get('target'), op.get('target_alias')),
                'source_port': op.get('source_port', 0),
                'target_port': op.get('target_port', 0),
            }
            if kind == 'add_edge':
                edges.append(edge)
            else:
                edges = [e for e in edges if not _same_edge(e, edge)]
    return nodes, edges


def check_graph(nodes, edges, catalog, connections=None):
    """Lista de problemas: dicts con level (error o warning), node, code y message."""
    issues = []
    connections = connections or []
    if not nodes:
        return issues
    incoming = {}
    outgoing = {}
    for edge in edges:
        incoming.setdefault(edge['target'], []).append(edge)
        outgoing.setdefault(edge['source'], []).append(edge)

    for alias in _ordered(nodes):
        node = nodes[alias]
        spec = catalog.get(node.get('type'))
        name = '%s (%s)' % (node.get('label') or node.get('type'), alias)
        if not spec:
            issues.append(_issue(WARNING, alias, 'unknown_type',
                                 '%s: el tipo %s no tiene ficha; no se puede revisar.' % (name, node.get('type'))))
            continue
        params = node.get('parameters') or {}
        if node.get('status') == 'unconfigured' or (node.get('status') is None and not params):
            issues.append(_issue(ERROR, alias, 'unconfigured',
                                 '%s: está sin configurar (rueda roja). Ábrelo y pulsa Aceptar.' % name))
        else:
            if node.get('status') == 'invalid':
                issues.append(_issue(ERROR, alias, 'invalid_schema',
                                     '%s: su configuración no encaja con lo que le llega; vuelve a abrirlo y aceptarlo.' % name))
            _check_parameters(alias, name, spec, params, connections, issues)
        _check_inputs(alias, name, spec, incoming.get(alias) or [], issues)
        _check_columns(alias, name, spec, params, incoming.get(alias) or [], nodes, issues)
        _check_outputs(alias, name, spec, outgoing.get(alias) or [], len(nodes), issues)

    for edge in edges:
        _check_edge(edge, nodes, catalog, issues)

    cycle = _find_cycle(nodes, edges)
    if cycle:
        issues.append(_issue(ERROR, cycle[0], 'cycle',
                             'Hay un ciclo: %s. Un flujo no puede volver a un nodo anterior.' % ' → '.join(cycle)))

    families = [(catalog.get(n.get('type')) or {}).get('family') or _family(n.get('type')) for n in nodes.values()]
    if 'output' not in families:
        issues.append(_issue(WARNING, None, 'no_output',
                             'El flujo no termina en ninguna salida: al ejecutarlo no se guardará ningún resultado.'))
    return issues


def summarize_issues(issues):
    errors = sum(1 for item in issues if item['level'] == ERROR)
    warnings = sum(1 for item in issues if item['level'] == WARNING)
    return {'errors': errors, 'warnings': warnings, 'ok': errors == 0}


def _column_values(value):
    if isinstance(value, str):
        return [part for part in value.split() if part != '-']
    if isinstance(value, list):
        return [part for part in value if isinstance(part, str) and part != '-']
    return []


def _check_columns(alias, name, spec, params, edges_in, nodes, issues):
    """Los parámetros marcados con column en la ficha tienen que existir en lo que llega por esa entrada.

    Solo se puede saber si el nodo anterior tiene una lista de columnas conocida: los que tienen una
    por cada salida, o los recién propuestos, no se comprueban.
    """
    for item in spec.get('parameters') or []:
        port = item.get('column')
        values = _column_values(params.get(item.get('name'))) if port is not None else []
        if not values:
            continue
        source = next((e.get('source') for e in edges_in if e.get('target_port', 0) == port), None)
        schema = (nodes.get(source) or {}).get('schema')
        if not isinstance(schema, list) or not schema or not all(isinstance(c, str) for c in schema):
            continue
        missing = [column for column in values if column not in schema]
        if missing:
            issues.append(_issue(ERROR, alias, 'unknown_column',
                                 '%s: la columna "%s" no llega por la entrada %s.' % (name, ', '.join(missing), port),
                                 param=item.get('name')))


def _check_parameters(alias, name, spec, params, connections, issues):
    if spec.get('type') == 'input_Excel' and params.get('excel-file') and not params.get('sheet-name') \
            and params.get('reading') != 'multiple':
        issues.append(_issue(ERROR, alias, 'missing_parameter', '%s: falta elegir la hoja del Excel.' % name,
                             param='sheet-name'))
    for item in spec.get('parameters') or []:
        key = item.get('name')
        value = params.get(key)
        if item.get('required') and value in (None, '', []):
            issues.append(_issue(ERROR, alias, 'missing_parameter',
                                 '%s: falta el parámetro obligatorio "%s".' % (name, key), param=key))
        choices = item.get('choices')
        if choices and isinstance(value, str) and value and value not in choices:
            issues.append(_issue(ERROR, alias, 'invalid_choice',
                                 '%s: "%s" no admite el valor "%s".' % (name, key, value), param=key))
    field = spec.get('connection_parameter')
    value = params.get(field) if field else None
    if value not in (None, ''):
        names = {c.get('name'): c.get('type') for c in connections}
        if value not in names:
            issues.append(_issue(ERROR, alias, 'unknown_connection',
                                 '%s: la conexión "%s" no está disponible para este usuario.' % (name, value),
                                 param=field))
        elif spec.get('connection_types') and names[value] not in spec.get('connection_types'):
            issues.append(_issue(ERROR, alias, 'connection_type',
                                 '%s: la conexión "%s" es %s y el nodo admite %s.'
                                 % (name, value, names[value], ', '.join(spec.get('connection_types'))),
                                 param=field))


def _check_inputs(alias, name, spec, edges_in, issues):
    ports = [p for p in spec.get('ports') or [] if p.get('direction') == 'input']
    for index, port in enumerate(ports):
        arriving = [e for e in edges_in if e.get('target_port', 0) == index]
        label = port.get('label') or index
        if not arriving and not port.get('optional'):
            issues.append(_issue(ERROR, alias, 'unconnected_input',
                                 '%s: la entrada %s (%s) no está conectada.' % (name, index, label)))
        if len(arriving) > 1:
            issues.append(_issue(ERROR, alias, 'duplicated_input',
                                 '%s: la entrada %s (%s) recibe %d conexiones; solo admite una.'
                                 % (name, index, label, len(arriving))))


def _check_outputs(alias, name, spec, edges_out, total, issues):
    outputs = port_count(spec, 'output')
    if outputs and not edges_out and total > 1:
        issues.append(_issue(WARNING, alias, 'dead_end',
                             '%s: ninguna de sus salidas está conectada; su resultado no se usa.' % name))


def _check_edge(edge, nodes, catalog, issues):
    source, target = nodes.get(edge['source']), nodes.get(edge['target'])
    if not source or not target:
        return
    source_spec, target_spec = catalog.get(source.get('type')), catalog.get(target.get('type'))
    if not source_spec or not target_spec:
        return
    sp, tp = edge.get('source_port', 0), edge.get('target_port', 0)
    if not isinstance(sp, int) or sp >= port_count(source_spec, 'output'):
        issues.append(_issue(ERROR, edge['source'], 'bad_port',
                             '%s no tiene la salida %s.' % (edge['source'], sp)))
        return
    if not isinstance(tp, int) or tp >= port_count(target_spec, 'input'):
        issues.append(_issue(ERROR, edge['target'], 'bad_port',
                             '%s no tiene la entrada %s.' % (edge['target'], tp)))
        return
    sk, tk = port_kind(source_spec, 'output', sp), port_kind(target_spec, 'input', tp)
    if sk != tk:
        issues.append(_issue(ERROR, edge['target'], 'kind_mismatch',
                             'La conexión %s → %s une un puerto de tipo %s con uno de tipo %s.'
                             % (edge['source'], edge['target'], sk, tk)))


def _find_cycle(nodes, edges):
    graph = {alias: [] for alias in nodes}
    for edge in edges:
        if edge['source'] in graph and edge['target'] in graph:
            graph[edge['source']].append(edge['target'])
    state = {}
    path = []

    def visit(alias):
        state[alias] = 1
        path.append(alias)
        for nxt in graph[alias]:
            if state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            if not state.get(nxt):
                found = visit(nxt)
                if found:
                    return found
        state[alias] = 2
        path.pop()
        return None

    for alias in _ordered(nodes):
        if not state.get(alias):
            found = visit(alias)
            if found:
                return found
    return None


def _ordered(nodes):
    def key(alias):
        digits = alias[1:] if alias.startswith('n') else ''
        return (0, int(digits)) if digits.isdigit() else (1, alias)
    return sorted(nodes, key=key)


def _family(type_name):
    name = type_name or ''
    for prefix, family in (('input_', 'input'), ('output_', 'output'), ('crea_', 'creator')):
        if name.startswith(prefix):
            return family
    return 'transform'


def _same_edge(a, b):
    return (a['source'], a['target'], a.get('source_port', 0), a.get('target_port', 0)) == \
        (b['source'], b['target'], b.get('source_port', 0), b.get('target_port', 0))


def _issue(level, node, code, message, param=None):
    issue = {'level': level, 'node': node, 'code': code, 'message': message}
    if param:
        issue['param'] = param
    return issue
