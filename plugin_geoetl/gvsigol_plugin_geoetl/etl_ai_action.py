# -*- coding: utf-8 -*-
"""Nodo Procesar datos (trans_AIAction): instrucción libre → SQL/PostGIS bajo contrato E/S."""
import json
import logging
import re
import uuid

import psycopg2
from psycopg2 import sql

from . import etl_ai
from .settings import GEOETL_DB

LOG = logging.getLogger('gvsigol')

MAX_INPUTS = 5
MAX_OUTPUTS = 10
OUTPUT_TYPES = ('text', 'integer', 'double', 'geometry', 'boolean')

_FORBIDDEN = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY|CALL|'
    r'EXECUTE|DO|VACUUM|ANALYZE|CLUSTER|REINDEX|SECURITY|SET\s+ROLE|SET\s+SESSION|'
    r'INTO|PERFORM|NOTIFY|LISTEN|LOAD|pg_sleep|dblink|lo_import|lo_export)\b',
    re.IGNORECASE,
)
_COMMENTS = re.compile(r'/\*.*?\*/|--.*?$', re.DOTALL | re.MULTILINE)

# OID habituales de PostgreSQL → tipos del diálogo
_PG_OID_TYPE = {
    16: 'boolean',
    20: 'integer', 21: 'integer', 23: 'integer',
    700: 'double', 701: 'double', 1700: 'double',
    1042: 'text', 1043: 'text', 25: 'text',
}


def feature_enabled():
    return etl_ai.feature_enabled()


def dedupe_schema_columns(columns):
    """
    Quita placeholders y garantiza nombres únicos (case-insensitive).
    Si hay colisión, renombra a name_2, name_3, …
    """
    out = []
    seen = {}
    for item in columns or []:
        if isinstance(item, str):
            name, col_type = item.strip(), 'text'
        elif isinstance(item, dict):
            name = str(item.get('name') or item.get('column') or '').strip()
            col_type = str(item.get('type') or 'text').strip().lower() or 'text'
        else:
            continue
        if not name or name.lower().startswith('_placeholder'):
            continue
        if col_type not in OUTPUT_TYPES:
            col_type = 'text'
        base = name
        key = base.lower()
        n = seen.get(key, 0) + 1
        seen[key] = n
        if n > 1:
            candidate = '%s_%s' % (base, n)
            while candidate.lower() in seen:
                n += 1
                seen[key] = n
                candidate = '%s_%s' % (base, n)
            name = candidate
            seen[name.lower()] = 1
        out.append({'name': name, 'type': col_type})
    return out


def parse_column_list(value, allow_empty=False):
    """Normaliza una lista [{name, type}, ...] o nombres sueltos."""
    if value in (None, ''):
        value = []
    if isinstance(value, str):
        value = json.loads(value) if value.strip() else []
    if not isinstance(value, list):
        raise ValueError('El esquema de columnas debe ser una lista.')
    raw = []
    for item in value:
        if isinstance(item, str):
            name, col_type = item.strip(), 'text'
        elif isinstance(item, dict):
            name = str(item.get('name') or '').strip()
            col_type = str(item.get('type') or 'text').strip().lower() or 'text'
        else:
            raise ValueError('Cada columna de salida debe tener name y type.')
        if not name or name.lower().startswith('_placeholder'):
            continue
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
            raise ValueError('Nombre de columna no válido: %s' % name)
        if col_type not in OUTPUT_TYPES:
            raise ValueError('Tipo de columna no válido: %s' % col_type)
        raw.append({'name': name, 'type': col_type})
    out = dedupe_schema_columns(raw)
    if not out and not allow_empty:
        raise ValueError('Define al menos una columna de salida.')
    return out


def parse_output_schema(value, allow_empty=False):
    """Compat: un solo esquema (lista plana de columnas)."""
    if _looks_like_multi_schemas(value):
        # Si llega multi, usa el primero
        blocks = value if isinstance(value, list) else []
        first = blocks[0] if blocks else []
        return parse_column_list(first, allow_empty=allow_empty)
    return parse_column_list(value, allow_empty=allow_empty)


def _looks_like_multi_schemas(value):
    """True si value es [[cols], [cols], ...] (esquema por salida)."""
    if not isinstance(value, list) or not value:
        return False
    first = value[0]
    if isinstance(first, list):
        return True
    if isinstance(first, dict) and (
        'columns' in first or (first.get('name') is None and 'schema' in first)
    ):
        return True
    return False


def parse_output_schemas(value, outputs_count, allow_empty=False):
    """
    Normaliza a una lista de longitud outputs_count.
    Acepta lista plana (legacy → se copia a todas las salidas) o lista de listas.
    """
    outputs_count = max(1, int(outputs_count or 1))
    if value in (None, ''):
        value = []
    if isinstance(value, str):
        value = json.loads(value) if value.strip() else []

    blocks = []
    if _looks_like_multi_schemas(value):
        for item in value:
            if isinstance(item, dict) and 'columns' in item:
                blocks.append(parse_column_list(item.get('columns') or [], allow_empty=True))
            else:
                blocks.append(parse_column_list(item or [], allow_empty=True))
    else:
        single = parse_column_list(value, allow_empty=True)
        # Legacy: el mismo contrato en todas las salidas
        blocks = [list(single) for _ in range(outputs_count)] if single else []

    while len(blocks) < outputs_count:
        # Nuevas salidas parten vacías (el diálogo puede rellenarlas)
        blocks.append([])
    blocks = blocks[:outputs_count]

    if not allow_empty:
        for index, cols in enumerate(blocks):
            if not cols:
                raise ValueError(
                    'Define al menos una columna en la salida %s.' % (index + 1)
                )
    return blocks


def _count(dicc, key, maximum, label):
    try:
        value = int(dicc.get(key) or 1)
    except (TypeError, ValueError):
        raise ValueError('%s debe ser un entero entre 1 y %s.' % (label, maximum))
    if value < 1 or value > maximum:
        raise ValueError('%s debe estar entre 1 y %s.' % (label, maximum))
    return value


def infer_outputs_count(instruction, declared=1):
    """
    Si la instrucción pide N salidas explícitamente, usa al menos ese N.
    No baja el valor declarado en el diálogo.
    """
    try:
        declared = max(1, int(declared or 1))
    except (TypeError, ValueError):
        declared = 1
    text = (instruction or '').strip().lower()
    if not text:
        return min(declared, MAX_OUTPUTS)

    patterns = [
        # "dos/2/tres… salidas" o "outputs"
        r'\b(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+)\s+salidas?\b',
        r'\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+outputs?\b',
        # "da como resultado dos salidas"
        r'\b(?:resultado|result|con)\s+(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|\d+)\s+salidas?\b',
        # "salida 1 … salida 2" → al menos 2
        r'\bsalida\s*2\b',
        r'\boutput\s*2\b',
        r'\buna\s+con\b.+\by\s+otra\s+con\b',
        r'\bone\s+with\b.+\band\s+(?:another|the\s+other)\s+with\b',
    ]
    word_map = {
        'dos': 2, 'two': 2, 'tres': 3, 'three': 3, 'cuatro': 4, 'four': 4,
        'cinco': 5, 'five': 5, 'seis': 6, 'six': 6, 'siete': 7, 'seven': 7,
        'ocho': 8, 'eight': 8, 'nueve': 9, 'nine': 9, 'diez': 10, 'ten': 10,
    }
    inferred = 1
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        if pattern.startswith(r'\bsalida') or pattern.startswith(r'\boutput') or 'una\\s+con' in pattern or 'one\\s+with' in pattern:
            inferred = max(inferred, 2)
            continue
        token = match.group(1).lower()
        if token.isdigit():
            inferred = max(inferred, int(token))
        else:
            inferred = max(inferred, word_map.get(token, 1))

    return max(1, min(MAX_OUTPUTS, max(declared, inferred)))


def parse_sqls(dicc, outputs_count, allow_empty=False):
    """
    Una sentencia SELECT/WITH por salida.
    Acepta sqls=[...] o sql='...' (legacy: un solo SQL compartido → se replica).
    """
    outputs_count = max(1, int(outputs_count or 1))
    raw_list = dicc.get('sqls')
    if isinstance(raw_list, str):
        try:
            raw_list = json.loads(raw_list) if raw_list.strip() else []
        except (TypeError, ValueError):
            raw_list = [raw_list]
    if isinstance(raw_list, list) and raw_list:
        sqls = [(s or '').strip() if isinstance(s, str) else '' for s in raw_list]
    else:
        single = (dicc.get('sql') or '').strip()
        sqls = [single] if single else []

    while len(sqls) < outputs_count:
        # Legacy: un SQL sirve a todas las salidas (proyección de columnas)
        sqls.append(sqls[0] if sqls else '')
    sqls = sqls[:outputs_count]

    if not allow_empty:
        for index, text in enumerate(sqls):
            if not text:
                raise ValueError(
                    'Falta el SQL de la salida %s. Pulsa Generar y revísalo.'
                    % (index + 1)
                )
            sanitize_sql(text)
    return sqls


def check_params(dicc, for_run=True):
    """Valida parámetros. for_run=True exige instrucción, SQL y columnas (ejecución)."""
    inputs_count = _count(dicc, 'inputs_count', MAX_INPUTS, 'inputs_count')
    outputs_count = _count(dicc, 'outputs_count', MAX_OUTPUTS, 'outputs_count')
    instruction = (dicc.get('instruction') or '').strip()
    raw_schema = dicc.get('output_schemas')
    if raw_schema in (None, ''):
        raw_schema = dicc.get('output_schema')
    output_schemas = parse_output_schemas(raw_schema, outputs_count, allow_empty=not for_run)
    sqls = parse_sqls(dicc, outputs_count, allow_empty=not for_run)
    sql_text = sqls[0] if sqls else ''
    if for_run:
        if not instruction:
            raise ValueError('Indica la instrucción en lenguaje natural.')
        if not any(sqls):
            raise ValueError('Falta el SQL. Pulsa Generar y revísalo antes de ejecutar.')
        for index, cols in enumerate(output_schemas):
            if not cols:
                raise ValueError('Define al menos una columna en la salida %s.' % (index + 1))
    return inputs_count, outputs_count, instruction, output_schemas, sql_text, sqls


def sanitize_sql(sql_text):
    text = (sql_text or '').strip().rstrip(';').strip()
    if not text:
        raise ValueError('El SQL está vacío.')
    cleaned = _COMMENTS.sub(' ', text)
    if ';' in cleaned:
        raise ValueError('Solo se admite una sentencia SQL (sin ;).')
    if _FORBIDDEN.search(cleaned):
        raise ValueError('El SQL solo puede ser un SELECT/WITH sobre las entradas del nodo.')
    head = cleaned.lstrip().lower()
    if not (head.startswith('select') or head.startswith('with')):
        raise ValueError('El SQL debe empezar por SELECT o WITH.')
    return text


def _input_aliases(inputs_count):
    return ['input_%s' % i for i in range(inputs_count)]


def assert_only_input_aliases(sql_text, inputs_count):
    """Avisa si aparecen input_N fuera del rango; no intenta parsear todo el SQL."""
    found = set(re.findall(r'\binput_(\d+)\b', sql_text, flags=re.IGNORECASE))
    allowed = {str(i) for i in range(inputs_count)}
    extra = sorted(found - allowed, key=int)
    if extra:
        raise ValueError(
            'El SQL usa entradas no declaradas (%s). Solo input_0…input_%s.'
            % (', '.join('input_' + n for n in extra), inputs_count - 1)
        )


def bind_sql(sql_text, table_names, schema=None):
    """Sustituye input_i por schema.tabla real (identificadores entrecomillados)."""
    schema = schema or GEOETL_DB['schema']
    bound = sanitize_sql(sql_text)
    assert_only_input_aliases(bound, len(table_names))
    for index, table in enumerate(table_names):
        alias = 'input_%s' % index
        qualified = '"%s"."%s"' % (
            schema.replace('"', '""'), str(table).replace('"', '""'),
        )
        bound = re.sub(r'\b' + re.escape(alias) + r'\b', qualified, bound, flags=re.IGNORECASE)
    return bound


def _connect():
    return psycopg2.connect(
        user=GEOETL_DB['user'], password=GEOETL_DB['password'],
        host=GEOETL_DB['host'], port=GEOETL_DB['port'], database=GEOETL_DB['database'],
    )


def _pg_type(col_type):
    return {
        'text': 'text',
        'integer': 'bigint',
        'double': 'double precision',
        'boolean': 'boolean',
        'geometry': 'geometry',
    }.get(col_type, 'text')


def _type_from_oid(type_code, name=''):
    mapped = _PG_OID_TYPE.get(type_code)
    if mapped:
        return mapped
    lower = (name or '').lower()
    if 'geom' in lower or lower.endswith('wkt'):
        return 'geometry'
    return 'text'


def dry_run_columns(sql_text, input_schemas, schema=None):
    """Compat: solo nombres de columnas del SELECT."""
    return [c['name'] for c in dry_run_schema(sql_text, input_schemas, schema=schema)]


def dry_run_schema(sql_text, input_schemas, schema=None):
    """Crea tablas temporales vacías y devuelve [{name, type}, ...] del SELECT."""
    schema = schema or GEOETL_DB['schema']
    inputs_count = len(input_schemas)
    sanitize_sql(sql_text)
    assert_only_input_aliases(sql_text, inputs_count)

    # Sufijo único: varias sugerencias en paralelo no pueden compartir _ai_action_in_0
    run_id = uuid.uuid4().hex[:12]
    conn = _connect()
    conn.autocommit = True
    cur = conn.cursor()
    temp_names = []
    try:
        for index, columns in enumerate(input_schemas):
            name = '_ai_action_in_%s_%s' % (index, run_id)
            temp_names.append(name)
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
                sql.Identifier(schema), sql.Identifier(name)))
            if not columns:
                # Nombre único por entrada para que a.* / b.* no choquen en el dry-run
                cols_sql = sql.SQL('{} text').format(
                    sql.Identifier('_placeholder_%s' % index))
            else:
                parts = []
                for col in columns:
                    if isinstance(col, dict):
                        col_name = col.get('name') or col.get('column')
                        col_type = _pg_type(str(col.get('type') or 'text').lower())
                    else:
                        col_name, col_type = str(col), 'text'
                    if not col_name:
                        continue
                    parts.append(sql.SQL('{} {}').format(sql.Identifier(col_name), sql.SQL(col_type)))
                if not parts:
                    parts = [sql.SQL('{} text').format(
                        sql.Identifier('_placeholder_%s' % index))]
                cols_sql = sql.SQL(', ').join(parts)
            cur.execute(sql.SQL('CREATE TABLE {}.{} ({})').format(
                sql.Identifier(schema), sql.Identifier(name), cols_sql))

        bound = bind_sql(sql_text, temp_names, schema=schema)
        cur.execute('SELECT * FROM (%s) AS _ai_action_probe LIMIT 0' % bound)
        result = []
        for desc in cur.description or []:
            result.append({
                'name': desc[0],
                'type': _type_from_oid(desc[1], desc[0]),
            })
        # Sin nombres repetidos ni placeholders internos del dry-run
        return dedupe_schema_columns(result)
    finally:
        for name in temp_names:
            try:
                cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
                    sql.Identifier(schema), sql.Identifier(name)))
            except Exception:
                pass
        cur.close()
        conn.close()


def suggest_schema_from_sql(sql_text, input_schemas):
    """Infiere el esquema de salida a partir del SQL (dry-run)."""
    if not input_schemas:
        raise ValueError('Hace falta el esquema de al menos una entrada.')
    if len(input_schemas) > MAX_INPUTS:
        raise ValueError('Como máximo %s entradas.' % MAX_INPUTS)
    try:
        cols = dry_run_schema(sql_text, input_schemas)
    except psycopg2.Error as exc:
        raise ValueError('No se ha podido analizar el SQL: %s' % (exc.diag.message_primary or exc)) from exc
    if not cols:
        raise ValueError('El SQL no ha devuelto columnas.')
    return cols


_SUGGEST_SCHEMAS_SYSTEM = (
    'Eres un asistente de esquemas ETL PostgreSQL/PostGIS. '
    'Devuelves SOLO un JSON '
    '{"outputs_count":N,"output_schemas":[[{"name":"...","type":"text|integer|double|geometry|boolean"},...],...]} '
    'con exactamente N listas de columnas (una por salida). '
    'La instrucción en lenguaje natural manda: si pide varias salidas, N>1. '
    'No inventes columnas de entrada; sí puedes proponer columnas calculadas que pida la instrucción. '
    'Tipos válidos en este JSON de UI: text, integer, double, geometry, boolean '
    '(geometry = columna espacial; el SQL tipará Point/LineString/Polygon/… + EPSG aparte). '
    'Si la instrucción no fija columnas, parte del esquema de entrada conservando lo útil.'
)


_COUNT_WORD_MAP = {
    'dos': 2, 'two': 2, 'tres': 3, 'three': 3, 'cuatro': 4, 'four': 4,
    'cinco': 5, 'five': 5, 'seis': 6, 'six': 6, 'siete': 7, 'seven': 7,
    'ocho': 8, 'eight': 8, 'nueve': 9, 'nine': 9, 'diez': 10, 'ten': 10,
}


def _count_token(token):
    token = (token or '').lower()
    if token.isdigit():
        return int(token)
    return _COUNT_WORD_MAP.get(token, 0)


def parse_inputs_from_instruction(instruction):
    """
    Devuelve N si la instrucción implica N entradas; 0 si no lo deja claro.
    p. ej. «join de dos tablas», «unir tres capas», «2 entradas».
    """
    text = (instruction or '').strip().lower()
    if not text:
        return 0
    inferred = 0
    match = re.search(
        r'\b(dos|tres|cuatro|cinco|two|three|four|five|\d+)\s+'
        r'(tablas?|entradas?|inputs?|capas?|layers?|datasets?|fuentes?)\b',
        text,
    )
    if match:
        inferred = max(inferred, _count_token(match.group(1)))
    if re.search(
        r'\b(join|inner\s+join|left\s+join|right\s+join|full\s+join|'
        r'uni[oó]n|unir|cruzar|combinar|merge|emparejar|relacionar)\b',
        text,
    ):
        inferred = max(inferred, 2)
    if re.search(r'\binput[_\s-]*2\b', text) or re.search(r'\bentrada\s*2\b', text):
        inferred = max(inferred, 2)
    if inferred < 1:
        return 0
    return min(MAX_INPUTS, inferred)


def parse_outputs_from_instruction(instruction):
    """Devuelve N si la instrucción pide N salidas; 0 si no lo deja claro."""
    text = (instruction or '').strip().lower()
    if not text:
        return 0
    inferred = 0
    match = re.search(
        r'\b(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+salidas?\b',
        text,
    ) or re.search(
        r'\b(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+outputs?\b',
        text,
    )
    if match:
        inferred = _count_token(match.group(1))
    if (
        re.search(r'\bsalida\s*2\b', text)
        or re.search(r'\boutput\s*2\b', text)
        or re.search(r'una\s+con[\s\S]+y\s+otra\s+con', text)
        or re.search(r'one\s+with[\s\S]+and\s+(?:another|the\s+other)\s+with', text)
    ):
        inferred = max(inferred, 2)
    # Un join / unión típico produce una sola tabla de resultado
    if inferred < 1 and parse_inputs_from_instruction(instruction) >= 2:
        if re.search(
            r'\b(join|inner\s+join|left\s+join|right\s+join|full\s+join|'
            r'uni[oó]n|unir|cruzar|combinar|merge)\b',
            text,
        ):
            inferred = 1
    if inferred < 1:
        return 0
    return min(MAX_OUTPUTS, inferred)


def input_schemas_have_columns(input_schemas):
    """True si algún bloque de entrada trae al menos una columna con nombre."""
    for block in input_schemas or []:
        if isinstance(block, dict):
            cols = block.get('columns') or []
        else:
            cols = block
        for col in cols or []:
            if isinstance(col, dict):
                name = col.get('name') or col.get('column')
            else:
                name = col
            if name:
                return True
    return False


def count_outputs_from_sqls(sqls):
    """Cuenta SELECTs no vacíos con texto distinto (ignora copias idénticas)."""
    seen = set()
    for raw in sqls or []:
        text = (raw or '').strip()
        if not text:
            continue
        key = re.sub(r'\s+', ' ', text).lower()
        seen.add(key)
    return min(MAX_OUTPUTS, len(seen))


def suggest_schemas_from_instruction(instruction, input_schemas, outputs_count=None, invoke=None):
    """
    Propone outputs_count + output_schemas a partir de la instrucción (sin generar SQL).
    """
    instruction = (instruction or '').strip()
    if not instruction:
        raise ValueError('Indica la instrucción en lenguaje natural.')
    if not input_schemas:
        raise ValueError('Hace falta el esquema de al menos una entrada.')
    if len(input_schemas) > MAX_INPUTS:
        raise ValueError('Como máximo %s entradas.' % MAX_INPUTS)

    try:
        declared = int(outputs_count) if outputs_count is not None else 1
    except (TypeError, ValueError):
        declared = 1
    declared = max(1, min(MAX_OUTPUTS, declared))
    from_instr = parse_outputs_from_instruction(instruction)
    target = from_instr or declared

    aliases = _normalize_input_aliases(input_schemas)
    invoke = invoke or etl_ai.model_invoker()
    user = json.dumps({
        'instruction': instruction,
        'inputs': aliases,
        'outputs_count_hint': target,
    }, ensure_ascii=False)
    raw = etl_ai._content_text(invoke(_SUGGEST_SCHEMAS_SYSTEM, user)).strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
    start, end = raw.find('{'), raw.rfind('}')
    data = {}
    if start != -1 and end > start:
        try:
            data = json.loads(raw[start:end + 1])
        except ValueError:
            data = {}
    if not isinstance(data, dict):
        data = {}

    try:
        model_count = int(data.get('outputs_count') or target)
    except (TypeError, ValueError):
        model_count = target
    model_count = max(1, min(MAX_OUTPUTS, model_count))
    if from_instr:
        model_count = max(model_count, from_instr)

    raw_schemas = data.get('output_schemas')
    if not isinstance(raw_schemas, list) or not raw_schemas:
        single = data.get('output_schema')
        raw_schemas = [single] if single else []
    schemas = parse_output_schemas(raw_schemas, model_count, allow_empty=True)
    if not any(schemas):
        # Fallback: copiar esquema de la primera entrada a cada salida
        base = []
        for col in (input_schemas[0] or []):
            if isinstance(col, dict):
                name = col.get('name') or col.get('column')
                if name:
                    base.append({'name': name, 'type': str(col.get('type') or 'text')})
            else:
                base.append({'name': str(col), 'type': 'text'})
        if not base:
            raise ValueError('No se han podido sugerir esquemas desde la instrucción.')
        schemas = [list(base) for _ in range(model_count)]
    return model_count, schemas


def assert_columns_match(actual, output_schema):
    expected = [col['name'] for col in output_schema]
    actual_list = list(actual or [])
    if [c.lower() for c in actual_list] != [c.lower() for c in expected]:
        raise ValueError(
            'Las columnas del SQL no coinciden con el contrato de salida.\n'
            'Esperado: %s\nObtenido: %s' % (', '.join(expected), ', '.join(actual_list) or '(ninguna)')
        )


def assert_columns_subset(actual, output_schema, label='salida'):
    """Cada columna del contrato debe existir en el resultado SQL."""
    actual_lower = {str(c).lower(): c for c in (actual or [])}
    missing = [col['name'] for col in output_schema if col['name'].lower() not in actual_lower]
    if missing:
        raise ValueError(
            'En la %s faltan columnas del SQL: %s.\nDisponibles: %s'
            % (label, ', '.join(missing), ', '.join(actual) or '(ninguna)')
        )


def _normalize_input_aliases(input_schemas):
    aliases = []
    for index, columns in enumerate(input_schemas):
        cols = []
        for col in columns or []:
            if isinstance(col, dict):
                name = col.get('name') or col.get('column')
                if name:
                    cols.append({'name': name, 'type': str(col.get('type') or 'text')})
            else:
                cols.append({'name': str(col), 'type': 'text'})
        aliases.append({'alias': 'input_%s' % index, 'columns': cols})
    return aliases


# Reglas PostGIS para el SQL generado (evitar geometry genérica sin SRID/tipo)
_GEOMETRY_SQL_RULES = (
    'GEOMETRÍA (obligatorio si hay geom/wkb_geometry o ST_*): '
    'NUNCA dejes el tipo GEOMETRY/geometry sin tipar. Toda geometría en el SELECT debe '
    'llevar tipo concreto y EPSG según lo que sea (puntos, líneas, polígonos, multi-…), '
    'p. ej. geometry(Point,4326), geometry(LineString,25830), geometry(MultiLineString,25830), '
    'geometry(Polygon,4326), geometry(MultiPolygon,25830). '
    'Elige el tipo que corresponda a la instrucción/entrada; MultiPolygon es solo un ejemplo. '
    'Si proyectas wkb_geometry de la entrada, conserva su tipología y SRID '
    '(ST_SetSRID / ST_Transform / ::geometry(Tipo,EPSG) solo si el EPSG es conocido). '
    'Si construyes o transformas geometría y conoces tipo+EPSG, termina con cast tipado '
    '(…)::geometry(Tipo,EPSG) AS wkb_geometry. Si la instrucción no fija EPSG, reutiliza el '
    'de la entrada. Si el EPSG NO se conoce: NO inventes ninguno (ni 4326 ni otro); tipa solo '
    'la tipología cuando se sepa (p. ej. ::geometry(Point)) o proyecta la geom tal cual, '
    'sin ST_SetSRID/ST_Transform con un código inventado. '
    'Prefiere el nombre wkb_geometry cuando exista en la entrada. '
)


def build_generate_messages(instruction, input_schemas, output_schema=None,
                            outputs_count=1, output_schemas=None):
    aliases = _normalize_input_aliases(input_schemas)
    outputs_count = max(1, int(outputs_count or 1))
    if output_schemas is not None:
        blocks = parse_output_schemas(output_schemas, outputs_count, allow_empty=True)
    else:
        single = parse_column_list(output_schema, allow_empty=True)
        blocks = [list(single) for _ in range(outputs_count)] if single else [[] for _ in range(outputs_count)]
    hints = [[{'name': c['name'], 'type': c['type']} for c in block] for block in blocks]

    if outputs_count > 1:
        system = (
            'Eres un generador de SQL PostgreSQL/PostGIS para un nodo ETL con VARIAS SALIDAS. '
            'Devuelves SOLO un JSON {"sqls":["SELECT…","SELECT…",…]} con exactamente %s sentencias '
            '(una por salida, en orden). Cada elemento es un SELECT o WITH independiente sobre las '
            'mismas tablas input_0, input_1, …. '
            'Cada salida puede tener FILAS distintas (filtros, JOIN vs anti-JOIN, etc.) y COLUMNAS '
            'distintas: eso es lo esperado. '
            'NUNCA empaquetes varias salidas en un solo SELECT con jsonb_agg, arrays, ni columnas '
            'que sean resultados anidados; cada salida debe ser una tabla relacional plana. '
            'Si la instrucción pide un INNER JOIN en una salida y los no unidos en otra, genera '
            'p. ej. SELECT a.*, b.* (o columnas con alias) para la primera, y '
            'SELECT a.* WHERE NOT EXISTS (…) para la segunda. '
            'JOIN: el campo común (p. ej. ID) va en el ON, NO limites el SELECT a solo esa clave. '
            'Si no conoces el esquema, proyecta todas las columnas sin duplicar la clave del JOIN, '
            'p. ej. SELECT a.*, b.* EXCLUDE ("ID") FROM input_0 AS a INNER JOIN input_1 AS b '
            'ON a."ID" = b."ID" (ajusta el nombre de la clave). Si sí conoces columnas y hay '
            'nombres repetidos, enumera con alias únicos; no uses «b.* AS algo» (inválido). '
            'La instrucción en lenguaje natural es la prioridad. '
            'output_schemas_hint es solo una pista por salida (puede estar vacía). '
            'No uses INSERT/UPDATE/DELETE/DROP/CREATE/INTO ni otras tablas. '
            'No inventes tablas ni columnas de entrada; sí puedes calcular columnas nuevas. '
            + _GEOMETRY_SQL_RULES
        ) % outputs_count
        user = json.dumps({
            'instruction': instruction,
            'inputs': aliases,
            'outputs_count': outputs_count,
            'output_schemas_hint': hints,
        }, ensure_ascii=False)
    else:
        system = (
            'Eres un generador de SQL PostgreSQL/PostGIS para un nodo ETL. '
            'Devuelves SOLO un JSON {"sql":"..."} con una única sentencia SELECT o WITH. '
            'Las únicas tablas permitidas son los alias input_0, input_1, … indicados. '
            'La instrucción en lenguaje natural es la prioridad: impleméntala con expresiones SQL reales '
            '(sumas, concatenaciones, ST_*, CASE, JOINs, etc.). Si pide un atributo nuevo (p. ej. id10 = id + 10), '
            'DEBE aparecer en el SELECT con ese alias y el cálculo; no te limites a proyectar columnas. '
            'JOIN de varias entradas: el campo común (p. ej. ID) sirve para el ON. '
            'Por defecto proyecta TODAS las columnas de las tablas unidas, no solo la clave, '
            'y NO repitas la clave del JOIN dos veces. '
            'Si el esquema de entrada está vacío o desconocido, genera algo del estilo '
            'SELECT a.*, b.* EXCLUDE ("ID") FROM input_0 AS a INNER JOIN input_1 AS b '
            'ON a."ID" = b."ID" (ajustando alias/nombre de clave a la instrucción; '
            'EXCLUDE es PostgreSQL). No uses «b.* AS "ID"» (inválido). '
            'Si conoces columnas y hay nombres repetidos entre tablas, enumera con alias únicos '
            '(a.id AS id, b.nombre AS nombre_b, …) dejando una sola copia de la clave. '
            'output_schema es solo una pista: puedes añadir columnas que pida la instrucción y, '
            'si no dice lo contrario, conservar el resto. '
            'No conviertas todo a ::text sin necesidad; usa el tipo adecuado (enteros, double, …). '
            'No uses INSERT/UPDATE/DELETE/DROP/CREATE/INTO ni otras tablas. '
            'No inventes tablas ni columnas de entrada que no existan; sí puedes calcular columnas nuevas. '
            + _GEOMETRY_SQL_RULES
        )
        user = json.dumps({
            'instruction': instruction,
            'inputs': aliases,
            'output_schema_hint': hints[0] if hints else [],
        }, ensure_ascii=False)
    return system, user


def parse_generated_sql(content):
    """Compat: extrae un único SQL (primer elemento si viene sqls)."""
    sqls = parse_generated_sqls(content, outputs_count=1)
    return sqls[0]


def parse_generated_sqls(content, outputs_count=1):
    """Parsea {"sql":"..."} o {"sqls":["...","..."]} → lista de longitud outputs_count."""
    outputs_count = max(1, int(outputs_count or 1))
    text = etl_ai._content_text(content).strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json|sql)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    sqls = []
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if isinstance(data.get('sqls'), list) and data['sqls']:
                sqls = [sanitize_sql(str(s)) for s in data['sqls'] if str(s).strip()]
            elif data.get('sql'):
                sqls = [sanitize_sql(str(data['sql']))]
    except json.JSONDecodeError:
        pass
    if not sqls and text.lstrip().lower().startswith(('select', 'with')):
        sqls = [sanitize_sql(text)]
    if not sqls:
        raise ValueError(
            'El modelo no ha devuelto un JSON {"sql":"..."} o {"sqls":[...]} válido.'
        )
    if len(sqls) < outputs_count:
        raise ValueError(
            'Se esperaban %s SQL (uno por salida) y el modelo devolvió %s. '
            'Vuelve a Generar; cada salida necesita su propio SELECT.'
            % (outputs_count, len(sqls))
        )
    return sqls[:outputs_count]


def generate_sql(instruction, input_schemas, output_schema=None, invoke=None,
                 outputs_count=1, output_schemas=None):
    """
    Genera SQL priorizando la instrucción.
    Devuelve (sql_text_o_lista, schema_o_lista_de_schemas).
    Con outputs_count==1: (str, [{name,type},…]).
    Con outputs_count>1: (list[str], list[list[{name,type}]]).
    Los esquemas de entrada pueden ir vacíos (solo stubs): el SQL se genera igual;
    el dry-run puede devolver esquema vacío sin fallar.
    """
    outputs_count = max(1, int(outputs_count or 1))
    if not (instruction or '').strip():
        raise ValueError('Indica la instrucción en lenguaje natural.')
    if input_schemas is None:
        input_schemas = []
    if not isinstance(input_schemas, list):
        raise ValueError('Hace falta el esquema de al menos una entrada.')
    if len(input_schemas) < 1:
        input_schemas = [[]]
    if len(input_schemas) > MAX_INPUTS:
        raise ValueError('Como máximo %s entradas.' % MAX_INPUTS)
    if outputs_count > MAX_OUTPUTS:
        raise ValueError('Como máximo %s salidas.' % MAX_OUTPUTS)

    has_real_columns = input_schemas_have_columns(input_schemas)
    invoke = invoke or etl_ai.model_invoker()
    system, user = build_generate_messages(
        instruction, input_schemas, output_schema=output_schema,
        outputs_count=outputs_count, output_schemas=output_schemas,
    )
    raw = invoke(system, user)
    sqls = parse_generated_sqls(raw, outputs_count=outputs_count)
    result_schemas = []
    for index, sql_text in enumerate(sqls):
        assert_only_input_aliases(sql_text, len(input_schemas))
        try:
            result_schema = dry_run_schema(sql_text, input_schemas)
        except Exception:
            if has_real_columns:
                raise
            result_schema = []
        if not result_schema and has_real_columns:
            raise ValueError(
                'El SQL de la salida %s no ha devuelto columnas.' % (index + 1)
            )
        result_schemas.append(result_schema or [])

    if outputs_count == 1:
        return sqls[0], result_schemas[0]
    return sqls, result_schemas


def _output_table_name(target, index):
    return target if index == 0 else '%s_o%s' % (target, index)


def _materialize_output(cur, conn, schema, out_name, bound, out_schema, label):
    staging = '%s_ai_tmp' % out_name
    cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
        sql.Identifier(schema), sql.Identifier(staging)))
    cur.execute(sql.SQL('CREATE TABLE {}.{} AS ({})').format(
        sql.Identifier(schema), sql.Identifier(staging), sql.SQL(bound)))
    conn.commit()
    cur.execute(sql.SQL('SELECT * FROM {}.{} LIMIT 0').format(
        sql.Identifier(schema), sql.Identifier(staging)))
    actual = [d[0] for d in cur.description or []]
    assert_columns_subset(actual, out_schema, label=label)
    col_sql = sql.SQL(', ').join(sql.Identifier(col['name']) for col in out_schema)
    cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
        sql.Identifier(schema), sql.Identifier(out_name)))
    cur.execute(sql.SQL('CREATE TABLE {}.{} AS SELECT {} FROM {}.{}').format(
        sql.Identifier(schema), sql.Identifier(out_name),
        col_sql,
        sql.Identifier(schema), sql.Identifier(staging)))
    conn.commit()
    cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
        sql.Identifier(schema), sql.Identifier(staging)))
    conn.commit()


def trans_AIAction(dicc):
    if not feature_enabled():
        raise ValueError(
            'El nodo SQL con IA está desactivado en esta instalación '
            '(ETL_AI_NODES_ENABLED o plugin GeoCopilot no disponible).'
        )
    inputs_count, outputs_count, _instruction, output_schemas, _sql_text, sqls = check_params(
        dicc, for_run=True
    )

    tables = list(dicc.get('data') or [])
    if len(tables) < inputs_count:
        raise ValueError(
            'Faltan entradas conectadas: se declararon %s y llegan %s.'
            % (inputs_count, len(tables))
        )
    tables = tables[:inputs_count]

    schema = GEOETL_DB['schema']
    target = dicc['id']
    unique_sqls = list({s for s in sqls})
    shared_sql = unique_sqls[0] if len(unique_sqls) == 1 else None

    conn = _connect()
    cur = conn.cursor()
    results = []
    try:
        if shared_sql is not None and outputs_count > 1:
            # Legacy: un SQL → staging compartido → proyección por salida
            bound = bind_sql(shared_sql, tables, schema=schema)
            staging = '%s_ai_src' % target
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
                sql.Identifier(schema), sql.Identifier(staging)))
            cur.execute(sql.SQL('CREATE TABLE {}.{} AS ({})').format(
                sql.Identifier(schema), sql.Identifier(staging), sql.SQL(bound)))
            conn.commit()
            cur.execute(sql.SQL('SELECT * FROM {}.{} LIMIT 0').format(
                sql.Identifier(schema), sql.Identifier(staging)))
            actual = [d[0] for d in cur.description or []]
            for index, out_schema in enumerate(output_schemas):
                assert_columns_subset(actual, out_schema, label='salida %s' % (index + 1))
                out_name = _output_table_name(target, index)
                col_sql = sql.SQL(', ').join(
                    sql.Identifier(col['name']) for col in out_schema
                )
                cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
                    sql.Identifier(schema), sql.Identifier(out_name)))
                cur.execute(sql.SQL('CREATE TABLE {}.{} AS SELECT {} FROM {}.{}').format(
                    sql.Identifier(schema), sql.Identifier(out_name),
                    col_sql,
                    sql.Identifier(schema), sql.Identifier(staging)))
                conn.commit()
                results.append(out_name)
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(
                sql.Identifier(schema), sql.Identifier(staging)))
            conn.commit()
        else:
            for index, (out_schema, sql_text) in enumerate(zip(output_schemas, sqls)):
                bound = bind_sql(sql_text, tables, schema=schema)
                out_name = _output_table_name(target, index)
                _materialize_output(
                    cur, conn, schema, out_name, bound, out_schema,
                    label='salida %s' % (index + 1),
                )
                results.append(out_name)
    finally:
        cur.close()
        conn.close()

    LOG.info(
        'trans_AIAction: %s salida(s), columnas=%s, sqls=%s',
        outputs_count,
        [len(s) for s in output_schemas],
        len(unique_sqls),
    )
    return results
