# -*- coding: utf-8 -*-
"""Human-readable summaries of import/export report JSON."""


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

    for row in report_json or []:
        if not isinstance(row, dict):
            continue
        if 'definition_layer_skipped' in row:
            d = row['definition_layer_skipped']
            skipped_layers.append({
                'layer': d.get('layer') or d.get('export_id') or '',
                'reason': d.get('reason') or '',
                'message': d.get('message') or '',
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
                'connection': 'external (%s)' % (d.get('kind') or 'reuse'),
            })
        elif row.get('imported'):
            imported_layers.append({
                'kind': row.get('imported'),
                'layer': row.get('layer') or '',
                'table': row.get('table') or '',
            })
        elif 'raster_layer_published' in row:
            d = row['raster_layer_published']
            imported_layers.append({
                'kind': 'raster',
                'layer': d.get('layer') or '',
                'table': d.get('primary_path') or '',
            })
        elif 'raster_import_error' in row:
            d = row['raster_import_error']
            layer_name = row.get('layer') or (d if isinstance(d, str) else '')
            step = row.get('step', '')
            errors.append('Raster import error%s: %s' % (
                (' [%s]' % step) if step else '',
                layer_name or str(d),
            ))
        elif row.get('warning'):
            warnings.append(str(row['warning']))
        elif 'definition_shared_layer_group_added' in row:
            d = row['definition_shared_layer_group_added']
            warnings.append(str(d.get('note') or d.get('layer_group')))
        elif row.get('fatal') and row.get('error'):
            errors.append(str(row['error']))
        elif row.get('error') and not row.get('imported'):
            errors.append(str(row['error']))

    status = 'ok'
    if errors:
        status = 'failed'
    elif skipped_layers or warnings:
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
