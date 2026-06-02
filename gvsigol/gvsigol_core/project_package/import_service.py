# -*- coding: utf-8 -*-
import ast
import datetime
import json
import logging
import os
import re
import shutil
import tempfile
from collections import Counter
import zipfile
from io import StringIO

from django.conf import settings
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _

from gvsigol.basetypes import CloneConf
from gvsigol_auth import auth_backend
from gvsigol_core import utils as core_utils
from gvsigol_core.models import Project, ProjectLayerGroup, ProjectRole, SharedView
from gvsigol_services import geographic_servers
from gvsigol_services import utils as services_utils
from gvsigol_services.models import (
    Connection,
    Datastore,
    Enumeration,
    EnumerationItem,
    Layer,
    LayerFieldEnumeration,
    LayerManageRole,
    LayerReadRole,
    LayerResource,
    LayerWriteRole,
    LayerGroup,
    Server,
    Workspace,
)
from gvsigol_symbology.models import Library
from gvsigol_symbology.services import sld_import

from gvsigol_core.project_package.connection_utils import _params_fingerprint
from gvsigol_core.project_package.gdal_io import (
    import_gpkg_to_postgis,
    is_gdal_available,
    list_gpkg_layers,
    pg_connection_from_datastore,
)
from gvsigol_core.project_package.manifest import (
    is_compatible_version,
    read_manifest_from_extracted,
    read_manifest_from_zip,
    verify_manifest_against_dir,
)
from gvsigol_core.models import ProjectPackageImportJob
from gvsigol_core.project_package.raster_sidecars import copy_sidecar_tree  # noqa: F401 (kept for external callers)
from gvsigol_core.project_package.constants import PROJECT_JSON
from gvsigol_core.project_package.connection_utils import is_foreign_postgis_datastore

LOG = logging.getLogger('gvsigol')


def _raster_import_root():
    return getattr(
        settings,
        'GVSIGOL_PROJECT_PACKAGE_RASTER_ROOT',
        os.path.join(settings.MEDIA_ROOT, 'data', 'RASTER'),
    )


def extract_zip_to(zip_path, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(dest_dir)


def _pg_token(s, fallback='x'):
    """PostgreSQL schema / safe identifier fragment from arbitrary text."""
    if not s:
        s = fallback
    out = re.sub(r'[^a-zA-Z0-9_]', '_', str(s))
    if not out:
        out = fallback
    if out[0].isdigit():
        out = 'p_' + out
    return out[:62]


def _default_workspace_from_project(snapshot):
    pdata = snapshot.get('project') or {}
    return _pg_token(pdata.get('name') or 'project', 'ws')


def _normalized_ws_ds_for_vector_layer(ld, default_ws):
    """Workspace/datastore from exported layer metadata (not the project name)."""
    wk = (ld.get('workspace_name') or '').strip()
    dk = (ld.get('datastore_name') or '').strip()
    schema = (ld.get('schema_name') or '').strip()
    if not dk and schema:
        dk = schema
    if not dk:
        dk = _pg_token(ld.get('source_name') or ld.get('name') or 'layer', 'ds')
    if not wk:
        wk = dk if not ld.get('datastore_is_foreign') else (default_ws or dk)
    return wk, dk


def _is_view_sql_layer_entry(ly):
    """True when this manifest entry contains a SQL view definition."""
    return bool(ly.get('view_sql_definition') and ly.get('vector_data_mode') == 'view_sql_definition')


def _collect_foreign_definition_layers(snapshot):
    """Per-layer rows for import wizard (foreign PostGIS definition-only)."""
    rows = []
    for group in snapshot.get('layer_groups', []):
        lg = group.get('layer_group') or {}
        lg_label = lg.get('title') or lg.get('name') or ''
        for ly in group.get('layers', []):
            if not _is_definition_only_layer_entry(ly):
                continue
            ld = ly.get('layer') or {}
            rows.append({
                'export_id': ly.get('export_id'),
                'title': ld.get('title') or ld.get('name') or '',
                'name': ld.get('name') or '',
                'layer_group': lg_label,
                'connection_key': ld.get('datastore_connection_key') or 'local_cartodb',
                'connection_label': ld.get('datastore_connection_label') or '',
            })
    return rows


def _parse_skip_definition_export_ids(wizard, snapshot=None):
    skipped = set(wizard.get('skip_definition_layer_export_ids') or [])
    skip_conn = set(wizard.get('skip_foreign_connection_keys') or [])
    if snapshot and skip_conn:
        for fl in _collect_foreign_definition_layers(snapshot):
            if fl.get('connection_key') in skip_conn and fl.get('export_id'):
                skipped.add(fl['export_id'])
    return skipped


def _parse_skip_view_export_ids(wizard):
    """Export IDs of view-sql layers the user chose to skip in the wizard."""
    return set(wizard.get('skip_view_layer_export_ids') or [])


def _active_definition_layers(snapshot, skipped_export_ids):
    """Definition-only layers that are not explicitly skipped in the wizard."""
    skipped = set(skipped_export_ids or [])
    for group in snapshot.get('layer_groups', []):
        for ly in group.get('layers', []):
            if not _is_definition_only_layer_entry(ly):
                continue
            eid = ly.get('export_id')
            if eid and eid in skipped:
                continue
            yield ly


def _foreign_connection_keys_required(snapshot, skipped_export_ids):
    keys = set()
    for ly in _active_definition_layers(snapshot, skipped_export_ids):
        ld = ly.get('layer') or {}
        ck = ld.get('datastore_connection_key') or 'local_cartodb'
        if ck != 'local_cartodb' or ld.get('datastore_is_foreign'):
            keys.add(ck)
    return keys


def extract_snapshot_layout(snapshot):
    """Layout for import wizard: GPKG targets per source connection, plus foreign DB for definition-only layers."""
    default_ws = _default_workspace_from_project(snapshot)
    foreign_map = {}
    gpkg_groups = {}
    gpkg_layers = []
    n_def = 0
    n_embedded = 0
    foreign_definition_layers = []
    raster_layers = []
    external_layers = []
    seen_external_params = set()

    for group in snapshot.get('layer_groups', []):
        lg_src = group.get('layer_group') or {}
        is_default_baselayer = (lg_src.get('name') or '').strip() == '__default_baselayergroup__'
        for ly in group.get('layers', []):
            lt = ly.get('layer_type')
            ld = ly.get('layer') or {}

            # Raster layers
            if lt and lt.startswith('c_') and ly.get('raster_bundle'):
                bundle = ly.get('raster_bundle') or {}
                primary = bundle.get('primary') or ''
                raster_layers.append({
                    'export_id': ly.get('export_id') or '',
                    'name': ld.get('name') or '',
                    'title': ld.get('title') or ld.get('name') or '',
                    'type': lt,
                    'primary_file': primary,
                    'file_count': len(bundle.get('files') or []),
                })
                continue

            # External layers (WMS, WMTS, etc.) — skip __default_baselayergroup__ ones
            # since they will be silently reused
            if ld.get('external') and not is_default_baselayer:
                ep = ld.get('external_params') or ''
                if ep not in seen_external_params:
                    seen_external_params.add(ep)
                    external_layers.append({
                        'export_id': ly.get('export_id') or '',
                        'name': ld.get('name') or '',
                        'title': ld.get('title') or ld.get('name') or '',
                        'type': lt or ld.get('type') or '',
                    })
                continue

            if lt != 'v_PostGIS':
                continue
            if ld.get('external'):
                continue
            vmode = ly.get('vector_data_mode')
            if ly.get('vector_gpkg'):
                n_embedded += 1
                ck = ld.get('datastore_connection_key') or 'local_cartodb'
                exp_wk, exp_ds = _normalized_ws_ds_for_vector_layer(ld, default_ws)
                is_foreign = bool(ld.get('datastore_is_foreign'))
                if ck not in gpkg_groups:
                    gpkg_groups[ck] = {
                        'connection_key': ck,
                        'connection_label': ld.get('datastore_connection_label') or ck,
                        'is_foreign_source': is_foreign,
                        'exported_workspace': exp_wk,
                        'exported_datastore': exp_ds,
                        'layer_count': 0,
                        'sample_layers': [],
                    }
                gpkg_groups[ck]['layer_count'] += 1
                if len(gpkg_groups[ck]['sample_layers']) < 5:
                    gpkg_groups[ck]['sample_layers'].append(ld.get('title') or ld.get('name'))
                # Individual entry for per-layer Skip in the wizard
                gpkg_layers.append({
                    'export_id': ly.get('export_id') or '',
                    'name': ld.get('name') or '',
                    'title': ld.get('title') or ld.get('name') or '',
                    'connection_key': ck,
                    'connection_label': ld.get('datastore_connection_label') or ck,
                    'is_foreign_source': is_foreign,
                    'exported_workspace': exp_wk,
                    'exported_datastore': exp_ds,
                })
            elif vmode == 'definition_only' or (
                not ly.get('vector_gpkg')
                and vmode != 'embedded'
                and ld.get('datastore_is_foreign')
            ):
                n_def += 1
                ck = ld.get('datastore_connection_key') or 'local_cartodb'
                if ck == 'local_cartodb' and not ld.get('datastore_is_foreign'):
                    continue
                if ck not in foreign_map:
                    foreign_map[ck] = {
                        'connection_key': ck,
                        'connection_label': ld.get('datastore_connection_label') or ck,
                        'layer_count': 0,
                        'sample_layers': [],
                    }
                foreign_map[ck]['layer_count'] += 1
                samples = foreign_map[ck]['sample_layers']
                layer_label = ld.get('title') or ld.get('name')
                if layer_label and layer_label not in samples and len(samples) < 8:
                    samples.append(layer_label)
    # Collect SQL view layers for the import wizard
    view_sql_layers = []
    for group in snapshot.get('layer_groups', []):
        for ly in group.get('layers', []):
            if not _is_view_sql_layer_entry(ly):
                continue
            ld = ly.get('layer') or {}
            view_def = ly.get('view_sql_definition') or {}
            view_sql_layers.append({
                'export_id': ly.get('export_id'),
                'name': ld.get('name') or '',
                'title': ld.get('title') or ld.get('name') or '',
                'view_name': view_def.get('view_name') or ld.get('source_name') or ld.get('name') or '',
                'schema': view_def.get('schema') or '',
                'sql': view_def.get('sql') or '',
                'gt_pk_metadata': view_def.get('gt_pk_metadata') or [],
                # Exported origin info for display in the import wizard
                'exported_workspace': ld.get('workspace_name') or '',
                'exported_datastore': ld.get('datastore_name') or '',
            })

    foreign_definition_layers = _collect_foreign_definition_layers(snapshot)
    primary_workspace = default_ws
    pdata = snapshot.get('project') or {}
    all_gpkg_targets = list(gpkg_groups.values())
    gpkg_local_targets = [g for g in all_gpkg_targets if not g.get('is_foreign_source')]
    gpkg_foreign_targets = [g for g in all_gpkg_targets if g.get('is_foreign_source')]
    return {
        'primary_workspace': primary_workspace,
        'exported_project_name': pdata.get('name'),
        'exported_project_title': pdata.get('title'),
        'definition_only_layers': n_def,
        'embedded_vector_layers': n_embedded,
        'gpkg_connection_targets': all_gpkg_targets,
        'gpkg_local_targets': gpkg_local_targets,
        'gpkg_foreign_targets': gpkg_foreign_targets,
        'gpkg_layers': gpkg_layers,
        'foreign_connections': list(foreign_map.values()),
        'foreign_definition_layers': foreign_definition_layers,
        'raster_layers': raster_layers,
        'external_layers': external_layers,
        'view_sql_layers': view_sql_layers,
    }


def _package_has_permissions(snapshot):
    if snapshot.get('project_roles'):
        return True
    for group in snapshot.get('layer_groups', []):
        for ly in group.get('layers', []):
            perms = ly.get('permissions') or {}
            if perms.get('read_roles') or perms.get('write_roles') or perms.get('manage_roles'):
                return True
    return False


def _get_or_create_workspace(server_id, ws_name, username):
    if not ws_name or not re.match(r'^[a-zA-Z0-9_\-]+$', ws_name):
        raise ValueError(_('Invalid workspace name in package: "%s"') % ws_name)
    server = Server.objects.get(id=int(server_id))
    existing = Workspace.objects.filter(name=ws_name).first()
    if existing:
        if existing.server_id != int(server_id):
            raise ValueError(
                _(
                    'Workspace "%(n)s" already exists on another GeoServer instance. '
                    'Use a different server or remove/rename that workspace.'
                )
                % {'n': ws_name}
            )
        return existing, False
    if server.frontend_url.endswith('/'):
        uri = server.frontend_url + ws_name
    else:
        uri = server.frontend_url + '/' + ws_name
    values = {
        'name': ws_name,
        'server': server,
        'description': ws_name + ' ws',
        'uri': uri,
        'wms_endpoint': server.getWmsEndpoint(ws_name),
        'wfs_endpoint': server.getWfsEndpoint(ws_name),
        'wcs_endpoint': server.getWcsEndpoint(ws_name),
        'wmts_endpoint': server.getWmtsEndpoint(ws_name),
        'cache_endpoint': server.getCacheEndpoint(ws_name),
    }
    ws = services_utils.create_workspace(server.id, ws_name, uri, values, username)
    if not ws:
        raise RuntimeError(_('Could not create GeoServer workspace "%s"') % ws_name)
    return ws, True


def _connection_params_json(connection, schema):
    conn_params = dict(connection.get_connection_params())
    conn_params['schema'] = schema
    conn_params.update(connection.get_extra_params())
    return json.dumps(conn_params)


def _datastore_uses_connection(datastore, connection):
    """True when the datastore points at the same PostGIS as the wizard-selected Connection."""
    if not datastore or not connection:
        return False
    if datastore.is_using_connection() and datastore.connection_id:
        return int(datastore.connection_id) == int(connection.id)
    fp_ds = _params_fingerprint(datastore.get_connection_params_dict())
    fp_cn = _params_fingerprint(connection.get_connection_params())
    return bool(fp_ds and fp_cn and fp_ds == fp_cn)


def _get_or_create_connection_datastore(username, ws_obj, ds_name, connection, schema, report):
    existing = Datastore.objects.filter(
        workspace=ws_obj,
        name=ds_name,
        connection=connection,
    ).select_related('connection').first()
    if existing and _datastore_uses_connection(existing, connection):
        report.append({
            'datastore_reused': {
                'workspace': ws_obj.name,
                'datastore': ds_name,
                'connection': connection.name,
            },
        })
        return existing, False

    other = Datastore.objects.filter(workspace=ws_obj, name=ds_name).select_related('connection').first()
    if other and not _datastore_uses_connection(other, connection):
        raise RuntimeError(
            _(
                'Datastore "%(ds)s" in workspace "%(ws)s" is already registered with '
                'another database connection ("%(other)s"). Select that connection in '
                'the wizard, or skip this layer.'
            )
            % {
                'ds': ds_name,
                'ws': ws_obj.name,
                'other': getattr(other.connection, 'name', other.name),
            }
        )
    try:
        connection.create_schema_if_not_exists(schema)
    except Exception as ex:
        LOG.warning('create_schema_if_not_exists failed: %s', ex, exc_info=True)
    params_json = _connection_params_json(connection, schema)
    ds = services_utils.add_datastore(
        ws_obj,
        'v_PostGIS',
        ds_name,
        _('Imported from package (%(schema)s)') % {'schema': schema},
        params_json,
        username,
        connection=connection,
        schema=schema,
    )
    if ds:
        if not ds.connection_id:
            ds.connection = connection
            ds.schema = schema
            ds.legacy_mode = False
            ds.save()
        report.append({
            'datastore_created': {
                'workspace': ws_obj.name,
                'datastore': ds_name,
                'connection': connection.name,
                'schema': schema,
            },
        })
        return ds, True

    gs = geographic_servers.get_instance().get_server_by_id(ws_obj.server_id)
    if gs.datastore_exists(ws_obj.name, ds_name):
        raise RuntimeError(
            _(
                'GeoServer store "%(ws)s:%(ds)s" already exists but is tied to another '
                'database connection. Select the matching connection or skip this layer.'
            )
            % {'ws': ws_obj.name, 'ds': ds_name}
        )

    raise RuntimeError(
        _('Could not create datastore "%(ds)s" for connection "%(conn)s"')
        % {'ds': ds_name, 'conn': connection.name}
    )


def _parse_gpkg_connection_targets(wizard, layout, server_id):
    """Resolve GPKG load targets: local = exported ws/ds; foreign = existing datastore."""
    foreign_ds = dict(wizard.get('gpkg_foreign_datastores') or {})
    for key, val in wizard.items():
        if not val or not key.startswith('gpkg_datastore_'):
            continue
        ck = key[len('gpkg_datastore_'):]
        try:
            foreign_ds[ck] = int(val)
        except (TypeError, ValueError):
            pass

    out = {}
    for row in layout.get('gpkg_connection_targets') or []:
        ck = row.get('connection_key')
        if not ck:
            continue
        if row.get('is_foreign_source'):
            ds_id = foreign_ds.get(ck)
            if not ds_id:
                raise ValueError(
                    _('Select a datastore for GPKG import (%(label)s)')
                    % {'label': row.get('connection_label') or ck}
                )
            ds = Datastore.objects.select_related('workspace', 'connection').get(pk=int(ds_id))
            if ds.workspace.server_id != int(server_id):
                raise ValueError(
                    _('Datastore "%(ds)s" is not on the selected server')
                    % {'ds': ds.name}
                )
            if is_foreign_postgis_datastore(ds):
                raise ValueError(
                    _('Datastore "%(ds)s" uses a foreign database. '
                      'Choose a local CartoDB datastore for GPKG import.')
                    % {'ds': ds.name}
                )
            out[ck] = {
                'workspace': ds.workspace.name,
                'datastore': ds.name,
                'datastore_id': ds.id,
            }
        else:
            ws = (row.get('exported_workspace') or '').strip()
            ds = (row.get('exported_datastore') or '').strip()
            if not ws or not ds:
                raise ValueError(
                    _('Missing workspace or datastore for local GPKG import (%(label)s)')
                    % {'label': row.get('connection_label') or ck}
                )
            if not re.match(r'^[a-zA-Z0-9_\-]+$', ws) or not re.match(r'^[a-zA-Z0-9_\-]+$', ds):
                raise ValueError(
                    _('Invalid workspace or datastore name for connection "%(label)s"')
                    % {'label': row.get('connection_label') or ck}
                )
            out[ck] = {'workspace': ws, 'datastore': ds}
    return out


def _build_datastore_map_from_gpkg_targets(server_id, username, gpkg_targets, report):
    """Create/reuse local CartoDB datastores from wizard GPKG target choices."""
    ws_objs = {}
    datastore_map = {}
    workspaces_created = []
    for ck, tgt in sorted(gpkg_targets.items()):
        if tgt.get('datastore_id'):
            ds = Datastore.objects.select_related('workspace').get(pk=int(tgt['datastore_id']))
            key = (ds.workspace.name, ds.name)
            if key not in datastore_map:
                datastore_map[key] = ds
                ws_objs[ds.workspace.name] = ds.workspace
                report.append({
                    'datastore_reused': {
                        'workspace': ds.workspace.name,
                        'datastore': ds.name,
                        'connection_key': ck,
                    },
                })
            continue
        wsn = tgt['workspace']
        dsn = tgt['datastore']
        if wsn not in ws_objs:
            ws, created = _get_or_create_workspace(server_id, wsn, username)
            ws_objs[wsn] = ws
            if created:
                report.append({'workspace_created': wsn})
                workspaces_created.append(ws)
        wk = ws_objs[wsn]
        key = (wsn, dsn)
        if key not in datastore_map:
            ds, _ds_created = _get_or_create_datastore(username, wk, dsn, report)
            datastore_map[key] = ds
    return datastore_map, ws_objs, workspaces_created


def _datastore_by_id(ds_id):
    """Return a Datastore instance by primary key, or None."""
    try:
        return Datastore.objects.select_related('workspace').get(pk=int(ds_id))
    except Exception:
        return None


def _embedded_target_datastore(ld, default_ws, gpkg_targets, datastore_map):
    ck = ld.get('datastore_connection_key') or 'local_cartodb'
    tgt = gpkg_targets.get(ck)
    if not tgt:
        wk, dk = _normalized_ws_ds_for_vector_layer(ld, default_ws)
        tgt = {'workspace': wk, 'datastore': dk}
    ds = datastore_map.get((tgt['workspace'], tgt['datastore']))
    if not ds:
        raise RuntimeError(
            _('Missing datastore for GPKG target workspace "%(w)s" / datastore "%(d)s"')
            % {'w': tgt['workspace'], 'd': tgt['datastore']}
        )
    return ds


def _get_or_create_datastore(username, ws_obj, ds_name, report):
    existing = Datastore.objects.filter(workspace=ws_obj, name=ds_name).first()
    if existing:
        report.append({'datastore_reused': {'workspace': ws_obj.name, 'datastore': ds_name}})
        return existing, False
    ds = services_utils.create_datastore(username, ds_name, ws_obj)
    if not ds:
        raise RuntimeError(_('Could not create datastore "%s" in workspace "%s"') % (ds_name, ws_obj.name))
    report.append({'datastore_created': {'workspace': ws_obj.name, 'datastore': ds_name}})
    return ds, True


def _unique_project_name(base):
    base = (base or 'project').strip() or 'project'
    base = base[:100]
    if not Project.objects.filter(name=base).exists():
        return base
    n = 2
    while n < 100000:
        suffix = '_%d' % n
        head = base[: 100 - len(suffix)] if len(base) + len(suffix) > 100 else base
        candidate = head + suffix
        if not Project.objects.filter(name=candidate).exists():
            return candidate
        n += 1
    raise RuntimeError(_('Could not allocate a unique project name from "%s"') % base)


def preflight_job(job: ProjectPackageImportJob):
    report = []
    if not job.zip_path or not os.path.isfile(job.zip_path):
        return {'ok': False, 'errors': ['zip_missing'], 'report': report}
    try:
        manifest = read_manifest_from_zip(job.zip_path)
    except Exception as ex:
        return {'ok': False, 'errors': ['invalid_zip:%s' % ex], 'report': report}
    ver = manifest.get('package_format_version')
    if not is_compatible_version(ver):
        return {'ok': False, 'errors': ['unsupported_version:%s' % ver], 'report': report}
    extract_dir = job.extract_dir
    if not extract_dir:
        extract_dir = tempfile.mkdtemp(prefix='pkgimp_')
        extract_zip_to(job.zip_path, extract_dir)
        job.extract_dir = extract_dir
    try:
        man2 = read_manifest_from_extracted(extract_dir)
    except Exception as ex:
        return {'ok': False, 'errors': ['manifest_read:%s' % ex], 'report': report}
    errs = verify_manifest_against_dir(man2, extract_dir)
    if errs:
        return {'ok': False, 'errors': errs, 'report': report}
    pj_path = os.path.join(extract_dir, PROJECT_JSON.replace('/', os.sep))
    with open(pj_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
    n_vec = sum(
        1
        for g in snapshot.get('layer_groups', [])
        for ly in g.get('layers', [])
        if ly.get('layer_type') == 'v_PostGIS' and ly.get('vector_gpkg')
    )
    n_ras = sum(
        1
        for g in snapshot.get('layer_groups', [])
        for ly in g.get('layers', [])
        if (ly.get('layer_type') or '').startswith('c_') and ly.get('raster_bundle')
    )
    report.append({'vectors_to_load': n_vec, 'raster_bundles': n_ras})
    layout = extract_snapshot_layout(snapshot)
    report.append({'package_layout': layout})
    if not is_gdal_available():
        report.append({
            'warning': _(
                'GDAL (pygdaltools) is not available on this server; '
                'vector GeoPackage import/export will fail.'
            ),
        })
    job.manifest_json = man2
    job.status = ProjectPackageImportJob.ST_PREFLIGHT_OK
    job.report_json = report
    job.save()
    return {'ok': True, 'errors': [], 'report': report, 'snapshot_summary': {'vectors': n_vec, 'rasters': n_ras}, 'package_layout': layout}


def _find_existing_layer_group(server_id, lg_src):
    """Reuse an already published layer group on this GeoServer (same-server copy)."""
    name = (lg_src.get('name') or '').strip()
    if name:
        lg = LayerGroup.objects.filter(server_id=server_id, name=name).first()
        if lg:
            return lg
    title = (lg_src.get('title') or '').strip()
    if title:
        return LayerGroup.objects.filter(server_id=server_id, title=title).first()
    return None


def _layer_belongs_to_group(lyr, layer_group):
    if layer_group is None or lyr is None:
        return True
    return lyr.layer_group_id == layer_group.id


def _delete_unused_empty_layer_group(layer_group_obj):
    """
    Safe delete placeholder LayerGroup created for import when no Layers and no PLGs remain.
    """
    if layer_group_obj is None:
        return False
    if Layer.objects.filter(layer_group_id=layer_group_obj.id).exists():
        return False
    if ProjectLayerGroup.objects.filter(layer_group_id=layer_group_obj.id).exists():
        return False
    gid = layer_group_obj.id
    layer_group_obj.delete()
    LOG.info(
        'Removed empty unused layer group %s left over after attaching shared definitions',
        gid,
    )
    return True


def _finalize_definition_foreign_layer_groups(
    project,
    plg_obj,
    placeholder_lg,
    plg_cfg,
    group_reuse_state,
    report,
):
    """
    When reusable PostGIS definitions already live on another LayerGroup, never move those
    Layers. Link this project to that group (reuse PLG or add PLG rows) instead.
    If the linked group exposes more Layers than matched from the package subset, emit a warning.
    """
    if not group_reuse_state:
        return
    foreign_map = group_reuse_state.get('foreign_definition_layers') or {}
    if not foreign_map:
        return
    reuse_pairs = sorted(foreign_map.items(), key=lambda kv: kv[0])
    placeholder_layer_cnt = Layer.objects.filter(layer_group_id=placeholder_lg.id).count()
    placeholder_empty = placeholder_layer_cnt == 0

    for idx, (shared_lg_id, pkg_layer_ids) in enumerate(reuse_pairs):
        try:
            shared_lg = LayerGroup.objects.get(pk=shared_lg_id)
        except LayerGroup.DoesNotExist:
            continue

        pkg_ids = set(pkg_layer_ids or [])
        extra_qs = Layer.objects.filter(layer_group=shared_lg).exclude(pk__in=list(pkg_ids))
        if extra_qs.exists():
            n_extra = extra_qs.count()
            labels = []
            for lyr in extra_qs.only('title', 'name')[:40]:
                label = (lyr.title or '').strip()
                nm = lyr.name or ''
                labels.append('%s [%s]' % (label, nm) if label else nm)
            txt = ', '.join(labels)
            if n_extra > 40:
                txt += _(' (+%d more)') % (n_extra - 40,)
            report.append({
                'warning': _(
                    'The reused layer group "%(lg)s" was linked to this project. '
                    'It also contains %(n)d layer(s) that were not part of this '
                    'package TOC block\'s reused definitions — they remain visible '
                    'because they share the server layer group: %(layers)s.'
                ) % {'lg': shared_lg.name, 'n': n_extra, 'layers': txt},
            })

        has_other_plg = ProjectLayerGroup.objects.filter(
            project_id=project.id,
            layer_group_id=shared_lg.id,
        ).exclude(pk=plg_obj.pk).exists()

        if idx == 0 and placeholder_empty:
            if has_other_plg:
                plg_obj.delete()
                _delete_unused_empty_layer_group(placeholder_lg)
                report.append({
                    'warning': _(
                        'This project already uses layer group "%(lg)s"; an extra empty TOC row '
                        'from this package block was removed.'
                    ) % {'lg': shared_lg.name},
                })
            else:
                plg_obj.layer_group = shared_lg
                plg_obj.save(update_fields=['layer_group'])
                _delete_unused_empty_layer_group(placeholder_lg)
            continue

        linked_now = ProjectLayerGroup.objects.filter(
            project_id=project.id,
            layer_group_id=shared_lg.id,
        ).exists()
        if linked_now:
            continue
        ProjectLayerGroup.objects.create(
            project=project,
            layer_group=shared_lg,
            multiselect=plg_cfg.get('multiselect', True),
            baselayer_group=False,
            default_baselayer=None,
        )
        if idx == 0:
            note = _(
                'Linked existing group "%(lg)s": reused definition layers already live there, '
                'while other layers in this package block stay in the newly created group.'
            ) % {'lg': shared_lg.name}
        else:
            note = _('Additional reused LayerGroup from this package block.')
        report.append({
            'definition_shared_layer_group_added': {
                'layer_group': shared_lg.name,
                'note': note,
            },
        })


def _wizard_connection_for_datastore(target_datastore):
    """Connection object for the wizard-selected PostGIS target."""
    if not target_datastore:
        return None
    if target_datastore.is_using_connection() and target_datastore.connection_id:
        if target_datastore.connection:
            return target_datastore.connection
        return Connection.objects.filter(pk=target_datastore.connection_id).first()
    return None


def _external_layer_signature(layer_entry):
    """Stable tuple for comparing external (WMS, etc.) layer definitions."""
    ld = layer_entry.get('layer') or {}
    return (
        ld.get('type') or 'e_WMS',
        (ld.get('external_params') or '') or '',
    )


def _basemap_external_only_signature(layers_flat):
    """
    If every layer is external, return a tuple signature of the whole group (order-normalized).
    Used to collapse duplicate identical basemap stacks to one LayerGroup during import.
    """
    sigs = []
    for layer_entry in layers_flat or []:
        ld = layer_entry.get('layer') or {}
        if not ld.get('external'):
            return None
        sigs.append(_external_layer_signature(layer_entry))
    if not sigs:
        return None
    return tuple(sorted(sigs, key=lambda t: (t[0], t[1])))


def _find_matching_external_in_layer_group(layer_group, layer_entry):
    """Find an external layer already published in this LayerGroup with the same endpoint params."""
    ld = layer_entry.get('layer') or {}
    return Layer.objects.filter(
        layer_group_id=layer_group.id,
        external=True,
        type=ld.get('type') or 'e_WMS',
        external_params=ld.get('external_params'),
    ).first()


def _find_reusable_definition_layer(layer_entry, target_datastore, layer_group):
    """
    Reuse a published layer only when it is on the target datastore (wizard connection).
    Never reuse by name/source_layer_id from another connection or datastore.
    The caller (_import_postgis_definition_layer) attaches the row to ``layer_group`` if needed.
    """
    del layer_group  # FK fix-up happens after lookup
    ld = layer_entry.get('layer') or {}
    table_name = (ld.get('source_name') or ld.get('name') or '').strip()
    layer_name = (ld.get('name') or table_name).strip()
    if not layer_name or not target_datastore:
        return None

    wizard_conn = _wizard_connection_for_datastore(target_datastore)

    def _layer_on_target_datastore(lyr):
        if not lyr or lyr.datastore_id != target_datastore.id:
            return False
        if wizard_conn:
            return _datastore_uses_connection(lyr.datastore, wizard_conn)
        return True

    lyr = (
        Layer.objects.filter(
            datastore_id=target_datastore.id,
            type='v_PostGIS',
            external=False,
        )
        .filter(Q(name=layer_name) | Q(source_name=table_name))
        .select_related('datastore__connection', 'layer_group')
        .first()
    )
    if lyr and _layer_on_target_datastore(lyr):
        return lyr

    src_id = layer_entry.get('source_layer_id')
    if src_id is not None:
        try:
            src_id = int(src_id)
        except (TypeError, ValueError):
            src_id = None
        if src_id:
            lyr = Layer.objects.filter(id=src_id).select_related(
                'datastore__connection', 'layer_group'
            ).first()
            if lyr and _layer_on_target_datastore(lyr):
                return lyr
    return None


def _is_definition_only_layer_entry(layer_entry):
    if layer_entry.get('vector_gpkg'):
        return False
    vmode = layer_entry.get('vector_data_mode')
    if vmode == 'definition_only':
        return True
    if vmode == 'embedded':
        return False
    ld = layer_entry.get('layer') or {}
    if layer_entry.get('layer_type') != 'v_PostGIS' or ld.get('external'):
        return False
    return bool(ld.get('datastore_is_foreign'))


def _group_allows_layer_group_reuse(group):
    """
    Do not reuse LayerGroups that contain vector layers to import: avoids attaching
    layers published on another database connection to the new project.
    """
    for layer_entry in group.get('layers', []):
        ld = layer_entry.get('layer') or {}
        if ld.get('external'):
            continue
        lt = layer_entry.get('layer_type')
        if lt == 'v_PostGIS' or layer_entry.get('vector_gpkg'):
            return False
        if lt and lt.startswith('c_'):
            return False
    return bool((group.get('layer_group') or {}).get('name'))


def _autofill_foreign_connection_map(snapshot, foreign_connection_map):
    """Map foreign connection keys from source layers when copying on the same server."""
    foreign_connection_map = dict(foreign_connection_map or {})
    for group in snapshot.get('layer_groups', []):
        for layer_entry in group.get('layers', []):
            ld = layer_entry.get('layer') or {}
            ck = ld.get('datastore_connection_key') or 'local_cartodb'
            if ck == 'local_cartodb' or ck in foreign_connection_map:
                continue
            src_id = layer_entry.get('source_layer_id')
            if src_id is None:
                continue
            try:
                src_id = int(src_id)
            except (TypeError, ValueError):
                continue
            lyr = Layer.objects.filter(id=src_id).select_related('datastore__connection').first()
            if lyr and lyr.datastore and lyr.datastore.is_using_connection() and lyr.datastore.connection_id:
                foreign_connection_map[ck] = lyr.datastore.connection_id
    return foreign_connection_map


def _unique_layer_group_name(server_id, workspace_name, desired_base):
    new_name = workspace_name + '_' + desired_base
    i = 1
    salt = ''
    while LayerGroup.objects.filter(name=new_name, server_id=server_id).exists():
        new_name = new_name + '_' + str(i) + salt
        i += 1
        if (i % 1000) == 0:
            salt = '_' + get_random_string(3)
    return new_name


def _unique_layer_name(datastore, base):
    name = base
    i = 1
    salt = ''
    while Layer.objects.filter(name=name, datastore=datastore).exists():
        name = base + '_' + str(i) + salt
        i += 1
        if (i % 1000) == 0:
            salt = '_' + get_random_string(3)
    return name


def _sanitize_pg_table_base(base):
    name = re.sub(r'[^a-zA-Z0-9_]', '_', str(base or 'layer'))
    if not name:
        name = 'layer'
    if name[0].isdigit():
        name = 'p_' + name
    return name[:62]


def _postgis_table_taken(intro, schema, name):
    if intro.object_exists(schema, name):
        return True
    low = name.lower()
    if low != name and intro.object_exists(schema, low):
        return True
    return False


def _unique_gpkg_table_name(target_datastore, schema, base, report):
    """Return a table name that is free both in PostgreSQL and in the gvSIG Layer
    registry for the given datastore.  Appends _1, _2, … until a free slot is
    found.  Never overwrites existing data.
    """
    intro, _db_params = target_datastore.get_db_connection()
    try:
        name = _sanitize_pg_table_base(base)
        candidate = name
        i = 1
        salt = ''
        while True:
            taken_pg = _postgis_table_taken(intro, schema, candidate)
            taken_layer = Layer.objects.filter(name=candidate, datastore=target_datastore).exists()
            low = candidate.lower()
            if low != candidate:
                taken_layer = taken_layer or Layer.objects.filter(
                    name=low, datastore=target_datastore
                ).exists()
            if not taken_pg and not taken_layer:
                break
            candidate = name + '_' + str(i) + salt
            i += 1
            if i % 1000 == 0:
                salt = '_' + get_random_string(3)
        if candidate != name:
            report.append({
                'warning': _(
                    'Layer "%(wanted)s" already exists in datastore "%(ds)s"; '
                    'loading as "%(actual)s".'
                ) % {
                    'wanted': name,
                    'ds': target_datastore.name,
                    'actual': candidate,
                },
            })
        return candidate
    finally:
        intro.close()


def _packaged_postgis_schema(ld):
    """Schema from package metadata; ignore when it equals the datastore label (common export mistake)."""
    packaged = (ld.get('schema_name') or '').strip()
    ds_name = (ld.get('datastore_name') or '').strip()
    if packaged and ds_name and packaged.lower() == ds_name.lower():
        return ''
    return packaged


def _connection_default_schema(connection):
    params = connection.get_connection_params() if connection else {}
    return (params.get('schema') or 'public').strip() or 'public'


def _datastore_postgis_schema(target_datastore, ld=None):
    """Real PostGIS schema for a datastore (never the GeoServer datastore display name)."""
    ld = ld or {}
    packaged = _packaged_postgis_schema(ld)
    if packaged:
        return packaged
    if target_datastore.is_using_connection() and target_datastore.schema:
        return target_datastore.schema.strip()
    params = target_datastore.get_connection_params_dict()
    sch = (params.get('schema') or '').strip()
    if sch:
        return sch
    gs = (target_datastore.get_schema_name() or '').strip()
    ds_name = (target_datastore.name or '').strip()
    if gs and (not ds_name or gs.lower() != ds_name.lower()):
        return gs
    return gs or 'public'


def _gpkg_load_schema(target_datastore, ld=None, use_ds_schema=False):
    """PostGIS schema for ogr2ogr GPKG load.

    Priority:
    1. schema_name recorded in the package metadata — used directly without
       comparing to the datastore name.  The schema_name IS the correct
       PostgreSQL schema where the layer lived on the source server; even when
       it equals the datastore name that is intentional (e.g. ds_carles/ds_carles).
       Skipped when use_ds_schema=True (user selected a different target datastore).
    2. Schema of the target datastore connection.
    3. Datastore name as fallback (CartoDB / legacy behaviour).
    """
    if ld and not use_ds_schema:
        raw_schema = (ld.get('schema_name') or '').strip()
        if raw_schema and re.match(r'^[a-zA-Z0-9_]+$', raw_schema):
            return raw_schema
    if target_datastore.is_using_connection() and target_datastore.schema:
        schema = target_datastore.schema.strip()
    else:
        schema = (target_datastore.get_schema_name() or '').strip()
        if not schema or schema == 'public':
            schema = (target_datastore.name or '').strip()
    if not schema or not re.match(r'^[a-zA-Z0-9_]+$', schema):
        raise RuntimeError(
            _('Invalid or missing schema for datastore "%(ds)s"')
            % {'ds': target_datastore.name}
        )
    return schema


def _postgis_table_exists(target_datastore, schema, table_name):
    intro = None
    try:
        intro, _db_params = target_datastore.get_db_connection()
        return bool(intro and intro.object_exists(schema, table_name))
    except Exception as ex:
        LOG.warning(
            'Could not verify table %s.%s on datastore %s: %s',
            schema,
            table_name,
            target_datastore.name,
            ex,
            exc_info=True,
        )
        return False
    finally:
        if intro:
            intro.close()


def _ensure_cartodb_schema_exists(schema):
    """Create schema in GVSIGOL_USERS_CARTODB if missing (required before ogr2ogr -nln)."""
    if not services_utils.create_schema(schema):
        raise RuntimeError(_('Could not create PostGIS schema "%s"') % schema)


def _gpkg_source_layer_name(gpkg_path, layer_entry=None):
    """Layer name inside the GeoPackage (gdaltools source layer)."""
    layers = list_gpkg_layers(gpkg_path)
    if not layers:
        raise RuntimeError(
            _('Could not read layers inside GeoPackage "%(path)s".')
            % {'path': os.path.basename(gpkg_path)}
        )

    ld = (layer_entry or {}).get('layer') or {}
    hints = []
    for value in (
        (layer_entry or {}).get('gpkg_layer_name'),
        ld.get('gpkg_layer_name'),
        ld.get('source_name'),
        ld.get('name'),
    ):
        value = (value or '').strip()
        if value and value not in hints:
            hints.append(value)

    lower_map = {name.lower(): name for name in layers}
    for hint in hints:
        match = lower_map.get(hint.lower())
        if match:
            return match

    if len(layers) == 1:
        LOG.info(
            'GPKG "%s": using sole layer "%s" (manifest hints: %s)',
            os.path.basename(gpkg_path),
            layers[0],
            hints or ['—'],
        )
        return layers[0]

    raise RuntimeError(
        _('GeoPackage "%(path)s" contains layers %(layers)s; none match %(hints)s.')
        % {
            'path': os.path.basename(gpkg_path),
            'layers': ', '.join(layers),
            'hints': ', '.join(hints) or '—',
        }
    )


def _verify_gpkg_table_loaded(target_datastore, schema, table_name):
    """Confirm ogr2ogr created the table before publishing on GeoServer."""
    intro, _db_params = target_datastore.get_db_connection()
    try:
        if intro.object_exists(schema, table_name):
            return table_name
        lowered = table_name.lower()
        if lowered != table_name and intro.object_exists(schema, lowered):
            return lowered
        if intro.object_exists('public', table_name):
            raise RuntimeError(
                _('ogr2ogr created table "%(table)s" in schema "public" instead of "%(schema)s". '
                  'Check datastore connection parameters.')
                % {'schema': schema, 'table': table_name}
            )
        existing = intro.get_tables(schema) or []
        hint = ''
        if existing:
            hint = ' Tables in schema: %s.' % ', '.join(existing[:15])
        raise RuntimeError(
            _('ogr2ogr did not create table "%(schema)s"."%(table)s".%(hint)s '
              'Check server logs for ogr2ogr output.')
            % {'schema': schema, 'table': table_name, 'hint': hint}
        )
    finally:
        intro.close()


def _publish_vector_layer_on_geoserver(
    server,
    target_datastore,
    gs_layer_name,
    table_name,
    title,
    is_queryable,
    extra_params,
    native_srs=None,
    schema=None,
):
    """
    Publish an existing PostGIS table on GeoServer with explicit attributes read from the DB.
    gs_layer_name must match Layer.name (WMS LAYERS=); table_name is the physical PostGIS table.
    """
    workspace = target_datastore.workspace
    if not schema:
        schema = _datastore_postgis_schema(target_datastore)
    include_pks = server.datastore_check_exposed_pks(target_datastore)
    conn = None
    try:
        conn, _db_params = target_datastore.get_db_connection()
        fields = server._featuretype_attributes(conn, schema, table_name, include_pk=include_pks)
    finally:
        if conn:
            conn.close()
    if not fields:
        raise RuntimeError(
            _('Could not read columns for table "%(schema)s"."%(table)s". '
              'Check that ogr2ogr loaded data into the datastore schema.')
            % {'schema': schema, 'table': table_name}
        )
    srs = native_srs or extra_params.get('srs')
    gs_extra = dict(extra_params)
    if table_name and table_name != gs_layer_name:
        gs_extra['nativeName'] = table_name
    if srs:
        gs_extra['srs'] = srs
        gs_extra['nativeBoundingBox'] = {
            'minx': 0,
            'maxx': 1,
            'miny': 0,
            'maxy': 1,
            'crs': srs,
        }
    if server.resource_exists(workspace.name, gs_layer_name):
        LOG.warning(
            'GeoServer layer "%s" already exists in workspace "%s"; skipping create_feature_type',
            gs_layer_name,
            workspace.name,
        )
    else:
        server.rest_catalog.create_feature_type(
            gs_layer_name,
            title or gs_layer_name,
            target_datastore.name,
            workspace.name,
            srs=srs,
            fields=fields,
            user=server.user,
            password=server.password,
            extraParams=gs_extra,
        )
    if target_datastore.type not in ('e_WMS', 'c_ImageMosaic'):
        server.setQueryable(
            workspace.name,
            target_datastore.name,
            target_datastore.type,
            gs_layer_name,
            is_queryable,
        )


def _reload_geoserver_vector_layer(server, layer):
    """Recalculate native/latlon bbox and refresh attributes after import."""
    try:
        server.reload_featuretype(
            layer,
            attributes=True,
            nativeBoundingBox=True,
            latLonBoundingBox=True,
        )
    except Exception as ex:
        LOG.warning(
            'Could not reload GeoServer feature type for layer %s: %s',
            layer.name,
            ex,
            exc_info=True,
        )


def _import_symbol_libraries(snapshot, extract_dir, report):
    """Restore symbol library image files from the package and create Library
    records on the target server if they do not already exist.

    Files are stored in the ZIP under  symbology/libraries/{lib_name}/{file}.
    They are extracted to  MEDIA_ROOT/symbol_libraries/{lib_name}/{file}.
    """
    libs = snapshot.get('symbol_libraries') or []
    if not libs:
        return
    for lib_data in libs:
        lib_name = (lib_data.get('name') or '').strip()
        if not lib_name:
            continue
        dest_dir = os.path.join(settings.MEDIA_ROOT, 'symbol_libraries', lib_name)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as _mk_exc:
            LOG.warning('Could not create symbol library dir %s: %s', dest_dir, _mk_exc)
            continue
        copied = 0
        for fname in lib_data.get('files') or []:
            src = os.path.join(
                extract_dir, 'symbology', 'libraries', lib_name, fname
            )
            if not os.path.isfile(src):
                LOG.warning('Symbol library file missing in package: %s', src)
                continue
            try:
                import shutil as _shutil
                _shutil.copy2(src, os.path.join(dest_dir, fname))
                copied += 1
            except Exception as _cp_exc:
                LOG.warning('Could not restore symbol library file %s: %s', fname, _cp_exc)
        # Create the Library record if absent
        try:
            lib_obj, created = Library.objects.get_or_create(
                name=lib_name,
                defaults={'description': lib_data.get('description') or ''},
            )
            action = 'created' if created else 'reused'
            report.append({
                'symbol_library_imported': {
                    'name': lib_name,
                    'files_copied': copied,
                    'action': action,
                },
            })
        except Exception as _lib_exc:
            LOG.warning('Could not create/reuse Library record "%s": %s', lib_name, _lib_exc)


def _import_layer_enumerations(layer_entry, lyr, username):
    """Create missing Enumeration/EnumerationItem records and bind them to *lyr*."""
    for en in layer_entry.get('enumerations', []):
        enum = None
        if en.get('enumeration_id'):
            enum = Enumeration.objects.filter(id=en['enumeration_id']).first()
        if enum is None and en.get('enumeration_name'):
            enum = Enumeration.objects.filter(name=en['enumeration_name']).first()
        if enum is None and en.get('enumeration_name') and en.get('enumeration_items') is not None:
            try:
                enum = Enumeration.objects.create(
                    name=en['enumeration_name'],
                    title=en.get('enumeration_title') or en['enumeration_name'],
                    created_by=username,
                    order_type=en.get('enumeration_order_type') or 'alphabetical',
                    show_first_value=bool(en.get('enumeration_show_first_value')),
                )
                for item in en.get('enumeration_items') or []:
                    EnumerationItem.objects.create(
                        enumeration=enum,
                        name=item['name'],
                        selected=bool(item.get('selected')),
                        order=int(item.get('order') or 0),
                    )
                LOG.info('Created enumeration "%s" from package', enum.name)
            except Exception as _enum_exc:
                LOG.warning(
                    'Could not create enumeration "%s": %s',
                    en.get('enumeration_name'), _enum_exc,
                )
                enum = None
        if enum:
            LayerFieldEnumeration.objects.get_or_create(
                layer=lyr,
                field=en['field'],
                defaults={
                    'enumeration': enum,
                    'multiple': bool(en.get('multiple')),
                },
            )


def _import_layer_resources(layer_entry, lyr, extract_dir):
    """Restore LayerResource (feature attachments) for *lyr* from the package.

    Files packaged under ``layer_resources/{eid}/`` are copied to the correct
    ``MEDIA_ROOT/resources/{lyr.id}/{type_dir}/`` directory so that serving
    code can find them.  URL/Alfresco resources (path starts with http/https)
    are kept as-is without file copying.
    """
    for res in layer_entry.get('layer_resources', []):
        feat = res.get('feature')
        if feat is None:
            continue
        try:
            rtype = int(res.get('type', LayerResource.EXTERNAL_FILE))
        except (TypeError, ValueError):
            rtype = LayerResource.EXTERNAL_FILE

        new_path = res.get('path') or ''
        zip_path = res.get('zip_path')
        if zip_path:
            src = os.path.join(extract_dir, zip_path.replace('/', os.sep))
            if os.path.isfile(src):
                try:
                    dest_dir = services_utils.get_resources_dir(lyr.id, rtype)
                    fname = os.path.basename(src)
                    dest_file = os.path.join(dest_dir, fname)
                    if not os.path.exists(dest_file):
                        shutil.copy2(src, dest_file)
                    new_path = os.path.relpath(dest_file, settings.MEDIA_ROOT)
                except Exception as _lrcp_exc:
                    LOG.warning(
                        'Could not restore layer resource %s for layer %s: %s',
                        zip_path, lyr.name, _lrcp_exc,
                    )
            else:
                LOG.warning(
                    'Layer resource file missing in package: %s (layer %s)',
                    zip_path, lyr.name,
                )

        LayerResource(
            layer=lyr,
            feature=int(feat),
            title=res.get('title') or '',
            path=new_path,
            type=rtype,
        ).save()


def _import_vector_layer(
    extract_dir,
    layer_entry,
    target_datastore,
    layer_group,
    server,
    username,
    import_permissions,
    id_map,
    report,
    use_ds_schema=False,
):
    ld = layer_entry['layer']
    gpkg_rel = layer_entry['vector_gpkg']
    gpkg_path = os.path.join(extract_dir, gpkg_rel.replace('/', os.sep))
    if not os.path.isfile(gpkg_path):
        report.append({'error': 'missing_gpkg', 'export_id': layer_entry.get('export_id')})
        return None
    layer_label = ld.get('title') or ld.get('name') or layer_entry.get('export_id')
    schema = _gpkg_load_schema(target_datastore, ld, use_ds_schema=use_ds_schema)
    _ensure_cartodb_schema_exists(schema)
    table_base = ld.get('source_name') or ld.get('name')
    table_name = _unique_gpkg_table_name(target_datastore, schema, table_base, report)

    pg_conn = pg_connection_from_datastore(target_datastore, schema=schema)
    gpkg_layer = _gpkg_source_layer_name(gpkg_path, layer_entry)
    try:
        import_gpkg_to_postgis(gpkg_path, gpkg_layer, pg_conn, table_name, schema)
    except Exception as gpkg_ex:
        LOG.warning(
            'GPKG import failed for layer %s (%s.%s): %s',
            layer_label, schema, table_name, gpkg_ex,
        )
        report.append({
            'gpkg_layer_skipped': {
                'export_id': layer_entry.get('export_id'),
                'layer': layer_label,
                'connection_key': ld.get('datastore_connection_key') or 'local_cartodb',
                'reason': 'gpkg_import_failed',
                'message': _(
                    'Layer "%(layer)s" could not be loaded into PostGIS '
                    '(%(schema)s.%(table)s): %(error)s'
                ) % {
                    'layer': layer_label,
                    'schema': schema,
                    'table': table_name,
                    'error': str(gpkg_ex),
                },
            },
        })
        return None
    table_name = _verify_gpkg_table_loaded(target_datastore, schema, table_name)
    report.append({'gpkg_loaded': {'schema': schema, 'table': table_name}})

    layer_conf = {}
    try:
        layer_conf = ast.literal_eval(ld.get('conf') or '{}')
    except Exception:
        layer_conf = {}

    if target_datastore.type in ('PostGIS', 'PostgreSQL', 'v_PostGIS'):
        intro = None
        try:
            intro, _db_params = target_datastore.get_db_connection()
            if intro:
                intro.promote_untyped_geometry_columns(schema, table_name)
                # For empty tables promote_untyped_geometry_columns cannot detect
                # the geometry type from data.  Fall back to the exported conf.
                _hint = (
                    layer_conf.get('featuretype', {}).get('geomtype') or ''
                ).strip().upper()
                if _hint and _hint not in ('', 'GEOMETRY', 'UNKNOWN'):
                    from gvsigol_services.backend_postgis import _GEOMETRY_SUBTYPES_GEOSERVER
                    if _hint in _GEOMETRY_SUBTYPES_GEOSERVER:
                        intro.promote_untyped_geometry_columns_hint(
                            schema, table_name, _hint
                        )
        except Exception as ex:
            LOG.warning(
                'Could not narrow generic geometry column after GPKG import %s.%s: %s',
                schema,
                table_name,
                ex,
                exc_info=True,
            )
        finally:
            if intro:
                intro.close()

    extra_params = {'max_features': layer_conf.get('featuretype', {}).get('', 0)}

    gs_layer_name = table_name

    _publish_vector_layer_on_geoserver(
        server,
        target_datastore,
        gs_layer_name,
        table_name,
        ld.get('title') or table_name,
        ld.get('queryable', True),
        extra_params,
        native_srs=ld.get('native_srs'),
        schema=schema,
    )

    lyr = Layer(
        external=False,
        external_params=ld.get('external_params'),
        datastore=target_datastore,
        layer_group=layer_group,
        name=gs_layer_name,
        title=ld.get('title'),
        abstract=ld.get('abstract'),
        type='v_PostGIS',
        public=ld.get('public', False),
        visible=ld.get('visible', False),
        queryable=ld.get('queryable', True),
        cached=ld.get('cached', False),
        single_image=ld.get('single_image', False),
        vector_tile=ld.get('vector_tile', False),
        allow_download=ld.get('allow_download', False),
        time_enabled=ld.get('time_enabled', False),
        time_enabled_field=ld.get('time_enabled_field'),
        time_enabled_endfield=ld.get('time_enabled_endfield'),
        time_presentation=ld.get('time_presentation'),
        time_resolution_year=ld.get('time_resolution_year') or 0,
        time_resolution_month=ld.get('time_resolution_month') or 0,
        time_resolution_week=ld.get('time_resolution_week') or 0,
        time_resolution_day=ld.get('time_resolution_day') or 0,
        time_resolution_hour=ld.get('time_resolution_hour') or 0,
        time_resolution_minute=ld.get('time_resolution_minute') or 0,
        time_resolution_second=ld.get('time_resolution_second') or 0,
        time_default_value_mode=ld.get('time_default_value_mode'),
        time_default_value=ld.get('time_default_value'),
        time_resolution=ld.get('time_resolution'),
        order=ld.get('order') or 100,
        created_by=username,
        conf=ld.get('conf'),
        detailed_info_enabled=ld.get('detailed_info_enabled', True),
        detailed_info_button_title=ld.get('detailed_info_button_title'),
        detailed_info_html=ld.get('detailed_info_html'),
        timeout=ld.get('timeout') or 30000,
        native_srs=ld.get('native_srs') or 'EPSG:4326',
        native_extent=ld.get('native_extent') or '-180,-90,180,90',
        latlong_extent=ld.get('latlong_extent') or '-180,-90,180,90',
        source_name=table_name,
        real_time=ld.get('real_time', False),
        update_interval=ld.get('update_interval') or 1000,
        featureapi_endpoint=ld.get('featureapi_endpoint') or '/api/v1',
    )
    lyr.save()

    if import_permissions:
        admin_role = auth_backend.get_admin_role()
        read_roles = [admin_role]
        write_roles = [admin_role]
        for row in layer_entry.get('permissions', {}).get('read_roles', []):
            lr = LayerReadRole(layer=lyr, role=row['role'], filtered=row.get('filtered', False), external=row.get('external', False))
            lr.save()
            read_roles.append(row['role'])
        for row in layer_entry.get('permissions', {}).get('write_roles', []):
            lw = LayerWriteRole(layer=lyr, role=row['role'], filtered=row.get('filtered', False), external=row.get('external', False))
            lw.save()
            write_roles.append(row['role'])
        for row in layer_entry.get('permissions', {}).get('manage_roles', []):
            LayerManageRole(layer=lyr, role=row['role']).save()
        server.setLayerDataRules(lyr, read_roles, write_roles)

    try:
        services_utils.set_time_enabled(server, lyr)
    except Exception as _ste_exc:
        LOG.warning(
            'set_time_enabled failed for layer %r (time_enabled=%s, field=%r): %s',
            lyr.name,
            lyr.time_enabled,
            lyr.time_enabled_field,
            _ste_exc,
        )

    _import_layer_enumerations(layer_entry, lyr, username)
    _import_layer_resources(layer_entry, lyr, extract_dir)

    default_done = False
    for i, st in enumerate(layer_entry.get('styles', [])):
        raw = st.get('sld')
        if isinstance(raw, bytes):
            sld_text = raw.decode('utf-8', errors='replace')
        else:
            sld_text = raw or ''
        sld_text = sld_text.strip()
        if not sld_text:
            continue
        style_name = _unique_style_name(server, lyr.datastore.workspace.name, st.get('name') or ('imported_%d' % i))
        is_def = bool(st.get('is_default')) and not default_done
        if is_def:
            default_done = True
        sld_import(style_name, is_def, lyr.id, StringIO(sld_text), server, style_type=st.get('type'))

    _reload_geoserver_vector_layer(server, lyr)
    server.updateThumbnail(lyr, 'create')
    core_utils.toc_add_layer(lyr)
    server.createOrUpdateGeoserverLayerGroup(lyr.layer_group)
    if lyr.vector_tile:
        server.update_vector_tile_format(lyr.datastore.workspace, lyr.name, True)
    if lyr.cached:
        server.reload_master()
    id_map[layer_entry['export_id']] = lyr.id
    report.append({'imported': 'vector', 'layer': lyr.name, 'table': table_name})
    return lyr


def _connection_for_import_key(connection_key, foreign_connection_map):
    if connection_key in (None, '', 'local_cartodb'):
        return None
    conn_id = foreign_connection_map.get(connection_key)
    if not conn_id and str(connection_key).startswith('conn_'):
        try:
            conn_id = int(str(connection_key)[5:])
        except (TypeError, ValueError):
            conn_id = None
    if not conn_id:
        raise ValueError(
            _('No database connection selected for "%(key)s"')
            % {'key': connection_key}
        )
    return Connection.objects.get(id=int(conn_id))


def _resolve_workspace_for_import(server_id, ws_name, ws_objs, username, report):
    """Return workspace object, creating or reusing it on the target server."""
    ws_obj = ws_objs.get(ws_name)
    if ws_obj:
        return ws_obj
    ws_obj, created = _get_or_create_workspace(server_id, ws_name, username)
    ws_objs[ws_name] = ws_obj
    if created:
        report.append({'workspace_created': ws_name})
    else:
        report.append({'workspace_reused': ws_name})
    return ws_obj


def _resolve_definition_datastore(
    ld,
    default_ws,
    server_id,
    ws_objs,
    datastore_map,
    connection_ds_cache,
    foreign_connection_map,
    username,
    report,
):
    wk, dk = _normalized_ws_ds_for_vector_layer(ld, default_ws)
    schema = _packaged_postgis_schema(ld)
    ck = ld.get('datastore_connection_key') or 'local_cartodb'

    if ck == 'local_cartodb':
        ds = datastore_map.get((wk, dk))
        if not ds:
            ws_obj = _resolve_workspace_for_import(server_id, wk, ws_objs, username, report)
            ds, _ds_created = _get_or_create_datastore(username, ws_obj, dk, report)
            datastore_map[(wk, dk)] = ds
        return ds

    try:
        connection = _connection_for_import_key(ck, foreign_connection_map)
    except (ValueError, Exception):
        # Connection key not mapped or doesn't exist on this server.
        # The source datastore may be a local PostGIS that happens to use a
        # Connection object (conn_N), but the view is local data — fall back
        # to creating a plain local datastore with the same name.
        LOG.warning(
            '_resolve_definition_datastore: connection key %r not found, '
            'falling back to local datastore for %s/%s', ck, wk, dk
        )
        ds = datastore_map.get((wk, dk))
        if not ds:
            ws_obj = _resolve_workspace_for_import(server_id, wk, ws_objs, username, report)
            ds, _ds_created = _get_or_create_datastore(username, ws_obj, dk, report)
            datastore_map[(wk, dk)] = ds
        return ds

    if not schema:
        schema = _connection_default_schema(connection)
    cache_key = (wk, dk, connection.id, schema)
    if cache_key in connection_ds_cache:
        return connection_ds_cache[cache_key]
    ws_obj = _resolve_workspace_for_import(server_id, wk, ws_objs, username, report)
    ds, _ds_created = _get_or_create_connection_datastore(username, ws_obj, dk, connection, schema, report)
    if ds.connection_id != connection.id:
        ds.connection = connection
        ds.schema = schema
        ds.legacy_mode = False
        ds.save(update_fields=['connection', 'schema', 'legacy_mode'])
    connection_ds_cache[cache_key] = ds
    datastore_map[(wk, dk, connection.id)] = ds
    return ds


def _import_postgis_definition_layer(
    layer_entry,
    target_datastore,
    layer_group,
    server,
    username,
    import_permissions,
    id_map,
    report,
    server_id=None,
    group_reuse_state=None,
    skip_layer_reuse=False,
    extract_dir=None,
):
    ld = layer_entry['layer']
    table_name = (ld.get('source_name') or ld.get('name') or 'layer').strip()
    if not table_name:
        raise ValueError(_('Definition-only layer has no table name in package metadata'))

    schema = _datastore_postgis_schema(target_datastore, ld)
    layer_name = _unique_layer_name(target_datastore, ld.get('name') or table_name)
    workspace = target_datastore.workspace
    conn_label = (
        target_datastore.connection.name
        if target_datastore.is_using_connection() and target_datastore.connection
        else target_datastore.name
    )

    if not _postgis_table_exists(target_datastore, schema, table_name):
        report.append({
            'definition_layer_skipped': {
                'export_id': layer_entry.get('export_id'),
                'layer': layer_name,
                'table': '%s.%s' % (schema, table_name),
                'datastore': target_datastore.name,
                'connection': conn_label,
                'reason': 'table_not_found',
                'message': _(
                    'Definition-only layer "%(layer)s": table "%(schema)s"."%(table)s" '
                    'was not found in connection "%(connection)s". The layer was not imported.'
                ) % {
                    'layer': layer_name,
                    'schema': schema,
                    'table': table_name,
                    'connection': conn_label,
                },
            },
        })
        LOG.warning(
            'Skipping definition-only layer %s: missing table %s.%s (datastore %s)',
            layer_name,
            schema,
            table_name,
            target_datastore.name,
        )
        return None

    existing = None if skip_layer_reuse else _find_reusable_definition_layer(layer_entry, target_datastore, layer_group)
    if existing:
        reuse_payload = {
            'export_id': layer_entry.get('export_id'),
            'layer': existing.name,
            'layer_id': existing.id,
            'layer_group': existing.layer_group.name,
            'connection': conn_label,
        }
        if existing.layer_group_id != layer_group.id and group_reuse_state is not None:
            fld = group_reuse_state.setdefault('foreign_definition_layers', {})
            fld.setdefault(existing.layer_group_id, set()).add(existing.id)
            reuse_payload['shared_layer_group_id'] = existing.layer_group_id
            reuse_payload['note'] = _(
                'Uses an existing LayerGroup on the server — the project will be linked '
                'to that group rather than stealing the Layer from another group.'
            )
        elif existing.layer_group_id == layer_group.id:
            reuse_payload['same_import_layer_group'] = True
        id_map[layer_entry['export_id']] = existing.id
        report.append({'definition_layer_reused': reuse_payload})
        return existing

    layer_conf = {}
    try:
        layer_conf = ast.literal_eval(ld.get('conf') or '{}')
    except Exception:
        layer_conf = {}
    extra_params = {'max_features': layer_conf.get('featuretype', {}).get('', 0)}

    if server.resource_exists(workspace.name, layer_name):
        report.append({
            'definition_layer_geoserver_exists': {
                'workspace': workspace.name,
                'layer': layer_name,
            },
        })
        LOG.info(
            'GeoServer layer %s:%s already published; skipping create_feature_type',
            workspace.name,
            layer_name,
        )
    else:
        try:
            _publish_vector_layer_on_geoserver(
                server,
                target_datastore,
                layer_name,
                table_name,
                ld.get('title') or layer_name,
                ld.get('queryable', True),
                extra_params,
                native_srs=ld.get('native_srs'),
                schema=schema,
            )
        except Exception as ex:
            report.append({
                'definition_layer_skipped': {
                    'export_id': layer_entry.get('export_id'),
                    'layer': layer_name,
                    'table': '%s.%s' % (schema, table_name),
                    'datastore': target_datastore.name,
                    'reason': 'geoserver_publish_failed',
                    'error': str(ex),
                    'message': _(
                        'Definition-only layer "%(layer)s": could not publish on GeoServer. '
                        'The layer was not imported.'
                    ) % {'layer': layer_name},
                },
            })
            LOG.warning(
                'Skipping definition-only layer %s after GeoServer publish failed: %s',
                layer_name,
                ex,
                exc_info=True,
            )
            return None

    lyr = Layer(
        external=False,
        external_params=ld.get('external_params'),
        datastore=target_datastore,
        layer_group=layer_group,
        name=layer_name,
        title=ld.get('title'),
        abstract=ld.get('abstract'),
        type='v_PostGIS',
        public=ld.get('public', False),
        visible=ld.get('visible', False),
        queryable=ld.get('queryable', True),
        cached=ld.get('cached', False),
        single_image=ld.get('single_image', False),
        vector_tile=ld.get('vector_tile', False),
        allow_download=ld.get('allow_download', False),
        time_enabled=ld.get('time_enabled', False),
        time_enabled_field=ld.get('time_enabled_field'),
        time_enabled_endfield=ld.get('time_enabled_endfield'),
        time_presentation=ld.get('time_presentation'),
        time_resolution_year=ld.get('time_resolution_year') or 0,
        time_resolution_month=ld.get('time_resolution_month') or 0,
        time_resolution_week=ld.get('time_resolution_week') or 0,
        time_resolution_day=ld.get('time_resolution_day') or 0,
        time_resolution_hour=ld.get('time_resolution_hour') or 0,
        time_resolution_minute=ld.get('time_resolution_minute') or 0,
        time_resolution_second=ld.get('time_resolution_second') or 0,
        time_default_value_mode=ld.get('time_default_value_mode'),
        time_default_value=ld.get('time_default_value'),
        time_resolution=ld.get('time_resolution'),
        order=ld.get('order') or 100,
        created_by=username,
        conf=ld.get('conf'),
        detailed_info_enabled=ld.get('detailed_info_enabled', True),
        detailed_info_button_title=ld.get('detailed_info_button_title'),
        detailed_info_html=ld.get('detailed_info_html'),
        timeout=ld.get('timeout') or 30000,
        native_srs=ld.get('native_srs') or 'EPSG:4326',
        native_extent=ld.get('native_extent') or '-180,-90,180,90',
        latlong_extent=ld.get('latlong_extent') or '-180,-90,180,90',
        source_name=table_name,
        real_time=ld.get('real_time', False),
        update_interval=ld.get('update_interval') or 1000,
        featureapi_endpoint=ld.get('featureapi_endpoint') or '/api/v1',
    )
    lyr.save()

    if import_permissions:
        admin_role = auth_backend.get_admin_role()
        read_roles = [admin_role]
        write_roles = [admin_role]
        for row in layer_entry.get('permissions', {}).get('read_roles', []):
            lr = LayerReadRole(
                layer=lyr,
                role=row['role'],
                filtered=row.get('filtered', False),
                external=row.get('external', False),
            )
            lr.save()
            read_roles.append(row['role'])
        for row in layer_entry.get('permissions', {}).get('write_roles', []):
            lw = LayerWriteRole(
                layer=lyr,
                role=row['role'],
                filtered=row.get('filtered', False),
                external=row.get('external', False),
            )
            lw.save()
            write_roles.append(row['role'])
        for row in layer_entry.get('permissions', {}).get('manage_roles', []):
            LayerManageRole(layer=lyr, role=row['role']).save()
        server.setLayerDataRules(lyr, read_roles, write_roles)

    try:
        services_utils.set_time_enabled(server, lyr)
    except Exception as _ste_exc:
        LOG.warning(
            'set_time_enabled failed for layer %r (time_enabled=%s, field=%r): %s',
            lyr.name,
            lyr.time_enabled,
            lyr.time_enabled_field,
            _ste_exc,
        )

    _import_layer_enumerations(layer_entry, lyr, username)
    _import_layer_resources(layer_entry, lyr, extract_dir)

    default_done = False
    for i, st in enumerate(layer_entry.get('styles', [])):
        raw = st.get('sld')
        if isinstance(raw, bytes):
            sld_text = raw.decode('utf-8', errors='replace')
        else:
            sld_text = raw or ''
        sld_text = sld_text.strip()
        if not sld_text:
            continue
        style_name = _unique_style_name(
            server,
            lyr.datastore.workspace.name,
            st.get('name') or ('imported_%d' % i),
        )
        is_def = bool(st.get('is_default')) and not default_done
        if is_def:
            default_done = True
        sld_import(style_name, is_def, lyr.id, StringIO(sld_text), server, style_type=st.get('type'))

    _reload_geoserver_vector_layer(server, lyr)
    server.updateThumbnail(lyr, 'create')
    core_utils.toc_add_layer(lyr)
    server.createOrUpdateGeoserverLayerGroup(lyr.layer_group)
    if lyr.vector_tile:
        server.update_vector_tile_format(lyr.datastore.workspace, lyr.name, True)
    if lyr.cached:
        server.reload_master()
    id_map[layer_entry['export_id']] = lyr.id
    report.append({'imported': 'vector_definition', 'layer': lyr.name, 'table': table_name})
    return lyr


def _import_view_sql_definition_layer(
    layer_entry,
    target_datastore,
    layer_group,
    server,
    username,
    import_permissions,
    id_map,
    report,
    server_id=None,
    sql_override=None,
    group_reuse_state=None,
    use_ds_schema=False,
    extract_dir=None,
):
    """
    Create a PostgreSQL view from a SQL definition and publish it in GeoServer.

    Flow:
    1. CREATE OR REPLACE VIEW in the target datastore (using the SQL from the
       manifest, optionally overridden by the wizard editor).
    2. Insert GT_pk_metadata rows so GeoServer can detect the primary key.
    3. Delegate the rest (GeoServer feature type + Django Layer) to
       _import_postgis_definition_layer, which will find the view via
       object_exists() and proceed normally.
    """
    ld = layer_entry.get('layer') or {}
    view_def = layer_entry.get('view_sql_definition') or {}
    layer_label = ld.get('title') or ld.get('name') or layer_entry.get('export_id')

    sql = (sql_override or view_def.get('sql') or '').strip()
    if not sql:
        report.append({
            'view_layer_skipped': {
                'export_id': layer_entry.get('export_id'),
                'layer': layer_label,
                'reason': 'no_sql',
                'message': _(
                    'View layer "%(layer)s" was not imported: no SQL definition available.'
                ) % {'layer': layer_label},
            },
        })
        return None

    # Always prefer the schema recorded in the view_sql_definition (captured at
    # export time directly from pg_get_viewdef / information_schema).  Only fall
    # back to the target-datastore schema when the export didn't record one.
    # When the user picked a different target datastore (use_ds_schema=True), use
    # that datastore's schema instead of the exported view's original schema.
    if use_ds_schema:
        schema = _datastore_postgis_schema(target_datastore, {})
    else:
        schema = (view_def.get('schema') or '').strip() or _datastore_postgis_schema(target_datastore, ld)
    base_view_name = (view_def.get('view_name') or ld.get('source_name') or ld.get('name') or 'view').strip()
    gt_pk_rows = view_def.get('gt_pk_metadata') or []

    # Ensure the schema exists (CartoDB setup may need it created).
    _ensure_cartodb_schema_exists(schema)

    intro = None
    view_name = base_view_name  # fallback so the except block can reference it safely
    try:
        intro, _conn_meta = target_datastore.get_db_connection()

        # Create a brand-new, uniquely-named view every time (force_unique=True).
        # This guarantees that each import produces an independent view instead of
        # overwriting an existing one with CREATE OR REPLACE VIEW.
        # create_view_from_sql returns the actual name used (base_view_name or _1, _2, …).
        view_name = intro.create_view_from_sql(schema, base_view_name, sql, force_unique=True)
        LOG.info('Created new view %s.%s in datastore %s', schema, view_name, target_datastore.name)
        # GT_pk_metadata: insert/update all exported rows with the target view_name.
        for row in gt_pk_rows:
            row_copy = dict(row)
            row_copy['table_schema'] = schema
            row_copy['table_name'] = view_name
            intro.insert_gt_pk_metadata_full_row(schema, view_name, row_copy)
        intro.cursor.connection.commit()
        report.append({
            'view_created': {
                'schema': schema,
                'view': view_name,
                'pk_metadata_rows': len(gt_pk_rows),
            },
        })
    except Exception as ex:
        if intro:
            try:
                intro.cursor.connection.rollback()
            except Exception:
                pass
        report.append({
            'view_layer_skipped': {
                'export_id': layer_entry.get('export_id'),
                'layer': layer_label,
                'reason': 'create_view_failed',
                'message': _(
                    'View layer "%(layer)s" was not imported: could not create view '
                    '"%(schema)s"."%(view)s": %(error)s'
                ) % {
                    'layer': layer_label,
                    'schema': schema,
                    'view': view_name,
                    'error': str(ex),
                },
            },
        })
        LOG.warning(
            'Skipping view layer %s: could not create view %s.%s: %s',
            layer_label, schema, view_name, ex, exc_info=True,
        )
        return None
    finally:
        if intro:
            try:
                intro.close()
            except Exception:
                pass

    # Update source_name and name in the layer metadata so _import_postgis_definition_layer
    # uses the actual created view name (may include a numeric suffix from create_view_from_sql).
    ld_copy = dict(ld)
    ld_copy['source_name'] = view_name
    ld_copy['name'] = view_name
    # Override schema_name so _datastore_postgis_schema() in the publishing step
    # looks in the same schema where we just created the view.
    ld_copy['schema_name'] = schema
    entry_copy = dict(layer_entry)
    entry_copy['layer'] = ld_copy

    # Now the view exists in PostGIS — delegate GeoServer publishing + Django Layer creation.
    # Pass skip_layer_reuse=True: SQL view layers must always be published as a NEW
    # GeoServer/Django layer.  Never reuse an existing Layer object (even if one with the
    # same name exists from a previous import), because the view was just (re-)created and
    # needs its own fresh metadata record, style, and TOC entry.
    return _import_postgis_definition_layer(
        entry_copy,
        target_datastore,
        layer_group,
        server,
        username,
        import_permissions,
        id_map,
        report,
        server_id=server_id,
        group_reuse_state=group_reuse_state,
        skip_layer_reuse=True,
        extract_dir=extract_dir,
    )


def _import_definition_layer_entry(
    layer_entry,
    default_ws,
    server_id,
    layer_group,
    gs,
    username,
    import_permissions,
    id_map,
    report,
    ws_objs,
    datastore_map,
    connection_ds_cache,
    foreign_connection_map,
    group_reuse_state=None,
    extract_dir=None,
):
    """Import one definition-only layer; never abort the whole job on failure."""
    ld = layer_entry.get('layer') or {}
    layer_label = ld.get('title') or ld.get('name') or layer_entry.get('export_id')
    try:
        target_ds = _resolve_definition_datastore(
            ld,
            default_ws,
            server_id,
            ws_objs,
            datastore_map,
            connection_ds_cache,
            foreign_connection_map,
            username,
            report,
        )
        return _import_postgis_definition_layer(
            layer_entry,
            target_ds,
            layer_group,
            gs,
            username,
            import_permissions,
            id_map,
            report,
            server_id=server_id,
            group_reuse_state=group_reuse_state,
            extract_dir=extract_dir,
        )
    except Exception as ex:
        report.append({
            'definition_layer_skipped': {
                'export_id': layer_entry.get('export_id'),
                'layer': layer_label,
                'reason': 'import_failed',
                'error': str(ex),
                'message': _(
                    'Definition-only layer "%(layer)s" was not imported. '
                    'You can add it manually later.'
                ) % {'layer': layer_label},
            },
        })
        LOG.warning(
            'Skipping definition-only layer %s: %s',
            layer_label,
            ex,
            exc_info=True,
        )
        return None


def _unique_style_name(server, ws_name, base):
    # Strip the workspace prefix from base before (re)adding it, so we never
    # end up with ws_foo_ws_foo_... in either the first attempt or the conflict loop.
    base_clean = (base or 'style')
    prefix = ws_name + '_'
    if base_clean.startswith(prefix):
        base_clean = base_clean[len(prefix):]
    name = (prefix + base_clean)[:210]
    i = 0
    salt = ''
    while server.getStyle(name) is not None:
        suffix = '_%d%s' % (i, salt)
        name = (prefix + base_clean)[: (210 - len(suffix))] + suffix
        i += 1
        if i % 1000 == 0:
            salt = '_' + get_random_string(3)
    return name


def _import_external_layer(layer_entry, layer_group, username, id_map, report):
    ld = layer_entry['layer']
    lyr = Layer(
        external=True,
        external_params=ld.get('external_params'),
        datastore=None,
        layer_group=layer_group,
        name=_unique_layer_name_external(layer_group, ld.get('name')),
        title=ld.get('title'),
        abstract=ld.get('abstract'),
        type=ld.get('type') or 'e_WMS',
        public=ld.get('public', False),
        visible=ld.get('visible', False),
        queryable=ld.get('queryable', True),
        cached=ld.get('cached', False),
        single_image=ld.get('single_image', False),
        vector_tile=ld.get('vector_tile', False),
        allow_download=ld.get('allow_download', False),
        time_enabled=ld.get('time_enabled', False),
        time_enabled_field=ld.get('time_enabled_field'),
        time_enabled_endfield=ld.get('time_enabled_endfield'),
        time_presentation=ld.get('time_presentation'),
        time_resolution_year=ld.get('time_resolution_year') or 0,
        time_resolution_month=ld.get('time_resolution_month') or 0,
        time_resolution_week=ld.get('time_resolution_week') or 0,
        time_resolution_day=ld.get('time_resolution_day') or 0,
        time_resolution_hour=ld.get('time_resolution_hour') or 0,
        time_resolution_minute=ld.get('time_resolution_minute') or 0,
        time_resolution_second=ld.get('time_resolution_second') or 0,
        time_default_value_mode=ld.get('time_default_value_mode'),
        time_default_value=ld.get('time_default_value'),
        time_resolution=ld.get('time_resolution'),
        order=ld.get('order') or 100,
        created_by=username,
        conf=ld.get('conf'),
        detailed_info_enabled=ld.get('detailed_info_enabled', True),
        detailed_info_button_title=ld.get('detailed_info_button_title'),
        detailed_info_html=ld.get('detailed_info_html'),
        timeout=ld.get('timeout') or 30000,
        native_srs=ld.get('native_srs') or 'EPSG:4326',
        native_extent=ld.get('native_extent') or '-180,-90,180,90',
        latlong_extent=ld.get('latlong_extent') or '-180,-90,180,90',
        source_name=ld.get('source_name'),
        real_time=ld.get('real_time', False),
        update_interval=ld.get('update_interval') or 1000,
        featureapi_endpoint=ld.get('featureapi_endpoint') or '/api/v1',
    )
    lyr.save()
    id_map[layer_entry['export_id']] = lyr.id
    report.append({'imported': 'external', 'layer': lyr.name})
    return lyr


def _build_source_layer_id_index(snapshot):
    """Map source Layer.pk -> package export_id for default/overview resolution."""
    index = {}
    for group in snapshot.get('layer_groups', []):
        for layer_entry in group.get('layers', []):
            src_id = layer_entry.get('source_layer_id')
            eid = layer_entry.get('export_id')
            if src_id is not None and eid:
                index[src_id] = eid
    return index


def _resolve_default_baselayer_export_id(plg, group_layers, source_id_index):
    """Resolve default base layer export_id (current + legacy package formats)."""
    eid = plg.get('default_baselayer_export_id')
    if eid:
        return eid

    for layer_entry in group_layers:
        if layer_entry.get('is_default_baselayer'):
            return layer_entry['export_id']

    legacy_pk = plg.get('default_baselayer')
    if legacy_pk is None:
        return None
    try:
        legacy_pk = int(legacy_pk)
    except (TypeError, ValueError):
        return None

    eid = source_id_index.get(legacy_pk)
    if eid:
        return eid

    if plg.get('baselayer_group') and group_layers:
        LOG.warning(
            'Legacy package: could not map default_baselayer pk %s; using first layer in base group',
            legacy_pk,
        )
        return group_layers[0]['export_id']
    return None


def _resolve_layer_overview_export_id(pdata, source_id_index):
    eid = pdata.get('layer_overview_export_id')
    if eid:
        return eid
    raw = pdata.get('layer_overview')
    if raw in (None, ''):
        return None
    try:
        legacy_pk = int(raw)
    except (TypeError, ValueError):
        return None
    return source_id_index.get(legacy_pk)


def _unique_layer_name_external(layer_group, base):
    name = base or 'layer'
    i = 1
    salt = ''
    while Layer.objects.filter(name=name, layer_group=layer_group).exists():
        name = (base or 'layer') + '_' + str(i) + salt
        i += 1
        if i % 1000 == 0:
            salt = '_' + get_random_string(3)
    return name


def _import_raster_layer(
    layer_entry, layer_group, extract_dir, server_id, ws_objs, default_ws,
    gs, username, id_map, report, job_id,
):
    """
    Copy raster bundle from the extracted package directly into the raster import root
    (no subdirectory), resolving name conflicts by appending _1, _2, ... to the stem.
    Then create a GeoTIFF datastore+coverage in GeoServer, register a Layer in DB,
    and record the new id in id_map.
    """
    ld = layer_entry['layer']
    bundle = layer_entry.get('raster_bundle') or {}
    lt = layer_entry.get('layer_type') or ld.get('type') or 'c_GeoTIFF'
    eid = layer_entry.get('export_id')

    raster_root = _raster_import_root()
    os.makedirs(raster_root, exist_ok=True)

    # Determine primary file name from bundle, fall back to first file
    primary_name = bundle.get('primary') or ''
    if not primary_name:
        for fi in bundle.get('files', []):
            candidate = os.path.basename(fi.get('path_in_zip', ''))
            if candidate.lower().endswith(('.tif', '.tiff', '.img', '.nc', '.jpg', '.png')):
                primary_name = candidate
                break
        if not primary_name and bundle.get('files'):
            primary_name = os.path.basename(bundle['files'][0]['path_in_zip'])

    if not primary_name:
        report.append({'raster_import_error': 'no_primary_file', 'export_id': eid, 'layer': ld.get('name')})
        LOG.error('_import_raster_layer: no primary file found for layer %s (export_id=%s)', ld.get('name'), eid)
        return None

    p_stem, p_ext = os.path.splitext(primary_name)

    # Resolve unique stem to avoid overwriting an existing raster
    new_stem = p_stem
    counter = 1
    while os.path.exists(os.path.join(raster_root, new_stem + p_ext)):
        new_stem = '%s_%d' % (p_stem, counter)
        counter += 1

    # Copy all bundle files renaming those that share the primary stem
    copied = []
    for fi in bundle.get('files', []):
        src = os.path.join(extract_dir, fi['path_in_zip'].replace('/', os.sep))
        if not os.path.isfile(src):
            LOG.warning('_import_raster_layer: bundle file not found: %s', src)
            continue
        orig_basename = os.path.basename(fi['path_in_zip'])
        orig_stem, orig_ext = os.path.splitext(orig_basename)
        if orig_stem.lower() == p_stem.lower():
            new_basename = new_stem + orig_ext
        else:
            new_basename = orig_basename
        dst = os.path.join(raster_root, new_basename)
        shutil.copy2(src, dst)
        copied.append(dst)

    if not copied:
        report.append({'raster_import_error': 'no_files_copied', 'export_id': eid, 'layer': ld.get('name')})
        LOG.error('_import_raster_layer: no files copied for layer %s (export_id=%s)', ld.get('name'), eid)
        return None

    primary_path = os.path.join(raster_root, new_stem + p_ext)
    if not os.path.isfile(primary_path):
        primary_path = copied[0]

    LOG.info(
        '_import_raster_layer: copied %d file(s) for layer %s -> %s',
        len(copied), ld.get('name'), primary_path,
    )

    ws_name = ld.get('workspace_name') or default_ws
    try:
        ws_obj = _resolve_workspace_for_import(server_id, ws_name, ws_objs, username, report)
    except Exception as exc:
        report.append({'raster_import_error': str(exc), 'layer': ld.get('name'), 'step': 'workspace'})
        LOG.error('_import_raster_layer: workspace error for %s: %s', ld.get('name'), exc, exc_info=True)
        return None

    base_ds_name = ld.get('datastore_name') or ld.get('name') or 'raster'
    ds_name = base_ds_name
    counter = 1
    while Datastore.objects.filter(workspace=ws_obj, name=ds_name).exists():
        ds_name = '%s_%d' % (base_ds_name, counter)
        counter += 1

    # GeoServer URL: file:///absolute/path/to/primary.tif
    tif_url = 'file://' + primary_path.replace(os.sep, '/')
    conn_params = json.dumps({'url': tif_url})
    LOG.info('_import_raster_layer: creating datastore %s with url=%s', ds_name, tif_url)
    try:
        ds_obj = services_utils.add_datastore(
            ws_obj, lt, ds_name, ld.get('abstract') or ds_name, conn_params, username
        )
        if not ds_obj:
            raise RuntimeError('add_datastore returned None')
    except Exception as exc:
        LOG.error('_import_raster_layer: create_datastore failed for %s: %s', ld.get('name'), exc, exc_info=True)
        report.append({'raster_import_error': str(exc), 'layer': ld.get('name'), 'step': 'create_datastore'})
        return None

    base_layer_name = ld.get('name') or ds_name
    layer_name = base_layer_name
    counter = 1
    try:
        while gs.resource_exists(ws_obj.name, layer_name):
            layer_name = '%s_%d' % (base_layer_name, counter)
            counter += 1
        gs.createCoverage(ws_obj, ds_obj, layer_name, ld.get('title') or layer_name)
    except Exception as exc:
        LOG.error('_import_raster_layer: createCoverage failed for %s: %s', ld.get('name'), exc, exc_info=True)
        report.append({'raster_import_error': str(exc), 'layer': ld.get('name'), 'step': 'create_coverage'})
        return None

    lyr = Layer(
        external=False,
        datastore=ds_obj,
        layer_group=layer_group,
        name=layer_name,
        title=ld.get('title'),
        abstract=ld.get('abstract'),
        type=lt,
        public=ld.get('public', False),
        visible=ld.get('visible', False),
        queryable=ld.get('queryable', False),
        cached=ld.get('cached', False),
        single_image=ld.get('single_image', False),
        vector_tile=ld.get('vector_tile', False),
        allow_download=ld.get('allow_download', False),
        time_enabled=ld.get('time_enabled', False),
        time_enabled_field=ld.get('time_enabled_field') or '',
        time_enabled_endfield=ld.get('time_enabled_endfield') or '',
        time_presentation=ld.get('time_presentation') or '',
        time_resolution_year=ld.get('time_resolution_year'),
        time_resolution_month=ld.get('time_resolution_month'),
        time_resolution_week=ld.get('time_resolution_week'),
        time_resolution_day=ld.get('time_resolution_day'),
        time_resolution_hour=ld.get('time_resolution_hour'),
        time_resolution_minute=ld.get('time_resolution_minute'),
        time_resolution_second=ld.get('time_resolution_second'),
        time_default_value_mode=ld.get('time_default_value_mode') or '',
        time_default_value=ld.get('time_default_value') or '',
        time_resolution=ld.get('time_resolution') or '',
        conf=ld.get('conf') or '',
        detailed_info_enabled=ld.get('detailed_info_enabled', False),
        detailed_info_button_title=ld.get('detailed_info_button_title') or '',
        detailed_info_html=ld.get('detailed_info_html') or '',
        timeout=ld.get('timeout'),
        real_time=ld.get('real_time', False),
        update_interval=ld.get('update_interval'),
        featureapi_endpoint=ld.get('featureapi_endpoint') or '',
        created_by=username,
        order=ld.get('order') or 1,
        native_srs=ld.get('native_srs'),
        native_extent=ld.get('native_extent'),
        latlong_extent=ld.get('latlong_extent'),
    )
    lyr.save()
    if eid:
        id_map[eid] = lyr.id
    LOG.info(
        '_import_raster_layer: published layer=%s datastore=%s path=%s',
        lyr.name, ds_name, primary_path,
    )
    report.append({'raster_layer_published': {
        'layer': lyr.name,
        'datastore': ds_name,
        'primary_path': primary_path,
        'files_copied': len(copied),
    }})

    # Apply exported styles (SLD) to the raster layer
    server_obj = gs  # gs is already the server object
    default_done = False
    for i, st in enumerate(layer_entry.get('styles', [])):
        raw = st.get('sld')
        if isinstance(raw, bytes):
            sld_text = raw.decode('utf-8', errors='replace')
        else:
            sld_text = raw or ''
        sld_text = sld_text.strip()
        if not sld_text:
            continue
        try:
            style_name = _unique_style_name(
                server_obj, ws_obj.name, st.get('name') or ('raster_imported_%d' % i)
            )
            is_def = bool(st.get('is_default')) and not default_done
            sld_import(style_name, is_def, lyr.id, StringIO(sld_text), server_obj, style_type=st.get('type'))
            default_done = default_done or is_def
        except Exception as _sld_exc:
            LOG.warning(
                '_import_raster_layer: could not import style %d for %s: %s',
                i, lyr.name, _sld_exc,
            )

    return lyr


def _resolve_import_tools(raw_tools_json, report):
    """Merge exported tool states with the tools available on this server.

    * If ``raw_tools_json`` is None/empty the package was exported without tool
      configuration (checkbox unchecked) → return the standard default tool set:
      all core tools enabled, all plugin tools disabled — exactly what a brand-new
      project gets.
    * For each tool in the package (checkbox checked):
        - If it exists on this server: apply the exported ``checked`` state.
        - If it does NOT exist: add a warning to *report* and skip it.
    * Tools present on this server but absent from the package keep their
      default state (core tools enabled, plugin tools disabled).

    Returns a JSON string suitable for ``Project.tools``.
    """
    from gvsigol_core.utils import get_available_tools

    if not raw_tools_json:
        # No tool configuration exported → use the same defaults as a new project:
        # core tools all enabled, plugin tools all disabled.
        return json.dumps(get_available_tools(core_enabled=True, plugin_enabled=False))

    try:
        exported = json.loads(raw_tools_json) if isinstance(raw_tools_json, str) else raw_tools_json
    except Exception:
        return json.dumps(get_available_tools(core_enabled=True, plugin_enabled=False))
    if not isinstance(exported, list):
        return json.dumps(get_available_tools(core_enabled=True, plugin_enabled=False))

    available = get_available_tools(core_enabled=True, plugin_enabled=True)
    available_map = {t['name']: t for t in available}
    exported_map = {t['name']: t for t in exported if isinstance(t, dict) and t.get('name')}

    merged = []
    for name, avail_tool in available_map.items():
        if name in exported_map:
            entry = dict(avail_tool)
            entry['checked'] = bool(exported_map[name].get('checked', avail_tool.get('checked', False)))
            merged.append(entry)
        else:
            merged.append(avail_tool)

    for name in exported_map:
        if name not in available_map:
            LOG.warning('Tool "%s" from package is not installed on this server; skipping.', name)
            report.append({'tool_not_installed': name})

    return json.dumps(merged)


def _remap_toc_order(project, snapshot, id_map):
    """
    After import, patch toc_order so that group/layer name changes (due to
    conflict-driven renames) are reflected.  Otherwise the viewer silently
    ignores the stored order values for any layer or group whose name changed.

    Strategy:
    * Groups: match by position – snapshot['layer_groups'][i] corresponds to
      project.projectlayergroup_set.order_by('id')[i] because PLG rows are
      always created in snapshot order.
    * Layers: use id_map (export_id → new Layer pk) to look up the new name.
    """
    old_toc_str = project.toc_order
    if not old_toc_str:
        return
    try:
        old_toc = json.loads(old_toc_str)
    except Exception:
        return
    if not isinstance(old_toc, dict) or not old_toc:
        return

    snap_groups = snapshot.get('layer_groups', [])
    plgs = list(
        project.projectlayergroup_set.order_by('id').select_related('layer_group')
    )

    # Build old → new group name map (positional)
    group_name_map = {}
    for sg, plg in zip(snap_groups, plgs):
        old_gname = sg['layer_group']['name']
        new_gname = plg.layer_group.name
        if old_gname != new_gname:
            group_name_map[old_gname] = new_gname

    # Build old → new layer name map (via id_map)
    layer_name_map = {}
    for sg in snap_groups:
        for entry in sg.get('layers', []):
            eid = entry.get('export_id')
            old_name = (entry.get('layer') or {}).get('name') or ''
            if not eid or not old_name or eid not in id_map:
                continue
            new_id = id_map[eid]
            try:
                new_name = Layer.objects.get(id=new_id).name
                if new_name and new_name != old_name:
                    layer_name_map[old_name] = new_name
            except Layer.DoesNotExist:
                pass

    if not group_name_map and not layer_name_map:
        return  # nothing to remap

    new_toc = {}
    for old_gname, gdata in old_toc.items():
        new_gname = group_name_map.get(old_gname, old_gname)
        new_gdata = dict(gdata)
        new_gdata['name'] = new_gname
        old_layers = gdata.get('layers') or {}
        new_layers = {}
        for old_lname, ldata in old_layers.items():
            new_lname = layer_name_map.get(old_lname, old_lname)
            new_ldata = dict(ldata)
            new_ldata['name'] = new_lname
            new_layers[new_lname] = new_ldata
        new_gdata['layers'] = new_layers
        new_toc[new_gname] = new_gdata

    project.toc_order = json.dumps(new_toc)
    project.save(update_fields=['toc_order'])


def commit_job(job: ProjectPackageImportJob, username, progress_cb=None):
    wiz = job.wizard_json or {}
    report = list(job.report_json or [])
    id_map = {}

    server = Server.objects.get(id=int(wiz['target_server_id']))

    extract_dir = job.extract_dir
    if not extract_dir:
        raise ValueError(_('Job not extracted; run preflight first'))

    pj_path = os.path.join(extract_dir, PROJECT_JSON.replace('/', os.sep))
    with open(pj_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    pdata = snapshot['project']
    default_ws = _default_workspace_from_project(snapshot)
    layout = extract_snapshot_layout(snapshot)
    primary_ws_name = layout['primary_workspace']

    override_name = (wiz.get('override_project_name') or '').strip()
    base_project_name = override_name or pdata.get('name') or 'imported_project'
    project_name = _unique_project_name(base_project_name)

    override_title = (wiz.get('override_project_title') or '').strip()
    project_title = override_title or pdata.get('title') or project_name

    workspaces_created = []
    datastore_map = {}
    project = None
    gs = None
    clone_conf = None
    try:
        # Restore symbol library files and records before processing layers so
        # that ExternalGraphicSymbolizers in the imported SLDs resolve correctly.
        _import_symbol_libraries(snapshot, extract_dir, report)

        ws_objs = {}
        connection_ds_cache = {}
        foreign_connection_map = _autofill_foreign_connection_map(
            snapshot,
            wiz.get('foreign_connection_map') or {},
        )
        reuse_existing_groups = wiz.get('reuse_existing_layer_groups', True)
        skipped_definition_ids = _parse_skip_definition_export_ids(wiz, snapshot)
        skipped_view_ids = _parse_skip_view_export_ids(wiz)
        skipped_raster_ids = set(wiz.get('skip_raster_export_ids') or [])
        skipped_external_ids = set(wiz.get('skip_external_export_ids') or [])
        skipped_gpkg_ck = set(wiz.get('skip_gpkg_connection_keys') or [])
        skipped_gpkg_layer_ids = set(wiz.get('skip_gpkg_layer_export_ids') or [])
        view_sql_overrides = wiz.get('view_sql_overrides') or {}
        local_datastore_overrides = wiz.get('local_datastore_overrides') or {}
        required_foreign_keys = _foreign_connection_keys_required(snapshot, skipped_definition_ids)
        for ck in required_foreign_keys:
            if ck == 'local_cartodb':
                continue
            if ck not in foreign_connection_map:
                raise ValueError(
                    _('Select a database connection for "%(key)s"')
                    % {'key': ck}
                )

        gpkg_targets = {}
        datastore_map = {}
        ws_objs = {}
        if layout.get('gpkg_connection_targets'):
            gpkg_targets = _parse_gpkg_connection_targets(wiz, layout, server.id)
            datastore_map, ws_objs, ws_created_extra = _build_datastore_map_from_gpkg_targets(
                server.id, username, gpkg_targets, report
            )
            workspaces_created.extend(ws_created_extra)

        import_permissions = _package_has_permissions(snapshot)
        clone_conf = CloneConf(
            permissions=CloneConf.PERMISSION_CLONE if import_permissions else CloneConf.PERMISSION_SKIP,
            copy_data=True,
            clean_on_failure=True,
        )

        exp_date = pdata.get('expiration_date')
        exp_dt = parse_datetime(exp_date) if exp_date else None
        if import_permissions:
            project_is_public = pdata.get('is_public', False)
        else:
            project_is_public = True
        project = Project(
            name=project_name,
            title=project_title,
            description=pdata.get('description'),
            logo_link=pdata.get('logo_link'),
            center_lat=pdata.get('center_lat'),
            center_lon=pdata.get('center_lon'),
            zoom=pdata.get('zoom') or 10,
            extent=pdata.get('extent'),
            extent4326_minx=pdata.get('extent4326_minx'),
            extent4326_miny=pdata.get('extent4326_miny'),
            extent4326_maxx=pdata.get('extent4326_maxx'),
            extent4326_maxy=pdata.get('extent4326_maxy'),
            toc_mode=pdata.get('toc_mode') or 'toc_hidden',
            toc_order=pdata.get('toc_order'),
            created_by=username,
            is_public=project_is_public,
            show_project_icon=pdata.get('show_project_icon', True),
            selectable_groups=pdata.get('selectable_groups', False),
            restricted_extent=pdata.get('restricted_extent', False),
            tools=_resolve_import_tools(pdata.get('tools'), report),
            baselayer_version=pdata.get('baselayer_version'),
            labels=pdata.get('labels'),
            expiration_date=exp_dt,
            custom_overview=False,
            layer_overview=None,
            viewer_default_crs=pdata.get('viewer_default_crs') or 'EPSG:3857',
            viewer_preferred_ui=pdata.get('viewer_preferred_ui') or '',
        )
        project.save()

        # Restore project logo and image from the package
        for field_name, file_key in (('logo', 'logo_file'), ('image', 'image_file')):
            fname = pdata.get(file_key)
            if not fname:
                continue
            src = os.path.join(extract_dir, 'project_images', fname)
            if not os.path.isfile(src):
                LOG.warning('Project image missing in package: %s', src)
                continue
            try:
                from django.core.files import File as DjangoFile
                field = getattr(project, field_name)
                with open(src, 'rb') as fh:
                    field.save(fname, DjangoFile(fh), save=True)
            except Exception as _img_exc:
                LOG.warning('Could not restore project %s (%s): %s', field_name, fname, _img_exc)

        # Restore shared views (bookmarks / marcadores) for the project
        _sv_imported = 0
        for sv_data in snapshot.get('shared_views', []):
            try:
                new_name = datetime.date.today().strftime('%Y%m%d') + get_random_string(length=32)
                new_url = settings.BASE_URL + '/gvsigonline/core/load_shared_view/' + new_name
                sv_exp = None
                raw_exp = sv_data.get('expiration_date')
                if raw_exp:
                    try:
                        sv_exp = datetime.date.fromisoformat(raw_exp)
                    except Exception:
                        sv_exp = None
                if sv_exp is None:
                    sv_exp = datetime.date.max
                SharedView(
                    name=new_name,
                    project_id=project.id,
                    description=sv_data.get('description') or '',
                    url=new_url,
                    state=sv_data.get('state') or '',
                    expiration_date=sv_exp,
                    created_by=sv_data.get('created_by') or username,
                    internal=bool(sv_data.get('internal', False)),
                ).save()
                _sv_imported += 1
            except Exception as _sv_exc:
                LOG.warning('Could not restore shared view: %s', _sv_exc)
        if _sv_imported:
            LOG.info('commit_job: restored %d shared view(s) for project %s', _sv_imported, project.name)

        gs = geographic_servers.get_instance().get_server_by_id(server.id)
        pending_default_baselayers = []
        source_layer_id_index = _build_source_layer_id_index(snapshot)
        pending_layer_overview_eid = _resolve_layer_overview_export_id(
            pdata, source_layer_id_index
        )

        canonical_baselayer_lg_by_sig = {}

        # Pre-count total layers for progress reporting
        _total_layers = sum(
            len(g.get('layers', []))
            for g in snapshot.get('layer_groups', [])
        ) or 1
        _done_layers = 0

        for group in snapshot.get('layer_groups', []):
            lg_src = group['layer_group']
            plg_cfg = group['project_layer_group']
            layers_flat = group.get('layers', [])

            basemap_sig = None
            if plg_cfg.get('baselayer_group'):
                basemap_sig = _basemap_external_only_signature(layers_flat)

            lg = None
            basemap_canonical_hit = False
            group_is_preexisting = False
            if basemap_sig is not None and basemap_sig in canonical_baselayer_lg_by_sig:
                lg = canonical_baselayer_lg_by_sig[basemap_sig]
                basemap_canonical_hit = True
                report.append({
                    'basemap_stack_canonical_layer_group': {
                        'layer_group': lg.name,
                        'external_layers': len(basemap_sig),
                    },
                })

            if lg is None and not basemap_canonical_hit:
                # __default_baselayergroup__ is always reused unconditionally: its layers
                # are shared across all projects and must never be duplicated on import.
                if (lg_src.get('name') or '').strip() == '__default_baselayergroup__':
                    lg = _find_existing_layer_group(server.id, lg_src)
                    if lg:
                        group_is_preexisting = True
                        report.append({
                            'layer_group_reused': {
                                'name': lg.name,
                                'title': lg.title,
                                'note': 'default_baselayergroup_unconditional_reuse',
                            },
                        })
                elif reuse_existing_groups and _group_allows_layer_group_reuse(group):
                    lg = _find_existing_layer_group(server.id, lg_src)
                    if lg:
                        group_is_preexisting = True
                        report.append({
                            'layer_group_reused': {
                                'name': lg.name,
                                'title': lg.title,
                            },
                        })
            if lg is None:
                lg_name = _unique_layer_group_name(server.id, primary_ws_name, lg_src['name'])
                lg = LayerGroup(
                    server_id=server.id,
                    name=lg_name,
                    title=lg_src.get('title'),
                    visible=lg_src.get('visible', False),
                    cached=lg_src.get('cached', False),
                    created_by=username,
                )
                lg.save()
                report.append({'layer_group_created': lg.name})
            if basemap_sig is not None and not basemap_canonical_hit:
                canonical_baselayer_lg_by_sig[basemap_sig] = lg
            plg_obj = ProjectLayerGroup.objects.create(
                project=project,
                layer_group=lg,
                multiselect=plg_cfg.get('multiselect', True),
                baselayer_group=plg_cfg.get('baselayer_group', False),
                default_baselayer=None,
            )
            default_eid = _resolve_default_baselayer_export_id(
                plg_cfg,
                layers_flat,
                source_layer_id_index,
            )

            group_reuse_state = {}

            for layer_entry in layers_flat:
                lt = layer_entry.get('layer_type')

                if basemap_canonical_hit or group_is_preexisting:
                    ld0 = layer_entry['layer']
                    if ld0.get('external'):
                        lyr = _find_matching_external_in_layer_group(lg, layer_entry)
                        if lyr:
                            id_map[layer_entry['export_id']] = lyr.id
                            report.append({
                                'external_layer_reused': {
                                    'layer': lyr.name,
                                    'kind': 'external',
                                    'note': _(
                                        'Layer already exists in this group '
                                        '(reused, not duplicated).'
                                    ),
                                },
                            })
                            continue
                        _import_external_layer(layer_entry, lg, username, id_map, report)
                        continue
                    LOG.warning(
                        'Basemap canonical reuse: expected only external layers, got %s',
                        ld0.get('name'),
                    )
                    continue

                if _is_view_sql_layer_entry(layer_entry):
                    eid = layer_entry.get('export_id')
                    ld = layer_entry.get('layer') or {}
                    if eid and eid in skipped_view_ids:
                        report.append({
                            'view_layer_skipped': {
                                'export_id': eid,
                                'layer': ld.get('title') or ld.get('name'),
                                'reason': 'wizard_skip',
                                'message': _(
                                    'View layer "%(layer)s" was skipped by choice in the import wizard.'
                                ) % {'layer': ld.get('title') or ld.get('name')},
                            },
                        })
                        continue
                    # Use _resolve_definition_datastore (same as definition-only layers):
                    # it finds or creates the correct workspace/datastore on the target server,
                    # matching the exported workspace+datastore names.  Using
                    # _embedded_target_datastore here would fall back to the default GPKG
                    # datastore (typically schema=public) instead of the view's real schema.
                    view_ds_override = bool(eid and eid in local_datastore_overrides)
                    if view_ds_override:
                        target_ds = _datastore_by_id(local_datastore_overrides[eid]) or \
                            _resolve_definition_datastore(
                                ld, default_ws, server.id, ws_objs, datastore_map,
                                connection_ds_cache, foreign_connection_map, username, report,
                            )
                    else:
                        target_ds = _resolve_definition_datastore(
                            ld,
                            default_ws,
                            server.id,
                            ws_objs,
                            datastore_map,
                            connection_ds_cache,
                            foreign_connection_map,
                            username,
                            report,
                        )
                    _import_view_sql_definition_layer(
                        layer_entry,
                        target_ds,
                        lg,
                        gs,
                        username,
                        import_permissions,
                        id_map,
                        report,
                        server_id=server.id,
                        use_ds_schema=view_ds_override,
                        sql_override=view_sql_overrides.get(eid) if eid else None,
                        group_reuse_state=group_reuse_state,
                        extract_dir=extract_dir,
                    )
                elif lt == 'v_PostGIS' and layer_entry.get('vector_gpkg'):
                    ld = layer_entry['layer']
                    ck = ld.get('datastore_connection_key') or 'local_cartodb'
                    eid = layer_entry.get('export_id')
                    if (eid and eid in skipped_gpkg_layer_ids) or ck in skipped_gpkg_ck:
                        report.append({
                            'gpkg_layer_skipped': {
                                'export_id': eid,
                                'layer': ld.get('title') or ld.get('name'),
                                'connection_key': ck,
                                'reason': 'wizard_skip',
                            },
                        })
                        continue
                    # Foreign-source layers always go into the user-selected target
                    # datastore's schema (their packaged schema belongs to an entirely
                    # different database).  Local layers only force the target schema
                    # when the user explicitly changed the datastore in the wizard.
                    is_foreign_source = (
                        ck != 'local_cartodb' or bool(ld.get('datastore_is_foreign'))
                    )
                    if eid and eid in local_datastore_overrides:
                        target_ds = _datastore_by_id(local_datastore_overrides[eid]) or \
                            _embedded_target_datastore(ld, default_ws, gpkg_targets, datastore_map)
                        use_ds_schema = True
                    else:
                        target_ds = _embedded_target_datastore(ld, default_ws, gpkg_targets, datastore_map)
                        use_ds_schema = is_foreign_source
                    _import_vector_layer(
                        extract_dir,
                        layer_entry,
                        target_ds,
                        lg,
                        gs,
                        username,
                        import_permissions,
                        id_map,
                        report,
                        use_ds_schema=use_ds_schema,
                    )
                elif _is_definition_only_layer_entry(layer_entry):
                    eid = layer_entry.get('export_id')
                    if eid and eid in skipped_definition_ids:
                        ld = layer_entry.get('layer') or {}
                        report.append({
                            'definition_layer_skipped': {
                                'export_id': eid,
                                'layer': ld.get('title') or ld.get('name'),
                                'reason': 'wizard_skip',
                                'message': _(
                                    'Definition-only layer "%(layer)s" was skipped by choice in the import wizard.'
                                ) % {'layer': ld.get('title') or ld.get('name')},
                            },
                        })
                        continue
                    _import_definition_layer_entry(
                        layer_entry,
                        default_ws,
                        server.id,
                        lg,
                        gs,
                        username,
                        import_permissions,
                        id_map,
                        report,
                        ws_objs,
                        datastore_map,
                        connection_ds_cache,
                        foreign_connection_map,
                        group_reuse_state=group_reuse_state,
                        extract_dir=extract_dir,
                    )
                elif layer_entry['layer'].get('external'):
                    eid = layer_entry.get('export_id')
                    if eid and eid in skipped_external_ids:
                        ld2 = layer_entry.get('layer') or {}
                        report.append({
                            'external_layer_skipped': {
                                'export_id': eid,
                                'layer': ld2.get('title') or ld2.get('name'),
                                'reason': 'wizard_skip',
                            },
                        })
                        continue
                    _import_external_layer(layer_entry, lg, username, id_map, report)
                elif lt and lt.startswith('c_') and layer_entry.get('raster_bundle'):
                    eid = layer_entry.get('export_id')
                    if eid and eid in skipped_raster_ids:
                        ld2 = layer_entry.get('layer') or {}
                        report.append({
                            'raster_layer_skipped': {
                                'export_id': eid,
                                'layer': ld2.get('title') or ld2.get('name'),
                                'reason': 'wizard_skip',
                            },
                        })
                        continue
                    _import_raster_layer(
                        layer_entry, lg, extract_dir, server.id, ws_objs,
                        default_ws, gs, username, id_map, report, job.id,
                    )
                else:
                    report.append({'skipped': lt, 'export_id': layer_entry.get('export_id')})

                _done_layers += 1
                if progress_cb:
                    # Scale layer progress from 20% to 80%
                    pct = 20 + int(60 * _done_layers / _total_layers)
                    progress_cb(pct, 'importing_layers')

            _finalize_definition_foreign_layer_groups(
                project,
                plg_obj,
                lg,
                plg_cfg,
                group_reuse_state,
                report,
            )
            if default_eid:
                plg_fresh = ProjectLayerGroup.objects.filter(pk=plg_obj.pk).first()
                if plg_fresh:
                    pending_default_baselayers.append((plg_fresh, default_eid))

        for plg_obj, default_eid in pending_default_baselayers:
            new_layer_id = id_map.get(default_eid)
            if new_layer_id:
                plg_obj.default_baselayer = new_layer_id
                plg_obj.save(update_fields=['default_baselayer'])
                report.append({
                    'default_baselayer_set': {
                        'project_layer_group': plg_obj.id,
                        'layer_id': new_layer_id,
                    },
                })
            else:
                report.append({
                    'default_baselayer_missing': {
                        'project_layer_group': plg_obj.id,
                        'export_id': default_eid,
                    },
                })

        if pending_layer_overview_eid:
            new_overview_id = id_map.get(pending_layer_overview_eid)
            if new_overview_id:
                project.layer_overview = str(new_overview_id)
                project.custom_overview = bool(pdata.get('custom_overview', True))
                project.save(update_fields=['layer_overview', 'custom_overview'])
                report.append({'layer_overview_set': new_overview_id})
            else:
                report.append({
                    'layer_overview_missing': pending_layer_overview_eid,
                })

        if import_permissions:
            for pr in snapshot.get('project_roles', []):
                ProjectRole(project=project, role=pr['role'], permission=pr.get('permission', ProjectRole.PERM_READ)).save()

        # Patch toc_order so renamed layers/groups still appear in the right order
        try:
            _remap_toc_order(project, snapshot, id_map)
        except Exception:
            LOG.exception('Could not remap toc_order after import')

        gs.reload_nodes()
        job.id_map_json = id_map
        job.report_json = report
        job.status = ProjectPackageImportJob.ST_COMMITTED
        job.save()
        try:
            from gvsigol_core.project_package.activity_log import record_import_activity

            record_import_activity(job, project)
        except Exception:
            LOG.exception('record_import_activity failed')
        return project
    except Exception as ex:
        LOG.exception('Package import failed')
        if clone_conf and clone_conf.clean_on_failure:
            try:
                if project:
                    project.delete()
                for ws in reversed(workspaces_created):
                    services_utils._workspace_delete(ws, delete_data=True)
                gs2 = geographic_servers.get_instance().get_server_by_id(server.id)
                gs2.reload_nodes()
            except Exception:
                LOG.exception('clean_on_failure')
        job.status = ProjectPackageImportJob.ST_FAILED
        job.report_json = report + [{'fatal': True, 'error': str(ex)}]
        job.save()
        raise
