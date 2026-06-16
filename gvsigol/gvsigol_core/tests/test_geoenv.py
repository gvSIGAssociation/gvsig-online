# coding: utf-8

'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

import re
import unittest

import gdaltools
from gdaltools.basetypes import GdalToolsError
from gdaltools.ogr2ogrcmd import Ogr2ogr
from gdaltools.gdalinfocmd import GdalInfo
from django.conf import settings
from django.test import tag


# ogr2ogr --formats lines: "  <driver> -<types>- (<caps>): <description>"
_FORMAT_LINE_RE = re.compile(
    r'^\s+(?P<driver>.+?)\s+-(?P<types>[^-]+)-\s+\((?P<caps>[^)]+)\):'
)

# Short name -> OGR driver name as reported by ogr2ogr --formats
_REQUIRED_VECTOR_DRIVERS = {
    'Shapefile': 'ESRI Shapefile',
    'GPKG': 'GPKG',
    'GeoJSON': 'GeoJSON',
    'GML': 'GML',
    'PostgreSQL': 'PostgreSQL',
    'KML': 'KML',
}

# Short name -> GDAL driver name as reported by gdalinfo --formats
_REQUIRED_RASTER_DRIVERS = {
    'GPKG': 'GPKG',
    'GeoTIFF': 'GTiff',
}


def _configure_gdaltools():
    """Apply the same GDAL tools base path as gvsigol at startup."""
    basepath = getattr(settings, 'GDALTOOLS_BASEPATH', '')
    if basepath:
        gdaltools.Wrapper.BASEPATH = basepath


def _get_ogr2ogr():
    """Return an ogr2ogr wrapper using the configured binary path."""
    _configure_gdaltools()
    return Ogr2ogr()


def _get_gdalinfo():
    """Return a gdalinfo wrapper using the configured binary path."""
    _configure_gdaltools()
    return GdalInfo()


def _parse_ogr_formats(stdout):
    """
    Parse ``ogr2ogr --formats`` / ``gdalinfo --formats`` output into a dict keyed
    by driver name.

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


def _fetch_gdalinfo_formats(gdalinfo):
    """Run ``gdalinfo --formats`` on the same binary used by pygdaltools."""
    gdalinfo._do_execute([gdalinfo._get_command(), '--formats'])
    return _parse_ogr_formats(gdalinfo.stdout)


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


def _assert_raster_driver(formats, driver_name):
    info = formats.get(driver_name)
    if info is None:
        available = ', '.join(sorted(formats.keys()))
        raise AssertionError(
            f"GDAL raster driver '{driver_name}' is not available. "
            f"Installed drivers: {available}"
        )
    if 'raster' not in info['types']:
        raise AssertionError(
            f"GDAL driver '{driver_name}' is registered but does not support "
            f"raster data (types: {info['types']})"
        )


@tag('env', 'no_db')
class GeoEnvTestCase(unittest.TestCase):
    """
    Checks that the OGR/GDAL environment used by gvSIG Online (via pygdaltools)
    provides the vector and raster drivers required by the platform.
    """

    @classmethod
    def setUpClass(cls):
        cls.ogr = _get_ogr2ogr()
        cls.ogr_command = cls.ogr._get_command()
        cls.gdalinfo = _get_gdalinfo()
        cls.gdalinfo_command = cls.gdalinfo._get_command()
        try:
            cls.ogr_formats = _fetch_ogr_formats(cls.ogr)
            cls.gdal_formats = _fetch_gdalinfo_formats(cls.gdalinfo)
        except GdalToolsError as exc:
            raise unittest.SkipTest(
                f"GDAL tools are not available "
                f"(ogr2ogr={cls.ogr_command}, gdalinfo={cls.gdalinfo_command}): "
                f"{exc.message}"
            ) from exc

    def test_ogr2ogr_binary_is_configured(self):
        self.assertTrue(
            self.ogr_command,
            msg="ogr2ogr binary path must be resolved by pygdaltools",
        )

    def test_gdalinfo_binary_is_configured(self):
        self.assertTrue(
            self.gdalinfo_command,
            msg="gdalinfo binary path must be resolved by pygdaltools",
        )

    def test_shapefile_driver_available(self):
        _assert_vector_driver(self.ogr_formats, _REQUIRED_VECTOR_DRIVERS['Shapefile'])

    def test_gpkg_vector_driver_available(self):
        _assert_vector_driver(self.ogr_formats, _REQUIRED_VECTOR_DRIVERS['GPKG'])

    def test_gpkg_raster_driver_available(self):
        _assert_raster_driver(self.gdal_formats, _REQUIRED_RASTER_DRIVERS['GPKG'])

    def test_geotiff_raster_driver_available(self):
        _assert_raster_driver(self.gdal_formats, _REQUIRED_RASTER_DRIVERS['GeoTIFF'])

    def test_geojson_driver_available(self):
        _assert_vector_driver(self.ogr_formats, _REQUIRED_VECTOR_DRIVERS['GeoJSON'])

    def test_gml_driver_available(self):
        _assert_vector_driver(self.ogr_formats, _REQUIRED_VECTOR_DRIVERS['GML'])

    def test_postgresql_driver_available(self):
        _assert_vector_driver(self.ogr_formats, _REQUIRED_VECTOR_DRIVERS['PostgreSQL'])

    def test_kml_driver_available(self):
        _assert_vector_driver(self.ogr_formats, _REQUIRED_VECTOR_DRIVERS['KML'])
