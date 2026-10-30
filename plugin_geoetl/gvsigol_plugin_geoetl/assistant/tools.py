# -*- coding: utf-8 -*-
"""Herramientas del agente. La autorización se comprueba aquí, no en las vistas de esquema."""

import json
import re

from langchain_core.tools import tool

from .catalog import public_specs
from .graph import validate_proposal

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


def build_tools(request, catalog, canvas, connections, restricted, holder):
    """holder es una lista de un elemento donde queda la última propuesta validada."""

    @tool
    def list_connections() -> str:
        """Lista las conexiones ETL que este usuario puede usar. Devuelve nombre y tipo, sin credenciales."""
        rows = []
        for item in connections:
            rows.append({'name': item.get('name'), 'type': item.get('type')})
        return _json({'connections': rows})

    @tool
    def get_node_specs(types: str) -> str:
        """Ficha de uno o varios tipos separados por comas. Hay que pedirla antes de usar un tipo en propose_workspace."""
        names = [part.strip() for part in (types or '').split(',') if part.strip()]
        found, missing = public_specs(catalog, names[:12])
        return _json({'specs': found, 'unknown': missing})

    @tool
    def list_tables(connection: str, schema: str = '') -> str:
        """Esquemas de una conexión autorizada, o tablas si se indica el esquema (en Oracle, el owner)."""
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

    @tool
    def get_table_schema(connection: str, schema: str, table: str) -> str:
        """Columnas de una tabla. schema es el esquema de PostgreSQL o SQL Server, o el owner de Oracle."""
        found = _find_connection(request, connection)
        if not found:
            return _json({'error': 'Conexión no disponible.'})
        if _bad_ident(schema) or _bad_ident(table):
            return _json({'error': 'Nombre de esquema o tabla no válido.'})
        try:
            columns = _columns(found, connection, schema, table)
        except Exception as exc:
            return _json({'error': 'No se ha podido leer el esquema.', 'detail': str(exc)[:300]})
        return _json({
            'connection': connection,
            'schema': schema,
            'table': table,
            'columns': columns,
        })

    @tool
    def propose_workspace(proposal_json: str) -> str:
        """Registra el flujo. proposal_json es un objeto con mode (replace o patch), name, description, assumptions (lista de frases) y, si mode es replace, nodes y edges. Cada node tiene id, type, label, parameters, schema y schemaold. Cada edge tiene source, target, source_port y target_port. Si mode es patch, ops es una lista de objetos con op add_node (y node), update_node (id, label, parameters), remove_node (id), add_edge o remove_edge (source, target, source_port, target_port). Los id son alias n1, n2…"""
        try:
            payload = json.loads(proposal_json)
        except (TypeError, ValueError):
            return _json({'error': 'proposal_json no es JSON.'})
        result = validate_proposal(
            payload,
            catalog,
            connections,
            canvas=canvas,
            restricted=restricted,
        )
        if not result.get('proposal'):
            return _json({
                'accepted': False,
                'warnings': result.get('warnings') or [],
            })
        holder[:] = [result]
        return _json({
            'accepted': True,
            'summary': result.get('summary') or [],
            'warnings': result.get('warnings') or [],
            'needs_confirmation': result.get('needs_confirmation'),
        })

    return [
        list_connections,
        get_node_specs,
        list_tables,
        get_table_schema,
        propose_workspace,
    ]


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
