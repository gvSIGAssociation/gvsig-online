import logging
import os
import subprocess

from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from gvsigol import settings
from gvsigol.celery import app as celery_app
from gvsigol_plugin_trip_planner.settings import GTFS_SCRIPT

from . import gtfs_files
from .models import GTFSProvider, GTFSstatus
from .utils import download_file, download_file_if_newer

logger = logging.getLogger(__name__)

REFRESH_TASK_NAME = 'gvsigol_plugin_trip_planner.trip_planner_refresh'
REFRESH_TASK = 'gvsigol_plugin_trip_planner.tasks.cron_trip_planner_refresh'
MAX_LOG = 8000  # characters of script output kept in GTFSstatus.message

# Status values (shown translated in gtfs_provider_list.html)
ST_RUNNING = 'Running'
ST_REBUILT = 'Success'
ST_UNCHANGED = 'Unchanged'
ST_NO_PROVIDERS = 'NoProviders'
ST_ERROR = 'Error'


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    if not PeriodicTask.objects.filter(name=REFRESH_TASK_NAME).exists():
        # si no se ha programado la tarea, la programamos para ejecutarse todos los días a las 00:01
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='01',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*'
        )
        PeriodicTask.objects.create(
            crontab=schedule,
            name=REFRESH_TASK_NAME,
            args='[0]',
            task=REFRESH_TASK,
        )


def set_status(status, message=''):
    statusModel, _ = GTFSstatus.objects.get_or_create(name='update')
    statusModel.status = status
    statusModel.message = (message or '')[-MAX_LOG:]
    statusModel.updated = timezone.now()
    statusModel.save()


def gtfs_dir():
    """Directory read by GTFS_SCRIPT (active providers only)."""
    return gtfs_files.staging_dir()


@celery_app.task
def cron_trip_planner_refresh(id, force=False):
    """Refresh the GTFS of the active providers and rebuild the graph (GTFS_SCRIPT) when
    the set of active GTFS files changed since the last successful build.
    force=True (manual "Update now") runs GTFS_SCRIPT anyway."""
    set_status(ST_RUNNING)
    logger.info('Actualizando Trip-Planner (force=%s)', force)

    try:
        providers = list(GTFSProvider.objects.filter(is_active=True).order_by('name'))
        if not providers:
            gtfs_files.sync_staging([])
            set_status(ST_NO_PROVIDERS)
            return {'refresh': False, 'status': ST_NO_PROVIDERS}

        log = []
        downloaded = []
        failed = []
        for p in providers:
            gtfs_files.migrate_legacy_file(p.id)
            if p.is_file:
                if not gtfs_files.has_source(p.id):
                    failed.append('{0} ({1})'.format(p.name, 'no file uploaded'))
                continue
            if not p.url:
                failed.append('{0} ({1})'.format(p.name, 'no URL'))
                continue
            src = gtfs_files.source_path(p.id)
            if os.path.exists(src):
                ok = download_file_if_newer(p.url, src)
            else:
                ok = download_file(p.url, src)
                if not ok:
                    failed.append('{0} ({1})'.format(p.name, p.url))
            if ok:
                downloaded.append(p.name)
                GTFSProvider.objects.filter(pk=p.pk).update(last_update=timezone.now())

        staged_ids = gtfs_files.sync_staging([p.id for p in providers])
        names = {p.id: p.name for p in providers}
        if downloaded:
            log.append('Downloaded: ' + ', '.join(downloaded))
        if failed:
            log.append('Failed: ' + ', '.join(failed))
        log.append('GTFS in graph: ' + (', '.join(names[i] for i in staged_ids) or '-'))

        if not staged_ids:
            log.append('No GTFS file available, graph not rebuilt.')
            set_status(ST_ERROR, '\n'.join(log))
            return {'refresh': False, 'status': ST_ERROR}

        statusModel, _ = GTFSstatus.objects.get_or_create(name='update')
        sig = gtfs_files.signature(staged_ids)
        if sig == statusModel.last_build_signature and not force:
            logger.info('GTFS have not changed')
            set_status(ST_ERROR if failed else ST_UNCHANGED, '\n'.join(log))
            return {'refresh': False, 'status': ST_UNCHANGED}

        result = _execute_script(GTFS_SCRIPT)
        log.append('$ ' + GTFS_SCRIPT)
        log.append(result['output'])
        if not result['success']:
            log.append(result['error'])
            set_status(ST_ERROR, '\n'.join(log))
            return {'refresh': False, 'status': ST_ERROR}

        GTFSstatus.objects.filter(name='update').update(last_build_signature=sig)
        set_status(ST_ERROR if failed else ST_REBUILT, '\n'.join(log))
        return {'refresh': True, 'status': ST_ERROR if failed else ST_REBUILT}

    except Exception as e:
        logger.exception('Error refreshing trip planner')
        set_status(ST_ERROR, str(e))
        return {'refresh': False, 'status': ST_ERROR, 'error': str(e)}


@celery_app.task(bind=True)
def execute_gtfs_scripts(sender):
    return _execute_script(GTFS_SCRIPT)


def _execute_script(cmd):
    """Run GTFS_SCRIPT through bash (so wildcards, pipes, etc. work).
    Execution stops at the first failing command (bash -e)."""
    try:
        logger.info('Executing GTFS script: %s', cmd)
        env = dict(os.environ, GTFS_DIR=gtfs_dir())
        proc = subprocess.run(['bash', '-e', '-c', cmd], capture_output=True, text=True, env=env)
        output = (proc.stdout or '') + (proc.stderr or '')
        if proc.stdout:
            logger.info(proc.stdout)
        if proc.stderr:
            logger.warning(proc.stderr)
        if proc.returncode != 0:
            return {'success': False, 'output': output.strip(),
                    'error': 'GTFS script exit code {0}'.format(proc.returncode)}
        return {'success': True, 'output': output.strip()}
    except Exception as e:
        logger.exception('Error executing GTFS script')
        return {'success': False, 'output': '', 'error': str(e)}
