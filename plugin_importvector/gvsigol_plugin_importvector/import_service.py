import csv
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import psycopg2
from psycopg2 import sql
from django.core.exceptions import ValidationError

from gvsigol_services.layer_publish import publish_postgis_resource
from gvsigol_services.shp2postgis import read_encoding

logger = logging.getLogger(__name__)

# Municipal / cadastral WKT often exceeds csv's default 128 KiB field limit.
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(16 * 1024 * 1024)


VALID_EXTENSIONS = {'.zip', '.shp', '.kml', '.geojson', '.json', '.csv'}
VALID_SQL_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
WKT_COLUMN_CANDIDATES = (
    'wkt', 'geom', 'geometry', 'the_geom', 'wkb_geometry', 'shape', 'geo',
)
DELIMITER_TO_OGR = {
    ',': 'COMMA',
    ';': 'SEMICOLON',
    '\t': 'TAB',
    '|': 'PIPE',
}
# Map concrete PostGIS/GeoServer subtypes used after CSV WKT import.
_SINGLE_TO_MULTI = {
    'POINT': 'MULTIPOINT',
    'LINESTRING': 'MULTILINESTRING',
    'POLYGON': 'MULTIPOLYGON',
}
_VRT_GEOMETRY_TYPE = {
    'POINT': 'wkbPoint',
    'MULTIPOINT': 'wkbMultiPoint',
    'LINESTRING': 'wkbLineString',
    'MULTILINESTRING': 'wkbMultiLineString',
    'POLYGON': 'wkbPolygon',
    'MULTIPOLYGON': 'wkbMultiPolygon',
}
_WKT_TYPE_RE = re.compile(
    r'^\s*(?:SRID=\d+\s*;\s*)?(MULTI)?(POINT|LINESTRING|POLYGON|GEOMETRYCOLLECTION)\b',
    re.IGNORECASE,
)


def _safe_extract_shapefile(zip_path, target_dir):
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = os.path.realpath(os.path.join(target_dir, member.filename))
            if not target.startswith(os.path.realpath(target_dir) + os.sep):
                raise ValidationError('The ZIP file contains an unsafe path')
        archive.extractall(target_dir)
    shapes = []
    for root, _, files in os.walk(target_dir):
        shapes.extend(
            os.path.join(root, name) for name in files
            if name.lower().endswith('.shp')
        )
    if len(shapes) != 1:
        raise ValidationError('The ZIP file must contain exactly one Shapefile')
    stem = os.path.splitext(shapes[0])[0]
    if not os.path.exists(stem + '.dbf') and not os.path.exists(stem + '.DBF'):
        raise ValidationError('The Shapefile is missing its DBF file')
    return shapes[0]


_PREFERRED_JSON_ROOT_KEYS = (
    'features', 'items', 'data', 'results', 'records', 'rows', 'list', 'values',
)


def _is_object_array(value):
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(row, dict) for row in value)
    )


def _find_json_table_roots(value, prefix='', max_depth=6):
    """Return (path, count) candidates for tabular arrays inside nested JSON."""
    if isinstance(value, dict) and value.get('type') in {
            'FeatureCollection', 'Feature'}:
        return []
    roots = []
    if _is_object_array(value):
        roots.append((prefix, len(value)))
        return roots
    if not isinstance(value, dict) or max_depth <= 0:
        return roots
    for key, child in value.items():
        path = '{}.{}'.format(prefix, key) if prefix else key
        if _is_object_array(child):
            roots.append((path, len(child)))
        elif isinstance(child, dict):
            roots.extend(_find_json_table_roots(child, path, max_depth - 1))
    return roots


def _score_json_root(path, count):
    leaf = (path.split('.')[-1] if path else '').lower()
    try:
        preferred = _PREFERRED_JSON_ROOT_KEYS.index(leaf)
        name_bonus = (len(_PREFERRED_JSON_ROOT_KEYS) - preferred) * 1000
    except ValueError:
        name_bonus = 0
    return name_bonus + int(count or 0)


def _suggest_json_root(roots):
    if not roots:
        return None
    return max(roots, key=lambda item: _score_json_root(item[0], item[1]))[0]


def _resolve_json_table_rows(value, root=None):
    if isinstance(value, dict) and value.get('type') in {
            'FeatureCollection', 'Feature'}:
        return None
    if root:
        current = value
        for part in str(root).split('.'):
            current = current.get(part) if isinstance(current, dict) else None
        return current if _is_object_array(current) else None
    if _is_object_array(value):
        return value
    if isinstance(value, dict):
        suggested = _suggest_json_root(_find_json_table_roots(value))
        if suggested:
            return _resolve_json_table_rows(value, suggested)
    return None


def _json_to_csv(json_path, target_dir, root=None):
    with open(json_path, encoding='utf-8-sig') as source:
        value = json.load(source)
    if isinstance(value, dict) and value.get('type') in {
            'FeatureCollection', 'Feature'}:
        return json_path, True
    rows = _resolve_json_table_rows(value, root=root or None)
    if rows is None:
        raise ValidationError(
            'Non-GeoJSON JSON must contain an array of objects. '
            'Pass json_root (e.g. response.items) if the array is nested.')
    columns = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    if not columns:
        raise ValidationError('The JSON table is empty')
    csv_path = os.path.join(target_dir, 'json_table.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(item, ensure_ascii=False)
                if isinstance(item, (dict, list)) else item
                for key, item in row.items()
            })
    return csv_path, False


def _connection_params(datastore):
    params = datastore.get_connection_params_dict()
    required = ('host', 'port', 'database', 'user')
    if any(not params.get(key) for key in required):
        raise ValidationError('The selected datastore has an incomplete connection')
    return params


def _has_geometry(params, schema, table):
    connection = psycopg2.connect(
        host=params['host'], port=params['port'],
        dbname=params['database'], user=params['user'],
        password=params.get('passwd', params.get('password', '')),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM geometry_columns
                    WHERE f_table_schema = %s AND f_table_name = %s
                )
                """,
                [schema, table],
            )
            return bool(cursor.fetchone()[0])
    finally:
        connection.close()


def _drop_geometry_columns(params, schema, table):
    """Remove PostGIS geometry columns when importing CSV as a plain table."""
    connection = psycopg2.connect(
        host=params['host'], port=params['port'],
        dbname=params['database'], user=params['user'],
        password=params.get('passwd', params.get('password', '')),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT f_geometry_column FROM geometry_columns
                WHERE f_table_schema = %s AND f_table_name = %s
                """,
                [schema, table],
            )
            columns = [row[0] for row in cursor.fetchall()]
            for column in columns:
                cursor.execute(
                    sql.SQL('ALTER TABLE {}.{} DROP COLUMN IF EXISTS {} CASCADE').format(
                        sql.Identifier(schema),
                        sql.Identifier(table),
                        sql.Identifier(column),
                    )
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _table_exists(params, schema, table):
    connection = psycopg2.connect(
        host=params['host'], port=params['port'],
        dbname=params['database'], user=params['user'],
        password=params.get('passwd', params.get('password', '')),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                )
                """,
                [schema, table],
            )
            return bool(cursor.fetchone()[0])
    finally:
        connection.close()


def _drop_table(params, schema, table):
    connection = psycopg2.connect(
        host=params['host'], port=params['port'],
        dbname=params['database'], user=params['user'],
        password=params.get('passwd', params.get('password', '')),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL('DROP TABLE IF EXISTS {}.{} CASCADE').format(
                    sql.Identifier(schema), sql.Identifier(table)))
        connection.commit()
    finally:
        connection.close()


def _detect_csv_delimiter(sample_line):
    counts = {
        ';': sample_line.count(';'),
        ',': sample_line.count(','),
        '\t': sample_line.count('\t'),
        '|': sample_line.count('|'),
    }
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ','


def _read_csv_headers(csv_path, delimiter=None):
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as source:
        sample = source.readline()
        if not sample:
            return [], delimiter or ','
        resolved = delimiter or _detect_csv_delimiter(sample)
        source.seek(0)
        reader = csv.reader(source, delimiter=resolved)
        headers = next(reader, [])
    return [header.strip() for header in headers if str(header).strip()], resolved


def _guess_wkt_column(headers):
    by_lower = {header.lower(): header for header in headers}
    for candidate in WKT_COLUMN_CANDIDATES:
        if candidate in by_lower:
            return by_lower[candidate]
    for header in headers:
        lowered = header.lower()
        if 'wkt' in lowered or lowered.endswith('_geom') or lowered.startswith('geom'):
            return header
    return None


def _launder_name(name):
    """Approximate GDAL LAUNDER=YES for PostgreSQL column names."""
    cleaned = re.sub(r'[^A-Za-z0-9_]', '_', (name or '').lower())
    if cleaned and cleaned[0].isdigit():
        cleaned = '_' + cleaned
    return cleaned[:63] or 'geom_text'


def _srs_to_srid(srs):
    if not srs:
        return 4326
    match = re.search(r'(\d+)\s*$', str(srs))
    return int(match.group(1)) if match else 4326


def _detect_csv_wkt_geometry_type(
        csv_path, wkt_column, delimiter=',', promote_to_multi=True,
        sample_limit=50):
    """
    Infer a concrete GeoServer-friendly subtype (e.g. MULTIPOLYGON) from WKT
    samples. Returns None when the type cannot be determined safely.
    """
    try:
        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source, delimiter=delimiter)
            if not reader.fieldnames or wkt_column not in reader.fieldnames:
                return None
            seen = set()
            sampled = 0
            for row in reader:
                raw = (row.get(wkt_column) or '').strip().strip('"')
                if not raw:
                    continue
                match = _WKT_TYPE_RE.match(raw)
                if not match:
                    continue
                base = match.group(2).upper()
                if base == 'GEOMETRYCOLLECTION':
                    return None
                geom_type = (
                    'MULTI' + base if match.group(1) else base
                )
                if promote_to_multi and geom_type in _SINGLE_TO_MULTI:
                    geom_type = _SINGLE_TO_MULTI[geom_type]
                seen.add(geom_type)
                sampled += 1
                if len(seen) > 1:
                    return None
                if sampled >= sample_limit:
                    break
            if len(seen) == 1:
                return next(iter(seen))
    except OSError:
        return None
    return None


def _build_csv_wkt_vrt(csv_path, workdir, wkt_column, srs=None,
                       geometry_type=None):
    """Build a VRT so GDAL always treats the chosen column as WKT geometry."""
    layer_name = os.path.splitext(os.path.basename(csv_path))[0]
    vrt_path = os.path.join(workdir, 'source_wkt.vrt')
    srs_xml = ''
    if srs:
        srs_xml = '<LayerSRS>{}</LayerSRS>\n'.format(srs)
    vrt_geom = _VRT_GEOMETRY_TYPE.get(
        (geometry_type or '').upper(), 'wkbUnknown')
    # Escape XML special chars in field/layer names.
    safe_field = (
        wkt_column.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
    )
    safe_layer = (
        layer_name.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
    )
    abs_csv = os.path.realpath(csv_path)
    content = (
        '<OGRVRTDataSource>\n'
        '  <OGRVRTLayer name="{layer}">\n'
        '    <SrcDataSource>{csv}</SrcDataSource>\n'
        '    <SrcLayer>{layer}</SrcLayer>\n'
        '    <GeometryType>{geom_type}</GeometryType>\n'
        '    {srs}'
        '    <GeometryField encoding="WKT" field="{field}"/>\n'
        '  </OGRVRTLayer>\n'
        '</OGRVRTDataSource>\n'
    ).format(
        layer=safe_layer, csv=abs_csv, srs=srs_xml, field=safe_field,
        geom_type=vrt_geom)
    with open(vrt_path, 'w', encoding='utf-8') as target:
        target.write(content)
    return vrt_path


def _narrow_postgis_geometry(datastore, schema, table, geom_subtype=None):
    """
    Narrow generic geometry(Geometry, srid) to a concrete subtype so GeoServer
    can bind a default style / legend. Same pattern as GPKG package import.
    """
    intro = None
    try:
        intro, _params = datastore.get_db_connection()
        if not intro:
            return
        intro.promote_untyped_geometry_columns(schema, table)
        hint = (geom_subtype or '').strip().upper()
        if hint and hint in _VRT_GEOMETRY_TYPE:
            intro.promote_untyped_geometry_columns_hint(schema, table, hint)
    finally:
        if intro:
            intro.close()


def _list_text_columns(params, schema, table):
    connection = psycopg2.connect(
        host=params['host'], port=params['port'],
        dbname=params['database'], user=params['user'],
        password=params.get('passwd', params.get('password', '')),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                  AND data_type IN ('character varying', 'text', 'character')
                ORDER BY ordinal_position
                """,
                [schema, table],
            )
            return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def _promote_wkt_text_to_geometry(
        params, schema, table, wkt_column, srs, geometry_type=None):
    """Fallback when ogr2ogr left the WKT column as plain text."""
    laundered = _launder_name(wkt_column)
    text_columns = _list_text_columns(params, schema, table)
    source_column = None
    for candidate in (laundered, wkt_column, wkt_column.lower()):
        if candidate in text_columns:
            source_column = candidate
            break
    if not source_column:
        for column in text_columns:
            if column.lower() in {c.lower() for c in WKT_COLUMN_CANDIDATES}:
                source_column = column
                break
    if not source_column:
        return False

    srid = _srs_to_srid(srs)
    concrete = (geometry_type or '').strip().upper()
    if concrete not in _VRT_GEOMETRY_TYPE:
        concrete = None
    # Prefer ST_Multi when narrowing to a MULTI* subtype so POLYGON WKT
    # lands as MultiPolygon (GeoServer-friendly).
    use_st_multi = concrete in (
        'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON',
    )
    if concrete:
        add_geom_sql = sql.SQL(
            'ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS geom geometry({}, {})'
        ).format(
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.SQL(concrete),
            sql.Literal(srid),
        )
    else:
        add_geom_sql = sql.SQL(
            'ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS geom geometry'
        ).format(sql.Identifier(schema), sql.Identifier(table))

    if use_st_multi:
        set_geom_sql = sql.SQL(
            """
            UPDATE {}.{}
            SET geom = ST_Multi(ST_SetSRID(ST_GeomFromText({}), %s))
            WHERE {} IS NOT NULL
              AND btrim({}::text) <> ''
              AND geom IS NULL
            """
        ).format(
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.Identifier(source_column),
            sql.Identifier(source_column),
            sql.Identifier(source_column),
        )
    else:
        set_geom_sql = sql.SQL(
            """
            UPDATE {}.{}
            SET geom = ST_SetSRID(ST_GeomFromText({}), %s)
            WHERE {} IS NOT NULL
              AND btrim({}::text) <> ''
              AND geom IS NULL
            """
        ).format(
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.Identifier(source_column),
            sql.Identifier(source_column),
            sql.Identifier(source_column),
        )

    connection = psycopg2.connect(
        host=params['host'], port=params['port'],
        dbname=params['database'], user=params['user'],
        password=params.get('passwd', params.get('password', '')),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(add_geom_sql)
            cursor.execute(set_geom_sql, [srid])
            cursor.execute(
                sql.SQL(
                    'CREATE INDEX IF NOT EXISTS {} ON {}.{} USING GIST (geom)'
                ).format(
                    sql.Identifier('{}_geom_idx'.format(table)[:63]),
                    sql.Identifier(schema),
                    sql.Identifier(table),
                )
            )
            # Keep attribute table tidy: drop the original text WKT column.
            if source_column != 'geom':
                cursor.execute(
                    sql.SQL('ALTER TABLE {}.{} DROP COLUMN IF EXISTS {}').format(
                        sql.Identifier(schema),
                        sql.Identifier(table),
                        sql.Identifier(source_column),
                    )
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return _has_geometry(params, schema, table)


def import_uploaded_resource(upload, datastore, layer_group, user, options):
    """Import an uploaded supported file into PostGIS and register it."""
    name = (options.get('name') or '').lower()
    if not VALID_SQL_NAME.match(name):
        raise ValidationError(
            'Name must start with a letter or underscore and contain only '
            'letters, numbers and underscores')
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in VALID_EXTENSIONS:
        raise ValidationError('Unsupported file format')

    workdir = tempfile.mkdtemp(prefix='project_import_')
    try:
        uploaded_path = os.path.join(workdir, 'source' + extension)
        with open(uploaded_path, 'wb') as target:
            for chunk in upload.chunks():
                target.write(chunk)

        source_path = uploaded_path
        source_is_geojson = extension == '.geojson'
        if extension == '.zip':
            source_path = _safe_extract_shapefile(uploaded_path, workdir)
        elif extension == '.json':
            source_path, source_is_geojson = _json_to_csv(
                uploaded_path, workdir, options.get('json_root'))

        params = _connection_params(datastore)
        schema = datastore.get_schema_name()
        if _table_exists(params, schema, name):
            raise ValidationError(
                'A table with this name already exists in the datastore')
        ogr2ogr = shutil.which('ogr2ogr')
        if not ogr2ogr:
            raise RuntimeError('ogr2ogr is not installed on the server')
        pg_dsn = (
            "PG:host={host} port={port} dbname={database} user={user}"
        ).format(**params)

        srs = options.get('srs') or None
        encoding = options.get('encoding')
        wkt_column = options.get('wkt_column') or None
        if isinstance(wkt_column, str):
            wkt_column = wkt_column.strip() or None
        # True unless the client explicitly sent wkt_column (even empty = no geom).
        auto_detect_wkt = options.get('auto_detect_wkt', True)
        expected_geometry = False
        force_tabular = False
        detected_geom_type = None
        open_options = []
        config_options = []
        nlt = 'PROMOTE_TO_MULTI'

        if extension == '.csv' or (
                extension == '.json' and not source_is_geojson):
            headers, detected_delimiter = _read_csv_headers(
                source_path, options.get('delimiter') or None)
            if not wkt_column and auto_detect_wkt:
                wkt_column = _guess_wkt_column(headers)
            elif not wkt_column and not auto_detect_wkt:
                # User cleared the WKT column → import as alphanumeric table.
                force_tabular = True
            if wkt_column and wkt_column not in headers:
                raise ValidationError(
                    'The selected WKT column "{}" was not found in the CSV'
                    .format(wkt_column))
            expected_geometry = bool(wkt_column)
            separator = options.get('delimiter') or detected_delimiter
            ogr_separator = DELIMITER_TO_OGR.get(separator)
            if ogr_separator:
                # Prefer config option: some GDAL builds warn on -oo SEPARATOR.
                config_options.extend(
                    ['--config', 'OGR_CSV_SEPARATOR', ogr_separator])
            if encoding and encoding != 'autodetect':
                open_options.extend(['-oo', 'ENCODING={}'.format(encoding)])
            if wkt_column:
                detected_geom_type = _detect_csv_wkt_geometry_type(
                    source_path, wkt_column, delimiter=separator)
                # VRT is the most reliable way to force WKT → geometry.
                # Concrete GeometryType helps GDAL; PostGIS typmod is narrowed
                # after load (ogr often still creates geometry(Geometry,srid)).
                source_path = _build_csv_wkt_vrt(
                    source_path, workdir, wkt_column, srs=srs,
                    geometry_type=detected_geom_type)
            elif force_tabular:
                # Plain alphanumeric table: keep every CSV column as text,
                # including WKT/geometry fields the user chose not to map.
                # GDAL still auto-probes names like wkt/geom/geometry unless we
                # override GEOM_POSSIBLE_NAMES; that would eat the attribute.
                nlt = 'NONE'
                open_options.extend([
                    '-oo', 'GEOM_POSSIBLE_NAMES=__no_geometry__',
                    '-oo', 'KEEP_GEOM_COLUMNS=YES',
                ])
            else:
                # No explicit column: help GDAL autodetect common names.
                open_options.extend([
                    '-oo',
                    'GEOM_POSSIBLE_NAMES={}'.format(
                        ','.join(WKT_COLUMN_CANDIDATES)),
                    '-oo', 'KEEP_GEOM_COLUMNS=NO',
                ])

        command = [ogr2ogr]
        command.extend(config_options)
        command.extend([
            '-f', 'PostgreSQL', pg_dsn, source_path,
            '-nln', '{}.{}'.format(schema, name),
            # PROMOTE_TO_MULTI for spatial layers; NONE for forced tabular CSV.
            '-nlt', nlt,
            '-lco', 'FID=ogc_fid', '-lco', 'LAUNDER=YES',
        ])
        if nlt != 'NONE':
            command.extend(['-lco', 'GEOMETRY_NAME=geom'])
        if srs and not force_tabular:
            command.extend(['-a_srs', srs])
        command.extend(open_options)

        if extension in ('.zip', '.shp'):
            shape_encoding = encoding
            if not shape_encoding or shape_encoding == 'autodetect':
                shape_encoding = read_encoding(source_path)
            # When a CPG is present GDAL reads it itself and read_encoding
            # intentionally returns None. Otherwise use File Manager's
            # detected/fallback encoding.
            if shape_encoding and shape_encoding != 'autodetect':
                command[1:1] = [
                    '--config', 'SHAPE_ENCODING', shape_encoding]
        environment = os.environ.copy()
        environment['PGPASSWORD'] = params.get(
            'passwd', params.get('password', ''))
        result = subprocess.run(
            command, env=environment, capture_output=True,
            timeout=3600,
        )
        stderr = result.stderr.decode('utf-8', errors='replace')
        if result.returncode:
            raise ValidationError(
                'The file could not be imported: {}'.format(
                    stderr.strip()[-1000:]))

        has_geometry = _has_geometry(params, schema, name)
        if force_tabular:
            # Honour explicit "no geometry" even if ogr left a residual geom col.
            if has_geometry:
                _drop_geometry_columns(params, schema, name)
            has_geometry = False
        if not has_geometry and wkt_column:
            # Fallback: convert leftover text WKT into a real geometry column.
            try:
                has_geometry = _promote_wkt_text_to_geometry(
                    params, schema, name, wkt_column, srs,
                    geometry_type=detected_geom_type)
            except Exception as exc:
                raise ValidationError(
                    'The CSV was imported but the WKT column "{}" could not '
                    'be converted to geometry: {}'.format(
                        wkt_column, exc)
                ) from exc
        if expected_geometry and not has_geometry:
            _drop_table(params, schema, name)
            raise ValidationError(
                'The selected WKT column "{}" did not produce a geometry. '
                'Check the column, the CSV separator and that values are valid WKT.'
                .format(wkt_column))

        if has_geometry:
            # GeoServer needs geometry(MultiPolygon,srid) etc., not Geometry.
            try:
                _narrow_postgis_geometry(
                    datastore, schema, name,
                    geom_subtype=detected_geom_type)
            except Exception as exc:
                # Publishing may still succeed; style/legend can be wrong.
                logger.warning(
                    'Could not narrow geometry column after import %s.%s: %s',
                    schema, name, exc, exc_info=True)


        # Persist effective options used during import (useful for debugging).
        if wkt_column:
            options = dict(options or {})
            options['wkt_column'] = wkt_column
        if detected_geom_type:
            options = dict(options or {})
            options['geometry_type'] = detected_geom_type
        if srs:
            options = dict(options or {})
            options.setdefault('native_srs', srs)

        try:
            layer = publish_postgis_resource(
                user=user,
                datastore=datastore,
                layer_group=layer_group,
                name=name,
                title=options.get('title') or name,
                has_geometry=has_geometry,
                properties=options,
                read_roles=options.get('read_roles'),
                write_roles=options.get('write_roles'),
                manage_roles=options.get('manage_roles'),
                is_public=options.get('is_public', False),
            )
        except Exception:
            _drop_table(params, schema, name)
            raise
        return layer, has_geometry
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
