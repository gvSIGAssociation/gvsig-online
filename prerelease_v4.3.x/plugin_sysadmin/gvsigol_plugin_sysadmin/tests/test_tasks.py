# coding: utf-8
# Compatible with Python 3.6+
from __future__ import unicode_literals

import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from gvsigol_plugin_sysadmin.models import SysadminTestRun
from gvsigol_plugin_sysadmin.tasks import parse_django_test_summary, run_sysadmin_tests

User = get_user_model()


class ParseSummaryTests(unittest.TestCase):
    def test_ok_simple(self):
        out = 'Ran 2 tests in 0.001s\n\nOK\n'
        s = parse_django_test_summary(out, '', 0)
        self.assertEqual(s.get('total'), 2)
        self.assertEqual(s.get('failed'), 0)

    def test_failed_line(self):
        out = 'Ran 4 tests in 1s\n\nFAILED (failures=1, errors=2, skipped=1)\n'
        s = parse_django_test_summary(out, '', 1)
        self.assertEqual(s.get('total'), 4)
        self.assertEqual(s.get('failed'), 1)
        self.assertEqual(s.get('errors'), 2)


@mock.patch('gvsigol_plugin_sysadmin.tasks.subprocess.run')
class RunSysadminTestsTaskTests(TestCase):
    def test_sets_success_on_zero_rc(self, mock_run):
        user = User.objects.create_user('celery_test_u', password='x')
        proc = mock.MagicMock()
        proc.returncode = 0
        proc.stdout = 'Ran 1 tests in 0s\n\nOK\n'
        proc.stderr = ''
        mock_run.return_value = proc
        run = SysadminTestRun.objects.create(
            requested_by=user,
            labels=['gvsigol_core.tests'],
            status=SysadminTestRun.STATUS_PENDING,
        )
        run_sysadmin_tests(run.id)
        run.refresh_from_db()
        self.assertEqual(run.status, SysadminTestRun.STATUS_SUCCESS)
        self.assertEqual(run.return_code, 0)
