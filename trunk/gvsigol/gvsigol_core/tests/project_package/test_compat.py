# -*- coding: utf-8 -*-
import json
import unittest

from gvsigol_core.project_package.manifest import is_compatible_version
from gvsigol_core.project_package.scrub import scrub_json_tree, assert_no_password_leak


class VersionCompatTests(unittest.TestCase):
    def test_accepts_1_x(self):
        self.assertTrue(is_compatible_version('1.0.0'))
        self.assertTrue(is_compatible_version('1.99.99'))

    def test_rejects_2_x_and_invalid(self):
        self.assertFalse(is_compatible_version('2.0.0'))
        self.assertFalse(is_compatible_version('0.9.0'))
        self.assertFalse(is_compatible_version('not-a-version'))


class GoldenSnapshotScrubTests(unittest.TestCase):
    """project.json-shaped payloads must not leak secrets after scrub."""

    def test_layer_like_payload_scrubbed(self):
        raw = {
            'name': 'lyr1',
            'datastore_name': 'ds',
            'connection_params': json.dumps({
                'host': 'h',
                'user': 'u',
                'password': 'TOP_SECRET',
            }),
        }
        scrubbed = scrub_json_tree(raw)
        blob = json.dumps(scrubbed, ensure_ascii=False)
        assert_no_password_leak(blob)
        self.assertIn('****', blob)
        self.assertNotIn('TOP_SECRET', blob)


if __name__ == '__main__':
    unittest.main()
