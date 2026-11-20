# -*- coding: utf-8 -*-
"""Human-readable summaries of import/export report JSON."""
import re as _re
from django.utils.translation import gettext as _


def _retranslate(text):
    """
    Messages/warnings are generated inside Celery tasks (no user locale), so
    they are stored in English.  Re-translate known patterns at display time.
    """
    if not text:
        return text

    # Layer "X" already exists in datastore "Y"; loading as "Z".  (current format)
    m = _re.match(
        r'^Layer "(.+)" already exists in datastore "(.+)"; loading as "(.+)"\.$',
        text,
    )
    if m:
        return _(
            'Layer "%(wanted)s" already exists in datastore "%(ds)s"; '
            'loading as "%(actual)s".'
        ) % {'wanted': m.group(1), 'ds': m.group(2), 'actual': m.group(3)}

    # Table "X" already exists in schema "Y"; loading as "Z".  (legacy format)
    m = _re.match(
        r'^Table "(.+)" already exists in schema "(.+)"; loading as "(.+)"\.$',
        text,
    )
    if m:
        return _(
            'Layer "%(wanted)s" already exists in datastore "%(ds)s"; '
            'loading as "%(actual)s".'
        ) % {'wanted': m.group(1), 'ds': m.group(2), 'actual': m.group(3)}

    # Definition-only layer "X" was skipped by choice in the import wizard.
    m = _re.match(
        r'^Definition-only layer "(.+)" was skipped by choice in the import wizard\.$',
        text,
    )
    if m:
        return _(
            'Definition-only layer "%(layer)s" was skipped by choice in the import wizard.'
        ) % {'layer': m.group(1)}

    # View layer "X" was skipped by choice in the import wizard.
    m = _re.match(
        r'^View layer "(.+)" was skipped by choice in the import wizard\.$',
        text,
    )
    if m:
        return _(
            'View layer "%(layer)s" was skipped by choice in the import wizard.'
        ) % {'layer': m.group(1)}

    # View layer "X" was not imported: no SQL definition available.
    m = _re.match(
        r'^View layer "(.+)" was not imported: no SQL definition available\.$',
        text,
    )
    if m:
        return _(
            'View layer "%(layer)s" was not imported: no SQL definition available.'
        ) % {'layer': m.group(1)}

    return text


# Machine-readable skip reasons → human labels (translated at call time)
def _reason_label(reason):
    mapping = {
        'wizard_skip': _('Skipped by user'),
        'table_not_found': _('Table not found'),
        'geoserver_publish_failed': _('GeoServer publish failed'),
        'no_sql': _('No SQL definition'),
        'create_view_failed': _('View creation failed'),
        'gpkg_import_failed': _('GPKG load failed'),
        'import_failed': _('Import failed'),
    }
    return mapping.get(reason, reason)


# Machine-readable import kind → human labels
def _kind_label(kind):
    mapping = {
        'vector': _('Vector'),
        'vector_definition': _('Vector (definition)'),
        'external': _('External layer'),
        'raster': _('Raster'),
        'view_sql': _('SQL view'),
        'wms_cascading': _('WMS cascading'),
    }
    return mapping.get(kind, kind)


def summarize_import_report(report_json):
    """
    Build a structured summary from commit/preflight report rows.
    Used in the import result page and activity log.
    """
    skipped_layers = []
    imported_layers = []
    reused_layers = []
    warnings = []
    errors = []

    SKIP_KEYS = (
        'definition_layer_skipped',
        'view_layer_skipped',
        'gpkg_layer_skipped',
        'external_layer_skipped',
        'raster_layer_skipped',
    )

    for row in report_json or []:
        if not isinstance(row, dict):
            continue

        matched_skip = next((k for k in SKIP_KEYS if k in row), None)
        if matched_skip:
            d = row[matched_skip]
            reason_code = d.get('reason') or ''
            skipped_layers.append({
                'layer': d.get('layer') or d.get('export_id') or '',
                'reason': _reason_label(reason_code),
                'reason_code': reason_code,
                'message': _retranslate(d.get('message') or ''),
                'table': d.get('table') or '',
                'connection': d.get('connection') or '',
            })
        elif 'definition_layer_reused' in row:
            d = row['definition_layer_reused']
            reused_layers.append({
                'layer': d.get('layer') or '',
                'connection': d.get('connection') or '',
            })
        elif 'external_layer_reused' in row:
            d = row['external_layer_reused']
            reused_layers.append({
                'layer': d.get('layer') or '',
                'connection': _('external') + ' (%s)' % (d.get('kind') or 'reuse'),
            })
        elif row.get('imported'):
            imported_layers.append({
                'kind': _kind_label(row.get('imported')),
                'kind_code': row.get('imported'),
                'layer': row.get('layer') or '',
                'table': row.get('table') or '',
            })
        elif 'raster_layer_published' in row:
            d = row['raster_layer_published']
            imported_layers.append({
                'kind': _kind_label('raster'),
                'kind_code': 'raster',
                'layer': d.get('layer') or '',
                'table': d.get('primary_path') or '',
            })
        elif 'wms_cascading_imported' in row:
            d = row['wms_cascading_imported']
            imported_layers.append({
                'kind': _kind_label('wms_cascading'),
                'kind_code': 'wms_cascading',
                'layer': d.get('layer') or '',
                'table': d.get('datastore') or '',
            })
        elif 'wms_cascading_error' in row:
            d = row['wms_cascading_error']
            # Non-fatal: the project is still created, just without this WMS layer → partial
            skipped_layers.append({
                'layer': d.get('layer') or d.get('export_id') or '',
                'reason': _('WMS store creation failed'),
                'reason_code': 'wms_cascading_error',
                'message': _('WMS cascading layer "%(layer)s" could not be imported: %(error)s') % {
                    'layer': d.get('layer') or d.get('export_id') or '',
                    'error': d.get('error') or '',
                },
                'table': '',
                'connection': '',
            })
        elif 'raster_import_error' in row:
            d = row['raster_import_error']
            layer_name = row.get('layer') or (d if isinstance(d, str) else '')
            step = row.get('step', '')
            errors.append(_('Raster import error') + ('%s: %s' % (
                (' [%s]' % step) if step else '',
                layer_name or str(d),
            )))
        elif 'tool_not_installed' in row:
            tool_name = row['tool_not_installed']
            warnings.append(
                _('Tool "%(tool)s" is not installed on this server and was not applied.')
                % {'tool': tool_name}
            )
        elif row.get('warning'):
            warnings.append(_retranslate(str(row['warning'])))
        elif 'definition_shared_layer_group_added' in row:
            d = row['definition_shared_layer_group_added']
            warnings.append(str(d.get('note') or d.get('layer_group')))
        elif row.get('fatal') and row.get('error'):
            errors.append(str(row['error']))
        elif row.get('error') and not row.get('imported'):
            errors.append(str(row['error']))

    # "partial" only when something was skipped for reasons beyond the user's
    # explicit choice (wizard_skip).  User-chosen skips and rename warnings
    # are expected outcomes and should not downgrade a successful import.
    involuntary_skips = [
        s for s in skipped_layers if s.get('reason_code') != 'wizard_skip'
    ]
    status = 'ok'
    if errors:
        status = 'failed'
    elif involuntary_skips:
        status = 'partial'

    return {
        'status': status,
        'skipped_layers': skipped_layers,
        'imported_layers': imported_layers,
        'reused_layers': reused_layers,
        'warnings': warnings,
        'errors': errors,
        'counts': {
            'imported': len(imported_layers),
            'skipped': len(skipped_layers),
            'reused': len(reused_layers),
            'warnings': len(warnings),
        },
    }
