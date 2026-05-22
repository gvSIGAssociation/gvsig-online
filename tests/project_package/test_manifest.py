import os
import shutil
import tempfile
import unittest

from gvsigol_core.project_package.manifest import compute_inventory, verify_manifest_against_dir
from gvsigol_core.project_package.constants import MANIFEST_PATH


class ManifestTests(unittest.TestCase):
    def test_inventory_excludes_manifest(self):
        root = tempfile.mkdtemp()
        try:
            with open(os.path.join(root, 'a.txt'), 'w') as f:
                f.write('x')
            os.makedirs(os.path.join(root, 'META-INF'), exist_ok=True)
            with open(os.path.join(root, MANIFEST_PATH.replace('/', os.sep)), 'w') as f:
                f.write('{}')
            inv = compute_inventory(root)
            paths = {i['path'] for i in inv}
            self.assertIn('a.txt', paths)
            self.assertNotIn(MANIFEST_PATH, paths)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_verify_detects_tamper(self):
        root = tempfile.mkdtemp()
        try:
            p = os.path.join(root, 'a.txt')
            with open(p, 'w') as f:
                f.write('hello')
            inv = compute_inventory(root)
            manifest = {'inventory': inv}
            self.assertEqual(verify_manifest_against_dir(manifest, root), [])
            with open(p, 'w') as f:
                f.write('tampered')
            self.assertTrue(any('checksum' in e for e in verify_manifest_against_dir(manifest, root)))
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
