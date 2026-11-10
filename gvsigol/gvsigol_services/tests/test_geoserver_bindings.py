# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from gvsigol_services.backend_postgis import _normalize_geometry_subtype_for_geoserver
from gvsigol_services.backend_geoserver import Geoserver


class GeometrySubtypeNormalizeTests(SimpleTestCase):

    def test_plain_types_forced_to_multi(self):
        # Single-part types are always promoted to Multi* for PostGIS layers.
        self.assertEqual(_normalize_geometry_subtype_for_geoserver('POINT'), 'MULTIPOINT')
        self.assertEqual(_normalize_geometry_subtype_for_geoserver('LINESTRING'), 'MULTILINESTRING')
        self.assertEqual(_normalize_geometry_subtype_for_geoserver('POLYGON'), 'MULTIPOLYGON')
        self.assertEqual(_normalize_geometry_subtype_for_geoserver('MULTILINESTRING'), 'MULTILINESTRING')
        self.assertEqual(_normalize_geometry_subtype_for_geoserver('MULTIPOLYGON'), 'MULTIPOLYGON')

    def test_postgis_measure_and_z_suffixes(self):
        self.assertEqual(
            _normalize_geometry_subtype_for_geoserver('MULTILINESTRINGM'),
            'MULTILINESTRING',
        )
        self.assertEqual(
            _normalize_geometry_subtype_for_geoserver('POINTZ'),
            'MULTIPOINT',
        )
        self.assertEqual(
            _normalize_geometry_subtype_for_geoserver('MULTIPOLYGONZM'),
            'MULTIPOLYGON',
        )

    def test_st_geometrytype_and_spaced_wkt_style(self):
        self.assertEqual(
            _normalize_geometry_subtype_for_geoserver('ST_MultiLineStringM'),
            'MULTILINESTRING',
        )
        self.assertEqual(
            _normalize_geometry_subtype_for_geoserver('MultiLineString M'),
            'MULTILINESTRING',
        )


class GetGeoserverBindingsTests(SimpleTestCase):

    def test_multilinestringm_maps_to_jts_multilinestring(self):
        binding = Geoserver.getGeoserverBindings(None, 'MULTILINESTRINGM')
        self.assertEqual(binding, 'com.vividsolutions.jts.geom.MultiLineString')

    def test_plain_multilinestring_unchanged(self):
        binding = Geoserver.getGeoserverBindings(None, 'MULTILINESTRING')
        self.assertEqual(binding, 'com.vividsolutions.jts.geom.MultiLineString')
