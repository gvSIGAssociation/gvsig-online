import os
import shutil
import tempfile
import unittest

from gvsigol_core.project_package.raster_sidecars import collect_sidecar_paths, copy_sidecar_tree


class RasterSidecarTests(unittest.TestCase):
    def test_collect_sidecars(self):
        d = tempfile.mkdtemp()
        try:
            base = os.path.join(d, 'tile.tif')
            with open(base, 'wb') as f:
                f.write(b'0')
            with open(os.path.join(d, 'tile.tfw'), 'w') as f:
                f.write('1')
            paths = collect_sidecar_paths(base)
            self.assertEqual(len(paths), 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_copy_sidecar_tree(self):
        d = tempfile.mkdtemp()
        dest = tempfile.mkdtemp()
        try:
            p = os.path.join(d, 'a.tif')
            with open(p, 'wb') as f:
                f.write(b'x')
            with open(os.path.join(d, 'a.prj'), 'w') as f:
                f.write('EPSG:4326')
            outs = copy_sidecar_tree([p, os.path.join(d, 'a.prj')], dest)
            self.assertTrue(any(x.endswith('a.tif') for x in outs))
            self.assertTrue(os.path.isfile(os.path.join(dest, 'a.tif')))
        finally:
            shutil.rmtree(d, ignore_errors=True)
            shutil.rmtree(dest, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
