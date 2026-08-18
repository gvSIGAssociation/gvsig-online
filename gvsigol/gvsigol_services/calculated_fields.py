# -*- coding: utf-8 -*-
"""
API for one-shot calculated attributes on PostGIS layers.
"""
from __future__ import unicode_literals

import ast
import json
import logging
import re

from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.translation import gettext as _
from psycopg2 import sql as sqlbuilder
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from gvsigol import settings
from gvsigol_core.models import ProjectLayerGroup
from gvsigol_services import geographic_servers, utils
from gvsigol_services.backend_geoserver import _valid_sql_name_regex
from gvsigol_services.formula_utils import FormulaError, compile_formula, validate_identifier
from gvsigol_services.models import Layer

logger = logging.getLogger(__name__)

_NUMERIC_TYPES = {
    'smallint', 'integer', 'bigint', 'decimal', 'numeric',
    'real', 'double precision', 'float4', 'float8', 'int2', 'int4', 'int8',
}


def _json_error(message, status=400, extra=None):
    payload = {'status': 'error', 'message': message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _one_to_many_hint(join_sources):
    """Aliases the frontend should aggregate, surfaced together with errors."""
    if not join_sources:
        return None
    aliases = [
        alias for alias, meta in join_sources.items() if meta.get('is_many')
    ]
    return {'one_to_many_aliases': aliases} if aliases else None


def _parse_json_body(request):
    # DRF already parsed the payload according to the content type
    parsed = getattr(request, 'data', None)
    if isinstance(parsed, dict):
        data = dict(parsed)
    elif request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            raise FormulaError(_('Invalid JSON body'))
    else:
        # form-encoded fallback
        data = {}
        for key in request.POST:
            data[key] = request.POST.get(key)
    if 'field_units' in data and isinstance(data['field_units'], str):
        try:
            data['field_units'] = json.loads(data['field_units'])
        except ValueError:
            data['field_units'] = {}
    if 'sources' in data and isinstance(data['sources'], str):
        try:
            data['sources'] = json.loads(data['sources'])
        except ValueError:
            data['sources'] = []
    return data


def _layer_params(layer):
    return json.loads(layer.datastore.connection_params)


def _same_connection(layer_a, layer_b):
    pa = _layer_params(layer_a)
    pb = _layer_params(layer_b)
    return (
        pa.get('host') == pb.get('host')
        and str(pa.get('port')) == str(pb.get('port'))
        and pa.get('database') == pb.get('database')
    )


def _project_layer_ids(project_id):
    """Return the layers that actually belong to the requested project TOC."""
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        raise FormulaError(_('Invalid or missing project'))
    group_ids = ProjectLayerGroup.objects.filter(
        project_id=project_id
    ).values_list('layer_group_id', flat=True)
    return set(Layer.objects.filter(
        layer_group_id__in=group_ids
    ).values_list('id', flat=True))


def _ensure_layers_in_project(project_layer_ids, *layers):
    if any(layer.id not in project_layer_ids for layer in layers):
        raise FormulaError(_('All participating layers must belong to the current project'))


def _request_user(request):
    """
    The authenticated principal of this request. Permissions must never be
    resolved from the request itself: the role claims are read from the Django
    session, which may belong to a different login when the frontend
    authenticates with a bearer token.
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        raise PermissionError(_('Not authorized'))
    return user


def _can_read(request, layer):
    return utils.can_read_layer(_request_user(request), layer)


def _can_write_calculated(request, layer):
    return utils.can_write_calculated_fields(request, layer)


def _can_receive_calculated(request, layer):
    """
    A layer can be offered as destination only when the feature is enabled on
    it and the user has the very same write permissions required on the layer
    the calculator was opened from.
    """
    return utils.can_use_calculated_fields(request, layer)


def _ensure_manageable_postgis(request, layer, require_flag=True):
    if layer.external or not layer.datastore or layer.datastore.type != 'v_PostGIS':
        raise FormulaError(_('Only PostGIS layers support calculated attributes'))
    if require_flag and not layer.allow_calculated_fields:
        raise FormulaError(_('Calculated attributes are not enabled for this layer'))
    if not _can_write_calculated(request, layer):
        raise PermissionError(_('Not authorized'))
    iconn, source_name, schema = layer.get_db_connection()
    with iconn as con:
        if con.is_view(schema, source_name):
            raise FormulaError(_('Calculated attributes cannot target SQL views'))
    return source_name, schema


def _get_numeric_fields(con, schema, table):
    info = con.get_fields_info(table, schema=schema)
    numeric = []
    for f in info:
        dtype = (f.get('type') or f.get('data_type') or '').lower()
        name = f.get('name') or f.get('column_name')
        if name and dtype in _NUMERIC_TYPES:
            numeric.append(name)
    return numeric, info


def _sql_ident(name):
    return sqlbuilder.Identifier(name)


def _qualified_column(alias, field):
    return sqlbuilder.SQL('{alias}.{field}').format(
        alias=sqlbuilder.Identifier(alias),
        field=sqlbuilder.Identifier(field),
    )


def _filter_condition(query, columns, alias):
    """
    Single condition of the attribute table filter. Operators mirror the ones
    the feature API understands, so the calculator hits exactly the same rows
    the user is seeing.
    """
    field = str(query.get('field') or '').strip()
    if field not in columns:
        raise FormulaError(_('Unknown field in the applied filter: {0}').format(field))
    operator = str(query.get('operator') or '').strip().upper()
    value = query.get('value')
    column = _qualified_column(alias, field) if alias else sqlbuilder.Identifier(field)

    if operator in ('IS NULL', 'IS NOT NULL'):
        condition = sqlbuilder.SQL('{col} {op}').format(
            col=column, op=sqlbuilder.SQL(operator))
    elif operator == 'IN':
        values = value if isinstance(value, (list, tuple)) else \
            [v.strip() for v in str(value or '').split(',') if v.strip()]
        if not values:
            return None
        cleaned = []
        for raw in values:
            text = str(raw).strip()
            if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
                text = text[1:-1]
            cleaned.append(text)
        condition = sqlbuilder.SQL('{col} IN ({vals})').format(
            col=column,
            vals=sqlbuilder.SQL(', ').join(
                [sqlbuilder.Literal(v) for v in cleaned]),
        )
    elif operator in ('CONTAINS', 'NOT CONTAINS'):
        values = value if isinstance(value, (list, tuple)) else [value]
        like = sqlbuilder.SQL('NOT LIKE') if operator == 'NOT CONTAINS' else sqlbuilder.SQL('LIKE')
        joiner = sqlbuilder.SQL(' AND ') if operator == 'NOT CONTAINS' else sqlbuilder.SQL(' OR ')
        parts = [
            sqlbuilder.SQL('{col} {like} {val}').format(
                col=column, like=like,
                val=sqlbuilder.Literal('%{0}%'.format('' if v is None else v)),
            )
            for v in values
        ]
        condition = sqlbuilder.SQL('({0})').format(joiner.join(parts))
    elif operator in ('=', '<>', '<', '>', '<=', '>=', 'LIKE', 'ILIKE'):
        condition = sqlbuilder.SQL('{col} {op} {val}').format(
            col=column,
            op=sqlbuilder.SQL(operator),
            val=sqlbuilder.Literal('' if value is None else str(value)),
        )
    else:
        raise FormulaError(_('Unsupported filter operator: {0}').format(operator))

    if query.get('notop'):
        return sqlbuilder.SQL('(NOT {0})').format(condition)
    return sqlbuilder.SQL('({0})').format(condition)


def _build_filter_where(filter_data, columns, alias=None):
    """
    Translate the filter currently applied in the attribute table into a WHERE
    clause over the base layer, or None when there is no usable filter.
    """
    if isinstance(filter_data, str):
        try:
            filter_data = json.loads(filter_data)
        except ValueError:
            return None
    if not isinstance(filter_data, dict):
        return None
    queries = filter_data.get('filterQueries') or []
    if not queries:
        return None

    operator = str(filter_data.get('filterOperator') or 'AND').strip().upper()
    joiner = sqlbuilder.SQL(' OR ') if operator == 'OR' else sqlbuilder.SQL(' AND ')

    parts = []
    for item in queries:
        if item.get('type') == 'qGroup':
            group_operator = str(item.get('op') or 'AND').strip().upper()
            group_joiner = sqlbuilder.SQL(' OR ') if group_operator == 'OR' \
                else sqlbuilder.SQL(' AND ')
            group = [_filter_condition(q, columns, alias) for q in (item.get('querys') or [])]
            group = [c for c in group if c is not None]
            if group:
                parts.append(sqlbuilder.SQL('({0})').format(group_joiner.join(group)))
        else:
            condition = _filter_condition(item, columns, alias)
            if condition is not None:
                parts.append(condition)

    if not parts:
        return None
    return sqlbuilder.SQL('({0})').format(joiner.join(parts))


def _zero_divisor_predicate(divisor_sqls):
    """WHERE fragment true when any compiled divisor equals 0."""
    if not divisor_sqls:
        return None
    parts = [
        sqlbuilder.SQL('(({expr}) = 0)').format(expr=sqlbuilder.SQL(fragment))
        for fragment in divisor_sqls
    ]
    return sqlbuilder.SQL('({0})').format(sqlbuilder.SQL(' OR ').join(parts))


def _read_conf(conf_manager):
    """
    layer.conf holds a dict once refresh_field_conf() has run, but a repr
    string when it comes straight from the database.
    """
    conf = conf_manager.conf
    if isinstance(conf, str):
        for parser in (ast.literal_eval, json.loads):
            try:
                conf = parser(conf)
                break
            except Exception:
                continue
    return conf if isinstance(conf, dict) else {}


def _store_field_meta(layer, field_name, formula, unit=None, dimension=None,
                      extra=None, conf_manager=None):
    conf_manager = conf_manager or layer.get_config_manager()
    conf = _read_conf(conf_manager)
    fields = conf.get('fields', [])
    found = False
    for field in fields:
        if field.get('name') == field_name:
            field['gvsigol_type'] = 'double'
            field['calculated_formula'] = formula
            if unit is not None:
                field['unit'] = unit
            if dimension is not None:
                field['dimension'] = dimension
            if extra:
                field.update(extra)
            found = True
            break
    if not found:
        entry = {
            'name': field_name,
            'visible': True,
            'editable': True,
            'infovisible': True,
            'gvsigol_type': 'double',
            'calculated_formula': formula,
        }
        if unit is not None:
            entry['unit'] = unit
        if dimension is not None:
            entry['dimension'] = dimension
        if extra:
            entry.update(extra)
        # titles for active languages when available
        for lang_code, _lang_name in getattr(settings, 'LANGUAGES', (('es', 'Spanish'),)):
            entry['title-' + lang_code] = field_name
        fields.append(entry)
    conf['fields'] = fields
    _sync_form_groups(conf)
    conf_manager.conf = conf
    layer.save()


def _sync_form_groups(conf):
    """
    Fields missing from every form group are dropped by the project API, so the
    new column would never reach the viewer nor the attribute table.
    """
    fields = conf.get('fields') or []
    if not fields:
        return
    # Imported lazily: views.py pulls in the whole services stack
    from gvsigol_services.views import _parse_form_groups
    conf['form_groups'] = _parse_form_groups(conf.get('form_groups') or [], fields)


def _refresh_layer_publication(layer):
    gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
    expose_pks = gs.datastore_check_exposed_pks(layer.datastore)
    gs.reload_featuretype(layer, nativeBoundingBox=False, latLonBoundingBox=False)
    gs.reload_nodes()
    conf_manager = layer.get_config_manager()
    conf_manager.refresh_field_conf(include_pks=expose_pks)
    # Returned so the caller keeps writing on the already refreshed conf
    return conf_manager


def _join_key_is_unique(con, schema, table, join_field):
    """True when every non-null join key appears at most once in the table."""
    query = sqlbuilder.SQL(
        "SELECT {field} FROM {schema}.{table} "
        "WHERE {field} IS NOT NULL "
        "GROUP BY {field} HAVING COUNT(*) > 1 LIMIT 1"
    ).format(
        field=sqlbuilder.Identifier(join_field),
        schema=sqlbuilder.Identifier(schema),
        table=sqlbuilder.Identifier(table),
    )
    con.cursor.execute(query)
    return con.cursor.fetchone() is None


def _check_unique_join_keys(con, schema, table, join_field):
    """Require a 1:1 / N:1 lookup key (used when writing into a joined layer)."""
    if not _join_key_is_unique(con, schema, table, join_field):
        raise FormulaError(
            _('Join field "{0}" on "{1}" is not unique; ambiguous joins are not allowed').format(
                join_field, table))


def _build_join_sources(con, resolved_sources):
    """
    Build the join_sources map expected by compile_formula.

    ``is_many`` is True when several related rows can match one base row
    (classic 1:N), so those fields must be wrapped in aggregates.
    """
    join_sources = {}
    for resolved in resolved_sources:
        alias = resolved['alias']
        join_sources[alias] = {
            'schema': resolved['schema'],
            'table': resolved['table'],
            'join_self': resolved['join_self'],
            'join_other': resolved['join_other'],
            'is_many': not _join_key_is_unique(
                con, resolved['schema'], resolved['table'], resolved['join_other']),
        }
    return join_sources


def _build_same_layer_resolver(alias_or_none=None):
    def resolver(name):
        # bare field
        if '.' not in name:
            if alias_or_none:
                return '{0}.{1}'.format(
                    sqlbuilder.Identifier(alias_or_none).as_string(None) if False else alias_or_none,
                    name
                )
            # Use quoted identifiers via as_string requires connection; return simple quoted form
            return '"{0}"'.format(name.replace('"', ''))
        alias, field = name.split('.', 1)
        return '"{0}"."{1}"'.format(alias.replace('"', ''), field.replace('"', ''))
    return resolver


def _safe_quote_ident(name):
    validate_identifier(name)
    return '"{0}"'.format(name)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculated_field_joinable_layers(request):
    """List PostGIS layers on the same DB connection that the user can read/manage."""
    try:
        params = getattr(request, 'query_params', request.GET)
        layer_id = int(params.get('layer_id'))
        project_layer_ids = _project_layer_ids(params.get('project_id'))
        layer = Layer.objects.select_related('datastore', 'datastore__workspace').get(id=layer_id)
        _ensure_layers_in_project(project_layer_ids, layer)
    except (TypeError, ValueError, Layer.DoesNotExist, FormulaError) as exc:
        if isinstance(exc, FormulaError):
            return _json_error(str(exc))
        return _json_error(_('Layer not found'), 404)
    try:
        if not _can_write_calculated(request, layer):
            return HttpResponseForbidden(json.dumps({'status': 'error', 'message': 'Not authorized'}),
                                         content_type='application/json')
        if not layer.datastore or layer.datastore.type != 'v_PostGIS':
            return _json_error(_('Only PostGIS layers are supported'))
        params = _layer_params(layer)
        host, port, database = params.get('host'), str(params.get('port')), params.get('database')
        candidates = Layer.objects.filter(
            id__in=project_layer_ids,
            datastore__type='v_PostGIS',
            external=False,
        ).select_related('datastore', 'datastore__workspace')
        result = []
        for candidate in candidates:
            if not _can_read(request, candidate):
                continue
            cp = _layer_params(candidate)
            if cp.get('host') != host or str(cp.get('port')) != port or cp.get('database') != database:
                continue
            iconn, source_name, schema = candidate.get_db_connection()
            with iconn as con:
                is_view = con.is_view(schema, source_name)
                numeric, info = _get_numeric_fields(con, schema, source_name)
                all_fields = [f.get('name') or f.get('column_name') for f in info]
            result.append({
                'id': candidate.id,
                'name': candidate.name,
                'title': candidate.title,
                'workspace': candidate.datastore.workspace.name,
                'source_name': source_name,
                'schema': schema,
                'is_view': is_view,
                'allow_calculated_fields': candidate.allow_calculated_fields,
                # Only layers flagged as destination-capable are offered to
                # write the result into
                'can_receive_calculated': (
                    not is_view and _can_receive_calculated(request, candidate)
                ),
                'numeric_fields': numeric,
                'fields': [f for f in all_fields if f],
                'is_current': candidate.id == layer.id,
            })
        return JsonResponse({'status': 'ok', 'layers': result})
    except Exception as exc:
        logger.exception('joinable layers')
        return _json_error(str(exc))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculated_field_join_cardinality(request):
    """
    Tell whether a join is 1:1 or 1:N as soon as the layer and both join fields
    are known, so the UI can offer aggregations only when they are needed.
    """
    try:
        data = _parse_json_body(request)
        layer = Layer.objects.get(id=int(data.get('layer_id')))
        project_layer_ids = _project_layer_ids(data.get('project_id'))
        _ensure_layers_in_project(project_layer_ids, layer)
        _ensure_manageable_postgis(request, layer, require_flag=True)

        results = {}
        iconn, _source_name, _schema = layer.get_db_connection()
        with iconn as con:
            for idx, src in enumerate(data.get('sources') or []):
                if not src or not src.get('layer_id'):
                    continue
                join_self = src.get('join_field_self') or src.get('join_field_current')
                join_other = src.get('join_field_other')
                if not join_self or not join_other:
                    continue
                alias = validate_identifier(src.get('alias') or ('t' + str(idx + 2)))
                validate_identifier(join_self)
                validate_identifier(join_other)
                other = Layer.objects.get(id=int(src['layer_id']))
                _ensure_layers_in_project(project_layer_ids, other)
                if not _same_connection(layer, other):
                    raise FormulaError(_('All layers must share the same database connection'))
                if not _can_read(request, other):
                    raise PermissionError(_('Not authorized to read related layer'))
                o_source = other.source_name or other.name
                o_schema = _layer_params(other).get('schema', 'public')
                results[alias] = not _join_key_is_unique(con, o_schema, o_source, join_other)

        return JsonResponse({
            'status': 'ok',
            'cardinality': {alias: ('many' if is_many else 'one')
                            for alias, is_many in results.items()},
            'one_to_many_aliases': [a for a, is_many in results.items() if is_many],
        })
    except PermissionError as exc:
        return HttpResponseForbidden(json.dumps({'status': 'error', 'message': str(exc)}),
                                     content_type='application/json')
    except (FormulaError, Layer.DoesNotExist, TypeError, ValueError) as exc:
        return _json_error(str(exc) or _('Layer not found'))
    except Exception as exc:
        logger.exception('join cardinality')
        return _json_error(str(exc))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculated_field_validate(request):
    """Validate formula and optionally units; return compiled info / preview sample."""
    join_sources = None
    try:
        data = _parse_json_body(request)
        layer = Layer.objects.get(id=int(data.get('layer_id')))
        project_layer_ids = _project_layer_ids(data.get('project_id'))
        _ensure_layers_in_project(project_layer_ids, layer)
        _ensure_manageable_postgis(request, layer, require_flag=True)
        formula = data.get('formula') or ''
        field_units = data.get('field_units') or {}
        sources = data.get('sources') or []

        iconn, source_name, schema = layer.get_db_connection()
        with iconn as con:
            numeric, info = _get_numeric_fields(con, schema, source_name)
            allowed = set()
            resolved = []

            if sources:
                base_alias = 't1'
                for f in numeric:
                    allowed.add('{0}.{1}'.format(base_alias, f))
                for idx, src in enumerate(sources):
                    other = Layer.objects.get(id=int(src['layer_id']))
                    _ensure_layers_in_project(project_layer_ids, other)
                    if not _same_connection(layer, other):
                        raise FormulaError(_('All layers must share the same database connection'))
                    if not _can_read(request, other):
                        raise PermissionError(_('Not authorized to read related layer'))
                    o_source = other.source_name or other.name
                    o_schema = _layer_params(other).get('schema', 'public')
                    alias = validate_identifier(src.get('alias') or ('t' + str(idx + 2)))
                    onum, _oinfo = _get_numeric_fields(con, o_schema, o_source)
                    for f in onum:
                        allowed.add('{0}.{1}'.format(alias, f))
                    join_self = validate_identifier(
                        src.get('join_field_self') or src.get('join_field_current'))
                    join_other = validate_identifier(src.get('join_field_other'))
                    resolved.append({
                        'alias': alias,
                        'schema': o_schema,
                        'table': o_source,
                        'join_self': join_self,
                        'join_other': join_other,
                    })
                join_sources = _build_join_sources(con, resolved)
            else:
                for f in numeric:
                    allowed.add(f)

            def resolver(name):
                if '.' not in name:
                    return _safe_quote_ident(name)
                alias, field = name.split('.', 1)
                return '"{0}"."{1}"'.format(alias, field)

            compiled = compile_formula(
                formula, allowed, resolver,
                field_units=field_units, result_unit=data.get('unit'),
                join_sources=join_sources, base_alias='t1')

            # The preview must show the same rows the attribute table is showing
            all_columns = {f.get('name') or f.get('column_name') for f in info}
            where = _build_filter_where(
                data.get('filter'), all_columns, alias='t1' if sources else None)

            # sample preview values (works with correlated join subqueries)
            preview_rows = []
            try:
                if sources:
                    q = sqlbuilder.SQL(
                        'SELECT ({expr})::double precision AS __result '
                        'FROM {schema}.{table} AS t1 {where} LIMIT 5'
                    ).format(
                        expr=sqlbuilder.SQL(compiled['sql']),
                        schema=sqlbuilder.Identifier(schema),
                        table=sqlbuilder.Identifier(source_name),
                        where=sqlbuilder.SQL('WHERE {0}').format(where) if where
                        else sqlbuilder.SQL(''),
                    )
                else:
                    cols = [
                        sqlbuilder.Identifier(f)
                        for f in compiled['referenced_fields'] if '.' not in f
                    ]
                    if cols:
                        q = sqlbuilder.SQL(
                            'SELECT {cols}, ({expr})::double precision AS __result '
                            'FROM {schema}.{table} {where} LIMIT 5'
                        ).format(
                            cols=sqlbuilder.SQL(', ').join(cols),
                            expr=sqlbuilder.SQL(compiled['sql']),
                            schema=sqlbuilder.Identifier(schema),
                            table=sqlbuilder.Identifier(source_name),
                            where=sqlbuilder.SQL('WHERE {0}').format(where) if where
                            else sqlbuilder.SQL(''),
                        )
                    else:
                        q = None
                if q is not None:
                    con.cursor.execute(q)
                    colnames = [d[0] for d in con.cursor.description]
                    for row in con.cursor.fetchall():
                        preview_rows.append(dict(zip(colnames, row)))
            except Exception:
                logger.exception('preview failed')

            row_count = None
            try:
                bare_where = _build_filter_where(data.get('filter'), all_columns)
                count_q = sqlbuilder.SQL('SELECT count(*) FROM {schema}.{table} {where}').format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(source_name),
                    where=sqlbuilder.SQL('WHERE {0}').format(bare_where) if bare_where
                    else sqlbuilder.SQL(''),
                )
                con.cursor.execute(count_q)
                row_count = con.cursor.fetchone()[0]
            except Exception:
                logger.exception('row count failed')

            division_by_zero_count = 0
            zero_pred = _zero_divisor_predicate(compiled.get('divisor_sqls'))
            if zero_pred is not None:
                try:
                    if where is not None:
                        zero_where = sqlbuilder.SQL('WHERE {0} AND {1}').format(where, zero_pred)
                    else:
                        zero_where = sqlbuilder.SQL('WHERE {0}').format(zero_pred)
                    if sources:
                        zero_q = sqlbuilder.SQL(
                            'SELECT count(*) FROM {schema}.{table} AS t1 {where}'
                        ).format(
                            schema=sqlbuilder.Identifier(schema),
                            table=sqlbuilder.Identifier(source_name),
                            where=zero_where,
                        )
                    else:
                        zero_q = sqlbuilder.SQL(
                            'SELECT count(*) FROM {schema}.{table} {where}'
                        ).format(
                            schema=sqlbuilder.Identifier(schema),
                            table=sqlbuilder.Identifier(source_name),
                            where=zero_where,
                        )
                    con.cursor.execute(zero_q)
                    division_by_zero_count = con.cursor.fetchone()[0]
                except Exception:
                    logger.exception('division by zero count failed')

        many_aliases = [
            alias for alias, meta in (join_sources or {}).items() if meta.get('is_many')
        ]
        return JsonResponse({
            'status': 'ok',
            'referenced_fields': compiled['referenced_fields'],
            'result_dimension': compiled['result_dimension'],
            'preview': preview_rows,
            'filtered': where is not None,
            'row_count': row_count,
            'division_by_zero_count': division_by_zero_count,
            'used_aggregates': compiled.get('used_aggregates', False),
            'one_to_many_aliases': many_aliases,
        })
    except PermissionError as exc:
        return HttpResponseForbidden(json.dumps({'status': 'error', 'message': str(exc)}),
                                     content_type='application/json')
    except (FormulaError, Layer.DoesNotExist, TypeError, ValueError) as exc:
        return _json_error(str(exc), extra=_one_to_many_hint(join_sources))
    except Exception as exc:
        logger.exception('validate calculated field')
        return _json_error(str(exc), extra=_one_to_many_hint(join_sources))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculated_field_create(request):
    """
    Create or update a double column and fill it once.

    Modes:
      - create: ADD COLUMN + UPDATE (default)
      - update: UPDATE an existing numeric column (no ADD COLUMN)
      - same layer / JOIN into current or explicitly joined layer
    """
    created_column = None
    target_layer = None
    join_sources = None
    try:
        data = _parse_json_body(request)
        layer_id = int(data.get('layer_id'))
        mode = (data.get('mode') or 'create').strip().lower()
        if mode not in ('create', 'update'):
            raise FormulaError(_('Invalid calculator mode'))
        project_layer_ids = _project_layer_ids(data.get('project_id'))
        layer = Layer.objects.select_related(
            'datastore', 'datastore__workspace', 'datastore__workspace__server', 'layer_group'
        ).get(id=layer_id)
        _ensure_layers_in_project(project_layer_ids, layer)
        source_name, schema = _ensure_manageable_postgis(request, layer, require_flag=True)

        field_name = validate_identifier((data.get('field_name') or '').lower())
        for ctrl in getattr(settings, 'CONTROL_FIELDS', []):
            if field_name == ctrl.get('name'):
                raise FormulaError(_('The field name "{0}" is a reserved name').format(field_name))
        if _valid_sql_name_regex.search(field_name) is None:
            raise FormulaError(_('Invalid field name: {0}').format(field_name))

        formula = data.get('formula') or ''
        field_units = data.get('field_units') or {}
        unit = data.get('unit')
        # On update an empty title must keep the titles the field already has
        title = (data.get('title') or '').strip()
        if not title and mode == 'create':
            title = field_name
        sources = data.get('sources') or []  # [{layer_id, alias, join_field_self, join_field_other}]
        destination_mode = data.get('destination_mode') or 'current_layer'
        if mode == 'update' and destination_mode != 'current_layer':
            # Updating an existing column is only offered on the layer the
            # calculator was opened from
            raise FormulaError(
                _('Existing attributes can only be updated on the current layer'))
        if destination_mode not in ('current_layer', 'existing_layer'):
            raise FormulaError(_('The result can only be stored in a participating layer'))
        target_layer_id = data.get('target_layer_id')

        target_layer = layer
        if destination_mode == 'existing_layer':
            if not target_layer_id:
                raise FormulaError(_('A destination layer is required'))
            source_layer_ids = {
                int(source['layer_id']) for source in sources if source.get('layer_id')
            }
            if int(target_layer_id) not in source_layer_ids:
                raise FormulaError(
                    _('The destination layer must be one of the explicitly joined layers'))
            target_layer = Layer.objects.select_related(
                'datastore', 'datastore__workspace', 'datastore__workspace__server', 'layer_group'
            ).get(id=int(target_layer_id))
            _ensure_layers_in_project(project_layer_ids, target_layer)
            _ensure_manageable_postgis(request, target_layer, require_flag=True)
            if not _same_connection(layer, target_layer):
                raise FormulaError(_('Target layer must share the same database connection'))

        iconn, t_source, t_schema = target_layer.get_db_connection()

        with iconn as con, transaction.atomic():
            # Build allowed fields and aliases
            numeric, info = _get_numeric_fields(con, schema, source_name)
            allowed = set()
            field_map = {}  # qualified or bare -> (schema, table, field, alias)

            if not sources:
                for f in numeric:
                    allowed.add(f)
                    field_map[f] = (schema, source_name, f, None)
            else:
                # t1 = current/base layer for formula references
                base_alias = 't1'
                for f in numeric:
                    q = '{0}.{1}'.format(base_alias, f)
                    allowed.add(q)
                    field_map[q] = (schema, source_name, f, base_alias)
                for idx, src in enumerate(sources):
                    other = Layer.objects.get(id=int(src['layer_id']))
                    _ensure_layers_in_project(project_layer_ids, other)
                    if not _can_read(request, other):
                        raise PermissionError(_('Not authorized to read related layer'))
                    if not _same_connection(layer, other):
                        raise FormulaError(_('All layers must share the same database connection'))
                    # same connection object already open; use schema/table from other
                    o_params = _layer_params(other)
                    o_schema = o_params.get('schema', 'public')
                    o_source = other.source_name or other.name
                    alias = validate_identifier(src.get('alias') or ('t' + str(idx + 2)))
                    onum, _oinfo = _get_numeric_fields(con, o_schema, o_source)
                    for f in onum:
                        q = '{0}.{1}'.format(alias, f)
                        allowed.add(q)
                        field_map[q] = (o_schema, o_source, f, alias)
                    join_self = validate_identifier(
                        src.get('join_field_self') or src.get('join_field_current'))
                    join_other = validate_identifier(src.get('join_field_other'))
                    src['_resolved'] = {
                        'alias': alias,
                        'schema': o_schema,
                        'table': o_source,
                        'join_self': join_self,
                        'join_other': join_other,
                        'layer': other,
                    }

                # Writing back to the base layer supports 1:N via aggregates
                # (correlated subqueries). Writing into a joined layer still
                # requires a deterministic 1:1 / N:1 lookup.
                if target_layer.id == layer.id:
                    join_sources = _build_join_sources(
                        con, [src['_resolved'] for src in sources])
                else:
                    for src in sources:
                        r = src['_resolved']
                        # Destination side can be N in an N:1 write-back; only
                        # extra lookup joins must stay unique.
                        if r['layer'].id == target_layer.id:
                            continue
                        _check_unique_join_keys(
                            con, r['schema'], r['table'], r['join_other'])

            def resolver(name):
                meta = field_map.get(name)
                if not meta:
                    raise FormulaError(_('Unknown field: {0}').format(name))
                _s, _t, field, alias = meta
                if alias:
                    return '"{0}"."{1}"'.format(alias, field)
                return '"{0}"'.format(field)

            compiled = compile_formula(
                formula, allowed, resolver,
                field_units=field_units, result_unit=data.get('unit'),
                join_sources=join_sources, base_alias='t1')
            if target_layer.id != layer.id and compiled.get('used_aggregates'):
                raise FormulaError(
                    _('Aggregations can only be used when the result is stored '
                      'on the current layer'))
            result_sql = '({0})::double precision'.format(compiled['sql'])

            existing_info = con.get_fields_info(t_source, schema=t_schema)
            existing = [f.get('name') or f.get('column_name') for f in existing_info]
            existing_types = {
                (f.get('name') or f.get('column_name')):
                    (f.get('type') or f.get('data_type') or '').lower()
                for f in existing_info
            }

            if mode == 'create':
                if field_name in existing:
                    raise FormulaError(_('Field already exists: {0}').format(field_name))
                con.add_column(t_schema, t_source, field_name, 'double precision')
                created_column = (t_schema, t_source, field_name)
            else:
                if field_name not in existing:
                    raise FormulaError(_('Field does not exist: {0}').format(field_name))
                pks = set(con.get_pk_columns(t_source, t_schema) or [])
                geoms = set(con.get_geometry_columns(t_source, t_schema) or [])
                if field_name in pks:
                    raise FormulaError(_('Cannot update the primary key'))
                if field_name in geoms:
                    raise FormulaError(_('Cannot update a geometry column'))
                dtype = existing_types.get(field_name, '')
                if dtype not in _NUMERIC_TYPES:
                    raise FormulaError(
                        _('Only numeric fields can be updated: {0}').format(field_name))

            # Only the rows the user has filtered in the attribute table get a
            # value; the rest stay untouched (NULL on create, previous value on update)
            base_columns = {f.get('name') or f.get('column_name') for f in info}
            table_filter = data.get('filter')

            if not sources:
                row_filter = _build_filter_where(table_filter, base_columns)
                update_q = sqlbuilder.SQL(
                    'UPDATE {schema}.{table} SET {field} = {expr} {where}'
                ).format(
                    schema=sqlbuilder.Identifier(t_schema),
                    table=sqlbuilder.Identifier(t_source),
                    field=sqlbuilder.Identifier(field_name),
                    expr=sqlbuilder.SQL(result_sql),
                    where=sqlbuilder.SQL('WHERE {0}').format(row_filter) if row_filter
                    else sqlbuilder.SQL(''),
                )
                con.cursor.execute(update_q)
            elif target_layer.id == layer.id:
                # Base-layer destination: expression already embeds correlated
                # subqueries for joins / aggregates, so no FROM join is needed.
                target_alias = '__calculated_target'
                rewritten = compiled['sql'].replace(
                    '"t1".', '"{0}".'.format(target_alias))
                row_filter = _build_filter_where(
                    table_filter, base_columns, alias=target_alias)
                result_sql2 = '({0})::double precision'.format(rewritten)
                update_q = sqlbuilder.SQL(
                    'UPDATE {schema}.{table} AS {target} '
                    'SET {field} = {expr} {where}'
                ).format(
                    schema=sqlbuilder.Identifier(t_schema),
                    table=sqlbuilder.Identifier(t_source),
                    target=sqlbuilder.Identifier(target_alias),
                    field=sqlbuilder.Identifier(field_name),
                    expr=sqlbuilder.SQL(result_sql2),
                    where=sqlbuilder.SQL('WHERE {0}').format(row_filter) if row_filter
                    else sqlbuilder.SQL(''),
                )
                con.cursor.execute(update_q)
            else:
                # Writing into a joined layer: classic UPDATE ... FROM join.
                # Requires unique keys on the lookup side (checked above).
                target_alias = '__calculated_target'
                target_sources = [
                    src for src in sources
                    if src['_resolved']['layer'].id == target_layer.id
                ]
                if len(target_sources) != 1:
                    raise FormulaError(
                        _('The destination layer must occur exactly once in the JOIN'))

                from_clauses = []
                where_parts = []
                target_r = target_sources[0]['_resolved']
                # Updating the joined side is only deterministic for a
                # one-to-one relation in this direction.
                _check_unique_join_keys(
                    con, schema, source_name, target_r['join_self'])
                rewritten = compiled['sql'].replace(
                    '"{0}".'.format(target_r['alias']),
                    '"{0}".'.format(target_alias))
                from_clauses.append(sqlbuilder.SQL(
                    '{schema}.{table} AS t1'
                ).format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(source_name),
                ))
                where_parts.append(sqlbuilder.SQL(
                    't1.{js} = {target}.{jo}'
                ).format(
                    js=sqlbuilder.Identifier(target_r['join_self']),
                    target=sqlbuilder.Identifier(target_alias),
                    jo=sqlbuilder.Identifier(target_r['join_other']),
                ))

                for src in sources:
                    r = src['_resolved']
                    if r['layer'].id == target_layer.id:
                        continue
                    from_clauses.append(sqlbuilder.SQL(
                        '{schema}.{table} AS {alias}'
                    ).format(
                        schema=sqlbuilder.Identifier(r['schema']),
                        table=sqlbuilder.Identifier(r['table']),
                        alias=sqlbuilder.Identifier(r['alias']),
                    ))
                    where_parts.append(sqlbuilder.SQL(
                        't1.{js} = {alias}.{jo}'
                    ).format(
                        js=sqlbuilder.Identifier(r['join_self']),
                        alias=sqlbuilder.Identifier(r['alias']),
                        jo=sqlbuilder.Identifier(r['join_other']),
                    ))

                row_filter = _build_filter_where(
                    table_filter, base_columns, alias='t1')
                if row_filter is not None:
                    where_parts.append(row_filter)

                result_sql2 = '({0})::double precision'.format(rewritten)
                update_q = sqlbuilder.SQL(
                    'UPDATE {schema}.{table} AS {target} '
                    'SET {field} = {expr} FROM {joins} WHERE {where}'
                ).format(
                    schema=sqlbuilder.Identifier(t_schema),
                    table=sqlbuilder.Identifier(t_source),
                    target=sqlbuilder.Identifier(target_alias),
                    field=sqlbuilder.Identifier(field_name),
                    expr=sqlbuilder.SQL(result_sql2),
                    joins=sqlbuilder.SQL(', ').join(from_clauses),
                    where=sqlbuilder.SQL(' AND ').join(where_parts),
                )
                con.cursor.execute(update_q)

            conf_manager = _refresh_layer_publication(target_layer)
            titles = {
                'title-' + lang_code: title
                for lang_code, _lang_name in getattr(settings, 'LANGUAGES', (('es', 'Spanish'),))
            } if title else None
            _store_field_meta(
                target_layer, field_name, formula, unit=unit,
                dimension=compiled.get('result_dimension'),
                extra=titles,
                conf_manager=conf_manager,
            )

        return JsonResponse({
            'status': 'ok',
            'mode': mode,
            'field_name': field_name,
            'layer_id': target_layer.id,
            'layer_name': target_layer.name,
            'destination_mode': destination_mode,
            'result_dimension': compiled.get('result_dimension'),
            'one_to_many_aliases': [
                alias for alias, meta in (join_sources or {}).items()
                if meta.get('is_many')
            ],
        })

    except PermissionError as exc:
        return HttpResponseForbidden(json.dumps({'status': 'error', 'message': str(exc)}),
                                     content_type='application/json')
    except (FormulaError, Layer.DoesNotExist, TypeError, ValueError) as exc:
        # best-effort cleanup
        try:
            if created_column and target_layer:
                iconn, _t_source, _t_schema = target_layer.get_db_connection()
                with iconn as con:
                    con.delete_column(created_column[0], created_column[1], created_column[2])
        except Exception:
            logger.exception('cleanup column failed')
        return _json_error(str(exc), extra=_one_to_many_hint(join_sources))
    except Exception as exc:
        logger.exception('create calculated field')
        return _json_error(str(exc), extra=_one_to_many_hint(join_sources))
