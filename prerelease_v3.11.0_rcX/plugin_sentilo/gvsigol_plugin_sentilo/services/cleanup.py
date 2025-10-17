from typing import List, Tuple
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from gvsigol_plugin_sentilo.settings import SENTILO_DB, CLEAN_OUTPUT_MODE, CLEAN_OUTPUT_SUFFIX, SENTILO_SCHEMA

LOGGER = logging.getLogger('gvsigol')

SUM_TYPES = {'TrafficFlowObserved', 'WifiBluDetector', 'PeopleCounter'}
AVG_TYPES = {'AirQualityObserved', 'NoiseLevelObserved', 'WeatherObserved', 'OnStreetParking'}


def _normalize_datetime(dt):
    """
    Normaliza datetime object para eliminar timezone info y trabajar solo con naive datetimes.
    Esto evita problemas de comparación entre offset-aware y offset-naive.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    # Verificar si es un objeto datetime
    if not isinstance(dt, datetime):
        return dt
    # Si el datetime tiene timezone info, la removemos para trabajar con naive datetimes
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _get_engine() -> Engine:
    conn_string = f"postgresql://{SENTILO_DB['user']}:{SENTILO_DB['password']}@{SENTILO_DB['host']}:{SENTILO_DB['port']}/{SENTILO_DB['database']}"
    return create_engine(conn_string)


def _get_columns(engine: Engine, schema: str, table: str) -> List[Tuple[str, str]]:
    # Returns list of (column_name, data_type)
    query = text(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table
        ORDER BY ordinal_position
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"schema": schema, "table": table}).fetchall()
    return [(r[0], r[1]) for r in rows]


def _build_numeric_expr(col_name: str, data_type: str) -> str:
    # Returns SQL expr that yields double precision numeric value, treating NULL/NaN as 0
    # If column type is textual, attempt to parse numbers like "57,4" or "57.4"
    if data_type in {"double precision", "real", "integer", "bigint", "numeric"}:
        # Handle NULL and NaN values by converting them to 0
        return f"COALESCE(NULLIF({col_name}, 'NaN'::double precision), 0)::double precision"
    # heuristic: treat names ending with _value as numeric-like even if text
    return (
        f"COALESCE("
        f"CASE WHEN {col_name} ~ '^-?[0-9]+([\\.,][0-9]+)?$' "
        f"THEN REPLACE({col_name}::text, ',', '.')::double precision "
        f"ELSE NULL END, 0)"
    )


def _build_text_expr(col_name: str) -> str:
    # For text fields in aggregation, choose MAX as representative value
    return f"MAX({col_name}) AS {col_name}"


def _build_agg_select(schema: str, table: str, cols: List[Tuple[str, str]], where_clause: str = "") -> Tuple[str, List[str]]:
    # Returns full SELECT aggregation SQL and list of output columns
    bucket_expr = "date_trunc('hour', observation_time) AS observation_time"
    select_parts: List[str] = ["component", "tipo", bucket_expr]
    output_columns: List[str] = ["component", "tipo", "observation_time"]

    # Prepare per-column aggregators
    for name, dtype in cols:
        if name in {"component", "tipo", "observation_time", "cleaned"}:
            continue
        if name == "id":
            # Use MIN(id) to get a representative id for each aggregated group
            select_parts.append("MIN(id) AS id")
            output_columns.append("id")
            continue
        # Numeric candidates
        if dtype in {"double precision", "real", "integer", "bigint", "numeric"} or name.endswith("_value"):
            num_expr = _build_numeric_expr(name, dtype)
            sum_types_str = "', '".join(sorted(SUM_TYPES))
            agg_expr = (
                f"CASE WHEN tipo IN ('{sum_types_str}') THEN SUM({num_expr}) "
                f"ELSE AVG({num_expr}) END AS {name}"
            )
            select_parts.append(agg_expr)
            output_columns.append(name)
        else:
            # Textual fallback
            select_parts.append(_build_text_expr(name))
            output_columns.append(name)

    select_sql = (
        "SELECT " + ", ".join(select_parts) + f"\nFROM {schema}.{table}\n"
        + (f"WHERE {where_clause}\n" if where_clause else "")
        + "GROUP BY component, tipo, date_trunc('hour', observation_time)"
    )
    return select_sql, output_columns


def _ensure_clean_table(engine: Engine, schema: str, src_table: str, out_table: str) -> None:
    # Recreate clean table to ensure it has no unique constraints that could cause conflicts
    with engine.begin() as conn:
        # Drop and recreate table without constraints to avoid aggregation conflicts
        sql_recreate = text(f"""
            DROP TABLE IF EXISTS {schema}.{out_table};
            CREATE TABLE {schema}.{out_table} (LIKE {schema}.{src_table} INCLUDING DEFAULTS INCLUDING STORAGE);
        """)
        conn.execute(sql_recreate)


def _ensure_progress_table(engine: Engine, schema: str) -> None:
    sql = text(
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.sentilo_clean_progress (
            source_table text PRIMARY KEY,
            cleaned_until timestamp without time zone NOT NULL
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(sql)


def _get_cleaned_until(engine: Engine, schema: str, src_table: str):
    query = text(
        f"SELECT cleaned_until FROM {schema}.sentilo_clean_progress WHERE source_table = :t"
    )
    with engine.connect() as conn:
        row = conn.execute(query, {"t": src_table}).fetchone()
    result = row[0] if row else None
    return _normalize_datetime(result)


def _set_cleaned_until(engine: Engine, schema: str, src_table: str, until_ts) -> None:
    # Normalizar el timestamp antes de guardarlo
    normalized_ts = _normalize_datetime(until_ts)
    upsert = text(
        f"""
        INSERT INTO {schema}.sentilo_clean_progress (source_table, cleaned_until)
        VALUES (:t, :u)
        ON CONFLICT (source_table) DO UPDATE SET cleaned_until = EXCLUDED.cleaned_until
        """
    )
    with engine.begin() as conn:
        conn.execute(upsert, {"t": src_table, "u": normalized_ts})


def clean_and_aggregate_table(source_table: str) -> None:
    """
    Cleans and aggregates data from source_table into a clean table (or overwrites source) according to rules.
    - Deletes unwanted rows (TrafficFlowObserved with intensity_uom = 'Veh/día') within window
    - Groups by component, tipo, hour bucket of observation_time
    - Aggregates numeric columns per tipo (SUM or AVG), textual columns as MAX (including end_observation_time)
    - Processes records up to yesterday 00:00, resuming from last cleaned watermark per table
    """
    engine = _get_engine()
    schema = SENTILO_SCHEMA
    src_table = source_table
    out_mode = CLEAN_OUTPUT_MODE
    out_table = f"{src_table}{CLEAN_OUTPUT_SUFFIX}"  # Always use temp table for aggregation

    # Ensure progress table
    _ensure_progress_table(engine, schema)

    # Determine window [start, end)
    with engine.connect() as conn:
        window_end = conn.execute(text("SELECT date_trunc('day', now())")).scalar()
    window_end = _normalize_datetime(window_end)
    
    window_start = _get_cleaned_until(engine, schema, src_table)
    if not window_start:
        # Start from the earliest observation or epoch
        with engine.connect() as conn:
            earliest = conn.execute(text(f"SELECT MIN(observation_time) FROM {schema}.{src_table}")).scalar()
        window_start = _normalize_datetime(earliest) or 'epoch'

    # Log para debug
    LOGGER.info("[Sentilo Cleanup] Window for %s.%s: start=%s (type: %s), end=%s (type: %s)", 
                schema, src_table, window_start, type(window_start).__name__, 
                window_end, type(window_end).__name__)
    
    # Solo comparar si ambos son datetime objects (no strings como 'epoch')
    if (isinstance(window_start, datetime) and isinstance(window_end, datetime) and 
        window_start >= window_end):
        LOGGER.info("[Sentilo Cleanup] Nothing to do for %s.%s (start >= end)", schema, src_table)
        return

    # Build window WHERE clauses
    window_where = (
        "observation_time >= :wstart AND observation_time < :wend"
    )
    window_params = {"wstart": window_start, "wend": window_end}

    # Delete unwanted rows in the window and count
    delete_sql = text(
        f"DELETE FROM {schema}.{src_table} "
        f"WHERE tipo = 'TrafficFlowObserved' AND intensity_uom = 'Veh/día' AND (observation_time >= :wstart AND observation_time < :wend)"
    )
    with engine.begin() as conn:
        res = conn.execute(delete_sql, window_params)
        deleted = res.rowcount if res.rowcount is not None else 0
    LOGGER.info("[Sentilo Cleanup] Deleted %s rows from %s.%s (Veh/día, window)", deleted, schema, src_table)

    # Count remaining rows to process in the window
    count_sql = text(f"SELECT COUNT(*) FROM {schema}.{src_table} WHERE {window_where}")
    with engine.connect() as conn:
        total_after = conn.execute(count_sql, window_params).scalar() or 0

    # Prepare aggregation only for the window
    cols = _get_columns(engine, schema, src_table)
    agg_select_sql, out_cols = _build_agg_select(schema, src_table, cols, where_clause=window_where)

    # Ensure output table and clear only the window there
    _ensure_clean_table(engine, schema, src_table, out_table)
    delete_out_sql = text(
        f"DELETE FROM {schema}.{out_table} WHERE {window_where}"
    )
    with engine.begin() as conn:
        conn.execute(delete_out_sql, window_params)

    # Insert aggregated window
    insert_sql = text(
        f"INSERT INTO {schema}.{out_table} (" + ", ".join(out_cols) + ")\n" + agg_select_sql
    )
    with engine.begin() as conn:
        conn.execute(insert_sql, window_params)

    # Aggregated count
    with engine.connect() as conn:
        aggregated = conn.execute(text("SELECT COUNT(*) FROM (" + agg_select_sql + ") t"), window_params).scalar() or 0

    LOGGER.info(
        "[Sentilo Cleanup] Processed table %s.%s -> %s.%s (window %s to %s). Input rows: %s, Deleted: %s, Aggregated groups: %s",
        schema, src_table, schema, out_table, window_start, window_end, total_after, deleted, aggregated
    )
    LOGGER.info("[Sentilo Cleanup] Note: NULL/NaN values treated as 0 in numeric aggregations")

    # If overwrite mode and we want source to reflect clean values for the window, refresh that window
    if out_mode == 'overwrite':
        with engine.begin() as conn:
            conn.execute(text(f"DELETE FROM {schema}.{src_table} WHERE {window_where}"), window_params)
            conn.execute(text(f"INSERT INTO {schema}.{src_table} SELECT * FROM {schema}.{out_table} WHERE {window_where}"), window_params)
        LOGGER.info("[Sentilo Cleanup] Overwrote source table %s.%s for window", schema, src_table)

    # Advance watermark
    _set_cleaned_until(engine, schema, src_table, window_end)


def clean_all_configured_tables() -> None:
    """Find all configured Sentilo tables and clean them."""
    engine = _get_engine()
    # Get list of distinct table names from plugin configuration table
    query = text("SELECT DISTINCT tabla_de_datos FROM gvsigol_plugin_sentilo_sentiloconfiguration")
    try:
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        tables = [r[0] for r in rows if r and r[0]]
    except Exception as e:
        LOGGER.error("[Sentilo Cleanup] Failed to fetch configured tables: %s", str(e))
        return
    for tbl in tables:
        try:
            clean_and_aggregate_table(tbl)
        except Exception as e:
            LOGGER.error("[Sentilo Cleanup] Error cleaning table %s: %s", tbl, str(e)) 