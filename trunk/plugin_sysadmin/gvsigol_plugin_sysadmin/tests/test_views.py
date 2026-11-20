# coding: utf-8
# Compatible with Python 3.6+
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from gvsigol_plugin_sysadmin import views


class SysadminViewAccessTests(TestCase):
    """Superuser gate using RequestFactory (no URLConf resolution required)."""

    def setUp(self):
        self.rf = RequestFactory()

    def test_home_allows_superuser(self):
        req = self.rf.get('/sysadmin/')
        req.user = User(username='su', is_superuser=True)
        resp = views.sysadmin_home(req)
        self.assertEqual(resp.status_code, 200)

    def test_home_blocks_non_superuser(self):
        req = self.rf.get('/sysadmin/')
        req.user = User(username='nu', is_superuser=False)
        resp = views.sysadmin_home(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'illegal-card', resp.content)

    def test_gol_settings_allows_superuser(self):
        req = self.rf.get('/sysadmin/settings/db/')
        req.user = User(username='su2', is_superuser=True)
        resp = views.gol_settings(req)
        self.assertEqual(resp.status_code, 200)
