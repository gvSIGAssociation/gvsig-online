# coding: utf-8

'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

import unittest
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos import Point
import json
from gvsigol_core.geom import transform_point, transform_wkt

class GeosGeometryTestCase(unittest.TestCase):
    """ Checks the behavior of coordinate transformations in GEOSGeometry,
    which is usually influenced by the execution environment
    (mainly GDAL and Django versions)
    """
    def setUp(self):
        pass

    def _transform_point_geographic(self, lon, lat, source_crs, target_crs):
        """
        Experimental function to transform a point from source_crs to target_crs
        circunventing the django GEOSGeometry bug in versions < 4.2 with GDAL >= 3.x.
        """
        p = f'POINT({lon} {lat})'
        geos_geom = GEOSGeometry(p, srid=source_crs)
        transformed_geom = geos_geom.transform(target_crs, clone=True)
        return transformed_geom

    def _transform_point_projected(self, x, y, source_crs, target_crs):
        """
        Function to transform a point from source_crs to target_crs for projected coordinates
        """
        geos_geom = Point(x, y, srid=source_crs)
        transformed_geom = geos_geom.transform(target_crs, clone=True)
        return transformed_geom

    def test_transform_point_4326_to_25830(self):
        lon = -0.459891
        lat = 39.770063
        delta = 0.00001
        source_crs = 4326
        target_crs = 25830
        expected_x = 717561.534888295806013
        expected_y = 4405323.14028216060251
        geom_25830 = self._transform_point_geographic(lon, lat, source_crs, target_crs)
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
        geom_4326 = self._transform_point_projected(x, y, source_crs, target_crs)
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
        geom_4258 = self._transform_point_geographic(lon, lat, source_crs, target_crs)
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
        geom_4326 = self._transform_point_geographic(lon, lat, source_crs, target_crs)
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
        geom_25831 = self._transform_point_projected(x, y, source_crs, target_crs)
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
        geom_25830 = self._transform_point_projected(x, y, source_crs, target_crs)
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
        geom_4258 = self._transform_point_projected(x, y, source_crs, target_crs)
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
        delta = 0.001
        source_crs = 4258
        target_crs = 25830
        expected_x = 717561.534888295806013
        expected_y = 4405323.14028216060251
        geom_25830 = self._transform_point_geographic(lon, lat, source_crs, target_crs)
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
        geom_3857 = self._transform_point_projected(x, y, source_crs, target_crs)
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
        geom_25830 = self._transform_point_projected(x, y, source_crs, target_crs)
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
        geom_3857 = self._transform_point_geographic(lon, lat, source_crs, target_crs)
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
        geom_4258 = self._transform_point_projected(x, y, source_crs, target_crs)
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
    #     geom_3035 = self._transform_point_projected(x, y, source_crs, target_crs)
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
    #     geom_25830 = self._transform_point_projected(x, y, source_crs, target_crs)
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
    #     geom_4258 = self._transform_point_projected(x, y, source_crs, target_crs)
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
    #     geom_3035 = self._transform_point_geographic(lon, lat, source_crs, target_crs)
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

