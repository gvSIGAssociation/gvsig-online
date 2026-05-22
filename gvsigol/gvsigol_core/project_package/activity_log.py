# -*- coding: utf-8 -*-
from gvsigol_core.models import ProjectPackageActivityLog, ProjectPackageImportJob
from gvsigol_core.project_package.report_summary import summarize_import_report

RECENT_ACTIVITY_LIMIT = 20


def record_import_activity(job, project=None):
    """Persist import outcome for the activity log (last N operations)."""
    summary = summarize_import_report(job.report_json)
    if project:
        job.result_project_id = project.id
    job.summary_json = summary
    job.save(update_fields=['result_project_id', 'summary_json'])

    project_name = ''
    if project:
        project_name = project.title or project.name
    elif job.manifest_json:
        project_name = (job.manifest_json.get('source_project_name') or '')[:200]

    status = ProjectPackageActivityLog.ST_FAILED
    if job.status == ProjectPackageImportJob.ST_COMMITTED:
        status = (
            ProjectPackageActivityLog.ST_PARTIAL
            if summary.get('status') == 'partial'
            else ProjectPackageActivityLog.ST_OK
        )

    ProjectPackageActivityLog.objects.create(
        operation=ProjectPackageActivityLog.OP_IMPORT,
        status=status,
        created_by=job.created_by or '',
        project_id=project.id if project else job.result_project_id,
        project_name=project_name[:200],
        import_job_id=job.id,
        summary_json=summary,
    )


def record_failed_import_activity(job, error_message=None):
    """Log a failed import when commit_job raises before activity was recorded."""
    summary = summarize_import_report(job.report_json)
    if error_message:
        summary.setdefault('errors', []).append(str(error_message))
        summary['status'] = 'failed'
    job.summary_json = summary
    job.save(update_fields=['summary_json'])

    ProjectPackageActivityLog.objects.create(
        operation=ProjectPackageActivityLog.OP_IMPORT,
        status=ProjectPackageActivityLog.ST_FAILED,
        created_by=job.created_by or '',
        import_job_id=job.id,
        summary_json=summary,
    )


def record_export_activity(username, project, export_options=None, report_lines=None, export_job_id=None):
    """Log a package export, marking it partial when any layer failed."""
    import json as _json
    export_options = export_options or {}
    lines = list(report_lines) if report_lines is not None else []

    export_errors = []
    for raw in lines:
        try:
            row = _json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue
        if isinstance(row, dict) and row.get('export_error'):
            export_errors.append({
                'layer': row.get('layer', ''),
                'error': str(row['export_error']),
            })

    status_str = 'partial' if export_errors else 'ok'
    summary = {
        'status': status_str,
        'export_permissions': bool(export_options.get('export_permissions')),
        'layer_vector_modes': export_options.get('layer_vector_modes') or {},
        'report_lines': lines,
        'export_errors': export_errors,
    }
    if export_job_id:
        summary['export_job_id'] = str(export_job_id)
    db_status = (
        ProjectPackageActivityLog.ST_PARTIAL
        if export_errors
        else ProjectPackageActivityLog.ST_OK
    )
    ProjectPackageActivityLog.objects.create(
        operation=ProjectPackageActivityLog.OP_EXPORT,
        status=db_status,
        created_by=username or '',
        project_id=project.id,
        project_name=(project.title or project.name)[:200],
        summary_json=summary,
    )


def recent_package_activity(limit=RECENT_ACTIVITY_LIMIT, username=None):
    """Last N import/export operations, optionally filtered by user."""
    qs = ProjectPackageActivityLog.objects.all().order_by('-created_at')
    if username:
        qs = qs.filter(created_by=username)
    return list(qs[:limit])


def _row_from_activity(entry):
    summ = entry.summary_json or {}
    has_export_lines = (
        entry.operation == ProjectPackageActivityLog.OP_EXPORT
        and 'report_lines' in summ
    )
    return {
        'created_at': entry.created_at,
        'operation': entry.operation,
        'status': entry.status,
        'project_name': entry.project_name,
        'created_by': entry.created_by,
        'summary': summ,
        'import_job_id': entry.import_job_id,
        'project_id': entry.project_id,
        'activity_log_id': entry.pk,
        'has_report': (
            (entry.operation == ProjectPackageActivityLog.OP_IMPORT and bool(entry.import_job_id))
            or has_export_lines
        ),
    }


def _row_from_import_job(job):
    summary = job.summary_json or summarize_import_report(job.report_json)
    if job.status == ProjectPackageImportJob.ST_FAILED:
        status = ProjectPackageActivityLog.ST_FAILED
    elif summary.get('status') == 'partial':
        status = ProjectPackageActivityLog.ST_PARTIAL
    else:
        status = ProjectPackageActivityLog.ST_OK
    project_name = ''
    if job.manifest_json:
        project_name = (job.manifest_json.get('source_project_name') or '')[:200]
    return {
        'created_at': job.created_at,
        'operation': ProjectPackageActivityLog.OP_IMPORT,
        'status': status,
        'project_name': project_name,
        'created_by': job.created_by or '',
        'summary': summary,
        'import_job_id': job.id,
        'project_id': job.result_project_id,
        'activity_log_id': None,
        'has_report': True,
    }


def get_package_report_rows(limit=RECENT_ACTIVITY_LIMIT, username=None):
    """
    Rows for templates: activity log when available, else recent import jobs.
    """
    try:
        activities = recent_package_activity(limit=limit, username=username)
        if activities:
            return [_row_from_activity(e) for e in activities]
    except Exception:
        pass

    qs = ProjectPackageImportJob.objects.filter(
        status__in=(
            ProjectPackageImportJob.ST_COMMITTED,
            ProjectPackageImportJob.ST_FAILED,
        ),
    ).order_by('-created_at')
    if username:
        qs = qs.filter(created_by=username)
    return [_row_from_import_job(j) for j in qs[:limit]]
