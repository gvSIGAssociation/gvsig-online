# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import os
import shutil
import tempfile
import uuid
import zipfile
from io import BytesIO

from django.conf import settings

from gvsigol_core.models import Project
from gvsigol_services.models import (
    Datastore,
    Layer,
    LayerFieldEnumeration,
    LayerManageRole,
    LayerReadRole,
    LayerResource,
    LayerWriteRole,
    LayerGroup,
    Server,
)
from gvsigol_symbology.models import StyleLayer
from gvsigol_symbology import sld_builder

from gvsigol_core.project_package.constants import MANIFEST_PATH, PROJECT_JSON, REPORTS_EXPORT_LOG
from gvsigol_core.project_package.manifest import build_base_manifest, compute_inventory
from gvsigol_core.project_package.raster_sidecars import (
    build_sidecar_manifest,
    collect_sidecar_paths,
    extract_primary_raster_path_from_connection_params,
)
from gvsigol_core.project_package.connection_utils import (
    datastore_connection_key,
    datastore_connection_label,
    is_foreign_postgis_datastore,
)
from gvsigol_core.project_package.gdal_io import export_postgis_to_gpkg, pg_connection_from_params
from gvsigol_core.project_package.scrub import scrub_json_tree

LOG = logging.getLogger('gvsigol')


def _schema_and_table(layer):
    table = layer.source_name if layer.source_name else layer.name
    schema = layer.datastore.get_schema_name() if layer.datastore else ''
    return schema, table


def _layer_group_to_dict(lg: LayerGroup):
    return {
        'name': lg.name,
        'title': lg.title,
        'visible': lg.visible,
        'cached': lg.cached,
        'created_by': lg.created_by,
        'server_name': Server.objects.filter(id=lg.server_id).values_list('name', flat=True).first(),
    }


def _serialize_permissions(layer):
    return {
        'read_roles': list(LayerReadRole.objects.filter(layer=layer).values('role', 'filtered', 'external')),
        'write_roles': list(LayerWriteRole.objects.filter(layer=layer).values('role', 'filtered', 'external')),
        'manage_roles': list(LayerManageRole.objects.filter(layer=layer).values('role')),
    }


def _vector_mode_for_layer(layer, export_options):
    """
    export_options['layer_vector_modes']: {str(layer_id): 'embedded'|'definition_only'|'view_sql_definition'}
    Local layers: embedded by default; foreign layers: definition_only by default.
    """
    modes = export_options.get('layer_vector_modes') or {}
    mode = modes.get(str(layer.id)) or modes.get(layer.id)
    if mode in ('embedded', 'definition_only', 'view_sql_definition'):
        return mode
    ds = layer.datastore
    if is_foreign_postgis_datastore(ds):
        return 'definition_only'
    return 'embedded'


def _export_view_sql_definition(layer, ds, schema, report):
    """
    Fetch the SQL definition and GT_pk_metadata for a view layer.
    Returns a dict to store as 'view_sql_definition' in the manifest entry,
    or None on failure (error appended to report).
    """
    import json as _json
    intro = None
    try:
        intro, _ = ds.get_db_connection()
        source = (layer.source_name or layer.name or '').strip()

        # Try the datastore's configured schema first.
        sql = intro.get_view_definition(schema, source)
        actual_schema = schema

        if not sql:
            # The view may live in a different schema; search across all.
            found_schema, found_sql = intro.find_view_in_any_schema(source)
            if found_sql:
                sql = found_sql
                actual_schema = found_schema
                LOG.warning(
                    'View "%s" not found in schema "%s"; found in "%s" — '
                    'exporting from there.',
                    source, schema, found_schema,
                )

        if not sql:
            report.append(_json.dumps({
                'layer': layer.name,
                'export_error': (
                    'view_sql_definition requested but view "%s" was not found '
                    'in schema "%s" or any other schema; falling back to GPKG.'
                    % (source, schema)
                ),
            }))
            return None

        gt_pk_rows = intro.get_gt_pk_metadata_full_rows(actual_schema, source)
        return {
            'sql': sql,
            'schema': actual_schema,
            'view_name': source,
            'gt_pk_metadata': gt_pk_rows,
        }
    except Exception as ex:
        report.append(_json.dumps({
            'layer': layer.name,
            'export_error': 'Failed to export view SQL definition: %s' % ex,
        }))
        return None
    finally:
        if intro:
            try:
                intro.close()
            except Exception:
                pass


def _serialize_layer(layer: Layer, datastore):
    if datastore is not None:
        ws = datastore.workspace
        datastore_name = datastore.name
        workspace_name = ws.name if ws else ''
        srv = ws.server if ws else None
        server_name = srv.name if srv else ''
    else:
        datastore_name = ''
        workspace_name = ''
        server_name = ''
    d = {
        'external': layer.external,
        'external_params': layer.external_params,
        'name': layer.name,
        'title': layer.title,
        'abstract': layer.abstract,
        'type': layer.type,
        'public': layer.public,
        'visible': layer.visible,
        'queryable': layer.queryable,
        'cached': layer.cached,
        'single_image': layer.single_image,
        'vector_tile': layer.vector_tile,
        'allow_download': layer.allow_download,
        'time_enabled': layer.time_enabled,
        'time_enabled_field': layer.time_enabled_field,
        'time_enabled_endfield': layer.time_enabled_endfield,
        'time_presentation': layer.time_presentation,
        'time_resolution_year': layer.time_resolution_year,
        'time_resolution_month': layer.time_resolution_month,
        'time_resolution_week': layer.time_resolution_week,
        'time_resolution_day': layer.time_resolution_day,
        'time_resolution_hour': layer.time_resolution_hour,
        'time_resolution_minute': layer.time_resolution_minute,
        'time_resolution_second': layer.time_resolution_second,
        'time_default_value_mode': layer.time_default_value_mode,
        'time_default_value': layer.time_default_value,
        'time_resolution': layer.time_resolution,
        'order': layer.order,
        'created_by': layer.created_by,
        'conf': layer.conf,
        'detailed_info_enabled': layer.detailed_info_enabled,
        'detailed_info_button_title': layer.detailed_info_button_title,
        'detailed_info_html': layer.detailed_info_html,
        'timeout': layer.timeout,
        'native_srs': layer.native_srs,
        'native_extent': layer.native_extent,
        'latlong_extent': layer.latlong_extent,
        'source_name': layer.source_name,
        'real_time': layer.real_time,
        'update_interval': layer.update_interval,
        'featureapi_endpoint': layer.featureapi_endpoint,
        'datastore_name': datastore_name,
        'workspace_name': workspace_name,
        'server_name': server_name,
        'schema_name': datastore.get_schema_name() if datastore else '',
        'datastore_connection_key': datastore_connection_key(datastore) if datastore else '',
        'datastore_connection_label': datastore_connection_label(datastore) if datastore else '',
        'datastore_is_foreign': is_foreign_postgis_datastore(datastore) if datastore else False,
    }
    return scrub_json_tree(d)


def _styles_payload(layer, skip_db_sld=False):
    """Returns (styles_list, sld_errors_list).

    If skip_db_sld is True the SLD body is exported as empty string without
    attempting any database connection (appropriate for definition-only or
    foreign-datastore layers whose DB may be unreachable).
    sld_errors_list entries have {style, error} for reporting.
    """
    out = []
    sld_errors = []
    for sl in StyleLayer.objects.filter(layer=layer).select_related('style').order_by('-style__is_default'):
        st = sl.style
        sld = ''
        if not skip_db_sld:
            try:
                body = sld_builder.build_sld(layer, st)
                if isinstance(body, bytes):
                    sld = body.decode('utf-8', errors='replace')
                else:
                    sld = str(body)
            except Exception as _sld_exc:
                LOG.warning(
                    'Could not serialize SLD for layer %s style %s (will export empty SLD): %s',
                    layer.id, st.id, _sld_exc,
                )
                sld_errors.append({'style': st.name, 'error': str(_sld_exc)})
        out.append({
            'name': st.name,
            'title': st.title,
            'is_default': st.is_default,
            'type': st.type,
            'sld': sld,
        })
    return out, sld_errors


def _project_scalar(project: Project):
    return scrub_json_tree({
        'name': project.name,
        'title': project.title,
        'description': project.description,
        'logo_link': project.logo_link,
        'center_lat': project.center_lat,
        'center_lon': project.center_lon,
        'zoom': project.zoom,
        'extent': project.extent,
        'extent4326_minx': project.extent4326_minx,
        'extent4326_miny': project.extent4326_miny,
        'extent4326_maxx': project.extent4326_maxx,
        'extent4326_maxy': project.extent4326_maxy,
        'toc_mode': project.toc_mode,
        'toc_order': project.toc_order,
        'created_by': project.created_by,
        'is_public': project.is_public,
        'show_project_icon': project.show_project_icon,
        'selectable_groups': project.selectable_groups,
        'restricted_extent': project.restricted_extent,
        'tools': project.tools,
        'baselayer_version': project.baselayer_version,
        'labels': project.labels,
        'expiration_date': project.expiration_date.isoformat() if project.expiration_date else None,
        'custom_overview': project.custom_overview,
        'layer_overview': project.layer_overview,
        'viewer_default_crs': project.viewer_default_crs,
        'viewer_preferred_ui': project.viewer_preferred_ui,
    })


def build_project_zip(project: Project, export_options=None, progress_cb=None):
    """
    Build ZIP bytes for the given project (manage permission must be checked by caller).

    Returns:
        Tuple ``(zip_buffer: BytesIO, download_filename: str, report_lines: list[str])``.
        ``report_lines`` equals the lines written to ``reports/export_log.jsonl`` in the ZIP.

    export_options:
      - export_permissions (bool): include layer/project role rules in the package
      - layer_vector_modes (dict): layer_id -> 'embedded' | 'definition_only' for foreign PostGIS layers
    """
    if export_options is None:
        export_options = {}
    export_permissions = bool(export_options.get('export_permissions'))
    include_raster_sidecars = bool(export_options.get('include_raster_sidecars', True))

    root = tempfile.mkdtemp(prefix='prjpkg_')
    try:
        data_dir = os.path.join(root, 'data', 'vector')
        raster_dir = os.path.join(root, 'data', 'raster')
        sym_dir = os.path.join(root, 'symbology', 'layers')
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(raster_dir, exist_ok=True)
        os.makedirs(sym_dir, exist_ok=True)
        log_lines = []

        prj_snapshot = {
            'project': _project_scalar(project),
            'project_roles': (
                list(project.projectrole_set.all().values('role', 'permission'))
                if export_permissions
                else []
            ),
            'layer_groups': [],
        }
        all_layer_export_id_by_pk = {}

        # Pre-count total layers for progress reporting
        _total_layers = sum(
            Layer.objects.filter(layer_group=prj_lg.layer_group).count()
            for prj_lg in project.projectlayergroup_set.all()
        ) or 1
        _done_layers = 0

        for prj_lg in project.projectlayergroup_set.all().order_by('id'):
            lg = prj_lg.layer_group
            group_layers = []
            layer_export_id_by_pk = {}
            for layer in Layer.objects.filter(layer_group=lg).order_by('order', 'id'):
                eid = str(uuid.uuid4())
                layer_export_id_by_pk[layer.id] = eid
                all_layer_export_id_by_pk[layer.id] = eid
                ds = layer.datastore
                is_default_base = bool(
                    prj_lg.baselayer_group
                    and prj_lg.default_baselayer
                    and prj_lg.default_baselayer == layer.id
                )
                # Determine vector mode early so we can skip remote DB calls for SLD
                _is_foreign = bool(layer.type == 'v_PostGIS' and is_foreign_postgis_datastore(ds))
                _vmode_early = _vector_mode_for_layer(layer, export_options) if _is_foreign else None
                _skip_db_sld = _is_foreign and _vmode_early == 'definition_only'
                _styles, _sld_errs = _styles_payload(layer, skip_db_sld=_skip_db_sld)
                if _sld_errs:
                    log_lines.append(json.dumps({
                        'layer': layer.name,
                        'sld_errors': _sld_errs,
                        'export_error': 'SLD serialization failed for %d style(s): %s' % (
                            len(_sld_errs),
                            '; '.join(e['error'] for e in _sld_errs),
                        ),
                    }))
                layer_entry = {
                    'export_id': eid,
                    'source_layer_id': layer.id,
                    'is_default_baselayer': is_default_base,
                    'layer': _serialize_layer(layer, ds),
                    'layer_type': layer.type,
                    'vector_gpkg': None,
                    'styles': _styles,
                    'enumerations': [],
                    'permissions': (
                        _serialize_permissions(layer) if export_permissions else {}
                    ),
                    'vector_data_mode': None,
                    'layer_resources': [
                        {
                            'feature': r['feature'],
                            'type': r['type'],
                            'path': r['path'],
                            'title': r['title'] or '',
                        }
                        for r in LayerResource.objects.filter(layer=layer).values(
                            'feature', 'type', 'path', 'title'
                        )
                    ],
                    'raster_bundle': None,
                }
                for lfe in LayerFieldEnumeration.objects.filter(layer=layer):
                    layer_entry['enumerations'].append({
                        'field': lfe.field,
                        'enumeration_id': lfe.enumeration_id,
                        'enumeration_name': getattr(lfe.enumeration, 'name', ''),
                    })

                try:
                    if layer.type == 'v_PostGIS' and ds and not layer.external:
                        schema, table = _schema_and_table(layer)
                        vmode = _vector_mode_for_layer(layer, export_options)
                        layer_entry['vector_data_mode'] = vmode
                        if vmode == 'view_sql_definition':
                            view_def = _export_view_sql_definition(
                                layer, ds, schema, log_lines
                            )
                            if view_def:
                                layer_entry['view_sql_definition'] = view_def
                                log_lines.append(json.dumps({
                                    'layer': layer.name,
                                    'vector': 'view_sql_definition',
                                    'schema': schema,
                                    'view': table,
                                }))
                            else:
                                # Fallback to GPKG: SQL retrieval failed
                                # (error already appended to log_lines by _export_view_sql_definition)
                                LOG.warning(
                                    'view_sql_definition requested for layer "%s" but SQL '
                                    'could not be retrieved; falling back to GPKG export.',
                                    layer.name,
                                )
                                vmode = 'embedded'
                                layer_entry['vector_data_mode'] = vmode
                        if vmode == 'embedded':
                            gpkg_rel = 'data/vector/%s.gpkg' % eid
                            gpkg_abs = os.path.join(root, gpkg_rel.replace('/', os.sep))
                            pg_conn = pg_connection_from_params(
                                ds.get_connection_params_dict(),
                                schema=schema,
                            )
                            gpkg_layer = export_postgis_to_gpkg(
                                schema, table, gpkg_abs, pg_conn=pg_conn
                            )
                            layer_entry['vector_gpkg'] = gpkg_rel
                            layer_entry['gpkg_layer_name'] = gpkg_layer
                            log_lines.append(json.dumps({'layer': layer.name, 'vector': gpkg_rel}))
                        elif vmode == 'definition_only':
                            log_lines.append(json.dumps({
                                'layer': layer.name,
                                'vector': 'definition_only',
                                'schema': schema,
                                'table': table,
                            }))
                    elif layer.type and layer.type.startswith('c_') and ds:
                        if not include_raster_sidecars:
                            log_lines.append(json.dumps({'layer': layer.name, 'raster': 'skipped_option_disabled'}))
                        else:
                            try:
                                params = (
                                    json.loads(ds.connection_params)
                                    if isinstance(ds.connection_params, str)
                                    else ds.connection_params
                                )
                            except Exception:
                                params = {}
                            primary = extract_primary_raster_path_from_connection_params(params or {})
                            if primary and os.path.isfile(primary):
                                paths = collect_sidecar_paths(primary)
                                bundle_files = []
                                dest_sub = os.path.join(raster_dir, eid)
                                os.makedirs(dest_sub, exist_ok=True)
                                for p in paths:
                                    bn = os.path.basename(p)
                                    rel = 'data/raster/%s/%s' % (eid, bn)
                                    shutil.copy2(p, os.path.join(root, rel.replace('/', os.sep)))
                                    _abs = os.path.join(root, rel.replace('/', os.sep))
                                    with open(_abs, 'rb') as _bf:
                                        _dig = hashlib.sha256(_bf.read()).hexdigest()
                                    bundle_files.append({'path_in_zip': rel, 'sha256': _dig})
                                layer_entry['raster_bundle'] = {
                                    'primary': os.path.basename(primary),
                                    'files': bundle_files,
                                    'sidecar_manifest': build_sidecar_manifest(paths),
                                }
                                log_lines.append(json.dumps({'layer': layer.name, 'raster': layer_entry['raster_bundle']['files']}))
                            else:
                                log_lines.append(json.dumps({'layer': layer.name, 'raster': 'skipped_no_file_path'}))
                    elif layer.type == 'v_PostGIS' and not layer.external:
                        vmode = _vector_mode_for_layer(layer, export_options)
                        layer_entry['vector_data_mode'] = vmode
                        schema, table = _schema_and_table(layer) if ds else ('', '')
                        log_lines.append(json.dumps({
                            'layer': layer.name,
                            'vector': vmode,
                            'schema': schema,
                            'table': table,
                            'note': 'metadata_only',
                        }))
                    else:
                        log_lines.append(json.dumps({'layer': layer.name, 'type': layer.type, 'note': 'metadata_only'}))
                except Exception as _layer_exc:
                    import traceback as _tb
                    log_lines.append(json.dumps({
                        'layer': layer.name,
                        'type': layer.type,
                        'export_error': str(_layer_exc),
                        'traceback': _tb.format_exc(),
                    }))

                sld_dir = os.path.join(sym_dir, eid)
                os.makedirs(sld_dir, exist_ok=True)
                for i, st in enumerate(layer_entry['styles']):
                    with open(os.path.join(sld_dir, 'style_%d.sld' % i), 'w', encoding='utf-8') as fh:
                        fh.write(st.get('sld') or '')

                group_layers.append(layer_entry)
                _done_layers += 1
                if progress_cb:
                    # Scale layer progress from 20% to 80%
                    pct = 20 + int(60 * _done_layers / _total_layers)
                    progress_cb(pct, 'exporting_layers')

            default_baselayer_eid = None
            if prj_lg.default_baselayer:
                default_baselayer_eid = layer_export_id_by_pk.get(prj_lg.default_baselayer)
            group_entry = {
                'layer_group': _layer_group_to_dict(lg),
                'project_layer_group': {
                    'multiselect': prj_lg.multiselect,
                    'baselayer_group': prj_lg.baselayer_group,
                    'default_baselayer_export_id': default_baselayer_eid,
                },
                'layers': group_layers,
            }
            prj_snapshot['layer_groups'].append(group_entry)

        if project.layer_overview not in (None, ''):
            try:
                overview_pk = int(project.layer_overview)
            except (TypeError, ValueError):
                overview_pk = None
            if overview_pk is not None:
                overview_eid = all_layer_export_id_by_pk.get(overview_pk)
                if overview_eid:
                    prj_snapshot['project']['layer_overview_export_id'] = overview_eid

        pj = os.path.join(root, PROJECT_JSON.replace('/', os.sep))
        os.makedirs(os.path.dirname(pj), exist_ok=True)
        with open(pj, 'w', encoding='utf-8') as f:
            json.dump(prj_snapshot, f, ensure_ascii=False, indent=2)

        rep = os.path.join(root, REPORTS_EXPORT_LOG.replace('/', os.sep))
        os.makedirs(os.path.dirname(rep), exist_ok=True)
        with open(rep, 'w', encoding='utf-8') as f:
            for line in log_lines:
                f.write(line + '\n')

        manifest = build_base_manifest(
            project.name,
            {
                'include_vectors': True,
                'include_raster_sidecars': include_raster_sidecars,
                'export_permissions': export_permissions,
                'layer_vector_modes': export_options.get('layer_vector_modes') or {},
            },
            [],
            {'gdaltools': True},
        )
        inv = compute_inventory(root)
        manifest['inventory'] = inv

        manifest_path = os.path.join(root, MANIFEST_PATH.replace('/', os.sep))
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    abs_path = os.path.join(dirpath, fn)
                    rel = os.path.relpath(abs_path, root).replace(os.sep, '/')
                    zf.write(abs_path, rel)
        buf.seek(0)
        return buf, '%s_project_package.zip' % project.name.replace(' ', '_'), list(log_lines)
    finally:
        shutil.rmtree(root, ignore_errors=True)
