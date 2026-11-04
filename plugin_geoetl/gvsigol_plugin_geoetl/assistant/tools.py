# -*- coding: utf-8 -*-
"""Herramientas del agente. La autorización se comprueba aquí, no en las vistas de esquema."""

import json
import re

from langchain_core.tools import tool

from .catalog import public_specs
from .graph import validate_proposal
from .review import check_graph, graph_after, summarize_issues

_IDENT = re.compile(r'^[A-Za-z0-9_$.]+$')
_LIST_CAP = 200


def _json(payload):
    return json.dumps(payload, ensure_ascii=False)


def _connections(request):
    from gvsigol_plugin_geoetl.views import get_etl_connections_list
    return get_etl_connections_list(request)


def _find_connection(request, name):
    for item in _connections(request):
        if item.get('name') == name:
            return item
    return None


def _bad_ident(value):
    return not value or not _IDENT.match(str(value))


_MAX_PROPOSALS = 3
_FILE_CAP = 200
_FILE_DEPTH = 4


def _guarded(trace, name, body):
    """Ejecuta una herramienta: un fallo inesperado se devuelve al modelo como error, no tumba el turno."""
    started = trace.start(name) if trace else None
    try:
        result = body()
        if trace:
            trace.finish(started, ok=True)
        return result
    except Exception as exc:  # noqa: BLE001 - la herramienta nunca debe romper el agente
        if trace:
            trace.finish(started, ok=False, error=type(exc).__name__)
        import logging
        logging.getLogger('gvsigol').exception('etl_assistant: fallo en la herramienta %s', name)
        return _json({'error': 'La herramienta %s ha fallado. Sigue sin ella o pregunta al usuario.' % name})


def build_tools(request, catalog, canvas, connections, restricted, holder, trace=None):
    """holder es una lista de un elemento donde queda la última propuesta validada."""
    attempts = {'propose': 0}

    @tool
    def list_connections() -> str:
        """Lista las conexiones ETL que este usuario puede usar. Devuelve nombre y tipo, sin credenciales."""
        def body():
            rows = [{'name': item.get('name'), 'type': item.get('type')} for item in connections]
            return _json({'connections': rows})
        return _guarded(trace, 'list_connections', body)

    @tool
    def get_node_specs(types: str) -> str:
        """Ficha de uno o varios tipos separados por comas (hasta 12). Hay que pedirla antes de usar un tipo en propose_workspace."""
        def body():
            names = [part.strip() for part in (types or '').split(',') if part.strip()]
            found, missing = public_specs(catalog, names[:12])
            return _json({'specs': found, 'unknown': missing})
        return _guarded(trace, 'get_node_specs', body)

    @tool
    def list_tables(connection: str, schema: str = '') -> str:
        """Esquemas de una conexión autorizada, o tablas si se indica el esquema (en Oracle, el owner)."""
        def body():
            found = _find_connection(request, connection)
            if not found:
                return _json({'error': 'Conexión no disponible.'})
            if schema and _bad_ident(schema):
                return _json({'error': 'Nombre de esquema no válido.'})
            try:
                rows = _list_level(found, connection, schema)
            except Exception as exc:
                return _json({'error': 'No se ha podido leer la conexión.', 'detail': str(exc)[:300]})
            return _json({
                'connection': connection,
                'type': found.get('type'),
                'schema': schema or None,
                'items': rows[:_LIST_CAP],
                'truncated': len(rows) > _LIST_CAP,
            })
        return _guarded(trace, 'list_tables', body)

    @tool
    def get_table_schema(connection: str, schema: str, table: str) -> str:
        """Columnas de una tabla. schema es el esquema de PostgreSQL o SQL Server, o el owner de Oracle."""
        def body():
            found = _find_connection(request, connection)
            if not found:
                return _json({'error': 'Conexión no disponible.'})
            if _bad_ident(schema) or _bad_ident(table):
                return _json({'error': 'Nombre de esquema o tabla no válido.'})
            try:
                columns = _columns(found, connection, schema, table)
            except Exception as exc:
                return _json({'error': 'No se ha podido leer el esquema.', 'detail': str(exc)[:300]})
            return _json({'connection': connection, 'schema': schema, 'table': table, 'columns': columns})
        return _guarded(trace, 'get_table_schema', body)

    @tool
    def list_files(folder: str = '', extensions: str = '') -> str:
        """Ficheros del gestor de ficheros a los que el usuario tiene acceso (solo nombres, no el contenido). folder es una carpeta relativa (vacío = todas las suyas); extensions, una lista separada por comas, por ejemplo "csv,txt" o "tif,tiff". Cada fichero trae value, la ruta lista para el parámetro de fichero del nodo."""
        return _guarded(trace, 'list_files', lambda: _json(_list_files(request, folder, extensions)))

    @tool
    def get_canvas_nodes(ids: str) -> str:
        """Parámetros y esquema completos de nodos del canvas abierto, por id separados por comas (n1,n4)."""
        def body():
            wanted = [part.strip() for part in (ids or '').split(',') if part.strip()][:20]
            nodes = []
            for node in canvas.get('nodes') or []:
                if isinstance(node, dict) and node.get('alias') in wanted:
                    nodes.append({
                        'id': node.get('alias'),
                        'type': node.get('type'),
                        'label': node.get('label'),
                        'status': node.get('status') or '',
                        'parameters': node.get('parameters') or {},
                        'schema': node.get('schema') or [],
                    })
            found = {n['id'] for n in nodes}
            return _json({'nodes': nodes, 'unknown': [w for w in wanted if w not in found]})
        return _guarded(trace, 'get_canvas_nodes', body)

    @tool
    def check_workspace(proposal_json: str = '') -> str:
        """Revisa el flujo y devuelve los problemas que se pueden comprobar: nodos sin configurar, parámetros obligatorios vacíos, entradas sin conectar, tipos de puerto que no encajan, ciclos, salidas sin usar y conexiones no disponibles. Sin argumentos revisa el canvas abierto. Con proposal_json (mismo formato que propose_workspace) revisa cómo quedaría el flujo con esa propuesta, sin registrarla."""
        def body():
            proposal = None
            warnings = []
            if (proposal_json or '').strip():
                try:
                    payload = json.loads(proposal_json)
                except (TypeError, ValueError):
                    return _json({'error': 'proposal_json no es JSON.'})
                result = validate_proposal(payload, catalog, connections, canvas=canvas, restricted=restricted)
                proposal = result.get('proposal')
                warnings = result.get('warnings') or []
                if not proposal:
                    return _json({'valid': False, 'warnings': warnings})
            nodes, edges = graph_after(proposal, canvas)
            issues = check_graph(nodes, edges, catalog, connections)
            return _json({
                'scope': 'proposal' if proposal else 'canvas',
                'nodes': len(nodes),
                'result': summarize_issues(issues),
                'issues': issues,
                'warnings': warnings,
            })
        return _guarded(trace, 'check_workspace', body)

    @tool
    def propose_workspace(proposal_json: str) -> str:
        """Registra el flujo. proposal_json es un objeto con mode (replace o patch), name, description, assumptions (lista de frases) y, si mode es replace, nodes y edges. Cada node tiene id, type, label, parameters, schema y schemaold. Cada edge tiene source, target, source_port y target_port. Si mode es patch, ops es una lista de objetos con op add_node (y node), update_node (id, label y solo los parameters que cambian), remove_node (id), add_edge o remove_edge (source, target, source_port, target_port). Los id son los n1, n2… que se ven en el canvas."""
        def body():
            attempts['propose'] += 1
            try:
                payload = json.loads(proposal_json)
            except (TypeError, ValueError):
                return _json({'accepted': False, 'errors': ['proposal_json no es JSON válido.'],
                              'instruction': 'Vuelve a llamar con un JSON válido.'})
            result = validate_proposal(payload, catalog, connections, canvas=canvas, restricted=restricted)
            last_try = attempts['propose'] >= _MAX_PROPOSALS
            if trace:
                trace.note('proposals', attempts['propose'])
            if not result.get('proposal'):
                return _json({
                    'accepted': False,
                    'errors': result.get('warnings') or ['La propuesta no contiene cambios válidos.'],
                    'instruction': ('No reintentes más: explica al usuario qué falta.' if last_try else
                                    'Corrige estos errores y vuelve a llamar a propose_workspace con la propuesta '
                                    'completa. Si falta información del usuario, pregúntasela.'),
                })
            holder[:] = [result]
            nodes, edges = graph_after(result['proposal'], canvas)
            issues = [item for item in check_graph(nodes, edges, catalog, connections)
                      if item['level'] == 'error' and item['code'] != 'unconfigured']
            fixable = bool(result.get('warnings') or issues)
            return _json({
                'accepted': True,
                'summary': result.get('summary') or [],
                'warnings': result.get('warnings') or [],
                'issues': [item['message'] for item in issues],
                'needs_confirmation': result.get('needs_confirmation'),
                'instruction': (
                    'Propuesta registrada. Si warnings o issues muestran algo que puedas corregir (tareas o '
                    'conexiones descartadas, entradas sin conectar, parámetros con valor no válido), vuelve a '
                    'llamar a propose_workspace con la propuesta completa corregida; la nueva sustituye a esta. '
                    'Lo que dependa del usuario (rutas, valores que no sabes) díselo en el texto.'
                    if fixable and not last_try else
                    'Propuesta registrada. Responde al usuario en una o dos frases, sin repetir la lista de '
                    'cambios, y dile qué tiene que completar.'),
            })
        return _guarded(trace, 'propose_workspace', body)

    return [
        list_connections,
        get_node_specs,
        list_tables,
        get_table_schema,
        list_files,
        get_canvas_nodes,
        check_workspace,
        propose_workspace,
    ]


def _list_files(request, folder, extensions):
    """
    Nombres de los ficheros que el usuario puede ver en el gestor de ficheros, con los mismos
    permisos que el propio gestor (superusuario: todo; staff: las carpetas de sus roles).
    """
    import os
    from django.conf import settings
    try:
        from gvsigol_filemanager.views import can_browse_path, can_manage_path
    except Exception:
        return {'error': 'El gestor de ficheros no está disponible.'}
    root = os.path.abspath(getattr(settings, 'FILEMANAGER_DIRECTORY', '') or '')
    if not root or not os.path.isdir(root):
        return {'error': 'El gestor de ficheros no está configurado.'}
    folder = (folder or '').strip().strip('/')
    if '..' in folder.split('/') or folder.startswith('.'):
        return {'error': 'Carpeta no válida.'}
    base = os.path.abspath(os.path.join(root, folder))
    if base != root and not base.startswith(root + os.sep):
        return {'error': 'Carpeta no válida.'}
    if not os.path.isdir(base):
        return {'error': 'La carpeta %s no existe.' % (folder or '/')}
    if not can_browse_path(request, folder):
        return {'error': 'No tienes acceso a la carpeta %s.' % (folder or '/')}
    wanted = {('.' + e.strip().lower().lstrip('.')) for e in (extensions or '').split(',') if e.strip()}
    files, truncated = [], False
    allowed_top = {}
    for current, dirs, names in os.walk(base):
        rel_dir = os.path.relpath(current, root)
        rel_dir = '' if rel_dir == '.' else rel_dir
        depth = 0 if not rel_dir else rel_dir.count(os.sep) + 1
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        if depth >= _FILE_DEPTH:
            dirs[:] = []
        if not rel_dir:
            # En la raíz solo se baja a las carpetas a las que el usuario tiene acceso.
            dirs[:] = [d for d in dirs if allowed_top.setdefault(d, can_manage_path(request, d))]
            if not request.user.is_superuser:
                continue      # los ficheros sueltos de la raíz no son de ningún rol
        for name in sorted(names):
            if name.startswith('.'):
                continue
            if wanted and os.path.splitext(name)[1].lower() not in wanted:
                continue
            if len(files) >= _FILE_CAP:
                truncated = True
                break
            rel = os.path.join(rel_dir, name) if rel_dir else name
            full = os.path.join(root, rel)
            try:
                size_kb = int(os.path.getsize(full) / 1024)
            except OSError:
                size_kb = None
            files.append({'path': rel, 'value': 'file://' + full, 'size_kb': size_kb})
        if truncated:
            break
    return {'folder': folder or '/', 'files': files, 'truncated': truncated,
            'hint': 'Si hay varios candidatos y no sabes cuál es, pregunta al usuario.'}


def _list_level(connection, name, schema):
    from gvsigol_plugin_geoetl import etl_schema
    kind = connection.get('type')
    if kind in ('PostgreSQL', 'PostGIS'):
        if schema:
            return list(etl_schema.get_table_name_postgres({'db': name, 'schema-name': schema}))
        return list(etl_schema.get_schema_name_postgres({'db': name}))
    if kind == 'Oracle':
        if schema:
            return list(etl_schema.get_tables_oracle({'db': name, 'owner-name': schema}))
        return list(etl_schema.get_owners_oracle({'db': name}))
    if kind == 'SQLServer':
        if schema:
            return list(etl_schema.get_tables_sqlserver({'db': name, 'schema-name': schema}))
        return list(etl_schema.get_schemas_sqlserver({'db': name}))
    return []


def _columns(connection, name, schema, table):
    from gvsigol_plugin_geoetl import etl_schema
    kind = connection.get('type')
    if kind in ('PostgreSQL', 'PostGIS'):
        return list(etl_schema.get_schema_postgres({
            'db': name,
            'schema-name': schema,
            'tablename': table,
        }))
    if kind == 'Oracle':
        return list(etl_schema.get_schema_oracle({
            'db': name,
            'owner-name': schema,
            'table-name': table,
            'checkbox': 'false',
        }))
    if kind == 'SQLServer':
        return list(etl_schema.get_data_schemas_sqlserver({
            'db': name,
            'schema-name': schema,
            'table-name': table,
            'checkbox': 'false',
        }))
    return []
