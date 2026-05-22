# -*- coding: utf-8 -*-
"""
Celery tasks for async project package export and import.

Export flow:
  1. View creates ProjectPackageExportJob (status=pending) and calls export_project_task.delay()
  2. Task builds the ZIP, saves it to disk, updates job.status = done/failed
  3. Status polling endpoint reads job.status; download endpoint serves the ZIP

Import flow:
  1. Wizard view saves wizard_json on the ImportJob, then calls import_project_task.delay()
  2. Task calls commit_job() which updates job.status = committed/failed internally
  3. Status polling endpoint reads job.status; on done redirects to result page
"""

import logging
import os

from celery.utils.log import get_task_logger
from django.conf import settings

from gvsigol.celery import app

logger = get_task_logger(__name__)


def _export_zip_dir():
    """Directory where export ZIPs are stored until download."""
    path = os.path.join(settings.MEDIA_ROOT, 'project_package_exports')
    os.makedirs(path, exist_ok=True)
    return path


def _progress(task, percent, step=''):
    """Emit a Celery PROGRESS state so callers can poll progress."""
    task.update_state(state='PROGRESS', meta={'percent': percent, 'step': step})


@app.task(bind=True, name='gvsigol_project_package.tasks.export_project_task')
def export_project_task(self, export_job_id, pid, export_options, username):
    """
    Build a project package ZIP asynchronously.

    Saves the result to MEDIA_ROOT/project_package_exports/<job_id>.zip
    and updates the ProjectPackageExportJob record accordingly.
    """
    from gvsigol_core.models import Project
    from gvsigol_core.project_package.activity_log import record_export_activity
    from gvsigol_core.project_package.export_service import build_project_zip
    from gvsigol_core.models import ProjectPackageExportJob

    job = ProjectPackageExportJob.objects.get(pk=export_job_id)
    job.status = ProjectPackageExportJob.ST_RUNNING
    job.celery_task_id = self.request.id
    job.save(update_fields=['status', 'celery_task_id'])
    _progress(self, 5, 'starting')

    try:
        project = Project.objects.get(pk=int(pid))
        _progress(self, 15, 'building_zip')

        def _export_cb(pct, step):
            _progress(self, pct, step)

        buf, fname, export_log_lines = build_project_zip(
            project, export_options=export_options, progress_cb=_export_cb
        )
        _progress(self, 80, 'saving_zip')

        zip_path = os.path.join(_export_zip_dir(), '%s.zip' % str(export_job_id))
        with open(zip_path, 'wb') as fh:
            fh.write(buf.getvalue())
        _progress(self, 85, 'recording')

        try:
            record_export_activity(username, project, export_options, report_lines=export_log_lines, export_job_id=export_job_id)
        except Exception:
            logger.exception('export_project_task: record_export_activity failed')

        import json as _json
        export_errors = []
        for raw in export_log_lines:
            try:
                row = _json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                continue
            if isinstance(row, dict) and row.get('export_error'):
                export_errors.append({'layer': row.get('layer', ''), 'error': str(row['export_error'])})

        _progress(self, 95, 'finishing')
        job.status = ProjectPackageExportJob.ST_DONE
        job.zip_path = zip_path
        job.zip_filename = fname
        job.summary_json = {
            'status': 'partial' if export_errors else 'ok',
            'export_errors': export_errors,
            'report_lines': list(export_log_lines),
        }
        job.save(update_fields=['status', 'zip_path', 'zip_filename', 'summary_json'])
        logger.info('export_project_task: done for project %s -> %s', pid, zip_path)

    except Exception as exc:
        logger.exception('export_project_task: failed for project %s', pid)
        job.status = ProjectPackageExportJob.ST_FAILED
        job.summary_json = {'status': 'failed', 'error': str(exc)}
        job.save(update_fields=['status', 'summary_json'])


@app.task(bind=True, name='gvsigol_project_package.tasks.import_project_task')
def import_project_task(self, import_job_id):
    """
    Commit an import job asynchronously.

    The ImportJob must already have wizard_json populated (done by the wizard view
    before firing this task).
    """
    from gvsigol_core.project_package.activity_log import record_failed_import_activity
    from gvsigol_core.project_package.import_service import commit_job
    from gvsigol_core.models import ProjectPackageImportJob

    job = ProjectPackageImportJob.objects.get(pk=import_job_id)
    job.status = ProjectPackageImportJob.ST_RUNNING
    job.celery_task_id = self.request.id
    job.save(update_fields=['status', 'celery_task_id'])
    _progress(self, 5, 'starting')

    try:
        _progress(self, 15, 'importing')

        def _import_cb(pct, step):
            _progress(self, pct, step)

        project = commit_job(job, job.created_by, progress_cb=_import_cb)
        # record_import_activity is already called inside commit_job — do NOT call it again here
        _progress(self, 95, 'finishing')
        logger.info('import_project_task: committed job %s -> project %s', import_job_id, project.id if project else None)
    except Exception as exc:
        logger.exception('import_project_task: failed for job %s', import_job_id)
        try:
            record_failed_import_activity(job, str(exc))
        except Exception:
            logger.exception('import_project_task: record_failed_import_activity also failed')
