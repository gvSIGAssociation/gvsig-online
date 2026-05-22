# -*- coding: utf-8 -*-
"""PostGIS ↔ GPKG transfers via pygdaltools (gdaltools), same as the rest of gvSIG Online."""
import logging
import os
import re
import shutil

from django.conf import settings

LOG = logging.getLogger('gvsigol')

_GPKG_LAYER_LINE = re.compile(r'^\s*\d+:\s+(.+?)\s*$')


def is_gdal_available():
    """True when pygdaltools/GDAL is configured and reachable."""
    try:
        import gdaltools

        gdaltools.ogr2ogr().get_version_tuple()
        return True
    except Exception:
        return False


def pg_connection_from_params(params, schema=None):
    import gdaltools

    if not params:
        raise ValueError('Missing PostGIS connection parameters')
    host = params.get('host', 'localhost')
    port = str(params.get('port', '5432'))
    dbname = params.get('database', '')
    user = params.get('user', '')
    password = params.get('passwd', params.get('password', ''))
    if schema is None:
        schema = params.get('schema') or 'public'
    return gdaltools.PgConnectionString(
        host=host,
        port=port,
        dbname=dbname,
        schema=schema,
        user=user,
        password=password,
    )


def pg_connection_from_cartodb(schema=None):
    c = settings.GVSIGOL_USERS_CARTODB
    return pg_connection_from_params(
        {
            'host': c.get('dbhost', 'localhost'),
            'port': c.get('dbport', '5432'),
            'database': c.get('dbname', ''),
            'user': c.get('dbuser', ''),
            'passwd': c.get('dbpassword', ''),
            'schema': schema or 'public',
        },
        schema=schema,
    )


def pg_connection_from_datastore(datastore, schema=None):
    params = dict(datastore.get_connection_params_dict())
    if schema:
        params['schema'] = schema
    elif not params.get('schema'):
        getter = getattr(datastore, 'get_schema_name', None)
        if getter:
            params['schema'] = getter() or 'public'
    return pg_connection_from_params(params, schema=params.get('schema'))


def _execute_ogr(ogr, operation_label):
    import gdaltools

    safe_args = getattr(ogr, 'safe_args', None) or []
    preview = ' '.join(str(a) for a in safe_args[:10])
    if len(safe_args) > 10:
        preview += ' ...'
    LOG.info('%s: %s', operation_label, preview)
    try:
        ogr.execute()
    except gdaltools.GdalToolsError as ex:
        detail = str(ex).strip() or 'gdaltools ogr2ogr failed'
        stderr = (getattr(ogr, 'stderr', None) or '').strip()
        if stderr:
            detail = '%s — %s' % (detail, stderr[:2000])
        LOG.error('%s failed: %s', operation_label, detail)
        raise RuntimeError(detail) from ex
    stderr = (getattr(ogr, 'stderr', None) or '').strip()
    if stderr:
        LOG.warning('%s stderr: %s', operation_label, stderr[:2000])


def _decode_ogrinfo_output(info_str):
    if info_str is None:
        return ''
    if isinstance(info_str, bytes):
        try:
            import sys

            enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
        except Exception:
            enc = 'utf-8'
        return info_str.decode(enc, errors='replace')
    return str(info_str)


def list_gpkg_layers(gpkg_path):
    """Return layer names inside a GeoPackage using gdaltools.ogrinfo."""
    import gdaltools

    gpkg_path = os.path.abspath(gpkg_path)
    layers = []
    seen = set()

    def _add(name):
        name = (name or '').strip()
        if name and name not in seen:
            seen.add(name)
            layers.append(name)

    try:
        info_str = _decode_ogrinfo_output(
            gdaltools.ogrinfo(gpkg_path, alltables=True, readonly=True)
        )
        for line in info_str.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith('layer name:'):
                _add(stripped.split(':', 1)[1])
            else:
                match = _GPKG_LAYER_LINE.match(line)
                if match:
                    _add(match.group(1))
    except Exception as ex:
        LOG.warning('Could not list GPKG layers via gdaltools: %s', ex, exc_info=True)
    return layers


def export_postgis_to_gpkg(schema, table, dest_gpkg, pg_conn=None):
    """
    Export a PostGIS table to GeoPackage. Returns the layer name stored in the GPKG.
    pg_conn: gdaltools.PgConnectionString (or None for default CartoDB).
    """
    import gdaltools

    for ident in (schema, table):
        if not ident or not all(c.isalnum() or c in '_-' for c in ident):
            raise ValueError('Invalid schema or table name for export')
    if pg_conn is None:
        pg_conn = pg_connection_from_cartodb(schema=schema)

    gpkg_layer = table
    dest_gpkg = os.path.abspath(dest_gpkg)
    os.makedirs(os.path.dirname(dest_gpkg), exist_ok=True)

    ogr = gdaltools.ogr2ogr()
    sql = 'SELECT * FROM "%s"."%s"' % (
        schema.replace('"', '""'),
        table.replace('"', '""'),
    )
    ogr.set_input(pg_conn)
    ogr.set_sql(sql)
    # pygdaltools defaults unknown extensions to ESRI Shapefile (10-char field names,
    # directory output). Must force GPKG explicitly.
    ogr.set_output(dest_gpkg, file_type='GPKG', table_name=gpkg_layer)
    ogr.set_output_mode(
        layer_mode=ogr.MODE_LAYER_CREATE,
        data_source_mode=ogr.MODE_DS_CREATE,
    )
    ogr.layer_creation_options = {'IDENTIFIER': gpkg_layer}
    _execute_ogr(ogr, 'export_postgis_to_gpkg')
    if not os.path.isfile(dest_gpkg):
        raise RuntimeError(
            'GeoPackage export did not create file "%s". Check GDAL logs.'
            % dest_gpkg
        )
    return gpkg_layer


def import_gpkg_to_postgis(gpkg_path, gpkg_layer, pg_conn, table_name, schema):
    """Load one GPKG layer into PostGIS (create table)."""
    import gdaltools

    gpkg_path = os.path.abspath(gpkg_path)
    ogr = gdaltools.ogr2ogr()
    ogr.set_input(gpkg_path, table_name=gpkg_layer)
    ogr.set_output(pg_conn, table_name=table_name)
    ogr.set_output_mode(
        layer_mode=ogr.MODE_LAYER_CREATE,
        data_source_mode=ogr.MODE_DS_UPDATE,
    )
    ogr.layer_creation_options = {
        'SCHEMA': schema,
        'GEOMETRY_NAME': 'wkb_geometry',
        'LAUNDER': 'NO',
    }
    _execute_ogr(ogr, 'import_gpkg_to_postgis')
