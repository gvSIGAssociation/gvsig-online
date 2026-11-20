# -*- coding: utf-8 -*-
import unittest

from gvsigol_plugin_geoetl.assistant.access import (
    feature_enabled,
    provider_is_ready,
    user_may_use,
    workspace_edit_mode,
)


class AccessTests(unittest.TestCase):
    def test_feature_needs_flag_install_and_provider(self):
        self.assertTrue(feature_enabled(True, True, True))
        self.assertFalse(feature_enabled(False, True, True))
        self.assertFalse(feature_enabled(True, False, True))
        self.assertFalse(feature_enabled(True, True, False))

    def test_provider_rejects_placeholders_and_empty_azure_endpoint(self):
        self.assertFalse(provider_is_ready('openai', False, 'sk-real'))
        self.assertFalse(provider_is_ready('openai', True, 'your_openai_api_key'))
        self.assertFalse(provider_is_ready('azure_openai', True, 'your_azure_openai_api_key', 'https://example'))
        self.assertFalse(provider_is_ready('azure_openai', True, 'sk-real', ''))
        self.assertFalse(provider_is_ready('other', True, 'sk-real'))
        self.assertTrue(provider_is_ready('openai', True, 'sk-real'))
        self.assertTrue(provider_is_ready('azure_openai', True, 'sk-real', 'https://example.openai.azure.com'))

    def test_only_staff_or_superuser_may_use_it(self):
        self.assertFalse(user_may_use(False, True, True))
        self.assertFalse(user_may_use(True, False, False))
        self.assertTrue(user_may_use(True, True, False))
        self.assertTrue(user_may_use(True, False, True))

    def test_edit_mode_ignores_any_client_flag(self):
        self.assertEqual(workspace_edit_mode(True, False), 'full')
        self.assertEqual(workspace_edit_mode(False, True), 'restricted')
        self.assertEqual(workspace_edit_mode(False, False), 'forbidden')
        self.assertEqual(workspace_edit_mode(True, True), 'full')
