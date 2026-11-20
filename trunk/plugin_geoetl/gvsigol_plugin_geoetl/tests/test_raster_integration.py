# -*- coding: utf-8 -*-
"""
Pruebas de integración de los nodos predictivos con la BD real del plugin (PostGIS).

No se ejecutan por defecto: necesitan la base de datos del ETL y escriben tablas temporales con el
prefijo "zzit_" (las borran al terminar). Para lanzarlas, dentro del contenedor del backend:

    GEOETL_INTEGRATION=1 python manage.py test gvsigol_plugin_geoetl.tests.test_raster_integration

Las del flujo completo con GeoServer están en test_raster_engine.py (GEOETL_INTEGRATION_GEOSERVER=1).
"""
import os
import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from gvsigol_plugin_geoetl import etl_raster as er
from gvsigol_plugin_geoetl.settings import GEOETL_DB as DB

try:
    import joblib
    import psycopg2
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import box
    DEPS = True
except ImportError:  # pragma: no cover
    DEPS = False

ENABLED = bool(os.environ.get('GEOETL_INTEGRATION'))
PFX = 'zzit_'
CRS = 'EPSG:25830'


def connect():
    conn = psycopg2.connect(user=DB['user'], password=DB['password'], host=DB['host'], port=DB['port'],
                            database=DB['database'])
    conn.autocommit = True
    return conn


@unittest.skipUnless(ENABLED and DEPS, 'Define GEOETL_INTEGRATION=1 para las pruebas con la BD')
class DatabaseCase(SimpleTestCase):

    def setUp(self):
        self.conn = connect()
        self.cur = self.conn.cursor()
        self.tmp = tempfile.mkdtemp()
        self.artifacts = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_name LIKE %s",
                         (DB['schema'], PFX + '%'))
        for (t,) in self.cur.fetchall():
            self.cur.execute('DROP TABLE IF EXISTS "%s"."%s"' % (DB['schema'], t))
        self.conn.close()
        shutil.rmtree(self.tmp, True)
        for p in self.artifacts:
            er.remove_artifact(p)

    def table_exists(self, name):
        self.cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
                         (DB['schema'], name))
        return self.cur.fetchone()[0] == 1

    def columns(self, name):
        self.cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s "
                         "ORDER BY ordinal_position", (DB['schema'], name))
        return [r[0] for r in self.cur.fetchall()]

    def create_points_table(self, name, rows):
        self.cur.execute('CREATE TABLE "%s"."%s" (ogc_fid serial PRIMARY KEY, x double precision, ruido double precision, '
                         'texto text, clase text, wkb_geometry geometry(Point, 25830))' % (DB['schema'], name))
        for i, (x, ruido, clase) in enumerate(rows):
            self.cur.execute('INSERT INTO "%s"."%s" (x, ruido, texto, clase, wkb_geometry) VALUES (%%s,%%s,%%s,%%s,'
                             'ST_SetSRID(ST_MakePoint(%%s,%%s),25830))' % (DB['schema'], name),
                             (x, ruido, 't%d' % i, clase, 500000 + i, 4300000 + i))

    def trained_model(self, features=('x', 'ruido')):
        rng = np.random.RandomState(1)
        df = pd.DataFrame({'x': np.r_[rng.normal(0, 1, 100), rng.normal(10, 1, 100)], 'ruido': rng.normal(0, 1, 200),
                           'y': ['A'] * 100 + ['B'] * 100})
        bundle, _, _ = er.train_model(df, 'y', list(features))
        path = er.new_artifact_path('zzit_model', '.joblib')
        joblib.dump(bundle, path)
        self.artifacts.append(path)
        return path


class TablePredictIntegration(DatabaseCase):

    def rows(self):
        rng = np.random.RandomState(7)
        rows = [(float(rng.normal(0, 1)), float(rng.normal()), 'A') for _ in range(30)]
        rows += [(float(rng.normal(10, 1)), float(rng.normal()), 'B') for _ in range(30)]
        rows += [(None, 0.5, 'A'), (5.0, None, 'B')]                  # filas con variables nulas
        return rows

    def test_adds_prediction_and_confidence_keeping_everything_else(self):
        self.create_points_table(PFX + 'src', self.rows())
        model = self.trained_model()
        res = er.trans_TablePredict({'id': PFX + 'out', 'data': [PFX + 'src', model], 'column': 'Predicción'})
        self.assertEqual(res, [PFX + 'out'])
        cols = self.columns(PFX + 'out')
        self.assertEqual(cols, ['ogc_fid', 'x', 'ruido', 'texto', 'clase', 'wkb_geometry', 'prediccion', 'prediccion_confidence'])
        self.assertNotIn('__rid', cols)
        self.cur.execute('SELECT count(*), count(prediccion), count(*) FILTER (WHERE prediccion = clase) '
                         'FROM "%s"."%s"' % (DB['schema'], PFX + 'out'))
        total, predicted, correct = self.cur.fetchone()
        self.assertEqual((total, predicted), (62, 60))                   # las dos filas con nulos quedan sin predecir
        self.assertGreaterEqual(correct, 58)
        self.cur.execute('SELECT DISTINCT ST_SRID(wkb_geometry), GeometryType(wkb_geometry) FROM "%s"."%s"'
                         % (DB['schema'], PFX + 'out'))
        self.assertEqual(self.cur.fetchall(), [(25830, 'POINT')])
        self.cur.execute('SELECT min(prediccion_confidence), max(prediccion_confidence) FROM "%s"."%s"' % (DB['schema'], PFX + 'out'))
        low, high = self.cur.fetchone()
        self.assertTrue(0 < low <= high <= 1)
        # la tabla de origen no se toca
        self.assertEqual(self.columns(PFX + 'src'), ['ogc_fid', 'x', 'ruido', 'texto', 'clase', 'wkb_geometry'])

    def test_numeric_classes_are_stored_as_numbers(self):
        self.cur.execute('CREATE TABLE "%s"."%s" (a double precision)' % (DB['schema'], PFX + 'num'))
        rng = np.random.RandomState(2)
        for v in list(rng.normal(0, 1, 40)) + list(rng.normal(10, 1, 40)):
            self.cur.execute('INSERT INTO "%s"."%s" VALUES (%%s)' % (DB['schema'], PFX + 'num'), (float(v),))
        df = pd.DataFrame({'a': np.r_[rng.normal(0, 1, 100), rng.normal(10, 1, 100)], 'c': [1] * 100 + [2] * 100})
        bundle, _, _ = er.train_model(df, 'c', ['a'])
        path = er.new_artifact_path('zzit_model2', '.joblib')
        joblib.dump(bundle, path)
        self.artifacts.append(path)
        er.trans_TablePredict({'id': PFX + 'numout', 'data': [PFX + 'num', path]})
        self.cur.execute("SELECT data_type FROM information_schema.columns WHERE table_schema=%s AND table_name=%s "
                         "AND column_name='prediction'", (DB['schema'], PFX + 'numout'))
        self.assertEqual(self.cur.fetchone()[0], 'bigint')

    def test_regression_gives_value_and_dispersion(self):
        self.cur.execute('CREATE TABLE "%s"."%s" (a double precision)' % (DB['schema'], PFX + 'reg'))
        for v in np.linspace(0, 10, 30):
            self.cur.execute('INSERT INTO "%s"."%s" VALUES (%%s)' % (DB['schema'], PFX + 'reg'), (float(v),))
        rng = np.random.RandomState(3)
        x = rng.uniform(0, 10, 300)
        bundle, _, _ = er.train_model(pd.DataFrame({'a': x, 'v': x * 2}), 'v', ['a'])
        path = er.new_artifact_path('zzit_model3', '.joblib')
        joblib.dump(bundle, path)
        self.artifacts.append(path)
        er.trans_TablePredict({'id': PFX + 'regout', 'data': [PFX + 'reg', path]})
        self.cur.execute('SELECT corr(a, prediction), min(prediction_confidence) FROM "%s"."%s"' % (DB['schema'], PFX + 'regout'))
        corr, low = self.cur.fetchone()
        self.assertGreater(corr, 0.99)
        self.assertGreaterEqual(low, 0)

    def test_errors_leave_nothing_behind(self):
        self.create_points_table(PFX + 'src', self.rows())
        model = self.trained_model(features=('x', 'ruido'))
        with self.assertRaisesRegex(Exception, 'ya tiene una columna llamada "clase"'):
            er.trans_TablePredict({'id': PFX + 'out', 'data': [PFX + 'src', model], 'column': 'clase'})
        self.assertFalse(self.table_exists(PFX + 'out'))
        self.cur.execute('CREATE TABLE "%s"."%s" (otra double precision)' % (DB['schema'], PFX + 'other'))
        with self.assertRaisesRegex(Exception, 'no tiene las columnas con las que se entrenó el modelo: x, ruido'):
            er.trans_TablePredict({'id': PFX + 'out', 'data': [PFX + 'other', model]})
        self.assertFalse(self.table_exists(PFX + 'out'))
        with self.assertRaisesRegex(Exception, 'Conecta'):
            er.trans_TablePredict({'id': PFX + 'out', 'data': [PFX + 'src']})
        with self.assertRaisesRegex(Exception, 'No se encuentra la tabla'):
            er.trans_TablePredict({'id': PFX + 'out', 'data': [PFX + 'inexistente', model]})

    def test_rerun_replaces_the_output(self):
        self.create_points_table(PFX + 'src', self.rows())
        model = self.trained_model()
        for _ in range(2):
            er.trans_TablePredict({'id': PFX + 'out', 'data': [PFX + 'src', model]})
        self.cur.execute('SELECT count(*) FROM "%s"."%s"' % (DB['schema'], PFX + 'out'))
        self.assertEqual(self.cur.fetchone()[0], 62)


class PolygonizeAndAssessIntegration(DatabaseCase):

    def classified(self, path, array, class_map):
        array = np.asarray(array, dtype='uint16')
        with rasterio.open(path, 'w', driver='GTiff', height=array.shape[0], width=array.shape[1], count=1,
                           dtype='uint16', crs=CRS, transform=from_origin(0, array.shape[0], 1, 1), nodata=0) as dst:
            dst.write(array, 1)
        er.write_meta(path, {'problem': 'classification', 'class_map': class_map})

    def test_polygonize_node_streams_into_postgis(self):
        a = np.ones((60, 20), dtype=int)
        a[:, 8:12] = 2
        path = os.path.join(self.tmp, 'cls.tif')
        self.classified(path, a, {'1': 'A', '2': 'B'})
        res = er.trans_RasterPolygonize({'id': PFX + 'pol', 'data': [path], 'classes': 'B', 'min-area': '1',
                                         'simplify': '0', 'connectivity': '4'})
        self.cur.execute('SELECT class_name, class_code, area, ST_SRID(wkb_geometry) FROM "%s"."%s"' % (DB['schema'], res[0]))
        self.assertEqual(self.cur.fetchall(), [('B', 2, 240.0, 25830)])

    def test_polygonize_failure_leaves_no_partial_table(self):
        a = np.ones((20, 20), dtype=int)
        path = os.path.join(self.tmp, 'cls.tif')
        self.classified(path, a, {'1': 'A'})
        with self.assertRaises(ValueError):
            er.trans_RasterPolygonize({'id': PFX + 'pol', 'data': [path], 'classes': 'NoExiste'})
        self.assertFalse(self.table_exists(PFX + 'pol'))

    def test_assess_node_writes_report_and_matrix(self):
        a = np.ones((40, 40), dtype=int)
        a[:, 20:] = 2
        path = os.path.join(self.tmp, 'cls.tif')
        self.classified(path, a, {'1': 'A', '2': 'B'})
        self.cur.execute('CREATE TABLE "%s"."%s" (clase text, wkb_geometry geometry(Polygon, 25830))' % (DB['schema'], PFX + 'val'))
        for label, geom in (('A', box(2, 2, 12, 12)), ('B', box(26, 2, 36, 12))):
            self.cur.execute('INSERT INTO "%s"."%s" VALUES (%%s, ST_SetSRID(ST_GeomFromWKB(%%s), 25830))' % (DB['schema'], PFX + 'val'),
                             (label, psycopg2.Binary(geom.wkb)))
        res = er.trans_ClassAssess({'id': PFX + 'as', 'data': [path, PFX + 'val'], 'class-attr': 'clase'})
        self.assertEqual(res, [PFX + 'as_0', PFX + 'as_1'])
        self.cur.execute('SELECT value FROM "%s"."%s" WHERE section=\'metric\' AND name=\'accuracy\'' % (DB['schema'], res[0]))
        self.assertEqual(self.cur.fetchone()[0], 1.0)
        self.assertEqual(self.columns(res[1]), ['real', 'pred_a', 'pred_b', 'total', 'recall'])
        with self.assertRaisesRegex(Exception, 'Conecta'):
            er.trans_ClassAssess({'id': PFX + 'as', 'data': [path], 'class-attr': 'clase'})
        with self.assertRaisesRegex(Exception, 'columna que contiene la clase'):
            er.trans_ClassAssess({'id': PFX + 'as', 'data': [path, PFX + 'val']})


class ClipIntegration(DatabaseCase):
    """Nodo Recortar ráster con la máscara en una tabla PostGIS (en otro sistema de coordenadas que el ráster)."""

    def make_raster(self, path):
        data = np.tile(np.arange(80, dtype='uint8'), (60, 1))[None].repeat(3, axis=0)
        with rasterio.open(path, 'w', driver='GTiff', height=60, width=80, count=3, dtype='uint8', crs=CRS,
                           transform=from_origin(500000, 4300060, 1, 1)) as dst:
            dst.write(data)
        er.write_meta(path, {'band_names': ['nir', 'rojo', 'verde']})

    def make_mask(self, name, polygon_25830, srid=4326, extra=None):
        import geopandas as gpd
        geoms = gpd.GeoSeries([polygon_25830] + list(extra or []), crs=CRS).to_crs('EPSG:%d' % srid)
        self.cur.execute('CREATE TABLE "%s"."%s" (id serial, wkb_geometry geometry(Geometry, %d))' % (DB['schema'], name, srid))
        for g in geoms:
            self.cur.execute('INSERT INTO "%s"."%s" (wkb_geometry) VALUES (ST_SetSRID(ST_GeomFromWKB(%%s), %d))'
                             % (DB['schema'], name, srid), (psycopg2.Binary(g.wkb),))

    def test_mask_in_another_crs_is_reprojected(self):
        path = os.path.join(self.tmp, 'in.tif')
        self.make_raster(path)
        self.make_mask(PFX + '_mask', box(500010, 4300020, 500030, 4300040))
        res = er.trans_RasterClip(
            {'id': PFX + '_clip', 'data': [path, PFX + '_mask'], 'mode': 'bbox', 'pixel-size': ''})
        self.artifacts.append(res[0])
        with rasterio.open(res[0]) as src:
            self.assertEqual((src.width, src.height), (20, 20))
            self.assertAlmostEqual(src.transform.c, 500010.0, delta=1.5)           # tolerancia de la ida y vuelta 25830 <-> 4326
        self.assertEqual(er.read_meta(res[0])['band_names'], ['nir', 'rojo', 'verde'])

    def test_resample_to_a_coarser_pixel_in_one_step(self):
        path = os.path.join(self.tmp, 'in.tif')
        self.make_raster(path)
        self.make_mask(PFX + '_mask', box(500000, 4300000, 500080, 4300060), srid=25830)
        res = er.trans_RasterClip({'id': PFX + '_clip', 'data': [path, PFX + '_mask'], 'mode': 'polygon',
                                   'pixel-size': '4', 'resampling': 'average'})
        self.artifacts.append(res[0])
        with rasterio.open(res[0]) as src:
            self.assertEqual((src.width, src.height, src.transform.a), (20, 15, 4.0))
            self.assertEqual(src.dtypes[0], 'uint8')

    def test_only_polygons_count_as_mask_and_errors_are_clear(self):
        from shapely.geometry import Point
        path = os.path.join(self.tmp, 'in.tif')
        self.make_raster(path)
        self.make_mask(PFX + '_pts', Point(500010, 4300020), srid=25830)
        with self.assertRaisesRegex(ValueError, 'capa de polígonos'):
            er.trans_RasterClip({'id': PFX + '_clip', 'data': [path, PFX + '_pts']})
        self.assertEqual([f for f in os.listdir(er.artifacts_root()) if f.startswith(PFX + '_clip')], [])
        with self.assertRaisesRegex(Exception, 'Conecta un ráster y una capa'):
            er.trans_RasterClip({'id': PFX + '_clip', 'data': [path]})
        self.make_mask(PFX + '_far', box(1, 1, 5, 5), srid=25830)
        with self.assertRaisesRegex(ValueError, 'no se solapa'):
            er.trans_RasterClip({'id': PFX + '_clip', 'data': [path, PFX + '_far']})
        self.assertEqual([f for f in os.listdir(er.artifacts_root()) if f.startswith(PFX + '_clip')], [])


class AreaEstimationIntegration(DatabaseCase):
    """Muestreo estratificado -> anotar la clase real -> estimar superficies, con tablas PostGIS reales."""

    def classified(self, path, array, class_map):
        array = np.asarray(array, dtype='uint16')
        with rasterio.open(path, 'w', driver='GTiff', height=array.shape[0], width=array.shape[1], count=1,
                           dtype='uint16', crs=CRS, transform=from_origin(500000, 4300000 + array.shape[0], 1, 1),
                           nodata=0) as dst:
            dst.write(array, 1)
        er.write_meta(path, {'problem': 'classification', 'class_map': class_map})

    def test_sample_label_and_estimate(self):
        # Mapa: A a la izquierda, B a la derecha. La "verdad": una franja de B está mal clasificada como A
        truth = np.ones((100, 100), dtype=int)
        truth[:, 40:] = 2
        mapped = truth.copy()
        mapped[:, 40:50] = 1                        # el mapa infraestima B en 1 000 píxeles
        path = os.path.join(self.tmp, 'map.tif')
        self.classified(path, mapped, {'1': 'A', '2': 'B'})
        res = er.trans_StratifiedSample({'id': PFX + 'smp', 'data': [path], 'per-class': '60', 'seed': '3'})
        self.assertEqual(self.columns(res[0]), ['ogc_fid', 'id', 'map_class', 'map_code', 'reference', 'wkb_geometry'])
        self.cur.execute('SELECT map_class, count(*), count(reference) FROM "%s"."%s" GROUP BY 1 ORDER BY 1' % (DB['schema'], res[0]))
        self.assertEqual(self.cur.fetchall(), [('A', 60, 0), ('B', 60, 0)])
        # El usuario anotaría la clase real en campo o con una ortofoto; aquí se toma de la "verdad"
        self.cur.execute('SELECT ogc_fid, ST_X(wkb_geometry), ST_Y(wkb_geometry) FROM "%s"."%s"' % (DB['schema'], res[0]))
        for fid, x, y in self.cur.fetchall():
            label = 'A' if truth[int(4300100 - y), int(x - 500000)] == 1 else 'B'
            self.cur.execute('UPDATE "%s"."%s" SET reference = %%s WHERE ogc_fid = %%s' % (DB['schema'], res[0]), (label, fid))
        out = er.trans_AreaEstimate({'id': PFX + 'area', 'data': [path, res[0]], 'reference-attr': 'reference',
                                     'confidence-level': '0.95'})
        self.cur.execute('SELECT class, map_area, estimated_area, ci_low, ci_high FROM "%s"."%s" ORDER BY class' % (DB['schema'], out[0]))
        rows = {r[0]: r[1:] for r in self.cur.fetchall()}
        self.assertEqual(rows['A'][0], 5000)                      # lo que dice el mapa
        self.assertEqual(rows['B'][0], 5000)
        self.assertLess(rows['A'][1], 5000)                       # la estimación corrige hacia la verdad (4 000 / 6 000)
        self.assertTrue(rows['B'][2] <= 6000 <= rows['B'][3], rows['B'])
        self.cur.execute('SELECT name, value FROM "%s"."%s"' % (DB['schema'], out[1]))
        report = dict(self.cur.fetchall())
        self.assertEqual(report['samples'], 120)
        self.assertEqual(report['total_area'], 10000)

    def test_polygons_are_rejected_and_unlabelled_points_are_skipped(self):
        path = os.path.join(self.tmp, 'map.tif')
        self.classified(path, np.ones((20, 20), dtype=int), {'1': 'A'})
        self.cur.execute('CREATE TABLE "%s"."%s" (clase text, wkb_geometry geometry(Polygon, 25830))' % (DB['schema'], PFX + 'poly'))
        self.cur.execute('INSERT INTO "%s"."%s" VALUES (\'A\', ST_MakeEnvelope(500001, 4300001, 500005, 4300005, 25830))' % (DB['schema'], PFX + 'poly'))
        with self.assertRaisesRegex(Exception, 'PUNTOS'):
            er.trans_AreaEstimate({'id': PFX + 'area', 'data': [path, PFX + 'poly'], 'reference-attr': 'clase'})
        with self.assertRaisesRegex(Exception, 'Nivel de confianza'):
            er.trans_AreaEstimate({'id': PFX + 'area', 'data': [path, PFX + 'poly'], 'reference-attr': 'clase',
                                   'confidence-level': '0.5'})


class SubsampleIntegration(DatabaseCase):

    def test_random_forest_node_subsamples_and_reports_it(self):
        from unittest import mock
        rng = np.random.RandomState(0)
        df = pd.DataFrame({'x': np.r_[rng.normal(0, 1, 3000), rng.normal(10, 1, 3000)], 'y': ['A'] * 3000 + ['B'] * 3000})
        er._write_table(df, PFX + 'train')
        with mock.patch.object(er.plugin_settings, 'ETL_RASTER_MAX_TRAIN_ROWS', 2000, create=True):
            res = er.trans_RandomForest({'id': PFX + 'rf', 'data': [PFX + 'train'], 'target': 'y', 'features': ['x'],
                                         'n-estimators': '20'})
        self.artifacts.append(res[1])
        self.cur.execute('SELECT value FROM "%s"."%s" WHERE section=\'training\' AND name=\'subsampled_from\'' % (DB['schema'], res[0]))
        self.assertEqual(self.cur.fetchone()[0], 6000)
        self.cur.execute('SELECT value FROM "%s"."%s" WHERE section=\'training\' AND name=\'rows\'' % (DB['schema'], res[0]))
        self.assertLess(self.cur.fetchone()[0], 6000)


class ModelsViewsIntegration(DatabaseCase):
    """Endpoints de los modelos guardados con usuarios reales (permisos y aislamiento entre usuarios)."""

    def setUp(self):
        super().setUp()
        from unittest import mock
        from django.test import RequestFactory
        from gvsigol_plugin_geoetl import etl_models, views
        self.em, self.views, self.factory = etl_models, views, RequestFactory()
        patcher = mock.patch.multiple(etl_models.plugin_settings, create=True, ETL_MODELS_DIR=self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

        class Staff:                       # usuario de personal sin ser superusuario
            is_authenticated = True
            is_active = True
            is_staff = True
            is_superuser = False
            username = 'zzit_staff'
            pk = None
        class Plain(Staff):
            is_staff = False
            username = 'zzit_plain'
        class Admin(Staff):
            is_superuser = True
            username = 'zzit_admin'
        self.staff, self.plain, self.admin = Staff(), Plain(), Admin()

    def call(self, view, user, method='get', **data):
        request = getattr(self.factory, method)('/x/', data)
        request.user = user
        return view(request)

    def save(self, owner, name='zzit_modelo'):
        bundle, _, _ = er.train_model(pd.DataFrame({'x': np.arange(40.0), 'y': ['A', 'B'] * 20}), 'y', ['x'], n_estimators=5)
        path = er.new_artifact_path('zzit_v', '.joblib')
        joblib.dump(bundle, path)
        self.artifacts.append(path)
        return self.em.save_model(owner, name, path, {'problem': 'classification', 'features': ['x'], 'classes': ['A', 'B']})

    def test_each_user_lists_only_their_own_models(self):
        import json
        self.save('zzit_staff')
        self.save(self.admin.username, 'zzit_del_admin')
        mine = json.loads(self.call(self.views.etl_models_list, self.staff).content)['models']
        self.assertEqual([m['name'] for m in mine], ['zzit_modelo'])
        self.assertEqual(mine[0]['versions'][0]['features'], ['x'])
        # un superusuario ve los suyos, y los de otro solo si lo pide expresamente
        own = json.loads(self.call(self.views.etl_models_list, self.admin).content)['models']
        self.assertEqual([m['name'] for m in own], ['zzit_del_admin'])
        other = json.loads(self.call(self.views.etl_models_list, self.admin, owner='zzit_staff').content)['models']
        self.assertEqual([m['name'] for m in other], ['zzit_modelo'])
        # un usuario normal no puede ver los de otro aunque lo pida
        sneaky = json.loads(self.call(self.views.etl_models_list, self.staff, owner=self.admin.username).content)['models']
        self.assertEqual([m['name'] for m in sneaky], ['zzit_modelo'])

    def test_staff_required_and_methods(self):
        self.assertEqual(self.call(self.views.etl_models_list, self.plain).status_code, 200)       # página de operación ilegal
        self.assertNotIn(b'models', self.call(self.views.etl_models_list, self.plain).content)
        self.assertEqual(self.call(self.views.etl_models_list, self.staff, method='post').status_code, 405)
        self.assertEqual(self.call(self.views.etl_models_delete, self.staff, method='get').status_code, 405)

    def test_delete_only_affects_the_requesting_user(self):
        import json
        self.save('zzit_staff')
        self.save(self.admin.username)
        response = self.call(self.views.etl_models_delete, self.staff, method='post', name='zzit_modelo', owner=self.admin.username)
        self.assertEqual(json.loads(response.content), {'deleted': 1})
        self.assertEqual(len(self.em.list_models(self.admin.username)), 1)              # el del otro intacto
        self.assertEqual(self.em.list_models('zzit_staff'), [])
        missing = self.call(self.views.etl_models_delete, self.staff, method='post', name='zzit_modelo')
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(self.call(self.views.etl_models_delete, self.staff, method='post').status_code, 400)

    def test_delete_one_version(self):
        import json
        self.save('zzit_staff')
        self.save('zzit_staff')
        response = self.call(self.views.etl_models_delete, self.staff, method='post', name='zzit_modelo', version='1')
        self.assertEqual(json.loads(response.content), {'deleted': 1})
        listed = json.loads(self.call(self.views.etl_models_list, self.staff).content)['models']
        self.assertEqual([v['version'] for v in listed[0]['versions']], [2])
