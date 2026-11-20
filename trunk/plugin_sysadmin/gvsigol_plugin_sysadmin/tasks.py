# -*- coding: utf-8 -*-
"""Celery task: run Django tests in a subprocess (isolated from the worker process)."""

import logging
import os
import re
import subprocess
import sys
import traceback

from django.conf import settings
from django.db import DatabaseError
from django.utils import timezone

from gvsigol.celery import app as celery_app

from gvsigol_plugin_sysadmin.models import SysadminTestRun
from gvsigol_plugin_sysadmin.test_registry import validate_sysadmin_test_labels

logger = logging.getLogger(__name__)


def _subprocess_timeout():
    return int(getattr(settings, 'GVSIGOL_SYSADMIN_TEST_RUN_TIMEOUT', 1800))


def parse_django_test_summary(stdout_text, stderr_text, return_code):
    """
    Best-effort parse of Django / unittest footer (Ran N tests ... OK / FAILED).
    Returns a dict suitable for SysadminTestRun.summary.
    """
    text = '%s\n%s' % (stdout_text or '', stderr_text or '')
    if not text.strip():
        return {
            'total': None,
            'passed': None,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'parse_error': True,
            'return_code': return_code,
        }

    tail = text[-8192:]
    ran_matches = list(re.finditer(r'Ran\s+(\d+)\s+tests?\s+in', tail))
    total = int(ran_matches[-1].group(1)) if ran_matches else None

    failures = 0
    errors_ct = 0
    skipped = 0
    fm = re.search(r'FAILED\s*\(([^)]+)\)', tail)
    if fm:
        for part in fm.group(1).split(','):
            part = part.strip()
            if part.startswith('failures='):
                failures = int(part.split('=', 1)[1].strip())
            elif part.startswith('errors='):
                errors_ct = int(part.split('=', 1)[1].strip())
            elif part.startswith('skipped='):
                skipped = int(part.split('=', 1)[1].strip())
    else:
        ok_paren = re.search(r'\bOK\s*(?:\(([^)]*)\))?\s*$', tail, re.MULTILINE)
        if ok_paren and ok_paren.group(1):
            sk = re.search(r'skipped\s*=\s*(\d+)', ok_paren.group(1))
            if sk:
                skipped = int(sk.group(1))

    passed = None
    if total is not None:
        if fm:
            passed = max(0, total - failures - errors_ct - skipped)
        elif re.search(r'^\s*OK\b', tail, re.MULTILINE):
            passed = max(0, total - skipped)

    return {
        'total': total,
        'passed': passed,
        'failed': failures,
        'errors': errors_ct,
        'skipped': skipped,
        'parse_error': total is None,
        'return_code': return_code,
    }


def _trim(text, limit):
    if text is None:
        return ''
    if limit and len(text) > limit:
        return text[:limit] + '\n... [truncated]\n'
    return text


@celery_app.task
def run_sysadmin_tests(run_id):
    """Execute `manage.py test` for the labels stored on SysadminTestRun *run_id*."""
    try:
        run = SysadminTestRun.objects.get(pk=run_id)
    except SysadminTestRun.DoesNotExist:
        logger.error('SysadminTestRun id=%s not found', run_id)
        return
    except DatabaseError:
        logger.exception('DB error loading SysadminTestRun id=%s', run_id)
        return

    if run.status != SysadminTestRun.STATUS_PENDING:
        logger.warning(
            'SysadminTestRun id=%s expected pending, got %s', run_id, run.status
        )
        return

    out_limit = getattr(settings, 'GVSIGOL_SYSADMIN_TEST_OUTPUT_MAX_CHARS', 2 ** 20)

    manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
    labels = list(run.labels or [])
    ok, err, unknown = validate_sysadmin_test_labels(labels)
    if not ok:
        detail = err or 'Label validation failed'
        if unknown:
            detail = '%s: %s' % (detail, ', '.join(unknown))
        logger.error(
            'SysadminTestRun id=%s rejected labels (defense in depth): %s',
            run_id,
            detail,
        )
        run.stderr = detail
        run.return_code = -1
        run.summary = {'error': 'invalid_labels'}
        run.status = SysadminTestRun.STATUS_ERROR
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                'stderr',
                'return_code',
                'summary',
                'finished_at',
                'status',
            ]
        )
        return

    run.status = SysadminTestRun.STATUS_RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=['status', 'started_at'])

    cmd = [sys.executable, manage_py, 'test'] + labels + ['--verbosity=2', '--keepdb']
    env = os.environ.copy()
    cwd = settings.BASE_DIR
    env.pop('DEBUG_REMOTE', None)
    logger.info('Sysadmin test run %s: %s', run_id, cmd)

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=_subprocess_timeout(),
        )
        stdout = _trim(proc.stdout, out_limit)
        stderr = _trim(proc.stderr, out_limit)
        summary = parse_django_test_summary(stdout, stderr, proc.returncode)
        run.stdout = stdout
        run.stderr = stderr
        run.return_code = proc.returncode
        run.summary = summary
        run.finished_at = timezone.now()
        if proc.returncode == 0:
            run.status = SysadminTestRun.STATUS_SUCCESS
        else:
            run.status = SysadminTestRun.STATUS_FAILURE
        run.save(
            update_fields=[
                'stdout',
                'stderr',
                'return_code',
                'summary',
                'finished_at',
                'status',
            ]
        )
    except subprocess.TimeoutExpired as exc:
        err = 'Subprocess timeout after %ss' % _subprocess_timeout()
        logger.error('SysadminTestRun id=%s: %s', run_id, err)
        partial_out = getattr(exc, 'stdout', None) or ''
        partial_err = getattr(exc, 'stderr', None) or ''
        if partial_out:
            partial_out = _trim(partial_out, out_limit)
        if partial_err:
            partial_err = _trim(partial_err, out_limit) + '\n' + err
        else:
            partial_err = err
        run.stdout = partial_out
        run.stderr = partial_err
        run.return_code = -1
        run.summary = {
            'total': None,
            'passed': None,
            'failed': None,
            'errors': None,
            'skipped': None,
            'error': 'timeout',
        }
        run.status = SysadminTestRun.STATUS_ERROR
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                'stdout',
                'stderr',
                'return_code',
                'summary',
                'finished_at',
                'status',
            ]
        )
    except Exception:
        logger.exception('SysadminTestRun id=%s failed', run_id)
        run.stdout = _trim(run.stdout, out_limit)
        run.stderr = _trim(traceback.format_exc(), out_limit)
        run.return_code = -1
        run.summary = {'error': 'worker_exception'}
        run.status = SysadminTestRun.STATUS_ERROR
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                'stdout',
                'stderr',
                'return_code',
                'summary',
                'finished_at',
                'status',
            ]
        )
