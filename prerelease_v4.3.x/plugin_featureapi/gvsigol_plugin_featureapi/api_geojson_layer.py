# -*- coding: utf-8 -*-
"""
api_geojson_layer.py — Reusable library for GeoJSON-backed PostGIS table queries.

These are pure Python functions (NOT Django views) that any plugin can call
after resolving its own layer object and opening a DB connection.  The caller
is responsible for authentication, URL routing and layer resolution.

Expected ``layer`` duck-type interface:
    layer.table_name  – str, name of the PostGIS table
    layer.schema      – str, PostgreSQL schema (e.g. 'etl_visualizer')
    layer.has_geometry – bool

``con`` must be an open psycopg2 connection; the functions close it when done.

Usage example from a Django view in any plugin:

    from gvsigol_plugin_featureapi import api_geojson_layer as featureapi_geojson

    def my_features_view(request, layer_id):
        layer, con = _resolve_my_layer(layer_id)
        if layer is None:
            return JsonResponse({'error': 'not found'}, status=404)
        return featureapi_geojson.geojson_layer_features(request, layer, con)
"""

import json
import logging

from psycopg2 import sql

from django.http import JsonResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_prop_cols(cur, table_name, schema):
    """Return non-geometry, non-PK column names in ordinal order."""
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
          AND column_name NOT IN ('geom', 'gvsig_etl_rowid')
          AND udt_name NOT IN ('geometry', 'geography')
        ORDER BY ordinal_position
        """,
        (schema, table_name)
    )
    return [r[0] for r in cur.fetchall()]


def _build_filter_where(filter_json, prop_cols):
    """
    Convert the ``filter`` JSON param (sent by @scolab/common DataTable) into a
    psycopg2 sql.SQL WHERE clause and a matching params list.

    Structure:  { "filterQueries": [...], "filterOperator": "AND"|"OR" }
    Each query: { "type": "query", "field": "col", "operator": "=", "value": "x", "notop": false }
    Or a group: { "type": "qGroup", "op": "AND"|"OR", "querys": [...] }

    Returns (sql.SQL(""), []) when the filter is absent or empty.
    """
    if not filter_json:
        return sql.SQL(""), []
    try:
        filter_data = json.loads(filter_json)
    except (ValueError, TypeError):
        return sql.SQL(""), []

    filter_queries = filter_data.get('filterQueries', [])
    filter_operator = filter_data.get('filterOperator', 'AND')
    join_kw = sql.SQL(' OR ') if str(filter_operator).strip().upper() == 'OR' else sql.SQL(' AND ')

    if not filter_queries:
        return sql.SQL(""), []

    conditions = []
    params = []

    for item in filter_queries:
        item_type = item.get('type', 'query')
        if item_type == 'query':
            cond, p = _single_condition(item, prop_cols)
            if cond is not None:
                conditions.append(cond)
                params.extend(p)
        elif item_type == 'qGroup':
            group_op = item.get('op', 'AND')
            group_join = sql.SQL(' OR ') if str(group_op).strip().upper() == 'OR' else sql.SQL(' AND ')
            group_conds, group_params = [], []
            for q in item.get('querys', []):
                cond, p = _single_condition(q, prop_cols)
                if cond is not None:
                    group_conds.append(cond)
                    group_params.extend(p)
            if group_conds:
                conditions.append(sql.SQL('(') + group_join.join(group_conds) + sql.SQL(')'))
                params.extend(group_params)

    if not conditions:
        return sql.SQL(""), []
    return join_kw.join(conditions), params


def _single_condition(query, prop_cols):
    """Build a single SQL condition from a filterQuery dict."""
    field = str(query.get('field', '')).strip()
    op = str(query.get('operator', '')).strip().upper()
    value = query.get('value')
    notop = bool(query.get('notop', False))

    if not field or field not in prop_cols:
        return None, []

    params = []
    if op == 'IS NULL':
        inner = sql.SQL('{col} IS NULL').format(col=sql.Identifier(field))
    elif op == 'IS NOT NULL':
        inner = sql.SQL('{col} IS NOT NULL').format(col=sql.Identifier(field))
    elif op == 'LIKE':
        inner = sql.SQL('{col} LIKE {val}').format(col=sql.Identifier(field), val=sql.Placeholder())
        params = [value if value is not None else '']
    elif op == 'ILIKE':
        inner = sql.SQL('{col} ILIKE {val}').format(col=sql.Identifier(field), val=sql.Placeholder())
        params = [value if value is not None else '']
    elif op == 'CONTAINS':
        inner = sql.SQL('{col} ILIKE {val}').format(col=sql.Identifier(field), val=sql.Placeholder())
        params = [f'%{value}%' if value else '%']
    elif op == 'NOT CONTAINS':
        inner = sql.SQL('{col} NOT ILIKE {val}').format(col=sql.Identifier(field), val=sql.Placeholder())
        params = [f'%{value}%' if value else '%']
    elif op == 'IN':
        vals = [v.strip() for v in str(value).split(',') if v.strip()] if value else []
        if not vals:
            return None, []
        placeholders = sql.SQL(', ').join([sql.Placeholder()] * len(vals))
        inner = sql.SQL('{col} IN ({vals})').format(col=sql.Identifier(field), vals=placeholders)
        params = vals
    elif op == '=':
        inner = sql.SQL('{col} = {val}').format(col=sql.Identifier(field), val=sql.Placeholder())
        params = [value]
    elif op == '<>':
        inner = sql.SQL('{col} <> {val}').format(col=sql.Identifier(field), val=sql.Placeholder())
        params = [value]
    elif op in ('>=', '<=', '>', '<'):
        inner = sql.SQL('{col} ' + op + ' {val}').format(col=sql.Identifier(field), val=sql.Placeholder())
        params = [value]
    else:
        return None, []

    if notop:
        return sql.SQL('NOT ({inner})').format(inner=inner), params
    return inner, params


# ---------------------------------------------------------------------------
# Public library functions  (called by plugin-specific Django views)
# ---------------------------------------------------------------------------

def geojson_layer_features(request, layer, con):
    """
    Featureapi-compatible paginated features endpoint.
    Consumed by @scolab/common DataTable and Filter components.

    Query params:
      max       – page size (default 25)
      page      – 0-indexed page number (default 0)
      text      – full-text filter on all text columns (optional)
      filter    – JSON filter from DataTable (filterQueries + filterOperator)
      sortfield – column name to sort by (optional)
      sortorder – 'ascend' | 'descend' (optional)
    """
    try:
        cur = con.cursor()
        table_name = layer.table_name
        schema = layer.schema

        max_items = int(request.GET.get('max', 25))
        page = int(request.GET.get('page', 0))
        text_search = request.GET.get('text', '').strip()
        filter_json = request.GET.get('filter', '')
        sortfield = request.GET.get('sortfield', '')
        sortorder = request.GET.get('sortorder', '')

        prop_cols = _get_prop_cols(cur, table_name, schema)
        if not prop_cols:
            con.close()
            return JsonResponse({'content': {'lendata': 0, 'features': []}})

        row_num_expr = sql.SQL("gvsig_etl_rowid AS _rowid")
        prop_sql = sql.SQL(', ').join([sql.Identifier(c) for c in prop_cols])
        geom_col = sql.SQL(", ST_AsGeoJSON(geom) AS _geom_json") if layer.has_geometry else sql.SQL("")

        where_parts, params = [], []

        filter_cond, filter_params = _build_filter_where(filter_json, prop_cols)
        if filter_cond != sql.SQL(""):
            where_parts.append(sql.SQL("(") + filter_cond + sql.SQL(")"))
            params.extend(filter_params)

        if text_search:
            text_conditions = []
            for col in prop_cols:
                text_conditions.append(
                    sql.SQL("CAST({col} AS TEXT) ILIKE {val}").format(
                        col=sql.Identifier(col), val=sql.Placeholder()
                    )
                )
                params.append(f'%{text_search}%')
            where_parts.append(sql.SQL("(") + sql.SQL(" OR ").join(text_conditions) + sql.SQL(")"))

        where_clause = sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_parts) if where_parts else sql.SQL("")

        if sortfield and sortfield in prop_cols:
            direction = sql.SQL("DESC") if sortorder == 'descend' else sql.SQL("ASC")
            order_clause = sql.SQL("ORDER BY {col} {dir}").format(
                col=sql.Identifier(sortfield), dir=direction
            )
        else:
            order_clause = sql.SQL("")

        count_q = sql.SQL("SELECT COUNT(*) FROM {schema}.{tbl} {where}").format(
            schema=sql.Identifier(schema),
            tbl=sql.Identifier(table_name),
            where=where_clause,
        )
        cur.execute(count_q, params)
        total = cur.fetchone()[0]

        inner_q = sql.SQL("SELECT {row_num}, {props}{geom} FROM {schema}.{tbl} {where} {order}").format(
            row_num=row_num_expr, props=prop_sql, geom=geom_col,
            schema=sql.Identifier(schema), tbl=sql.Identifier(table_name),
            where=where_clause, order=order_clause,
        )
        data_q = sql.SQL("SELECT * FROM ({inner}) _t LIMIT {lim} OFFSET {off}").format(
            inner=inner_q, lim=sql.Literal(max_items), off=sql.Literal(page * max_items),
        )
        cur.execute(data_q, params)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]

        features = []
        for row in rows:
            props, geom_json = {}, None
            for i, col in enumerate(col_names):
                if col == '_geom_json':
                    geom_json = row[i]
                else:
                    val = row[i]
                    props[col] = val.isoformat() if hasattr(val, 'isoformat') else val
            features.append({
                'type': 'Feature',
                'geometry': json.loads(geom_json) if geom_json else None,
                'properties': props,
            })

        cur.close()
        con.close()
        return JsonResponse({'content': {'lendata': total, 'features': features}})

    except Exception as e:
        logger.exception("geojson_layer_features error: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


def geojson_layer_fieldoptions(request, layer, con):
    """
    Returns distinct values for a field.
    Consumed by @scolab/common Filter (traditional fallback).

    Query params:
      fieldselected – column name
      lang          – language (unused, for API compatibility)
    """
    try:
        cur = con.cursor()
        fieldselected = request.GET.get('fieldselected', '')
        if not fieldselected:
            con.close()
            return JsonResponse([], safe=False)

        prop_cols = _get_prop_cols(cur, layer.table_name, layer.schema)
        if fieldselected not in prop_cols:
            cur.close(); con.close()
            return JsonResponse([], safe=False)

        q = sql.SQL(
            "SELECT DISTINCT {col} FROM {schema}.{tbl} "
            "WHERE {col} IS NOT NULL ORDER BY {col} LIMIT 1000"
        ).format(
            col=sql.Identifier(fieldselected),
            schema=sql.Identifier(layer.schema),
            tbl=sql.Identifier(layer.table_name),
        )
        cur.execute(q)
        values = [str(r[0]) for r in cur.fetchall()]
        cur.close(); con.close()
        return JsonResponse(values, safe=False)

    except Exception as e:
        logger.exception("geojson_layer_fieldoptions error: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


def geojson_layer_fieldoptions_paginated(request, layer, con):
    """
    Paginated distinct field values.
    Consumed by @scolab/common Filter (Select2-style components).

    Query params:
      fieldselected – column name
      limit         – page size (default 50)
      offset        – offset (default 0)
      search        – filter string (optional)
      lang          – language (unused)
    """
    try:
        cur = con.cursor()
        fieldselected = request.GET.get('fieldselected', '')
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        search = request.GET.get('search', '').strip()

        if not fieldselected:
            con.close()
            return JsonResponse({'data': [], 'has_more': False, 'total': 0, 'offset': 0})

        prop_cols = _get_prop_cols(cur, layer.table_name, layer.schema)
        if fieldselected not in prop_cols:
            cur.close(); con.close()
            return JsonResponse({'data': [], 'has_more': False, 'total': 0, 'offset': 0})

        params = []
        search_clause = sql.SQL("")
        if search:
            search_clause = sql.SQL("AND CAST({col} AS TEXT) ILIKE {val}").format(
                col=sql.Identifier(fieldselected), val=sql.Placeholder()
            )
            params.append(f'%{search}%')

        count_q = sql.SQL(
            "SELECT COUNT(DISTINCT {col}) FROM {schema}.{tbl} "
            "WHERE {col} IS NOT NULL {search}"
        ).format(
            col=sql.Identifier(fieldselected),
            schema=sql.Identifier(layer.schema),
            tbl=sql.Identifier(layer.table_name),
            search=search_clause,
        )
        cur.execute(count_q, params)
        total = cur.fetchone()[0]

        data_q = sql.SQL(
            "SELECT DISTINCT {col} FROM {schema}.{tbl} "
            "WHERE {col} IS NOT NULL {search} ORDER BY {col} LIMIT {lim} OFFSET {off}"
        ).format(
            col=sql.Identifier(fieldselected),
            schema=sql.Identifier(layer.schema),
            tbl=sql.Identifier(layer.table_name),
            search=search_clause,
            lim=sql.Literal(limit),
            off=sql.Literal(offset),
        )
        cur.execute(data_q, params)
        values = [str(r[0]) for r in cur.fetchall()]
        cur.close(); con.close()

        return JsonResponse({
            'data': values,
            'has_more': (offset + limit) < total,
            'total': total,
            'offset': offset,
        })

    except Exception as e:
        logger.exception("geojson_layer_fieldoptions_paginated error: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


def geojson_layer_single_feature(request, layer, con, rowid):
    """
    Returns a single feature by its stable row ID.
    Consumed by @scolab/common DataTable (zoom to selected row) and PopupInfo.

    Query params:
      source_epsg – if contains '3857', return geometry in EPSG:3857 (no transform);
                    otherwise return in EPSG:4326 for client-side transform.
    """
    try:
        cur = con.cursor()
        table_name = layer.table_name
        prop_cols = _get_prop_cols(cur, table_name, layer.schema)

        if not prop_cols:
            cur.close(); con.close()
            return JsonResponse({'error': 'No columns'}, status=404)

        prop_sql = sql.SQL(', ').join([sql.Identifier(c) for c in prop_cols])

        source_epsg = request.GET.get('source_epsg', '')
        use_strict_crs = bool(source_epsg and '3857' in source_epsg)
        print(
            f"[geojson_single_feature] table={table_name} rowid={rowid} "
            f"source_epsg={source_epsg!r} use_strict_crs={use_strict_crs} has_geometry={layer.has_geometry}"
        )
        if use_strict_crs:
            geom_col = (
                sql.SQL(", ST_AsGeoJSON(geom) AS _geom_json")
                if layer.has_geometry else sql.SQL("")
            )
        else:
            geom_col = (
                sql.SQL(", ST_AsGeoJSON(ST_Transform(geom, 4326)) AS _geom_json")
                if layer.has_geometry else sql.SQL("")
            )

        q = sql.SQL(
            "SELECT gvsig_etl_rowid AS _rowid, {props}{geom} "
            "FROM {schema}.{tbl} WHERE gvsig_etl_rowid = {rid}"
        ).format(
            props=prop_sql, geom=geom_col,
            schema=sql.Identifier(layer.schema),
            tbl=sql.Identifier(table_name),
            rid=sql.Literal(rowid),
        )
        cur.execute(q)
        row = cur.fetchone()
        col_names = [desc[0] for desc in cur.description]
        cur.close(); con.close()

        if not row:
            return JsonResponse({'error': 'Feature not found'}, status=404)

        props, geom_json = {}, None
        for i, col in enumerate(col_names):
            if col == '_geom_json':
                geom_json = row[i]
            else:
                val = row[i]
                props[col] = val.isoformat() if hasattr(val, 'isoformat') else val

        if geom_json:
            parsed_geom = json.loads(geom_json)
            coords = parsed_geom.get('coordinates')
            first_coord = coords[0] if coords else None
            print(
                f"[geojson_single_feature] returning CRS={'EPSG:3857' if use_strict_crs else 'EPSG:4326'} "
                f"first_coord={first_coord}"
            )
        else:
            parsed_geom = None

        return JsonResponse({'content': {
            'type': 'Feature',
            'geometry': parsed_geom,
            'properties': props,
        }})

    except Exception as e:
        logger.exception("geojson_layer_single_feature error: %s", e)
        return JsonResponse({'error': str(e)}, status=500)
