# coding: utf-8

'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

import unittest
from django.contrib.gis.geos import GEOSGeometry
import json
from gvsigol_core.geom import transform_point, transform_wkt


class PatchedGeosPointTestCase(unittest.TestCase):
    """ Checks the behavior of coordinate transformations using gvsigol convinience functions
    created to avoid inconsistences in Django/GEOSGeometry behaviour depending on GDAL/LIBPROJ versions.
    """
    def setUp(self):
        pass

    def test_transform_point_4326_to_25830(self):
        lon = -0.459891
        lat = 39.770063
        delta = 0.00001
        source_crs = 4326
        target_crs = 25830
        expected_x = 717561.534888295806013
        expected_y = 4405323.14028216060251
        geom_25830 = transform_point(lon, lat, source_crs, target_crs)
        self.assertAlmostEqual(geom_25830.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_25830 = GEOSGeometry(geom_25830.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_25830.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_25830.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_25830_to_4326(self):
        x = 717561.534888295806013
        y = 4405323.14028216060251
        delta = 0.00001
        source_crs = 25830
        target_crs = 4326
        expected_lon = -0.459891
        expected_lat = 39.770063
        geom_4326 = transform_point(x, y, source_crs, target_crs)
        self.assertAlmostEqual(geom_4326.x, expected_lon, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.y, expected_lat, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_4326 = json.loads(geom_4326.geojson)
        self.assertAlmostEqual(json_geom_4326['coordinates'][0], expected_lon, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1], expected_lat, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_4326 = GEOSGeometry(geom_4326.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_4326.x, expected_lon, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_4326.y, expected_lat, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_4326_to_4258(self):
        lon = -0.459891
        lat = 39.770063
        delta = 0.00001
        source_crs = 4326
        target_crs = 4258
        expected_lon = -0.459891
        expected_lat = 39.770063
        geom_4258 = transform_point(lon, lat, source_crs, target_crs)
        self.assertAlmostEqual(geom_4258.x, expected_lon, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.y, expected_lat, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0], expected_lon, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1], expected_lat, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_4258 = GEOSGeometry(geom_4258.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_4258.x, expected_lon, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_4258.y, expected_lat, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_4258_to_4326(self):
        lon = -0.459891
        lat = 39.770063
        delta = 0.00001
        source_crs = 4258
        target_crs = 4326
        expected_lon = -0.459891
        expected_lat = 39.770063
        geom_4326 = transform_point(lon, lat, source_crs, target_crs)
        self.assertAlmostEqual(geom_4326.x, expected_lon, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.y, expected_lat, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_4326 = json.loads(geom_4326.geojson)
        self.assertAlmostEqual(json_geom_4326['coordinates'][0], expected_lon, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1], expected_lat, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_4326 = GEOSGeometry(geom_4326.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_4326.x, expected_lon, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_4326.y, expected_lat, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_25830_to_25831(self):
        x = 717561.534888295806013
        y = 4405323.14028216060251
        delta = 0.0001
        source_crs = 25830
        target_crs = 25831
        expected_x = 203643.49230225582
        expected_y = 4407964.880515147
        geom_25831 = transform_point(x, y, source_crs, target_crs)
        self.assertAlmostEqual(geom_25831.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_25831 = json.loads(geom_25831.geojson)
        self.assertAlmostEqual(json_geom_25831['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_25831 = GEOSGeometry(geom_25831.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_25831.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_25831.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_25831_to_25830(self):
        x = 203643.49230225582
        y = 4407964.880515147
        delta = 0.0001
        source_crs = 25831
        target_crs = 25830
        expected_x = 717561.534888295806013
        expected_y = 4405323.14028216060251
        geom_25830 = transform_point(x, y, source_crs, target_crs)
        self.assertAlmostEqual(geom_25830.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_25830 = GEOSGeometry(geom_25830.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_25830.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_25830.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_25830_to_4258(self):
        x = 717561.534888295806013
        y = 4405323.14028216060251
        delta = 0.00001
        source_crs = 25830
        target_crs = 4258
        expected_lon = -0.459890999
        expected_lat = 39.770062997
        geom_4258 = transform_point(x, y, source_crs, target_crs)
        self.assertAlmostEqual(geom_4258.x, expected_lon, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.y, expected_lat, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0], expected_lon, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1], expected_lat, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_4258 = GEOSGeometry(geom_4258.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_4258.x, expected_lon, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_4258.y, expected_lat, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_4258_to_25830(self):
        lon = -0.459890999
        lat = 39.770062997
        delta = 0.0001
        source_crs = 4258
        target_crs = 25830
        expected_x = 717561.534888295806013
        expected_y = 4405323.139951234
        geom_25830 = transform_point(lon, lat, source_crs, target_crs)
        self.assertAlmostEqual(geom_25830.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_25830 = GEOSGeometry(geom_25830.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_25830.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_25830.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_25830_to_3857(self):
        x = 717561.534888295806013
        y = 4405323.14028216060251
        delta = 0.001
        source_crs = 25830
        target_crs = 3857
        expected_x = -51194.832
        expected_y = 4832584.505507748
        geom_3857 = transform_point(x, y, source_crs, target_crs)
        self.assertAlmostEqual(geom_3857.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_3857 = json.loads(geom_3857.geojson)
        self.assertAlmostEqual(json_geom_3857['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_3857 = GEOSGeometry(geom_3857.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_3857.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_3857.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_3857_to_25830(self):
        x = -51194.832
        y = 4832584.505507748
        delta = 0.001
        source_crs = 3857
        target_crs = 25830
        expected_x = 717561.534888295806013
        expected_y = 4405323.14028216060251
        geom_25830 = transform_point(x, y, source_crs, target_crs)
        self.assertAlmostEqual(geom_25830.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_25830 = GEOSGeometry(geom_25830.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_25830.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_25830.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_4258_to_3857(self):
        lon = 39.770062997
        lat = -0.459890999
        delta = 0.0001
        source_crs = 4258
        target_crs = 3857
        expected_x = 4427183.161642451770604
        expected_y = -51195.38155358115182
        geom_3857 = transform_point(lon, lat, source_crs, target_crs)
        self.assertAlmostEqual(geom_3857.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_3857 = json.loads(geom_3857.geojson)
        self.assertAlmostEqual(json_geom_3857['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_3857 = GEOSGeometry(geom_3857.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_3857.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_3857.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    def test_transform_point_3857_to_4258(self):
        x = -51194.832
        y = 4832584.505
        delta = 0.00001
        source_crs = 3857
        target_crs = 4258
        expected_lon = -0.459890999
        expected_lat = 39.770062997
        geom_4258 = transform_point(x, y, source_crs, target_crs)
        self.assertAlmostEqual(geom_4258.x, expected_lon, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.y, expected_lat, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0], expected_lon, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1], expected_lat, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry
        geos_geom_4258 = GEOSGeometry(geom_4258.wkt, srid=target_crs)
        self.assertAlmostEqual(geos_geom_4258.x, expected_lon, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geos_geom_4258.y, expected_lat, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    # def test_transform_point_25830_to_3035(self):
    #     x = -51194.832
    #     y = 4832584.505
    #     delta = 0.001
    #     source_crs = 25830
    #     target_crs = 3035
    #     expected_x = 3423086.058265099
    #     expected_y = 1914956.959543988
    #     geom_3035 = transform_point(x, y, source_crs, target_crs)
    #     print("atencion test_transform_point_25830_to_3035")
    #     print(geom_3035.x)
    #     print(expected_x)
    #     self.assertAlmostEqual(geom_3035.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geom_3035.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

    #     # Check the Geojson of transformed geometry
    #     json_geom_3035 = json.loads(geom_3035.geojson)
    #     self.assertAlmostEqual(json_geom_3035['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(json_geom_3035['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

    #     # Check the WKT of transformed geometry
    #     geos_geom_3035 = GEOSGeometry(geom_3035.wkt, srid=target_crs)
    #     self.assertAlmostEqual(geos_geom_3035.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geos_geom_3035.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    # def test_transform_point_3035_to_25830(self):
    #     x = 3423086.0582650988
    #     y = 1914956.9595439876
    #     delta = 0.001
    #     source_crs = 3035
    #     target_crs = 25830
    #     expected_x = -51194.832
    #     expected_y = 4832584.505
    #     geom_25830 = transform_point(x, y, source_crs, target_crs)
    #     self.assertAlmostEqual(geom_25830.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geom_25830.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

    #     # Check the Geojson of transformed geometry
    #     json_geom_25830 = json.loads(geom_25830.geojson)
    #     self.assertAlmostEqual(json_geom_25830['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(json_geom_25830['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

    #     # Check the WKT of transformed geometry
    #     geos_geom_25830 = GEOSGeometry(geom_25830.wkt, srid=target_crs)
    #     self.assertAlmostEqual(geos_geom_25830.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geos_geom_25830.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    # def test_transform_point_3035_to_4258(self):
    #     x = 3423086.0582650988
    #     y = 1914956.9595439876
    #     delta = 0.00001
    #     source_crs = 3035
    #     target_crs = 4258
    #     expected_lon = -0.45989099
    #     expected_lat = 39.77006299
    #     geom_4258 = transform_point(x, y, source_crs, target_crs)
    #     self.assertAlmostEqual(geom_4258.x, expected_lon, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geom_4258.y, expected_lat, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

    #     # Check the Geojson of transformed geometry
    #     json_geom_4258 = json.loads(geom_4258.geojson)
    #     self.assertAlmostEqual(json_geom_4258['coordinates'][0], expected_lon, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(json_geom_4258['coordinates'][1], expected_lat, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

    #     # Check the WKT of transformed geometry
    #     geos_geom_4258 = GEOSGeometry(geom_4258.wkt, srid=target_crs)
    #     self.assertAlmostEqual(geos_geom_4258.x, expected_lon, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geos_geom_4258.y, expected_lat, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")

    # def test_transform_point_4258_to_3035(self):
    #     lon = -0.45989099
    #     lat = 39.77006299
    #     delta = 0.001
    #     source_crs = 4258
    #     target_crs = 3035
    #     expected_x = 3423086.058265099
    #     expected_y = 1914956.959543988
    #     geom_3035 = transform_point(lon, lat, source_crs, target_crs)
    #     self.assertAlmostEqual(geom_3035.x, expected_x, delta=delta, msg=f"x coordinate transformation failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geom_3035.y, expected_y, delta=delta, msg=f"y coordinate transformation failed from {source_crs} to {target_crs}")

    #     # Check the Geojson of transformed geometry
    #     json_geom_3035 = json.loads(geom_3035.geojson)
    #     self.assertAlmostEqual(json_geom_3035['coordinates'][0], expected_x, delta=delta, msg=f"transformed json x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(json_geom_3035['coordinates'][1], expected_y, delta=delta, msg=f"transformed json y coordinate failed from {source_crs} to {target_crs}")

    #     # Check the WKT of transformed geometry
    #     geos_geom_3035 = GEOSGeometry(geom_3035.wkt, srid=target_crs)
    #     self.assertAlmostEqual(geos_geom_3035.x, expected_x, delta=delta, msg=f"transformed wkt x coordinate failed from {source_crs} to {target_crs}")
    #     self.assertAlmostEqual(geos_geom_3035.y, expected_y, delta=delta, msg=f"transformed wkt y coordinate failed from {source_crs} to {target_crs}")


# LINESTRING(714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513,  717885.443754401084.016)
# MULTILINESTRING((714340.11389 4402692.86474, 715832.48897 4401572.49473), (717012.14105 4401031.56513, 717885.44375 4401084.016))

class PatchedGeosLinestringTestCase(unittest.TestCase):
    """ Checks the behavior of coordinate transformations using gvsigol convinience functions
    created to avoid inconsistences in Django/GEOSGeometry behaviour depending on GDAL/LIBPROJ versions.
    """
    def setUp(self):
        pass

    def test_transform_linestring_4326_to_25830(self):
        wkt = 'LINESTRING (-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066)'
        delta = 0.00001
        source_crs = 4326
        target_crs = 25830
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        geom_25830 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25830.coords[0][0], expected_x_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1], expected_y_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0], expected_x_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1], expected_y_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[2][0], expected_x_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[2][1], expected_y_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[3][0], expected_x_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[3][1], expected_y_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_25830.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_25830_to_4326(self):
        wkt = 'LINESTRING(714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016)'
        delta = 0.00001
        source_crs = 25830
        target_crs = 4326
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4326 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4326.coords[0][0], expected__lon_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][1], expected__lat_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][0], expected__lon_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][1], expected__lat_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[2][0], expected__lon_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[2][1], expected__lat_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[3][0], expected__lon_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[3][1], expected__lat_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        

        # Check the Geojson of transformed geometry
        json_geom_4326 = json.loads(geom_4326.geojson)
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_4326.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_4326_to_4258(self):
        wkt = 'LINESTRING (-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066)'
        delta = 0.00001
        source_crs = 4326
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4258 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4258.coords[0][0], expected__lon_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1], expected__lat_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0], expected__lon_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1], expected__lat_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[2][0], expected__lon_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[2][1], expected__lat_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[3][0], expected__lon_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[3][1], expected__lat_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        

        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_4258.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_4258_to_4326(self):
        wkt = 'LINESTRING (-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066)'
        delta = 0.00001
        source_crs = 4258
        target_crs = 4326
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4326 = transform_wkt(wkt, source_crs, target_crs)
        
        self.assertAlmostEqual(geom_4326.coords[0][0], expected__lon_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][1], expected__lat_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][0], expected__lon_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][1], expected__lat_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[2][0], expected__lon_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[2][1], expected__lat_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[3][0], expected__lon_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[3][1], expected__lat_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_4326 = json.loads(geom_4326.geojson)
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_4326.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")


    def test_transform_linestring_25830_to_25831(self):
        wkt = 'LINESTRING(714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016)'
        delta = 0.00001
        source_crs = 25830
        target_crs = 25831
        expected_x_0 = 200251.40850083757
        expected_y_0 = 4405554.974307208
        expected_x_1 = 201666.1899918826
        expected_y_1 = 4404336.570427252
        expected_x_2 = 202807.58059562254
        expected_y_2 = 4403717.582285645
        expected_x_3 = 203682.8748760639
        expected_y_3 = 4403711.4663969185
        geom_25831 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25831.coords[0][0], expected_x_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[0][1], expected_y_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[1][0], expected_x_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[1][1], expected_y_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[2][0], expected_x_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[2][1], expected_y_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[3][0], expected_x_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[3][1], expected_y_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25831 = json.loads(geom_25831.geojson)
        self.assertAlmostEqual(json_geom_25831['coordinates'][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_25831.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_25831_to_25830(self):
        wkt = 'LINESTRING(200251.40850083757 4405554.974307208, 201666.1899918826 4404336.570427252, 202807.58059562254 4403717.582285645, 203682.8748760639 4403711.4663969185)'
        delta = 0.0001
        source_crs = 25831
        target_crs = 25830
        
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        geom_25830 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25830.coords[0][0], expected_x_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1], expected_y_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0], expected_x_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1], expected_y_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[2][0], expected_x_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[2][1], expected_y_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[3][0], expected_x_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[3][1], expected_y_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_25830.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_25830_to_4258(self):
        wkt = 'LINESTRING(714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016)'
        delta = 0.00001
        source_crs = 25830
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4258 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4258.coords[0][0], expected__lon_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1], expected__lat_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0], expected__lon_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1], expected__lat_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[2][0], expected__lon_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[2][1], expected__lat_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[3][0], expected__lon_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[3][1], expected__lat_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        

        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_4258.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")


    def test_transform_linestring_4258_to_25830(self):
        wkt = 'LINESTRING (-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066)'
        delta = 0.00001
        source_crs = 4258
        target_crs = 25830
        
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        geom_25830 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25830.coords[0][0], expected_x_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1], expected_y_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0], expected_x_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1], expected_y_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[2][0], expected_x_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[2][1], expected_y_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[3][0], expected_x_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[3][1], expected_y_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_25830.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_25830_to_3857(self):
        wkt = 'LINESTRING(714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016)'
        delta = 0.001
        source_crs = 25830
        target_crs = 3857
        
        expected_x_0 = -55473.34948015408
        expected_y_0 = 4829274.257160724
        expected_x_1 = -53577.01221140767
        expected_y_1 = 4827759.717904298
        expected_x_2 = -52065.81335081684
        expected_y_2 = 4827011.5456999075
        expected_x_3 = -50930.53416872382
        expected_y_3 = 4827047.655472828
        geom_3857 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_3857.coords[0][0], expected_x_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][1], expected_y_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][0], expected_x_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][1], expected_y_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[2][0], expected_x_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[2][1], expected_y_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[3][0], expected_x_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[3][1], expected_y_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_3857 = json.loads(geom_3857.geojson)
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_3857.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_4258_to_3857(self):
        wkt = 'LINESTRING (-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066)'
        delta = 0.001
        source_crs = 4258
        target_crs = 3857
        
        expected_x_0 = -55473.34948015408
        expected_y_0 = 4829274.257160724
        expected_x_1 = -53577.01221140767
        expected_y_1 = 4827759.717904298
        expected_x_2 = -52065.81335081684
        expected_y_2 = 4827011.5456999075
        expected_x_3 = -50930.53416872382
        expected_y_3 = 4827047.655472828
        geom_3857 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_3857.coords[0][0], expected_x_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][1], expected_y_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][0], expected_x_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][1], expected_y_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[2][0], expected_x_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[2][1], expected_y_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[3][0], expected_x_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[3][1], expected_y_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_3857 = json.loads(geom_3857.geojson)
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_3857.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_linestring_3857_to_4258(self):
        wkt = 'LINESTRING (-55473.34948015408 4829274.257160724, -53577.01221140767 4827759.717904298, -52065.81335081684 4827011.5456999075, -50930.53416872382 4827047.655472828)'
        delta = 0.00001
        source_crs = 3857
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4258 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4258.coords[0][0], expected__lon_0, delta=delta, msg=f"linestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1], expected__lat_0, delta=delta, msg=f"linestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0], expected__lon_1, delta=delta, msg=f"linestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1], expected__lat_1, delta=delta, msg=f"linestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[2][0], expected__lon_2, delta=delta, msg=f"linestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[2][1], expected__lat_2, delta=delta, msg=f"linestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[3][0], expected__lon_3, delta=delta, msg=f"linestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[3][1], expected__lat_3, delta=delta, msg=f"linestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        

        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = geom_4258.wkt.split("(")[1].split(")")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")


class PatchedGeosMultiLinestringTestCase(unittest.TestCase):
    """ Checks the behavior of coordinate transformations using gvsigol convinience functions
    created to avoid inconsistences in Django/GEOSGeometry behaviour depending on GDAL/LIBPROJ versions.
    """
    def setUp(self):
        pass

    def test_transform_multilinestring_4326_to_25830(self):
        wkt = 'MULTILINESTRING ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875), (-0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066))'
        delta = 0.00001
        source_crs = 4326
        target_crs = 25830
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        geom_25830 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25830.coords[0][0][0], expected_x_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][0][1], expected_y_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][0], expected_x_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][1], expected_y_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][0], expected_x_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][1], expected_y_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][0], expected_x_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][1], expected_y_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_25830.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_25830_to_4326(self):
        wkt = 'MULTILINESTRING ((714340.11389 4402692.86474, 715832.48897 4401572.49473), (717012.14105 4401031.56513, 717885.44375 4401084.016))'
        delta = 0.00001
        source_crs = 25830
        target_crs = 4326
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4326 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4326.coords[0][0][0], expected__lon_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][0][1], expected__lat_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][1][0], expected__lon_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][1][1], expected__lat_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][0][0], expected__lon_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][0][1], expected__lat_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][1][0], expected__lon_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][1][1], expected__lat_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_4326 = json.loads(geom_4326.geojson)
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][0][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][0][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][1][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][1][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_4326.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_4326_to_4258(self):
        wkt = 'MULTILINESTRING ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875), (-0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066))'
        delta = 0.00001
        source_crs = 4326
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4258 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4258.coords[0][0][0], expected__lon_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][0][1], expected__lat_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1][0], expected__lon_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1][1], expected__lat_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0][0], expected__lon_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0][1], expected__lat_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1][0], expected__lon_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1][1], expected__lat_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_4258.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_4258_to_4326(self):
        wkt = 'MULTILINESTRING ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875), (-0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066))'
        delta = 0.00001
        source_crs = 4258
        target_crs = 4326
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4326 = transform_wkt(wkt, source_crs, target_crs)
        
        self.assertAlmostEqual(geom_4326.coords[0][0][0], expected__lon_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][0][1], expected__lat_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][1][0], expected__lon_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[0][1][1], expected__lat_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][0][0], expected__lon_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][0][1], expected__lat_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][1][0], expected__lon_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4326.coords[1][1][1], expected__lat_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_4326 = json.loads(geom_4326.geojson)
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][0][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][0][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][1][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4326['coordinates'][1][1][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_4326.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_25830_to_25831(self):
        wkt = 'MULTILINESTRING ((714340.11389 4402692.86474, 715832.48897 4401572.49473), (717012.14105 4401031.56513, 717885.44375 4401084.016))'
        delta = 0.0001
        source_crs = 25830
        target_crs = 25831
        expected_x_0 = 200251.40850083757
        expected_y_0 = 4405554.974307208
        expected_x_1 = 201666.1899918826
        expected_y_1 = 4404336.570427252
        expected_x_2 = 202807.58059562254
        expected_y_2 = 4403717.582285645
        expected_x_3 = 203682.8748760639
        expected_y_3 = 4403711.4663969185
        geom_25831 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25831.coords[0][0][0], expected_x_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[0][0][1], expected_y_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[0][1][0], expected_x_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[0][1][1], expected_y_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[1][0][0], expected_x_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[1][0][1], expected_y_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[1][1][0], expected_x_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25831.coords[1][1][1], expected_y_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25831 = json.loads(geom_25831.geojson)
        self.assertAlmostEqual(json_geom_25831['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][1][0][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][1][0][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][1][1][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25831['coordinates'][1][1][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_25831.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_25831_to_25830(self):
        wkt = 'MULTILINESTRING ((200251.40850083757 4405554.974307208, 201666.1899918826 4404336.570427252), (202807.58059562254 4403717.582285645, 203682.8748760639 4403711.4663969185))'
        delta = 0.0001
        source_crs = 25831
        target_crs = 25830
        
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        geom_25830 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25830.coords[0][0][0], expected_x_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][0][1], expected_y_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][0], expected_x_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][1], expected_y_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][0], expected_x_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][1], expected_y_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][0], expected_x_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][1], expected_y_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_25830.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_25830_to_4258(self):
        wkt = 'MULTILINESTRING ((714340.11389 4402692.86474, 715832.48897 4401572.49473), (717012.14105 4401031.56513, 717885.44375 4401084.016))'
        delta = 0.00001
        source_crs = 25830
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4258 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4258.coords[0][0][0], expected__lon_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][0][1], expected__lat_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1][0], expected__lon_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1][1], expected__lat_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0][0], expected__lon_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0][1], expected__lat_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1][0], expected__lon_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1][1], expected__lat_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_4258.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_4258_to_25830(self):
        wkt = 'MULTILINESTRING ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875), (-0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066))'
        delta = 0.00001
        source_crs = 4258
        target_crs = 25830
        
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        geom_25830 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25830.coords[0][0][0], expected_x_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][0][1], expected_y_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][0], expected_x_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][1], expected_y_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][0], expected_x_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][1], expected_y_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][0], expected_x_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][1], expected_y_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_25830.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_25830_to_3857(self):
        wkt = 'MULTILINESTRING ((714340.11389 4402692.86474, 715832.48897 4401572.49473), (717012.14105 4401031.56513, 717885.44375 4401084.016))'
        delta = 0.001
        source_crs = 25830
        target_crs = 3857
        
        expected_x_0 = -55473.34948015408
        expected_y_0 = 4829274.257160724
        expected_x_1 = -53577.01221140767
        expected_y_1 = 4827759.717904298
        expected_x_2 = -52065.81335081684
        expected_y_2 = 4827011.5456999075
        expected_x_3 = -50930.53416872382
        expected_y_3 = 4827047.655472828
        geom_3857 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_3857.coords[0][0][0], expected_x_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][0][1], expected_y_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][1][0], expected_x_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][1][1], expected_y_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][0][0], expected_x_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][0][1], expected_y_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][1][0], expected_x_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][1][1], expected_y_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_3857 = json.loads(geom_3857.geojson)
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][0][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][0][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][1][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][1][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_3857.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_3857_to_25830(self):
        wkt = 'MULTILINESTRING ((-55473.34948015408 4829274.257160724, -53577.01221140767 4827759.717904298), (-52065.81335081684 4827011.5456999075, -50930.53416872382 4827047.655472828))'
        delta = 0.001
        source_crs = 3857
        target_crs = 25830
        
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        geom_25830 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_25830.coords[0][0][0], expected_x_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][0][1], expected_y_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][0], expected_x_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[0][1][1], expected_y_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][0], expected_x_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][0][1], expected_y_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][0], expected_x_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_25830.coords[1][1][1], expected_y_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_25830 = json.loads(geom_25830.geojson)
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][0][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_25830['coordinates'][1][1][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_25830.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_4258_to_3857(self):
        wkt = 'MULTILINESTRING ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875), (-0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066))'
        delta = 0.001
        source_crs = 4258
        target_crs = 3857
        
        expected_x_0 = -55473.34948015408
        expected_y_0 = 4829274.257160724
        expected_x_1 = -53577.01221140767
        expected_y_1 = 4827759.717904298
        expected_x_2 = -52065.81335081684
        expected_y_2 = 4827011.5456999075
        expected_x_3 = -50930.53416872382
        expected_y_3 = 4827047.655472828
        geom_3857 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_3857.coords[0][0][0], expected_x_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][0][1], expected_y_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][1][0], expected_x_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[0][1][1], expected_y_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][0][0], expected_x_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][0][1], expected_y_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][1][0], expected_x_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_3857.coords[1][1][1], expected_y_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_3857 = json.loads(geom_3857.geojson)
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][0][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][0][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][1][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_3857['coordinates'][1][1][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_3857.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_multilinestring_3857_to_4258(self):
        wkt = 'MULTILINESTRING ((-55473.34948015408 4829274.257160724, -53577.01221140767 4827759.717904298), (-52065.81335081684 4827011.5456999075, -50930.53416872382 4827047.655472828))'
        delta = 0.00001
        source_crs = 3857
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        geom_4258 = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(geom_4258.coords[0][0][0], expected__lon_0, delta=delta, msg=f"multilinestring x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][0][1], expected__lat_0, delta=delta, msg=f"multilinestring y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1][0], expected__lon_1, delta=delta, msg=f"multilinestring x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[0][1][1], expected__lat_1, delta=delta, msg=f"multilinestring y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0][0], expected__lon_2, delta=delta, msg=f"multilinestring x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][0][1], expected__lat_2, delta=delta, msg=f"multilinestring y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1][0], expected__lon_3, delta=delta, msg=f"multilinestring x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(geom_4258.coords[1][1][1], expected__lat_3, delta=delta, msg=f"multilinestring y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_geom_4258 = json.loads(geom_4258.geojson)
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][0][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_geom_4258['coordinates'][1][1][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        wkt_parts = geom_4258.wkt.split("((")[1].split("))")[0].split("), (")
        coords_part1 = wkt_parts[0].split(",")
        coord0 = coords_part1[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords_part1[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coords_part2 = wkt_parts[1].split(",")
        coord2 = coords_part2[0].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords_part2[1].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")


class PatchedGeosPolygonTestCase(unittest.TestCase):
    """ Checks the behavior of coordinate transformations using gvsigol convinience functions
    created to avoid inconsistences in Django/GEOSGeometry behaviour depending on GDAL/LIBPROJ versions.
    """
    def setUp(self):
        pass

    def test_transform_polygon_4326_to_25830(self):
        wkt = 'POLYGON ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066, -0.4983255769932612 39.74720322603334))'
        delta = 0.00001
        source_crs = 4326
        target_crs = 25830
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected_x_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected_y_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected_x_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected_y_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected_x_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected_y_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected_x_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected_y_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")


    def test_transform_polygon_25830_to_4326(self):
        wkt = 'POLYGON ((714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016, 714340.11389 4402692.86474))'
        delta = 0.00001
        source_crs = 25830
        target_crs = 4326
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected__lon_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected__lat_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected__lon_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected__lat_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected__lon_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected__lat_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected__lon_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected__lat_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_4326_to_4258(self):
        wkt = 'POLYGON ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066, -0.4983255769932612 39.74720322603334))'
        delta = 0.00001
        source_crs = 4326
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected__lon_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected__lat_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected__lon_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected__lat_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected__lon_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected__lat_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected__lon_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected__lat_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_4258_to_4326(self):
        wkt = 'POLYGON ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066, -0.4983255769932612 39.74720322603334))'
        delta = 0.00001
        source_crs = 4258
        target_crs = 4326
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)
        
        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected__lon_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected__lat_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected__lon_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected__lat_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected__lon_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected__lat_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected__lon_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected__lat_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_25830_to_25831(self):
        wkt = 'POLYGON ((714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016, 714340.11389 4402692.86474))'
        delta = 0.00001
        source_crs = 25830
        target_crs = 25831
        expected_x_0 = 200251.40850083757
        expected_y_0 = 4405554.974307208
        expected_x_1 = 201666.1899918826
        expected_y_1 = 4404336.570427252
        expected_x_2 = 202807.58059562254
        expected_y_2 = 4403717.582285645
        expected_x_3 = 203682.8748760639
        expected_y_3 = 4403711.4663969185
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected_x_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected_y_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected_x_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected_y_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected_x_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected_y_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected_x_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected_y_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_25831_to_25830(self):
        wkt = 'POLYGON ((200251.40850083757 4405554.974307208, 201666.1899918826 4404336.570427252, 202807.58059562254 4403717.582285645, 203682.8748760639 4403711.4663969185, 200251.40850083757 4405554.974307208))'
        delta = 0.0001
        source_crs = 25831
        target_crs = 25830
        
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected_x_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected_y_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected_x_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected_y_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected_x_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected_y_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected_x_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected_y_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_25830_to_4258(self):
        wkt = 'POLYGON ((714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016, 714340.11389 4402692.86474))'
        delta = 0.00001
        source_crs = 25830
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected__lon_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected__lat_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected__lon_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected__lat_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected__lon_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected__lat_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected__lon_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected__lat_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_4258_to_25830(self):
        wkt = 'POLYGON ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066, -0.4983255769932612 39.74720322603334))'
        delta = 0.00001
        source_crs = 4258
        target_crs = 25830
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected_x_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected_y_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected_x_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected_y_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected_x_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected_y_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected_x_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected_y_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")


    def test_transform_polygon_25830_to_3857(self):
        wkt = 'POLYGON ((714340.11389 4402692.86474, 715832.48897 4401572.49473, 717012.14105 4401031.56513, 717885.44375 4401084.016, 714340.11389 4402692.86474))'
        delta = 0.001
        source_crs = 25830
        target_crs = 3857
        
        expected_x_0 = -55473.34948015408
        expected_y_0 = 4829274.257160724
        expected_x_1 = -53577.01221140767
        expected_y_1 = 4827759.717904298
        expected_x_2 = -52065.81335081684
        expected_y_2 = 4827011.5456999075
        expected_x_3 = -50930.53416872382
        expected_y_3 = 4827047.655472828
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected_x_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected_y_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected_x_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected_y_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected_x_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected_y_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected_x_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected_y_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_3857_to_25830(self):
        wkt = 'POLYGON ((-55473.34948015408 4829274.257160724, -53577.01221140767 4827759.717904298, -52065.81335081684 4827011.5456999075, -50930.53416872382 4827047.655472828, -55473.34948015408 4829274.257160724))'
        delta = 0.001
        source_crs = 3857
        target_crs = 25830
        
        expected_x_0 = 714340.11389
        expected_y_0 = 4402692.86474
        expected_x_1 = 715832.48897
        expected_y_1 = 4401572.49473
        expected_x_2 = 717012.14105
        expected_y_2 = 4401031.56513
        expected_x_3 = 717885.44375
        expected_y_3 = 4401084.016
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected_x_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected_y_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected_x_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected_y_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected_x_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected_y_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected_x_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected_y_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_4258_to_3857(self):
        wkt = 'POLYGON ((-0.4983255769932612 39.74720322603334, -0.4812904894696575 39.736741654561875, -0.46771515913153 39.73157312257331, -0.4575167727213614 39.73182258543066, -0.4983255769932612 39.74720322603334))'
        delta = 0.001
        source_crs = 4258
        target_crs = 3857
        
        expected_x_0 = -55473.34948015408
        expected_y_0 = 4829274.257160724
        expected_x_1 = -53577.01221140767
        expected_y_1 = 4827759.717904298
        expected_x_2 = -52065.81335081684
        expected_y_2 = 4827011.5456999075
        expected_x_3 = -50930.53416872382
        expected_y_3 = 4827047.655472828
        transformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(transformed_geom.coords[0][0][0], expected_x_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][0][1], expected_y_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][0], expected_x_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][1][1], expected_y_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][0], expected_x_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][2][1], expected_y_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][0], expected_x_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(transformed_geom.coords[0][3][1], expected_y_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_transformed_geom = json.loads(transformed_geom.geojson)
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][0], expected_x_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][0][1], expected_y_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][0], expected_x_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][1][1], expected_y_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][0], expected_x_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][2][1], expected_y_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][0], expected_x_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_transformed_geom['coordinates'][0][3][1], expected_y_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = transformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected_x_0, delta=delta, msg=f"transformed wkt x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected_y_0, delta=delta, msg=f"transformed wkt y coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected_x_1, delta=delta, msg=f"transformed wkt x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected_y_1, delta=delta, msg=f"transformed wkt y coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected_x_2, delta=delta, msg=f"transformed wkt x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected_y_2, delta=delta, msg=f"transformed wkt y coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected_x_3, delta=delta, msg=f"transformed wkt x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected_y_3, delta=delta, msg=f"transformed wkt y coordinate 3 failed from {source_crs} to {target_crs}")

    def test_transform_polygon_3857_to_4258(self):
        wkt = 'POLYGON ((-55473.34948015408 4829274.257160724, -53577.01221140767 4827759.717904298, -52065.81335081684 4827011.5456999075, -50930.53416872382 4827047.655472828, -55473.34948015408 4829274.257160724))'
        delta = 0.00001
        source_crs = 3857
        target_crs = 4258
        expected__lon_0 = -0.4983255769932612
        expected__lat_0 = 39.74720322603334
        expected__lon_1 = -0.4812904894696575
        expected__lat_1 = 39.736741654561875
        expected__lon_2 = -0.46771515913153
        expected__lat_2 = 39.73157312257331
        expected__lon_3 = -0.4575167727213614
        expected__lat_3 = 39.73182258543066
        tranformed_geom = transform_wkt(wkt, source_crs, target_crs)

        self.assertAlmostEqual(tranformed_geom.coords[0][0][0], expected__lon_0, delta=delta, msg=f"polygon x coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(tranformed_geom.coords[0][0][1], expected__lat_0, delta=delta, msg=f"polygon y coordinate 0 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(tranformed_geom.coords[0][1][0], expected__lon_1, delta=delta, msg=f"polygon x coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(tranformed_geom.coords[0][1][1], expected__lat_1, delta=delta, msg=f"polygon y coordinate 1 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(tranformed_geom.coords[0][2][0], expected__lon_2, delta=delta, msg=f"polygon x coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(tranformed_geom.coords[0][2][1], expected__lat_2, delta=delta, msg=f"polygon y coordinate 2 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(tranformed_geom.coords[0][3][0], expected__lon_3, delta=delta, msg=f"polygon x coordinate 3 transformation failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(tranformed_geom.coords[0][3][1], expected__lat_3, delta=delta, msg=f"polygon y coordinate 3 transformation failed from {source_crs} to {target_crs}")
        
        # Check the Geojson of transformed geometry
        json_tranformed_geom = json.loads(tranformed_geom.geojson)
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][0][0], expected__lon_0, delta=delta, msg=f"transformed json x coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][0][1], expected__lat_0, delta=delta, msg=f"transformed json y coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][1][0], expected__lon_1, delta=delta, msg=f"transformed json x coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][1][1], expected__lat_1, delta=delta, msg=f"transformed json y coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][2][0], expected__lon_2, delta=delta, msg=f"transformed json x coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][2][1], expected__lat_2, delta=delta, msg=f"transformed json y coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][3][0], expected__lon_3, delta=delta, msg=f"transformed json x coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(json_tranformed_geom['coordinates'][0][3][1], expected__lat_3, delta=delta, msg=f"transformed json y coordinate 3 failed from {source_crs} to {target_crs}")

        # Check the WKT of transformed geometry        
        coords = tranformed_geom.wkt.split("((")[1].split("))")[0].split(",")
        coord0 = coords[0].strip().split(" ")
        self.assertAlmostEqual(float(coord0[0]), expected__lon_0, delta=delta, msg=f"transformed wkt lon coordinate 0 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord0[1]), expected__lat_0, delta=delta, msg=f"transformed wkt lat coordinate 0 failed from {source_crs} to {target_crs}")
        coord1 = coords[1].strip().split(" ")
        self.assertAlmostEqual(float(coord1[0]), expected__lon_1, delta=delta, msg=f"transformed wkt lon coordinate 1 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord1[1]), expected__lat_1, delta=delta, msg=f"transformed wkt lat coordinate 1 failed from {source_crs} to {target_crs}")
        coord2 = coords[2].strip().split(" ")
        self.assertAlmostEqual(float(coord2[0]), expected__lon_2, delta=delta, msg=f"transformed wkt lon coordinate 2 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord2[1]), expected__lat_2, delta=delta, msg=f"transformed wkt lat coordinate 2 failed from {source_crs} to {target_crs}")
        coord3 = coords[3].strip().split(" ")
        self.assertAlmostEqual(float(coord3[0]), expected__lon_3, delta=delta, msg=f"transformed wkt lon coordinate 3 failed from {source_crs} to {target_crs}")
        self.assertAlmostEqual(float(coord3[1]), expected__lat_3, delta=delta, msg=f"transformed wkt lat coordinate 3 failed from {source_crs} to {target_crs}")

