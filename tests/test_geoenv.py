# coding: utf-8

'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

import re
import unittest

import gdaltools
from gdaltools.basetypes import GdalToolsError
from gdaltools.ogr2ogrcmd import Ogr2ogr
from django.conf import settings
from django.test import tag


# ogr2ogr --formats lines: "  <driver> -<types>- (<caps>): <description>"
_FORMAT_LINE_RE = re.compile(
    r'^\s+(?P<driver>.+?)\s+-(?P<types>[^-]+)-\s+\((?P<caps>[^)]+)\):'
)

# Short name -> OGR driver name as reported by ogr2ogr --formats
_REQUIRED_VECTOR_DRIVERS = {
    'Shapefile': 'ESRI Shapefile',
    'GeoJSON': 'GeoJSON',
    'GML': 'GML',
    'PostgreSQL': 'PostgreSQL',
    'KML': 'KML',
}


def _configure_gdaltools():
    """Apply the same GDAL tools base path as gvsigol at startup."""
    basepath = getattr(settings, 'GDALTOOLS_BASEPATH', '')
    if basepath:
        gdaltools.Wrapper.BASEPATH = basepath


def _get_ogr2ogr():
    """Return an ogr2ogr wrapper using the configured binary path."""
    _configure_gdaltools()
    command_path = getattr(settings, 'OGR2OGR_PATH', None) or None
    # gdaltools.ogr2ogr() factory only accepts version; use the class for a custom path
    return Ogr2ogr(command_path=command_path)


def _parse_ogr_formats(stdout):
    """
    Parse ``ogr2ogr --formats`` output into a dict keyed by driver name.

    Each value is a dict with ``types`` (e.g. "vector" or "raster,vector")
    and ``capabilities`` (e.g. "rw+v").
    """
    formats = {}
    for line in stdout.splitlines():
        match = _FORMAT_LINE_RE.match(line)
        if match:
            formats[match.group('driver').strip()] = {
                'types': match.group('types').strip(),
                'capabilities': match.group('caps').strip(),
            }
    return formats


def _fetch_ogr_formats(ogr):
    """Run ``ogr2ogr --formats`` on the same binary used by pygdaltools."""
    ogr._do_execute([ogr._get_command(), '--formats'])
    return _parse_ogr_formats(ogr.stdout)


def _assert_vector_driver(formats, driver_name):
    info = formats.get(driver_name)
    if info is None:
        available = ', '.join(sorted(formats.keys()))
        raise AssertionError(
            f"OGR driver '{driver_name}' is not available. "
            f"Installed drivers: {available}"
        )
    if 'vector' not in info['types']:
        raise AssertionError(
            f"OGR driver '{driver_name}' is registered but does not support "
            f"vector data (types: {info['types']})"
        )


@tag('env', 'no_db')
class GeoEnvTestCase(unittest.TestCase):
    """
    Checks that the OGR/GDAL environment used by gvSIG Online (via pygdaltools)
    provides the vector drivers required by the platform.
    """

    @classmethod
    def setUpClass(cls):
        cls.ogr = _get_ogr2ogr()
        cls.ogr_command = cls.ogr._get_command()
        try:
            cls.formats = _fetch_ogr_formats(cls.ogr)
        except GdalToolsError as exc:
            raise unittest.SkipTest(
                f"ogr2ogr is not available at {cls.ogr_command}: {exc.message}"
            ) from exc

    def test_ogr2ogr_binary_is_configured(self):
        self.assertTrue(
            self.ogr_command,
            msg="ogr2ogr binary path must be resolved by pygdaltools",
        )

    def test_shapefile_driver_available(self):
        _assert_vector_driver(self.formats, _REQUIRED_VECTOR_DRIVERS['Shapefile'])

    def test_gpkg_vector_driver_available(self):
        info = self.formats.get('GPKG')
        self.assertIsNotNone(
            info,
            msg="OGR driver 'GPKG' (GeoPackage) is not available",
        )
        self.assertIn(
            'vector',
            info['types'],
            msg=f"GPKG must support vector data (types: {info['types']})",
        )

    def test_gpkg_raster_driver_available(self):
        info = self.formats.get('GPKG')
        self.assertIsNotNone(
            info,
            msg="OGR driver 'GPKG' (GeoPackage) is not available",
        )
        self.assertIn(
            'raster',
            info['types'],
            msg=f"GPKG must support raster data (types: {info['types']})",
        )

    def test_geojson_driver_available(self):
        _assert_vector_driver(self.formats, _REQUIRED_VECTOR_DRIVERS['GeoJSON'])

    def test_gml_driver_available(self):
        _assert_vector_driver(self.formats, _REQUIRED_VECTOR_DRIVERS['GML'])

    def test_postgresql_driver_available(self):
        _assert_vector_driver(self.formats, _REQUIRED_VECTOR_DRIVERS['PostgreSQL'])

    def test_kml_driver_available(self):
        _assert_vector_driver(self.formats, _REQUIRED_VECTOR_DRIVERS['KML'])
