# -*- coding: utf-8 -*-
"""Helpers to classify PostGIS datastores (local vs foreign) for project packages."""
import hashlib
import json

from django.conf import settings

from gvsigol_services.models import Connection, Datastore, Layer


def _cartodb_params():
    c = settings.GVSIGOL_USERS_CARTODB
    return {
        'host': c.get('dbhost', 'localhost'),
        'port': str(c.get('dbport', '5432')),
        'database': c.get('dbname', ''),
        'user': c.get('dbuser', ''),
    }


def _params_fingerprint(params):
    if not params:
        return ''
    host = str(params.get('host', ''))
    port = str(params.get('port', '5432'))
    database = str(params.get('database', ''))
    user = str(params.get('user', ''))
    return '%s:%s:%s:%s' % (host, port, database, user)


def is_local_cartodb_params(params):
    return _params_fingerprint(params) == _params_fingerprint(_cartodb_params())


def pg_conn_string_from_params(params):
    host = params.get('host', 'localhost')
    port = params.get('port', '5432')
    dbname = params.get('database', '')
    user = params.get('user', '')
    passwd = params.get('passwd', params.get('password', ''))
    return (
        'PG:host=%s port=%s dbname=%s user=%s password=%s'
        % (host, port, dbname, user, passwd)
    )


def datastore_connection_key(datastore):
    """
    Stable key to group layers that share the same DB connection in import wizard.
    Local CartoDB datastores always return 'local_cartodb', even if they happen
    to have a Connection object pointing to localhost.
    """
    if datastore is None:
        return 'unknown'
    # Check local first: a Connection pointing to localhost is still local.
    if is_local_cartodb_params(datastore.get_connection_params_dict()):
        return 'local_cartodb'
    if datastore.is_using_connection() and datastore.connection_id:
        return 'conn_%s' % datastore.connection_id
    fp = _params_fingerprint(datastore.get_connection_params_dict())
    digest = hashlib.sha256(fp.encode('utf-8')).hexdigest()[:16]
    return 'legacy_%s' % digest


def datastore_connection_label(datastore):
    if datastore is None:
        return '?'
    if datastore.is_using_connection() and datastore.connection:
        return datastore.connection.name
    params = datastore.get_connection_params_dict()
    return '%s@%s:%s/%s' % (
        params.get('user', '?'),
        params.get('host', '?'),
        params.get('port', '?'),
        params.get('database', '?'),
    )


def is_foreign_postgis_datastore(datastore):
    """True when the layer DB is not the default GVSIGOL_USERS_CARTODB database."""
    if datastore is None:
        return False
    if datastore.type not in ('PostGIS', 'PostgreSQL', 'v_PostGIS'):
        t = (datastore.type or '')
        if not t.startswith('v_'):
            return False
    params = datastore.get_connection_params_dict()
    return not is_local_cartodb_params(params)


def local_cartodb_datastores_for_server(server_id):
    """PostGIS datastores on this GeoServer that point at GVSIGOL_USERS_CARTODB (GPKG load targets)."""
    qs = Datastore.objects.filter(
        workspace__server_id=int(server_id),
        type='v_PostGIS',
    ).select_related('workspace', 'connection').order_by('workspace__name', 'name')
    return [ds for ds in qs if not is_foreign_postgis_datastore(ds)]


def _detect_views_in_datastore(ds, source_names):
    """Return the subset of source_names that are SQL views in ds (one DB query)."""
    if not source_names:
        return set()
    try:
        intro, _ = ds.get_db_connection()
        if intro is None:
            return set()
        params = ds.get_connection_params_dict()
        schema = (params.get('schema') or 'public').strip() or 'public'
        result = intro.get_views_in_schema(schema, list(source_names))
        intro.close()
        return result
    except Exception:
        return set()


def analyze_project_layers(project):
    """
    Inventory for export wizard: which vector layers are local vs foreign PostGIS,
    and which local layers are SQL views.
    """
    layers_out = []
    foreign_keys = {}

    # Collect layers per datastore first so we can batch-detect views.
    ds_to_layers = {}  # ds_id -> (ds, list of (layer, entry_placeholder))

    for prj_lg in project.projectlayergroup_set.all():
        lg = prj_lg.layer_group
        for layer in Layer.objects.filter(layer_group=lg).order_by('order', 'id'):
            if layer.type != 'v_PostGIS' or layer.external:
                continue
            ds = layer.datastore
            foreign = is_foreign_postgis_datastore(ds)
            ck = datastore_connection_key(ds)
            entry = {
                'layer_id': layer.id,
                'name': layer.name,
                'source_name': layer.source_name or layer.name,
                'title': layer.title or layer.name,
                'layer_group': lg.title or lg.name,
                'is_foreign': foreign,
                'is_view': False,
                'connection_key': ck,
                'connection_label': datastore_connection_label(ds),
                'default_vector_mode': 'embedded',
            }
            layers_out.append(entry)
            if not foreign and ds:
                ds_to_layers.setdefault(ds.id, (ds, []))[1].append(entry)
            if foreign:
                if ck not in foreign_keys:
                    foreign_keys[ck] = {
                        'connection_key': ck,
                        'connection_label': datastore_connection_label(ds),
                        'layers': [],
                    }
                foreign_keys[ck]['layers'].append({
                    'layer_id': layer.id,
                    'name': layer.name,
                    'title': layer.title or layer.name,
                })

    # Batch-detect views per datastore (one query per unique local datastore).
    for _ds_id, (ds, entries) in ds_to_layers.items():
        source_names = {e['source_name'] for e in entries if e['source_name']}
        view_names = _detect_views_in_datastore(ds, source_names)
        for entry in entries:
            if entry['source_name'] in view_names:
                entry['is_view'] = True

    has_roles = project.projectrole_set.exists()
    return {
        'project_id': project.id,
        'project_name': project.name,
        'is_public': bool(project.is_public),
        'has_project_roles': has_roles,
        'ask_export_permissions': (not project.is_public) and has_roles,
        'vector_layers': layers_out,
        'foreign_connections': list(foreign_keys.values()),
    }
