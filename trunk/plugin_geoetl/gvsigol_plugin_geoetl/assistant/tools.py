# -*- coding: utf-8 -*-
"""Herramientas del agente. La autorización se comprueba aquí, no en las vistas de esquema."""

import contextlib
import json
import logging
import re
import threading

from langchain_core.tools import tool

from .catalog import public_specs
from .context import as_context
from .graph import validate_proposal
from .review import check_graph, graph_after, summarize_issues
from .tool_schemas import INVALID_ARGUMENTS, AskArgs, ProposalArgs, plain, proposal_payload

LOGGER = logging.getLogger('gvsigol')

_SECRET_PARAMETER = re.compile(r'pass(word|wd)?$|secret|token|api[-_]?key|credential|contrase', re.IGNORECASE)

_IDENT = re.compile(r'^[A-Za-z0-9_$.]+$')
_LIST_CAP = 200


def _json(payload):
    return json.dumps(payload, ensure_ascii=False)


def _bad_ident(value):
    return not value or not _IDENT.match(str(value))


_MAX_PROPOSALS = 3
_FILE_CAP = 200
_FILE_DEPTH = 4


def redact_parameters(parameters):
    """Parámetros de un nodo sin los que parezcan credenciales: el canvas se envía al proveedor de IA."""
    if not isinstance(parameters, dict):
        return parameters
    return {key: value for key, value in parameters.items() if not _SECRET_PARAMETER.search(str(key))}


def _release_thread_connections():
    """LangGraph ejecuta las herramientas en hilos propios: sus conexiones de Django no las cierra nadie."""
    if threading.current_thread().name.startswith('ThreadPoolExecutor'):
        from django.db import connections
        connections.close_all()


def _guarded(trace, name, body, lock=None):
    """Ejecuta una herramienta: un fallo inesperado se devuelve al modelo como error, no tumba el turno.

    Con lock, las llamadas en paralelo de un mismo turno se atienden de una en una:
    comparten la propuesta registrada y el contador de intentos.
    """
    with (lock or contextlib.nullcontext()):
        started = trace.start(name) if trace else None
        try:
            result = body()
            if trace:
                trace.finish(started, ok=True)
            return result
        except Exception as exc:  # noqa: BLE001 - la herramienta nunca debe romper el agente
            if trace:
                trace.finish(started, ok=False, error=type(exc).__name__)
            LOGGER.exception('etl_assistant: fallo en la herramienta %s', name)
            return _json({'error': 'La herramienta %s ha fallado. Sigue sin ella o pregunta al usuario.' % name})
        finally:
            _release_thread_connections()


def build_tools(request, catalog, canvas, connections, restricted, holder, trace=None, reviews=None, asked=None,
                alternatives=False, columns=False):
    """holder es una lista de un elemento donde queda la última propuesta validada.

    En reviews (si se pasa) queda la última revisión del canvas abierto
    (check_workspace sin propuesta), para enseñarla con botones en el panel.
    Con asked (una lista) se añade ask_user, y ahí quedan sus preguntas.
    Con columns se añade get_file_columns y se leen las columnas de las entradas propuestas.
    Con alternatives, las suposiciones de propose_workspace pueden ser objetos
    con nodo y parámetro, y la propuesta lleva sus alternativas (alternatives.py).

    request es el request de Django o un AssistantContext (context.py) con los
    permisos ya resueltos; con un contexto, connections y restricted salen de él.
    """
    context = as_context(request, connections, restricted)
    connections = context.connections
    restricted = context.restricted
    attempts = {'propose': 0}
    lock = threading.Lock()

    def guarded(name, body):
        return _guarded(trace, name, body, lock)

    @tool
    def list_connections() -> str:
        """Lista las conexiones ETL que este usuario puede usar. Devuelve nombre y tipo, sin credenciales."""
        def body():
            rows = [{'name': item.get('name'), 'type': item.get('type')} for item in connections]
            return _json({'connections': rows})
        return guarded('list_connections', body)

    @tool
    def get_node_specs(types: str) -> str:
        """Ficha de uno o varios tipos separados por comas (hasta 12). Hay que pedirla antes de usar un tipo en propose_workspace."""
        def body():
            names = [part.strip() for part in (types or '').split(',') if part.strip()]
            found, missing = public_specs(catalog, names[:12])
            return _json({'specs': found, 'unknown': missing})
        return guarded('get_node_specs', body)

    @tool
    def list_tables(connection: str, schema: str = '') -> str:
        """Esquemas de una conexión autorizada, o tablas si se indica el esquema (en Oracle, el owner)."""
        def body():
            found = context.find_connection(connection)
            if not found:
                return _json({'error': 'Conexión no disponible.'})
            if schema and _bad_ident(schema):
                return _json({'error': 'Nombre de esquema no válido.'})
            try:
                rows = _list_level(found, connection, schema)
            except Exception:
                # El detalle puede incluir host y usuario: se queda en el log, no va al proveedor de IA
                LOGGER.exception('etl_assistant: no se pudo leer la conexión')
                return _json({'error': 'No se ha podido leer la conexión.'})
            return _json({
                'connection': connection,
                'type': found.get('type'),
                'schema': schema or None,
                'items': rows[:_LIST_CAP],
                'truncated': len(rows) > _LIST_CAP,
            })
        return guarded('list_tables', body)

    @tool
    def get_table_schema(connection: str, schema: str, table: str) -> str:
        """Columnas de una tabla. schema es el esquema de PostgreSQL o SQL Server, o el owner de Oracle."""
        def body():
            found = context.find_connection(connection)
            if not found:
                return _json({'error': 'Conexión no disponible.'})
            if _bad_ident(schema) or _bad_ident(table):
                return _json({'error': 'Nombre de esquema o tabla no válido.'})
            try:
                columns = _columns(found, connection, schema, table)
            except Exception:
                LOGGER.exception('etl_assistant: no se pudo leer el esquema de una tabla')
                return _json({'error': 'No se ha podido leer el esquema.'})
            return _json({'connection': connection, 'schema': schema, 'table': table, 'columns': columns})
        return guarded('get_table_schema', body)

    @tool
    def list_files(folder: str = '', extensions: str = '') -> str:
        """Ficheros del gestor de ficheros a los que el usuario tiene acceso (solo nombres, no el contenido). folder es una carpeta relativa (vacío = todas las suyas); extensions, una lista separada por comas, por ejemplo "csv,txt" o "tif,tiff". Cada fichero trae value, la ruta lista para el parámetro de fichero del nodo."""
        return guarded('list_files', lambda: _json(_list_files(context, folder, extensions)))

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
                        'parameters': redact_parameters(node.get('parameters') or {}),
                        'schema': node.get('schema') or [],
                    })
            found = {n['id'] for n in nodes}
            return _json({'nodes': nodes, 'unknown': [w for w in wanted if w not in found]})
        return guarded('get_canvas_nodes', body)

    @tool(args_schema=ProposalArgs)
    def check_workspace(mode=None, name=None, description=None, assumptions=None, nodes=None, edges=None, ops=None,
                        proposal_json=None) -> str:
        """Revisa el flujo y devuelve los problemas que se pueden comprobar: nodos sin configurar, parámetros obligatorios vacíos, columnas que no llegan, entradas sin conectar, tipos de puerto que no encajan, ciclos, salidas sin usar y conexiones no disponibles. Sin argumentos revisa el canvas abierto. Con una propuesta (mismos campos que propose_workspace) revisa cómo quedaría, sin registrarla."""
        def body():
            proposal = None
            warnings = []
            try:
                payload = proposal_payload(proposal_json, mode=mode, name=name, description=description,
                                           assumptions=assumptions, nodes=nodes, edges=edges, ops=ops)
            except ValueError:
                return _json({'error': 'proposal_json no es JSON.'})
            if payload:
                result = validate_proposal(payload, catalog, connections, canvas=canvas, restricted=restricted)
                proposal = result.get('proposal')
                warnings = result.get('warnings') or []
                if not proposal:
                    return _json({'valid': False, 'warnings': warnings})
            graph_nodes, graph_edges = graph_after(proposal, canvas)
            issues = check_graph(graph_nodes, graph_edges, catalog, connections)
            if proposal is None and reviews is not None:
                reviews[:] = [issues]
            return _json({
                'scope': 'proposal' if proposal else 'canvas',
                'nodes': len(graph_nodes),
                'result': summarize_issues(issues),
                'issues': issues,
                'warnings': warnings,
            })
        return guarded('check_workspace', body)

    @tool(args_schema=ProposalArgs)
    def propose_workspace(mode=None, name=None, description=None, assumptions=None, nodes=None, edges=None, ops=None,
                          proposal_json=None) -> str:
        """Registra el flujo: es la única forma de cambiar el canvas. Con mode replace manda todos los nodes y edges; con mode patch, las ops (add_node, update_node con solo los parameters que cambian, remove_node, add_edge o remove_edge). Los id son los n1, n2... que se ven en el canvas."""
        def body():
            attempts['propose'] += 1
            try:
                payload = proposal_payload(proposal_json, mode=mode, name=name, description=description,
                                           assumptions=assumptions, nodes=nodes, edges=edges, ops=ops)
            except ValueError:
                return _json({'accepted': False, 'errors': ['proposal_json no es JSON válido.'],
                              'instruction': 'Vuelve a llamar con un JSON válido.'})
            structured = []
            if columns:
                from .columns import normalize_proposal
                payload = normalize_proposal(payload, catalog, canvas)
            if alternatives:
                from .alternatives import split_assumptions
                payload, structured = split_assumptions(payload)
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
            if structured:
                from .alternatives import resolve_alternatives
                try:
                    result['assumption_choices'] = resolve_alternatives(structured, result, canvas, catalog, context)
                except Exception:
                    import logging
                    logging.getLogger('gvsigol').exception('etl_assistant: no se pudieron preparar las alternativas')
            read_columns = {}
            if columns:
                from .columns import enrich_proposal
                read_columns = enrich_proposal(result, context)
            holder[:] = [result]
            graph_nodes, graph_edges = graph_after(result['proposal'], canvas)
            issues = [item for item in check_graph(graph_nodes, graph_edges, catalog, connections)
                      if item['level'] == 'error' and item['code'] != 'unconfigured']
            fixable = bool(result.get('warnings') or issues)
            return _json({
                'accepted': True,
                'summary': result.get('summary') or [],
                'warnings': result.get('warnings') or [],
                'issues': [item['message'] for item in issues],
                'needs_confirmation': result.get('needs_confirmation'),
                'columns': read_columns,
                'instruction': (
                    'Propuesta registrada. Si warnings o issues muestran algo que puedas corregir (tareas o '
                    'conexiones descartadas, entradas sin conectar, parámetros con valor no válido), vuelve a '
                    'llamar a propose_workspace con la propuesta completa corregida; la nueva sustituye a esta. '
                    'Lo que dependa del usuario (rutas, valores que no sabes) díselo en el texto.'
                    if fixable and not last_try else
                    'Propuesta registrada. Responde al usuario en una o dos frases, sin repetir la lista de '
                    'cambios, y dile qué tiene que completar.'),
            })
        return guarded('propose_workspace', body)

    @tool(args_schema=AskArgs)
    def ask_user(questions=None, questions_json=None) -> str:
        """Pregunta al usuario lo que no se puede deducir; el panel enseña las opciones para elegir con un clic. Hasta 4 preguntas, cada una con label, text y source. Orígenes: choices (con node o type y param), connections, datastores (destino de una tabla PostGIS), tables (con connection y schema), columns (con connection, schema y table, o con file), files (con extensions: se elige en el administrador de archivos), workspaces, layer_groups o custom (con options, solo para reglas que no salen de los datos). Después escribe solo una frase breve, sin repetir las preguntas ni las opciones."""
        def body():
            from .questions import resolve_questions
            if (questions_json or '').strip():
                try:
                    payload = json.loads(questions_json)
                except (TypeError, ValueError):
                    return _json({'accepted': False, 'errors': ['questions_json no es JSON válido.']})
            else:
                payload = plain(questions)
            if isinstance(payload, dict):
                payload = payload.get('questions')
            proposal = holder[-1].get('proposal') if holder else None
            resolved, notes = resolve_questions(payload, catalog, canvas, context, proposal)
            if not resolved:
                return _json({'accepted': False, 'errors': notes or ['No hay ninguna pregunta válida.']})
            asked[:] = [resolved]
            if trace:
                trace.note('asked', [[q['source'], len(q['options'])] for q in resolved])
            return _json({
                'accepted': True,
                'questions': [{'id': q['id'], 'label': q['label'], 'options': len(q['options'])}
                              for q in resolved],
                'notes': notes,
                'instruction': ('Preguntas registradas: el panel las enseña con sus opciones. Termina con una '
                                'frase breve, sin repetir las preguntas ni las opciones, y no llames a '
                                'propose_workspace en este turno.'),
            })
        return guarded('ask_user', body)

    @tool
    def get_file_columns(file: str, sheet: str = '') -> str:
        """Columnas de un fichero del usuario (shp, csv, xls, xlsx, kml). file es el valor file://... que eligió el usuario. Si es un Excel con varias hojas, devuelve sheets y hay que repetir con sheet."""
        def body():
            from .columns import read_file
            read = read_file(file, sheet, context) or {}
            return _json({'columns': read.get('schema'), 'sheets': read.get('sheets'), 'error': read.get('error')})
        return guarded('get_file_columns', body)

    for typed in (check_workspace, propose_workspace, ask_user):
        typed.handle_validation_error = INVALID_ARGUMENTS

    built = [
        list_connections,
        get_node_specs,
        list_tables,
        get_table_schema,
        list_files,
        get_canvas_nodes,
        check_workspace,
        propose_workspace,
    ]
    if asked is not None:
        built.append(ask_user)
    if columns:
        built.append(get_file_columns)
    return built


def _list_files(context, folder, extensions):
    """
    Nombres de los ficheros que el usuario puede ver en el gestor de ficheros, con los mismos
    permisos que el propio gestor (superusuario: todo; staff: las carpetas de sus roles).
    """
    import os
    from django.conf import settings
    try:
        import gvsigol_filemanager.views  # noqa: F401
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
    if not context.can_browse(folder):
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
            dirs[:] = [d for d in dirs if allowed_top.setdefault(d, context.can_manage_dir(d))]
            if not context.is_superuser:
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
