# -*- coding: utf-8 -*-
"""Controles de seguridad del motor ETL: SQL del nodo IA, conexiones y tipos de nodo."""
import re

import sqlglot
from sqlglot import exp

# Funciones con efectos (DDL interno, lectura de tablas por nombre, acceso al servidor).
# El nodo IA solo puede leer de sus entradas: ninguna de estas tiene uso legítimo ahí.
_FORBIDDEN_FUNCTIONS = {
    # PostGIS: ejecutan ALTER/DROP TABLE por dentro
    'addgeometrycolumn', 'dropgeometrycolumn', 'dropgeometrytable', 'updategeometrysrid',
    'populate_geometry_columns', 'addauth', 'checkauth', 'disablelongtransactions',
    'enablelongtransactions', 'lockrow', 'unlockrows',
    # Leen tablas o ejecutan SQL pasado como texto
    'query_to_xml', 'query_to_xmlschema', 'query_to_xml_and_xmlschema',
    'cursor_to_xml', 'cursor_to_xmlschema',
    'table_to_xml', 'table_to_xmlschema', 'table_to_xml_and_xmlschema',
    'schema_to_xml', 'schema_to_xmlschema', 'schema_to_xml_and_xmlschema',
    'database_to_xml', 'database_to_xmlschema', 'database_to_xml_and_xmlschema',
    'ts_stat', 'ts_rewrite', 'crosstab', 'crosstab2', 'crosstab3', 'crosstab4', 'connectby',
    # Estado del servidor
    'set_config', 'nextval', 'setval',
}
_FORBIDDEN_PREFIXES = ('pg_', 'lo_', 'dblink', 'postgis_')
_ALLOWED_PG_FUNCTIONS = {'pg_typeof'}
# Funciones de esquema público (PostGIS) o del catálogo; las de otros esquemas pueden ser
# funciones de usuario con efectos.
_ALLOWED_FUNCTION_SCHEMAS = {'public', 'pg_catalog'}

_INPUT_ALIAS = re.compile(r'^input_\d+$', re.IGNORECASE)


def _function_name(node):
    if isinstance(node, exp.Anonymous):
        return str(node.name or '').lower()
    return (node.sql_name() or '').lower()


def _forbidden_function(name):
    if name in _ALLOWED_PG_FUNCTIONS:
        return False
    if name in _FORBIDDEN_FUNCTIONS:
        return True
    return name.startswith(_FORBIDDEN_PREFIXES)


def validate_ai_select(sql_text):
    """
    Valida la estructura del SQL del nodo IA con el parser de PostgreSQL de sqlglot:
    una sola consulta de lectura, solo tablas input_N o CTE propias, sin funciones con efectos.
    Lanza ValueError con un mensaje para el usuario.
    """
    try:
        statements = [s for s in sqlglot.parse(sql_text, read='postgres') if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise ValueError('No se ha podido validar el SQL: %s' % str(exc).splitlines()[0]) from exc
    if len(statements) != 1:
        raise ValueError('Solo se admite una sentencia SQL.')
    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise ValueError('El SQL debe ser una consulta SELECT/WITH.')

    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create,
                             exp.Drop, exp.Alter, exp.Command, exp.Into, exp.Set, exp.Lock)):
            raise ValueError('El SQL solo puede leer datos (SELECT/WITH).')

    cte_names = {str(cte.alias_or_name).lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if isinstance(table.this, exp.Func):
            # Función en FROM (ST_Dump, generate_series…): se valida abajo como función
            continue
        name = str(table.name or '').lower()
        if table.db or table.catalog:
            raise ValueError(
                'El SQL solo puede leer de las entradas del nodo (input_0, input_1…); '
                'no se permite «%s».' % table.sql(dialect='postgres')
            )
        if not (_INPUT_ALIAS.match(name) or name in cte_names):
            raise ValueError(
                'El SQL solo puede leer de las entradas del nodo (input_0, input_1…); '
                'no se permite la tabla «%s».' % name
            )

    for func in tree.find_all(exp.Func):
        name = _function_name(func)
        if _forbidden_function(name):
            raise ValueError('La función %s no está permitida en este nodo.' % name)
        parent = func.parent
        if isinstance(parent, exp.Dot) and parent.expression is func:
            schema = str(parent.this.name if hasattr(parent.this, 'name') else parent.this).lower()
            if schema not in _ALLOWED_FUNCTION_SCHEMAS:
                raise ValueError(
                    'Solo se permiten funciones de PostgreSQL/PostGIS; no %s.%s.' % (schema, name)
                )
    return sql_text


# ---------------------------------------------------------------------------
# Conexiones
# ---------------------------------------------------------------------------

# Claves de parámetros de nodo que contienen el nombre de una Connection
CONNECTION_PARAM_KEYS = ('db', 'db-option', 'api')


def allowed_connection_names(username):
    """
    Nombres de conexión que puede usar el usuario en el ETL (misma regla que el editor).
    None = todas (superusuario).
    """
    from django.contrib.auth.models import User
    from django.db.models import Q
    from gvsigol_auth import auth_backend
    from gvsigol_services.models import Connection, ConnectionRole

    user = User.objects.filter(username=username).first()
    if user is None:
        return set()
    if user.is_superuser:
        return None
    roles = list(auth_backend.get_roles(user) or []) + [user.username]
    role_conn_ids = ConnectionRole.objects.filter(
        role__in=roles, can_use_etl=True,
    ).values_list('connection_id', flat=True)
    return set(Connection.objects.filter(
        Q(allow_all_etl=True) | Q(created_by=user.username) | Q(id__in=role_conn_ids)
    ).values_list('name', flat=True))


def canvas_connection_names(node_params_list, workspace_params=None):
    """Nombres de conexión referenciados por los nodos y por los parámetros del workspace."""
    names = set()
    for params in node_params_list:
        if not isinstance(params, dict):
            continue
        for key in CONNECTION_PARAM_KEYS:
            value = params.get(key)
            if isinstance(value, str) and value.strip():
                names.add(value.strip())
    if isinstance(workspace_params, dict):
        uses_db = bool(workspace_params.get('sql-before')) or bool(workspace_params.get('sql-after')) \
            or workspace_params.get('radio-params-user') == 'postgres'
        value = workspace_params.get('db')
        if uses_db and isinstance(value, str) and value.strip():
            names.add(value.strip())
    return names


def assert_connections_allowed(username, names):
    """PermissionError si el usuario no puede usar alguna de las conexiones."""
    if not names:
        return
    allowed = allowed_connection_names(username)
    if allowed is None:
        return
    denied = sorted(n for n in names if n not in allowed)
    if denied:
        raise PermissionError(
            'El usuario %s no tiene permiso ETL sobre la conexión: %s.' % (username, ', '.join(denied))
        )


# ---------------------------------------------------------------------------
# Tipos de nodo
# ---------------------------------------------------------------------------

_NODE_TYPE = re.compile(r'^(input|trans|output|crea)_[A-Za-z0-9]+$')


def resolve_node_function(module, node_type):
    """Devuelve la función del nodo solo si el tipo es un nodo ETL real del módulo."""
    if not isinstance(node_type, str) or not _NODE_TYPE.match(node_type):
        raise ValueError('Tipo de nodo no válido: %s' % node_type)
    func = getattr(module, node_type, None)
    if not callable(func):
        raise ValueError('Tipo de nodo desconocido: %s' % node_type)
    return func
