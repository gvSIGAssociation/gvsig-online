# -*- coding: utf-8 -*-
"""
Tests del núcleo de los nodos predictivos / ráster (sin BD).
Ráster sintético: 40x40, 3 bandas. Mitad izquierda = clase "A" (valores bajos),
mitad derecha = clase "B" (valores altos).
"""
import os
import shutil
import tempfile
import time

import numpy as np
import pandas as pd
from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import etl_raster as er

try:
    import rasterio
    from rasterio.transform import from_origin
    import geopandas as gpd
    from shapely.geometry import box
    import sklearn  # noqa: F401
    DEPS = True
except ImportError:  # pragma: no cover
    DEPS = False

CRS = 'EPSG:25830'
SIZE = 40  # píxeles de 1 m, origen (0, 40)


def write_raster(path, nodata_pixel=False):
    rng = np.random.RandomState(0)
    data = np.zeros((3, SIZE, SIZE), dtype='float32')
    data[:, :, :SIZE // 2] = rng.normal(50, 5, (3, SIZE, SIZE // 2))
    data[:, :, SIZE // 2:] = rng.normal(200, 5, (3, SIZE, SIZE // 2))
    if nodata_pixel:
        data[:, 0, 0] = -9999
    with rasterio.open(path, 'w', driver='GTiff', height=SIZE, width=SIZE, count=3, dtype='float32',
                       crs=CRS, transform=from_origin(0, SIZE, 1, 1), nodata=-9999) as dst:
        dst.write(data)


def samples_gdf(label_a='A', label_b='B'):
    # Dos polígonos por clase dentro de cada mitad
    geoms = [box(2, 2, 12, 12), box(2, 20, 12, 30), box(26, 2, 36, 12), box(26, 20, 36, 30)]
    return gpd.GeoDataFrame({'clase': [label_a, label_a, label_b, label_b]}, geometry=geoms, crs=CRS)


class HelpersTest(SimpleTestCase):

    def test_parse_band_names(self):
        self.assertEqual(er.parse_band_names('Rojo, Infrarrojo cercano ,', 3), ['rojo', 'infrarrojo_cercano', 'b3'])
        self.assertEqual(er.parse_band_names(None, 2), ['b1', 'b2'])
        # nombres repetidos o que empiezan por número se hacen válidos y únicos
        self.assertEqual(er.parse_band_names(['x', 'X', '1a'], 3), ['x', 'x_2', 'b_1a'])

    def test_artifact_refs(self):
        self.assertTrue(er.is_raster_ref('/tmp/a/b.TIF'))
        self.assertTrue(er.is_model_ref('/tmp/a/m.joblib'))
        self.assertFalse(er.is_artifact_ref('node_1_0'))
        self.assertFalse(er.is_raster_ref('/tmp/a/m.joblib'))

    def test_remove_artifact_only_inside_artifacts_dir(self):
        root = er.artifacts_root()
        inside = os.path.join(root, 'test_rm_%d.tif' % os.getpid())
        open(inside, 'w').close()
        er.write_meta(inside, {'a': 1})
        outside_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside_dir, True)
        outside = os.path.join(outside_dir, 'ajeno.tif')
        open(outside, 'w').close()
        self.assertTrue(er.remove_artifact(inside))
        self.assertFalse(os.path.exists(inside))
        self.assertFalse(os.path.exists(er.meta_path(inside)))
        self.assertFalse(er.remove_artifact(outside))          # fuera del directorio: no se toca
        self.assertTrue(os.path.exists(outside))
        self.assertFalse(er.remove_artifact('nombre_de_tabla'))  # no es una ruta
        self.assertFalse(er.remove_artifact(inside))             # ya no existe

    def test_remove_artifact_deletes_the_link_not_the_original(self):
        original_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, original_dir, True)
        original = os.path.join(original_dir, 'original.tif')
        open(original, 'w').close()
        link = os.path.join(er.artifacts_root(), 'test_ln_%d.tif' % os.getpid())
        os.symlink(original, link)
        self.assertTrue(er.remove_artifact(link))
        self.assertFalse(os.path.lexists(link))
        self.assertTrue(os.path.exists(original))               # el fichero del usuario sigue ahí

    def test_clean_old_artifacts(self):
        root = er.artifacts_root()
        old = os.path.join(root, 'test_old_%d.tif' % os.getpid())
        new = os.path.join(root, 'test_new_%d.tif' % os.getpid())
        for p in (old, new):
            open(p, 'w').close()
        past = time.time() - 48 * 3600
        os.utime(old, (past, past))
        try:
            er.clean_old_artifacts(24)
            self.assertFalse(os.path.exists(old))
            self.assertTrue(os.path.exists(new))
        finally:
            for p in (old, new):
                if os.path.exists(p):
                    os.remove(p)


class TrainTest(SimpleTestCase):

    def test_detect_problem(self):
        self.assertEqual(er.detect_problem(pd.Series(['a', 'b'])), 'classification')
        self.assertEqual(er.detect_problem(pd.Series([1, 2, 1, 2])), 'classification')
        self.assertEqual(er.detect_problem(pd.Series(np.linspace(0, 1, 100))), 'regression')
        self.assertEqual(er.detect_problem(pd.Series([1, 2]), forced='regression'), 'regression')

    def test_classification_report(self):
        rng = np.random.RandomState(1)
        df = pd.DataFrame({'x': np.r_[rng.normal(0, 1, 100), rng.normal(10, 1, 100)],
                           'ruido': rng.normal(0, 1, 200),
                           'y': ['A'] * 100 + ['B'] * 100})
        bundle, report, _m = er.train_model(df, 'y', ['x', 'ruido'])
        self.assertEqual(bundle['problem'], 'classification')
        self.assertEqual(bundle['classes'], ['A', 'B'])
        metrics = dict(zip(report[report.section == 'metric'].name, report[report.section == 'metric'].value))
        self.assertGreater(metrics['accuracy'], 0.95)
        imp = report[report.section == 'importance']
        self.assertEqual(imp.iloc[0]['name'], 'x')  # ordenadas de mayor a menor
        self.assertEqual(len(report[report.section == 'class_balance']), 2)

    def test_regression(self):
        rng = np.random.RandomState(2)
        x = rng.uniform(0, 10, 300)
        df = pd.DataFrame({'x': x, 'y': 3 * x + rng.normal(0, 0.1, 300)})
        bundle, report, _m = er.train_model(df, 'y', ['x'])
        self.assertEqual(bundle['problem'], 'regression')
        r2 = report[report.name == 'r2'].value.iloc[0]
        self.assertGreater(r2, 0.9)

    def test_null_target_rows_are_ignored(self):
        df = pd.DataFrame({'x': list(range(40)), 'y': ['A'] * 20 + ['B'] * 15 + [None] * 5})
        _, report, _m = er.train_model(df, 'y', ['x'])
        self.assertEqual(report[(report.section == 'training') & (report.name == 'rows')].value.iloc[0], 35)

    def test_text_feature_is_reported_by_name(self):
        df = pd.DataFrame({'x': range(30), 'texto': ['a', 'b', 'c'] * 10, 'y': ['A', 'B'] * 15})
        with self.assertRaisesRegex(ValueError, 'texto.*no es numérica'):
            er.train_model(df, 'y', ['x', 'texto'])

    def test_validation_errors(self):
        df = pd.DataFrame({'x': range(30), 'y': ['A'] * 30})
        with self.assertRaisesRegex(ValueError, '2 clases'):
            er.train_model(df, 'y', ['x'])
        with self.assertRaisesRegex(ValueError, 'no existe'):
            er.train_model(df, 'zzz', ['x'])
        with self.assertRaisesRegex(ValueError, 'al menos una variable'):
            er.train_model(df, 'y', ['y'])
        with self.assertRaisesRegex(ValueError, 'al menos'):
            er.train_model(df.head(4), 'y', ['x'])


class RasterTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio / geopandas / scikit-learn')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.tif = os.path.join(self.tmp, 'in.tif')
        write_raster(self.tif, nodata_pixel=True)

    def test_sample_pixels(self):
        df = er.sample_raster_pixels(self.tif, samples_gdf(), 'clase', band_names=['r', 'g', 'ir'])
        self.assertEqual(list(df.columns), ['r', 'g', 'ir', 'clase', er.AUX_X, er.AUX_Y, er.AUX_POLY])
        self.assertEqual(sorted(df[er.AUX_POLY].unique()), [0, 1, 2, 3])
        # x,y son el centro del píxel (CRS del ráster) y caen dentro de su polígono
        first = df[df[er.AUX_POLY] == 0]
        self.assertTrue(first[er.AUX_X].between(2, 12).all() and first[er.AUX_Y].between(2, 12).all())
        self.assertEqual(first[er.AUX_X].iloc[0] % 1, 0.5)
        self.assertEqual(len(df), 4 * 100)
        self.assertEqual(df['clase'].value_counts().to_dict(), {'A': 200, 'B': 200})
        self.assertLess(df[df.clase == 'A']['r'].mean(), 100)

    def test_sample_limit_per_class(self):
        df = er.sample_raster_pixels(self.tif, samples_gdf(), 'clase', max_per_class=50)
        self.assertEqual(df['clase'].value_counts().to_dict(), {'A': 50, 'B': 50})

    def test_sample_reprojects_samples(self):
        gdf = samples_gdf().to_crs('EPSG:4326')
        df = er.sample_raster_pixels(self.tif, gdf, 'clase')
        self.assertGreater(len(df), 350)

    def test_sample_errors(self):
        with self.assertRaisesRegex(ValueError, 'columna de clase'):
            er.sample_raster_pixels(self.tif, samples_gdf(), 'otra')
        lejos = gpd.GeoDataFrame({'clase': ['A']}, geometry=[box(5000, 5000, 5010, 5010)], crs=CRS)
        with self.assertRaisesRegex(ValueError, 'Ningún polígono'):
            er.sample_raster_pixels(self.tif, lejos, 'clase')

    def test_train_and_predict_raster(self):
        names = ['r', 'g', 'ir']
        er.write_meta(self.tif, {'band_names': names})
        df = er.sample_raster_pixels(self.tif, samples_gdf(), 'clase', band_names=names)
        bundle, _, _m = er.train_model(df, 'clase', names)

        out = os.path.join(self.tmp, 'out.tif')
        class_map = er.predict_raster_file(self.tif, bundle, out, block=16)  # bloques parciales
        self.assertEqual(class_map, {'1': 'A', '2': 'B'})
        self.assertEqual(er.read_meta(out)['class_map'], class_map)

        with rasterio.open(out) as dst:
            res = dst.read(1)
            self.assertEqual(dst.dtypes[0], 'uint16')
            self.assertEqual(dst.crs.to_string(), CRS)
        self.assertEqual(res[0, 0], 0)  # pixel nodata de entrada -> sin dato
        self.assertTrue((res[5:35, :18] == 1).all())
        self.assertTrue((res[5:35, 22:] == 2).all())

    def test_predict_regression_raster(self):
        names = ['r', 'g', 'ir']
        er.write_meta(self.tif, {'band_names': names})
        df = pd.DataFrame({'r': np.linspace(0, 255, 200), 'g': np.linspace(0, 255, 200),
                           'ir': np.linspace(0, 255, 200)})
        df['valor'] = df['r'] * 2.0
        bundle, _, _m = er.train_model(df, 'valor', names, problem='regression')
        out = os.path.join(self.tmp, 'reg.tif')
        self.assertEqual(er.predict_raster_file(self.tif, bundle, out), {})
        with rasterio.open(out) as dst:
            res = dst.read(1)
            self.assertEqual(dst.dtypes[0], 'float32')
        self.assertEqual(res[0, 0], er.REGRESSION_NODATA)
        self.assertLess(res[20, 5], res[20, 35])

    def test_confidence_raster_classification(self):
        names = ['r', 'g', 'ir']
        er.write_meta(self.tif, {'band_names': names})
        df = er.sample_raster_pixels(self.tif, samples_gdf(), 'clase', band_names=names)
        bundle, _, _m = er.train_model(df, 'clase', names)
        out, conf = os.path.join(self.tmp, 'out.tif'), os.path.join(self.tmp, 'conf.tif')
        er.predict_raster_file(self.tif, bundle, out, block=16, confidence_path=conf)
        with rasterio.open(conf) as src:
            c = src.read(1)
            self.assertEqual(src.dtypes[0], 'float32')
            self.assertEqual(src.nodata, er.REGRESSION_NODATA)
        with rasterio.open(out) as src:
            classes = src.read(1)
        self.assertEqual(c[0, 0], er.REGRESSION_NODATA)          # sin dato donde la clasificación no tiene
        valid = classes != 0
        self.assertTrue(((c[valid] >= 0) & (c[valid] <= 1)).all())
        self.assertGreater(c[5:35, :18].mean(), 0.95)             # zonas puras: confianza alta
        self.assertEqual(er.read_meta(conf)['kind'], 'confidence')
        self.assertNotIn('class_map', er.read_meta(conf))         # no se puede poligonizar por error

    def test_confidence_does_not_change_the_prediction(self):
        names = ['r', 'g', 'ir']
        er.write_meta(self.tif, {'band_names': names})
        df = er.sample_raster_pixels(self.tif, samples_gdf(), 'clase', band_names=names)
        bundle, _, _m = er.train_model(df, 'clase', names)
        a, b = os.path.join(self.tmp, 'a.tif'), os.path.join(self.tmp, 'b.tif')
        er.predict_raster_file(self.tif, bundle, a)
        er.predict_raster_file(self.tif, bundle, b, confidence_path=os.path.join(self.tmp, 'c.tif'))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'a_conf.tif')))
        with rasterio.open(a) as x, rasterio.open(b) as y:
            self.assertTrue((x.read(1) == y.read(1)).all())

    def test_uncertainty_raster_regression(self):
        names = ['r', 'g', 'ir']
        er.write_meta(self.tif, {'band_names': names})
        rng = np.random.RandomState(4)
        df = pd.DataFrame({'r': rng.uniform(0, 255, 300)})
        df['g'], df['ir'] = df['r'], df['r']
        df['valor'] = df['r'] * 2.0 + rng.normal(0, 5, 300)
        bundle, _, _m = er.train_model(df, 'valor', names, problem='regression')
        out, unc = os.path.join(self.tmp, 'reg.tif'), os.path.join(self.tmp, 'unc.tif')
        er.predict_raster_file(self.tif, bundle, out, confidence_path=unc)
        plain = os.path.join(self.tmp, 'plain.tif')
        er.predict_raster_file(self.tif, bundle, plain)
        with rasterio.open(unc) as src:
            u = src.read(1)
        with rasterio.open(out) as a, rasterio.open(plain) as b:
            np.testing.assert_allclose(a.read(1), b.read(1), rtol=1e-4)   # misma predicción
        self.assertEqual(u[0, 0], er.REGRESSION_NODATA)
        self.assertTrue((u[u != er.REGRESSION_NODATA] >= 0).all())
        self.assertEqual(er.read_meta(unc)['kind'], 'uncertainty')

    def test_predict_requires_same_bands(self):
        er.write_meta(self.tif, {'band_names': ['r', 'g', 'ir']})
        df = pd.DataFrame({'otra': np.arange(40.0), 'y': ['A', 'B'] * 20})
        bundle, _, _m = er.train_model(df, 'y', ['otra'])
        with self.assertRaisesRegex(ValueError, 'no tiene las bandas'):
            er.predict_raster_file(self.tif, bundle, os.path.join(self.tmp, 'x.tif'))

    def test_input_raster_node(self):
        with override_settings(FILEMANAGER_DIRECTORY=self.tmp):
            res = er.input_Raster({'id': 'n1', 'raster-file': 'file://' + self.tif,
                                   'band-names': 'Rojo,Verde,IR'})
        try:
            self.assertEqual(len(res), 1)
            self.assertTrue(er.is_raster_ref(res[0]))
            self.assertEqual(er.read_meta(res[0])['band_names'], ['rojo', 'verde', 'ir'])
            with rasterio.open(res[0]) as src:
                self.assertEqual(src.count, 3)
        finally:
            for p in (res[0], er.meta_path(res[0])):
                if os.path.lexists(p):
                    os.remove(p)

    def test_input_raster_rejects_other_files(self):
        txt = os.path.join(self.tmp, 'a.txt')
        open(txt, 'w').close()
        with override_settings(FILEMANAGER_DIRECTORY=self.tmp):
            with self.assertRaisesRegex(ValueError, 'GeoTIFF'):
                er.input_Raster({'id': 'n1', 'raster-file': txt})
            with self.assertRaisesRegex(ValueError, 'No se encuentra'):
                er.input_Raster({'id': 'n1', 'raster-file': os.path.join(self.tmp, 'no.tif')})
            with self.assertRaisesRegex(ValueError, 'Selecciona'):
                er.input_Raster({'id': 'n1', 'raster-file': ''})

    def test_raster_path_must_be_inside_file_manager(self):
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        outside = os.path.join(other, 'fuera.tif')
        shutil.copyfile(self.tif, outside)
        with override_settings(FILEMANAGER_DIRECTORY=self.tmp):
            with self.assertRaisesRegex(ValueError, 'gestor de ficheros'):
                er.resolve_raster_path(outside)
            # los enlaces simbólicos que escapan del directorio también se rechazan
            link = os.path.join(self.tmp, 'enlace.tif')
            os.symlink(outside, link)
            with self.assertRaisesRegex(ValueError, 'gestor de ficheros'):
                er.resolve_raster_path(link)
            # y los intentos de salir con ..
            with self.assertRaisesRegex(ValueError, 'gestor de ficheros'):
                er.resolve_raster_path(os.path.join(self.tmp, '..', os.path.basename(other), 'fuera.tif'))

    def test_raster_schema_for_dialog(self):
        with override_settings(FILEMANAGER_DIRECTORY=self.tmp):
            info = er.raster_schema({'raster-file': 'file://' + self.tif, 'band-names': 'Rojo, Verde'})
        self.assertEqual(info['bands'], ['rojo', 'verde', 'b3'])
        self.assertEqual(info['crs'], CRS)
        self.assertEqual((info['width'], info['height']), (SIZE, SIZE))

class PolygonizeTest(SimpleTestCase):
    """Ráster clasificado sintético 20x20: clase 1 (izq.), clase 2 (der.), un píxel suelto de clase 2 y nodata."""

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio / geopandas / scikit-learn')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.tif = os.path.join(self.tmp, 'cls.tif')
        arr = np.zeros((20, 20), dtype='uint16')
        arr[:, :10] = 1
        arr[:, 10:] = 2
        arr[3, 3] = 2          # píxel suelto de clase 2 dentro de la clase 1
        arr[0, 0] = 0          # sin dato
        with rasterio.open(self.tif, 'w', driver='GTiff', height=20, width=20, count=1, dtype='uint16',
                           crs=CRS, transform=from_origin(0, 20, 1, 1), nodata=0) as dst:
            dst.write(arr, 1)
        er.write_meta(self.tif, {'problem': 'classification', 'class_map': {'1': 'A', '2': 'B'}})

    def test_all_classes(self):
        gdf = er.polygonize_raster_file(self.tif)
        self.assertEqual(sorted(gdf.class_name.unique()), ['A', 'B'])
        self.assertEqual(gdf.crs.to_epsg(), 25830)
        # El área total es la de todos los píxeles válidos (400 - 1 nodata)
        self.assertAlmostEqual(gdf.area.sum(), 399.0)
        self.assertEqual(len(gdf[gdf.class_name == 'B']), 2)  # bloque + píxel suelto

    def test_filter_class_and_min_area(self):
        gdf = er.polygonize_raster_file(self.tif, classes=['B'], min_area=2)
        self.assertEqual(list(gdf.class_name), ['B'])          # el píxel suelto (1 m2) se descarta
        self.assertAlmostEqual(gdf.area.iloc[0], 200.0)

    def test_simplify_keeps_valid_geometry(self):
        gdf = er.polygonize_raster_file(self.tif, simplify=0.5)
        self.assertTrue(gdf.is_valid.all())

    def test_errors(self):
        with self.assertRaisesRegex(ValueError, 'no existen'):
            er.polygonize_raster_file(self.tif, classes=['Z'])
        with self.assertRaisesRegex(ValueError, 'conectividad'):
            er.polygonize_raster_file(self.tif, connectivity=6)
        reg = os.path.join(self.tmp, 'reg.tif')
        shutil.copyfile(self.tif, reg)
        er.write_meta(reg, {'problem': 'regression', 'class_map': {}})
        with self.assertRaisesRegex(ValueError, 'regresión'):
            er.polygonize_raster_file(reg)

    def test_empty_result_has_columns(self):
        gdf = er.polygonize_raster_file(self.tif, min_area=10000)
        self.assertEqual(len(gdf), 0)
        self.assertEqual(list(gdf.columns), ['class_name', 'class_code', 'area', 'geometry'])



def clustered_frame(per_polygon=100, polygons=8, seed=3):
    """
    Muestras con autocorrelación: el valor de la variable lo fija el polígono y no la clase,
    así que un modelo que memoriza polígonos acierta al validar al azar y falla por zonas.
    """
    rng = np.random.RandomState(seed)
    rows = []
    for poly in range(polygons):
        level = rng.uniform(0, 100)
        cx, cy = (poly % 4) * 50.0, (poly // 4) * 50.0
        for k in range(per_polygon):
            rows.append({'v': level + rng.normal(0, 0.05), 'clase': 'A' if poly % 2 == 0 else 'B',
                         er.AUX_X: cx + (k % 10), er.AUX_Y: cy + (k // 10), er.AUX_POLY: poly})
    return pd.DataFrame(rows)


class ReportTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan scikit-learn')

    @staticmethod
    def metric(report, section, name):
        return float(report[(report.section == section) & (report.name == name)].value.iloc[0])

    def test_confusion_matrix_and_per_class_metrics(self):
        rng = np.random.RandomState(1)
        df = pd.DataFrame({'x': np.r_[rng.normal(0, 1, 100), rng.normal(10, 1, 100)],
                           'y': ['Agua'] * 100 + ['Suelo'] * 100})
        _, report, matrix = er.train_model(df, 'y', ['x'])
        # tabla ancha: una fila por clase real, una columna por clase predicha
        self.assertEqual(list(matrix.columns), ['real', 'pred_agua', 'pred_suelo', 'total', 'recall'])
        self.assertEqual(list(matrix['real']), ['Agua', 'Suelo'])
        self.assertEqual(int(matrix['total'].sum()), int(self.metric(report, 'training', 'test_rows')))
        self.assertGreater(matrix.loc[0, 'pred_agua'], matrix.loc[0, 'pred_suelo'])
        self.assertGreater(matrix.loc[0, 'recall'], 0.9)
        # el informe lleva lo mismo en formato largo
        self.assertEqual(self.metric(report, 'confusion', 'Agua -> Agua'), matrix.loc[0, 'pred_agua'])
        for key in ('precision', 'recall', 'f1', 'support'):
            self.assertEqual(len(report[(report.section == 'per_class') & report.name.str.endswith(':' + key)]), 2)
        self.assertGreater(self.metric(report, 'metric', 'kappa'), 0.8)
        self.assertIn('balanced_accuracy', set(report.name))
        self.assertIn('Clase peor clasificada', er.summarize_report(report))

    def test_confusion_matrix_values_are_exact(self):
        # Con la validación cruzada por polígono todas las filas se evalúan una vez
        df = clustered_frame(per_polygon=40)
        _, report, matrix = er.train_model(df, 'clase', ['v'], validation='polygon', folds=4)
        self.assertEqual(int(matrix['total'].sum()), len(df))
        pred_cols = [c for c in matrix.columns if c.startswith('pred_')]
        self.assertEqual(int(matrix[pred_cols].to_numpy().sum()), len(df))

    def test_no_evaluation_gives_empty_matrix(self):
        df = pd.DataFrame({'x': np.arange(40.0), 'y': ['A', 'B'] * 20})
        _, report, matrix = er.train_model(df, 'y', ['x'], test_percent=0)
        self.assertEqual(len(matrix), 0)
        self.assertEqual(list(matrix.columns), ['real', 'pred_a', 'pred_b', 'total', 'recall'])
        self.assertNotIn('accuracy', set(report.name))

    def test_regression_matrix_has_metrics(self):
        rng = np.random.RandomState(2)
        x = rng.uniform(0, 10, 300)
        df = pd.DataFrame({'x': x, 'y': 3 * x + rng.normal(0, 0.1, 300)})
        _, report, matrix = er.train_model(df, 'y', ['x'])
        self.assertEqual(list(matrix['metric']), ['r2', 'rmse', 'mae'])
        self.assertIn('mae', set(report.name))

    def test_aux_columns_are_never_features(self):
        df = clustered_frame()
        bundle, _, _m = er.train_model(df, 'clase', ['v', er.AUX_X, er.AUX_Y, er.AUX_POLY])
        self.assertEqual(bundle['features'], ['v'])


class SpatialValidationTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan scikit-learn')

    @staticmethod
    def accuracy(report):
        return float(report[(report.section == 'metric') & (report.name == 'accuracy')].value.iloc[0])

    def test_spatial_validation_is_more_pessimistic_than_random(self):
        df = clustered_frame()
        _, rnd, _m = er.train_model(df, 'clase', ['v'])
        _, poly, _m = er.train_model(df, 'clase', ['v'], validation='polygon', folds=4)
        _, block, _m = er.train_model(df, 'clase', ['v'], validation='block', folds=4, block_size=50)
        self.assertGreater(self.accuracy(rnd), 0.9)
        self.assertLess(self.accuracy(poly), 0.8)
        self.assertLess(self.accuracy(block), 0.8)

    def test_report_describes_the_folds(self):
        df = clustered_frame()
        _, report, _m = er.train_model(df, 'clase', ['v'], validation='polygon', folds=4)
        self.assertEqual(len(report[report.section == 'fold']), 4)
        row = lambda n: float(report[(report.section == 'training') & (report.name == n)].value.iloc[0])
        self.assertEqual(row('folds'), 4)
        self.assertEqual(row('groups'), 8)
        self.assertEqual(row('test_rows'), len(df))
        self.assertIn('fold_score_std', set(report.name))

    def test_folds_are_limited_by_number_of_groups(self):
        df = clustered_frame(polygons=4)
        _, report, _m = er.train_model(df, 'clase', ['v'], validation='polygon', folds=10)
        self.assertEqual(float(report[(report.section == 'training') & (report.name == 'folds')].value.iloc[0]), 4)

    def test_class_with_a_single_polygon_is_explained(self):
        df = clustered_frame(polygons=3)  # clase B solo en el polígono 1
        with self.assertRaisesRegex(ValueError, 'clase "B" solo tiene muestras en 1'):
            er.train_model(df, 'clase', ['v'], validation='polygon')

    def test_single_block_is_explained(self):
        df = clustered_frame()
        with self.assertRaisesRegex(ValueError, 'Solo hay 1 bloques'):
            er.train_model(df, 'clase', ['v'], validation='block', block_size=100000)

    def test_missing_aux_columns_and_bad_block_size(self):
        df = clustered_frame().drop(columns=[er.AUX_POLY])
        with self.assertRaisesRegex(ValueError, 'Muestrear ráster'):
            er.train_model(df, 'clase', ['v'], validation='polygon')
        df = clustered_frame().drop(columns=[er.AUX_X])
        with self.assertRaisesRegex(ValueError, 'coordenadas'):
            er.train_model(df, 'clase', ['v'], validation='block', block_size=10)
        with self.assertRaisesRegex(ValueError, 'tamaño del bloque'):
            er.train_model(clustered_frame(), 'clase', ['v'], validation='block', block_size=0)
        with self.assertRaisesRegex(ValueError, 'desconocido'):
            er.train_model(clustered_frame(), 'clase', ['v'], validation='otra')

    def test_regression_with_polygon_validation(self):
        df = clustered_frame()
        df['valor'] = df['v'] * 2
        _, report, matrix = er.train_model(df, 'valor', ['v'], problem='regression',
                                           validation='polygon', folds=4)
        self.assertIn('r2', set(report.name))
        self.assertEqual(list(matrix['metric']), ['r2', 'rmse', 'mae'])


def write_classified(path, array, class_map=None):
    """Ráster clasificado sintético (uint16, 0 = sin dato) con su .meta.json."""
    array = np.asarray(array, dtype='uint16')
    with rasterio.open(path, 'w', driver='GTiff', height=array.shape[0], width=array.shape[1], count=1,
                       dtype='uint16', crs=CRS, transform=from_origin(0, array.shape[0], 1, 1), nodata=0) as dst:
        dst.write(array, 1)
    er.write_meta(path, {'problem': 'classification', 'class_map': class_map or {'1': 'A', '2': 'B'}})


def read_band(path, band=1):
    with rasterio.open(path) as src:
        return src.read(band)


class MajorityFilterTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio / scipy')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, 'cls.tif')
        self.out = os.path.join(self.tmp, 'out.tif')

    def test_isolated_pixel_is_removed(self):
        a = np.ones((20, 20))
        a[10, 10] = 2
        write_classified(self.src, a)
        er.majority_filter_file(self.src, self.out, size=3)
        self.assertTrue((read_band(self.out) == 1).all())

    def test_straight_edge_does_not_move(self):
        a = np.ones((20, 20))
        a[:, 10:] = 2
        write_classified(self.src, a)
        er.majority_filter_file(self.src, self.out, size=5, iterations=3)
        self.assertTrue((read_band(self.out) == a).all())

    def test_nodata_is_kept_and_not_filled(self):
        a = np.ones((20, 20))
        a[:5, :] = 0
        a[10, 10] = 0
        write_classified(self.src, a)
        er.majority_filter_file(self.src, self.out, size=3)
        res = read_band(self.out)
        self.assertTrue((res[:5, :] == 0).all())
        self.assertEqual(res[10, 10], 0)
        self.assertEqual(res[12, 12], 1)

    def test_result_does_not_depend_on_block_size(self):
        rng = np.random.RandomState(7)
        a = rng.randint(1, 4, (61, 73))
        a[rng.rand(61, 73) < 0.05] = 0
        write_classified(self.src, a, {'1': 'A', '2': 'B', '3': 'C'})
        er.majority_filter_file(self.src, self.out, size=5, iterations=2, block=16)
        other = os.path.join(self.tmp, 'big.tif')
        er.majority_filter_file(self.src, other, size=5, iterations=2, block=1000)
        self.assertTrue((read_band(self.out) == read_band(other)).all())

    def test_tie_keeps_own_class(self):
        a = np.array([[1, 2]] * 2)   # cada píxel ve 2 y 2 en la ventana: empate
        write_classified(self.src, a)
        er.majority_filter_file(self.src, self.out, size=3)
        self.assertTrue((read_band(self.out) == a).all())

    def test_validation(self):
        write_classified(self.src, np.ones((10, 10)))
        with self.assertRaisesRegex(ValueError, 'ventana'):
            er.majority_filter_file(self.src, self.out, size=4)
        with self.assertRaisesRegex(ValueError, 'repeticiones'):
            er.majority_filter_file(self.src, self.out, iterations=0)
        multi = os.path.join(self.tmp, 'multi.tif')
        write_raster(multi)
        with self.assertRaisesRegex(ValueError, 'una banda'):
            er.majority_filter_file(multi, self.out)

    def test_sieve_removes_small_patches_only(self):
        a = np.ones((30, 30))
        a[5:7, 5:7] = 2          # 4 píxeles
        a[15:25, 15:25] = 2      # 100 píxeles
        a[0, :] = 0
        write_classified(self.src, a)
        er.sieve_file(self.src, self.out, min_pixels=10)
        res = read_band(self.out)
        self.assertTrue((res[5:7, 5:7] == 1).all())
        self.assertTrue((res[15:25, 15:25] == 2).all())
        self.assertTrue((res[0, :] == 0).all())
        with self.assertRaisesRegex(ValueError, 'al menos 2'):
            er.sieve_file(self.src, self.out, min_pixels=1)
        with self.assertRaisesRegex(ValueError, 'conectividad'):
            er.sieve_file(self.src, self.out, min_pixels=4, connectivity=6)

    def test_node_keeps_class_map_and_requires_classification(self):
        a = np.ones((20, 20))
        a[10, 10] = 2
        write_classified(self.src, a, {'1': 'Agua', '2': 'Suelo'})
        res = er.trans_RasterMajority({'id': 'zzmaj', 'data': [self.src], 'mode': 'majority',
                                       'window': '3', 'iterations': '1'})
        try:
            self.assertTrue((read_band(res[0]) == 1).all())
            self.assertEqual(er.read_meta(res[0])['class_map'], {'1': 'Agua', '2': 'Suelo'})
        finally:
            er.remove_artifact(res[0])
        plain = os.path.join(self.tmp, 'plain.tif')
        write_raster(plain)
        with self.assertRaisesRegex(Exception, 'clasificado'):
            er.trans_RasterMajority({'id': 'zzmaj', 'data': [plain]})
        with self.assertRaisesRegex(Exception, 'Conecta'):
            er.trans_RasterMajority({'id': 'zzmaj', 'data': []})
        sieve = er.trans_RasterMajority({'id': 'zzmaj', 'data': [self.src], 'mode': 'sieve', 'min-pixels': '4'})
        try:
            self.assertTrue((read_band(sieve[0]) == 1).all())
        finally:
            er.remove_artifact(sieve[0])


class SpectralIndexTest(SimpleTestCase):

    NAMES = ['azul', 'verde', 'rojo', 'ir', 'swir']

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, 'in.tif')
        self.out = os.path.join(self.tmp, 'out.tif')
        data = np.zeros((5, 4, 4), dtype='float32')
        data[0], data[1], data[2], data[3], data[4] = 10, 20, 50, 150, 100
        data[:, 0, 0] = -9999          # nodata
        data[2:4, 1, 1] = 0            # rojo + ir = 0 -> división entre cero
        with rasterio.open(self.src, 'w', driver='GTiff', height=4, width=4, count=5, dtype='float32',
                           crs=CRS, transform=from_origin(0, 4, 1, 1), nodata=-9999) as dst:
            dst.write(data)

    def add(self, index, selected, **kw):
        return er.add_index_file(self.src, self.out, index, self.NAMES, selected, **kw)

    def test_ndvi(self):
        names = self.add('ndvi', ['ir', 'rojo'])
        self.assertEqual(names, self.NAMES + ['ndvi'])
        with rasterio.open(self.out) as src:
            self.assertEqual(src.count, 6)
            self.assertEqual(src.dtypes[0], 'float32')
            self.assertEqual(src.nodata, er.REGRESSION_NODATA)
        ndvi = read_band(self.out, 6)
        self.assertAlmostEqual(float(ndvi[2, 2]), (150 - 50) / (150 + 50), places=5)
        self.assertEqual(ndvi[0, 0], er.REGRESSION_NODATA)        # nodata de entrada
        self.assertEqual(ndvi[1, 1], er.REGRESSION_NODATA)        # divisor 0
        self.assertEqual(read_band(self.out, 3)[2, 2], 50)        # las bandas originales no cambian
        self.assertEqual(read_band(self.out, 3)[0, 0], er.REGRESSION_NODATA)

    def test_other_indices(self):
        ndwi = (lambda: (self.add('ndwi', ['verde', 'ir']), read_band(self.out, 6))[1])()
        self.assertAlmostEqual(float(ndwi[2, 2]), (20 - 150) / (20 + 150), places=5)
        self.add('ndbi', ['swir', 'ir'])
        self.assertAlmostEqual(float(read_band(self.out, 6)[2, 2]), (100 - 150) / (100 + 150), places=5)
        self.add('nd', ['ir', 'azul'], output_name='mi indice')
        self.assertEqual(er.parse_band_names(self.NAMES + ['mi indice'], 6)[-1], 'mi_indice')
        self.assertAlmostEqual(float(read_band(self.out, 6)[2, 2]), (150 - 10) / (150 + 10), places=5)
        self.add('brightness', [])
        self.assertAlmostEqual(float(read_band(self.out, 6)[2, 2]), (10 + 20 + 50 + 150 + 100) / 5.0, places=4)

    def test_savi_and_evi_use_the_reflectance_scale(self):
        self.add('savi', ['ir', 'rojo'], scale=1000.0, savi_l=0.5)
        nir, red = 0.150, 0.050
        self.assertAlmostEqual(float(read_band(self.out, 6)[2, 2]), 1.5 * (nir - red) / (nir + red + 0.5), places=5)
        self.add('evi', ['ir', 'rojo', 'azul'], scale=1000.0)
        blue = 0.010
        self.assertAlmostEqual(float(read_band(self.out, 6)[2, 2]),
                               2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1), places=5)

    def test_output_name_is_made_unique(self):
        names = self.add('ndvi', ['ir', 'rojo'], output_name='rojo')
        self.assertEqual(names[-1], 'rojo_2')

    def test_errors(self):
        with self.assertRaisesRegex(ValueError, 'desconocido'):
            self.add('xx', [])
        with self.assertRaisesRegex(ValueError, 'papel'):
            self.add('ndvi', ['ir'])
        with self.assertRaisesRegex(ValueError, 'no tiene las bandas: nope'):
            self.add('ndvi', ['ir', 'nope'])
        with self.assertRaisesRegex(ValueError, 'escala'):
            self.add('savi', ['ir', 'rojo'], scale=0)

    def test_result_does_not_depend_on_block_size(self):
        self.add('ndvi', ['ir', 'rojo'], block=3)
        small = read_band(self.out, 6)
        self.add('ndvi', ['ir', 'rojo'], block=512)
        self.assertTrue((small == read_band(self.out, 6)).all())

    def test_node_propagates_band_names_to_the_model(self):
        er.write_meta(self.src, {'band_names': self.NAMES, 'crs': CRS})
        res = er.trans_RasterIndex({'id': 'zzidx', 'data': [self.src], 'index': 'ndvi',
                                    'band-1': 'ir', 'band-2': 'rojo', 'name': 'NDVI'})
        try:
            self.assertEqual(er.read_meta(res[0])['band_names'], self.NAMES + ['ndvi'])
            with self.assertRaisesRegex(Exception, 'Elige'):
                er.trans_RasterIndex({'id': 'zzidx', 'data': [self.src]})
            with self.assertRaisesRegex(Exception, 'Conecta'):
                er.trans_RasterIndex({'id': 'zzidx', 'data': [], 'index': 'ndvi'})
        finally:
            er.remove_artifact(res[0])


class PublishStyleTest(SimpleTestCase):
    """Estilo del ráster publicado: clases, rampa de valores o rampa 0-1 para la confianza."""

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        from gvsigol_plugin_geoetl import etl_raster_publish as pub
        self.pub = pub
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def float_raster(self, name, values, meta):
        path = os.path.join(self.tmp, name)
        with rasterio.open(path, 'w', driver='GTiff', height=1, width=len(values), count=1, dtype='float32',
                           crs=CRS, transform=from_origin(0, 1, 1, 1), nodata=er.REGRESSION_NODATA) as dst:
            dst.write(np.array([values], dtype='float32'), 1)
        er.write_meta(path, meta)
        return path

    @staticmethod
    def quantities(json_data):
        import json
        return [json.loads(e['json'])['quantity'] for e in json_data['entries']]

    def test_confidence_uses_the_full_0_1_scale(self):
        path = self.float_raster('c.tif', [0.9, 1.0, er.REGRESSION_NODATA], {'kind': 'confidence'})
        data, kind = self.pub.build_style_json('s', 't', path)
        self.assertEqual(kind, 'ramp')
        self.assertEqual(self.quantities(data), [0.0, 1.0])

    def test_uncertainty_and_regression_use_the_data_range(self):
        path = self.float_raster('u.tif', [2.0, 8.0, er.REGRESSION_NODATA], {'kind': 'uncertainty'})
        data, _ = self.pub.build_style_json('s', 't', path)
        self.assertEqual(self.quantities(data), [2.0, 8.0])

    def test_classified_raster_gets_one_entry_per_class(self):
        path = os.path.join(self.tmp, 'cls.tif')
        write_classified(path, np.ones((4, 4)), {'1': 'Agua', '2': 'Suelo'})
        data, kind = self.pub.build_style_json('s', 't', path)
        self.assertEqual(kind, 'values')
        self.assertEqual(self.quantities(data), [1, 2])


def blocky_classification(path, height=60, width=50, seed=5, classes=3, nodata_fraction=0.03):
    """Clasificación con manchas de tamaños muy distintos (varias cruzan cualquier costura)."""
    rng = np.random.RandomState(seed)
    small = rng.randint(1, classes + 1, (height // 6 + 1, width // 5 + 1))
    a = np.kron(small, np.ones((6, 5), dtype=int))[:height, :width]
    noise = rng.rand(height, width) < 0.04
    a[noise] = rng.randint(1, classes + 1, noise.sum())
    a[rng.rand(height, width) < nodata_fraction] = 0
    write_classified(path, a, {str(i): 'C%d' % i for i in range(1, classes + 1)})
    return a


class StripPolygonizeTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio / geopandas')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, 'cls.tif')

    @staticmethod
    def dissolved(gdf):
        from shapely.ops import unary_union
        return {name: unary_union(list(g.geometry)) for name, g in gdf.groupby('class_name')}

    def test_strips_give_the_same_polygons_as_one_pass(self):
        blocky_classification(self.src)
        whole = er.polygonize_raster_file(self.src)                       # una sola franja
        for strip_rows in (1, 2, 7, 13):
            strips = er.polygonize_raster_file(self.src, strip_pixels=50 * strip_rows)
            self.assertEqual(len(whole), len(strips), 'franjas de %d filas' % strip_rows)
            a, b = self.dissolved(whole), self.dissolved(strips)
            self.assertEqual(sorted(a), sorted(b))
            for name in a:
                self.assertAlmostEqual(a[name].symmetric_difference(b[name]).area, 0, places=6, msg=name)
            self.assertAlmostEqual(whole.area.sum(), strips.area.sum(), places=6)

    def test_a_large_patch_crossing_seams_is_a_single_polygon(self):
        a = np.ones((40, 10), dtype=int)
        a[:, 4] = 2                                   # banda vertical que atraviesa todas las costuras
        write_classified(self.src, a)
        gdf = er.polygonize_raster_file(self.src, strip_pixels=10 * 3)    # franjas de 3 filas
        self.assertEqual(int((gdf.class_name == 'B').sum()), 1)
        self.assertEqual(float(gdf[gdf.class_name == 'B'].area.iloc[0]), 40.0)
        self.assertEqual(int((gdf.class_name == 'A').sum()), 2)

    def test_holes_crossing_a_seam_are_kept(self):
        a = np.ones((12, 12), dtype=int)
        a[5:7, 5:7] = 2                               # hueco de otra clase justo en la costura (fila 6)
        write_classified(self.src, a)
        strips = er.polygonize_raster_file(self.src, strip_pixels=12 * 6)
        whole = er.polygonize_raster_file(self.src)
        self.assertEqual(len(strips), len(whole))
        outer = strips[strips.class_name == 'A'].geometry.iloc[0]
        self.assertEqual(len(outer.interiors), 1)
        self.assertEqual(float(outer.area), 144.0 - 4.0)

    def test_filters_apply_after_merging(self):
        a = np.ones((20, 10), dtype=int)
        a[8:12, 0:2] = 2                              # 2x4 = 8 píxeles, partido en dos por la costura de la fila 10
        write_classified(self.src, a)
        gdf = er.polygonize_raster_file(self.src, classes=['B'], min_area=6, strip_pixels=10 * 10)
        self.assertEqual(len(gdf), 1)                 # cada mitad (4 px) sola no llegaría a 6
        self.assertEqual(float(gdf.area.iloc[0]), 8.0)
        self.assertEqual(len(er.polygonize_raster_file(self.src, classes=['B'], min_area=9, strip_pixels=100)), 0)

    def test_chunks_and_streaming(self):
        blocky_classification(self.src)
        chunks = list(er.iter_polygon_chunks(self.src, chunk_size=10, strip_pixels=50 * 5))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 10 for c in chunks))
        self.assertEqual(sum(len(c) for c in chunks), len(er.polygonize_raster_file(self.src)))
        self.assertTrue(all(r['geometry'].geom_type == 'Polygon' for c in chunks for r in c))

    def test_simplify_keeps_only_polygons(self):
        blocky_classification(self.src)
        gdf = er.polygonize_raster_file(self.src, simplify=0.5, strip_pixels=50 * 7)
        self.assertTrue((gdf.geometry.geom_type == 'Polygon').all())
        self.assertTrue(gdf.geometry.is_valid.all())

    def test_rotated_raster_is_processed_in_one_pass(self):
        from affine import Affine
        a = np.ones((20, 10), dtype='uint16')
        a[3:6, 2:4] = 2
        with rasterio.open(self.src, 'w', driver='GTiff', height=20, width=10, count=1, dtype='uint16', crs=CRS,
                           transform=Affine(1, 0.2, 0, 0.2, -1, 20), nodata=0) as dst:
            dst.write(a, 1)
        er.write_meta(self.src, {'problem': 'classification', 'class_map': {'1': 'A', '2': 'B'}})
        gdf = er.polygonize_raster_file(self.src, strip_pixels=10)
        self.assertEqual(len(gdf), 2)

    def test_errors_are_kept(self):
        blocky_classification(self.src)
        with self.assertRaisesRegex(ValueError, 'no existen'):
            er.polygonize_raster_file(self.src, classes=['Zzz'])
        with self.assertRaisesRegex(ValueError, 'conectividad'):
            er.polygonize_raster_file(self.src, connectivity=5)
        plain = os.path.join(self.tmp, 'plain.tif')
        write_raster(plain)
        with self.assertRaisesRegex(ValueError, 'no es una clasificación'):
            er.polygonize_raster_file(plain)


class ResourceLimitsTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.tif = os.path.join(self.tmp, 'in.tif')
        write_raster(self.tif)

    def patch(self, **values):
        from unittest import mock
        patcher = mock.patch.multiple(er.plugin_settings, create=True, **values)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_pixel_limit_blocks_every_raster_step(self):
        self.patch(ETL_RASTER_MAX_PIXELS=100)          # el ráster de prueba tiene 1600
        names = ['r', 'g', 'ir']
        with self.assertRaisesRegex(ValueError, 'máximo permitido'):
            er.add_index_file(self.tif, os.path.join(self.tmp, 'o.tif'), 'brightness', names, [])
        cls = os.path.join(self.tmp, 'cls.tif')
        write_classified(cls, np.ones((40, 40)))
        with self.assertRaisesRegex(ValueError, 'máximo permitido'):
            er.majority_filter_file(cls, os.path.join(self.tmp, 'o.tif'))
        with self.assertRaisesRegex(ValueError, 'máximo permitido'):
            er.sieve_file(cls, os.path.join(self.tmp, 'o.tif'), 4)
        with self.assertRaisesRegex(ValueError, 'máximo permitido'):
            list(er.iter_polygon_chunks(cls))
        with override_settings(FILEMANAGER_DIRECTORY=self.tmp):
            with self.assertRaisesRegex(ValueError, 'máximo permitido'):
                er.input_Raster({'id': 'zzlim', 'raster-file': self.tif})

    def test_zero_means_no_limit(self):
        self.patch(ETL_RASTER_MAX_PIXELS=0, ETL_RASTER_SIEVE_MAX_PIXELS=0)
        cls = os.path.join(self.tmp, 'cls.tif')
        write_classified(cls, np.ones((40, 40)))
        er.sieve_file(cls, os.path.join(self.tmp, 'o.tif'), 4)

    def test_sieve_limit_is_configurable(self):
        self.patch(ETL_RASTER_SIEVE_MAX_PIXELS=100)
        cls = os.path.join(self.tmp, 'cls.tif')
        write_classified(cls, np.ones((40, 40)))
        with self.assertRaisesRegex(ValueError, 'filtro de mayoría'):
            er.sieve_file(cls, os.path.join(self.tmp, 'o.tif'), 4)

    def test_not_enough_disk_space_is_reported(self):
        from unittest import mock
        usage = shutil._ntuple_diskusage(total=10 ** 9, used=10 ** 9 - 1000, free=1000)
        with mock.patch('shutil.disk_usage', return_value=usage):
            with self.assertRaisesRegex(ValueError, 'espacio suficiente'):
                er.check_free_space(10000, 10000, 4, 4, directory=self.tmp)
            names = ['r', 'g', 'ir']
            with self.assertRaisesRegex(ValueError, 'espacio suficiente'):
                er.add_index_file(self.tif, os.path.join(self.tmp, 'o.tif'), 'brightness', names, [])
        er.check_free_space(100, 100, 1, 1, directory=self.tmp)       # con disco real, no molesta

    def test_unreadable_disk_does_not_block(self):
        from unittest import mock
        with mock.patch('shutil.disk_usage', side_effect=OSError('x')):
            er.check_free_space(10 ** 6, 10 ** 6, 4, 4, directory=self.tmp)

    def test_training_table_is_subsampled_keeping_small_classes(self):
        rng = np.random.RandomState(0)
        df = pd.DataFrame({'x': rng.normal(size=20000),
                           'y': ['grande'] * 19000 + ['pequena'] * 1000})
        reduced, original = er.subsample_training_rows(df, 'y', 5000, seed=1)
        self.assertEqual(original, 20000)
        self.assertEqual(int((reduced.y == 'pequena').sum()), 1000)      # no pierde la clase pequeña
        self.assertLess(len(reduced), 8000)
        same, none = er.subsample_training_rows(df, 'y', 0)
        self.assertIsNone(none)
        self.assertEqual(len(same), 20000)
        small, none = er.subsample_training_rows(df.head(100), 'y', 5000)
        self.assertIsNone(none)

    def test_regression_subsample_is_random_and_reproducible(self):
        df = pd.DataFrame({'x': np.arange(10000.0), 'y': np.arange(10000.0) * 1.5})
        a, n = er.subsample_training_rows(df, 'y', 2000, seed=3)
        b, _ = er.subsample_training_rows(df, 'y', 2000, seed=3)
        self.assertEqual(n, 10000)
        self.assertEqual(len(a), 2000)
        self.assertTrue((a.x.values == b.x.values).all())

    def test_n_jobs_setting(self):
        self.patch(ETL_RASTER_N_JOBS=2)
        self.assertEqual(er.n_jobs(), 2)
        self.patch(ETL_RASTER_N_JOBS=0)
        self.assertEqual(er.n_jobs(), 1)
        bundle, _, _m = er.train_model(pd.DataFrame({'x': np.arange(40.0), 'y': ['A', 'B'] * 20}), 'y', ['x'])
        self.assertEqual(bundle['model'].n_jobs, 1)


class AssessClassificationTest(SimpleTestCase):
    """Evaluación con muestras de validación independientes."""

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio / geopandas / scikit-learn')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, 'cls.tif')
        a = np.ones((40, 40), dtype=int)           # clase A a la izquierda, B a la derecha
        a[:, 20:] = 2
        a[0:5, 0:5] = 2                            # 25 píxeles de B dentro de la zona A (error del modelo)
        a[30:, :] = 0                              # franja sin clasificar
        write_classified(self.src, a, {'1': 'A', '2': 'B'})

    def gdf(self, geoms, labels, crs=CRS):
        return gpd.GeoDataFrame({'clase': labels}, geometry=geoms, crs=crs)

    @staticmethod
    def value(report, section, name):
        return float(report[(report.section == section) & (report.name == name)].value.iloc[0])

    def test_polygons_metrics_and_matrix(self):
        # Raster 40x40 con origen (0,40): fila 0 = y 39. El polígono 1 cubre filas 0-9, columnas 0-9.
        gdf = self.gdf([box(0, 30, 10, 40), box(25, 30, 35, 40)], ['A', 'B'])
        report, matrix, unknown = er.assess_classification(self.src, gdf, 'clase')
        self.assertEqual(unknown, [])
        self.assertEqual(self.value(report, 'assessment', 'validation_pixels'), 200)
        # A: 100 px reales, 25 de ellos predichos B; B: 100 correctos
        self.assertEqual(matrix.loc[matrix.real == 'A', 'pred_a'].iloc[0], 75)
        self.assertEqual(matrix.loc[matrix.real == 'A', 'pred_b'].iloc[0], 25)
        self.assertEqual(matrix.loc[matrix.real == 'B', 'pred_b'].iloc[0], 100)
        self.assertAlmostEqual(self.value(report, 'metric', 'accuracy'), 175 / 200.0)
        self.assertAlmostEqual(self.value(report, 'per_class', 'A:recall'), 0.75)         # exactitud del productor
        self.assertAlmostEqual(self.value(report, 'per_class', 'B:precision'), 100 / 125.0)  # exactitud del usuario
        self.assertEqual(self.value(report, 'assessment', 'unclassified_pixels'), 0)

    def test_unclassified_pixels_are_reported_not_counted(self):
        gdf = self.gdf([box(0, 0, 10, 40)], ['A'])           # cubre filas 0-39; las filas 30-39 están sin clasificar
        report, matrix, _ = er.assess_classification(self.src, gdf, 'clase')
        self.assertEqual(self.value(report, 'assessment', 'unclassified_pixels'), 100)
        self.assertEqual(self.value(report, 'assessment', 'validation_pixels'), 300)

    def test_points_and_outside_samples(self):
        from shapely.geometry import Point
        pts = [Point(5.5, 35.5), Point(30.5, 35.5), Point(5.5, 5.5), Point(500, 500)]   # el último fuera del ráster
        report, matrix, _ = er.assess_classification(self.src, self.gdf(pts, ['A', 'B', 'A', 'A']), 'clase')
        self.assertEqual(self.value(report, 'assessment', 'validation_pixels'), 2)      # el tercero cae en la franja sin clasificar
        self.assertEqual(self.value(report, 'assessment', 'samples_outside_raster'), 1)
        self.assertEqual(self.value(report, 'assessment', 'unclassified_pixels'), 1)
        self.assertAlmostEqual(self.value(report, 'metric', 'accuracy'), 1.0)

    def test_class_missing_from_the_model_counts_as_error(self):
        gdf = self.gdf([box(0, 30, 10, 40), box(25, 30, 35, 40)], ['A', 'Bosque'])
        report, matrix, unknown = er.assess_classification(self.src, gdf, 'clase')
        self.assertEqual(unknown, ['Bosque'])
        self.assertEqual(self.value(report, 'assessment', 'classes_not_in_model'), 1)
        self.assertEqual(self.value(report, 'per_class', 'Bosque:recall'), 0.0)
        self.assertLess(self.value(report, 'metric', 'accuracy'), 0.5)

    def test_samples_in_another_crs_are_reprojected(self):
        gdf = self.gdf([box(0, 30, 10, 40)], ['A'])
        report, _, _ = er.assess_classification(self.src, gdf, 'clase')
        self.assertEqual(self.value(report, 'assessment', 'validation_pixels'), 100)

    def test_errors(self):
        gdf = self.gdf([box(0, 30, 10, 40)], ['A'])
        with self.assertRaisesRegex(ValueError, 'columna de clase'):
            er.assess_classification(self.src, gdf, 'otra')
        far = self.gdf([box(5000, 5000, 5010, 5010)], ['A'])
        with self.assertRaisesRegex(ValueError, 'Ninguna muestra'):
            er.assess_classification(self.src, far, 'clase')
        plain = os.path.join(self.tmp, 'plain.tif')
        write_raster(plain)
        with self.assertRaisesRegex(ValueError, 'no es una clasificación'):
            er.assess_classification(plain, gdf, 'clase')
        nocrs = gpd.GeoDataFrame({'clase': ['A']}, geometry=[box(0, 30, 10, 40)])
        with self.assertRaisesRegex(ValueError, 'sistema de coordenadas'):
            er.assess_classification(self.src, nocrs, 'clase')

    def test_null_and_line_samples_are_ignored(self):
        from shapely.geometry import LineString
        gdf = self.gdf([box(0, 30, 10, 40), LineString([(0, 0), (5, 5)]), box(25, 30, 35, 40)], ['A', 'A', None])
        report, _, _ = er.assess_classification(self.src, gdf, 'clase')
        self.assertEqual(self.value(report, 'assessment', 'ignored_samples'), 2)
        self.assertEqual(self.value(report, 'assessment', 'validation_pixels'), 100)

    def test_summary_mentions_the_assessment(self):
        gdf = self.gdf([box(0, 30, 10, 40), box(25, 30, 35, 40)], ['A', 'B'])
        report, _, _ = er.assess_classification(self.src, gdf, 'clase')
        text = er.summarize_report(report)
        self.assertIn('Evaluacion', text)
        self.assertIn('Clase peor clasificada', text)


def write_gradient(path, width, height, res, origin_x, origin_y, crs=CRS, bands=1, nodata=-9999):
    """Ráster cuyo valor es la coordenada X del centro del píxel (banda 1) y la Y (banda 2, si hay)."""
    xs = origin_x + (np.arange(width) + 0.5) * res
    ys = origin_y - (np.arange(height) + 0.5) * res
    data = np.zeros((bands, height, width), dtype='float32')
    data[0] = xs[None, :]
    if bands > 1:
        data[1] = ys[:, None]
    with rasterio.open(path, 'w', driver='GTiff', height=height, width=width, count=bands, dtype='float32',
                       crs=crs, transform=from_origin(origin_x, origin_y, res, res), nodata=nodata) as dst:
        dst.write(data)


class StackRastersTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ref = os.path.join(self.tmp, 'ref.tif')
        write_gradient(self.ref, 40, 40, 1.0, 100.0, 540.0, bands=2)      # 2 bandas, píxel de 1 m
        self.out = os.path.join(self.tmp, 'out.tif')

    def path(self, name):
        return os.path.join(self.tmp, name)

    def test_same_grid_keeps_values_and_names(self):
        other = self.path('other.tif')
        write_gradient(other, 40, 40, 1.0, 100.0, 540.0, bands=1)
        names = er.stack_rasters([self.ref, other], self.out, [['rojo', 'verde'], ['mdt']])
        self.assertEqual(names, ['rojo', 'verde', 'mdt'])
        with rasterio.open(self.out) as src:
            self.assertEqual((src.count, src.width, src.height), (3, 40, 40))
            self.assertEqual(src.dtypes[0], 'float32')
            self.assertEqual(src.nodata, er.REGRESSION_NODATA)
            data = src.read()
        self.assertTrue((data[0] == data[2]).all())

    def test_finer_resolution_is_resampled_to_the_reference_grid(self):
        fine = self.path('fine.tif')
        write_gradient(fine, 80, 80, 0.5, 100.0, 540.0)
        er.stack_rasters([self.ref, fine], self.out, [['a', 'b'], ['x']], resampling='bilinear')
        with rasterio.open(self.out) as src:
            data = src.read()
            self.assertEqual((src.width, src.height), (40, 40))
        np.testing.assert_allclose(data[2][5:35, 5:35], data[0][5:35, 5:35], atol=1e-3)   # gradiente lineal

    def test_nearest_never_creates_new_values(self):
        coarse = self.path('coarse.tif')
        write_gradient(coarse, 8, 8, 5.0, 100.0, 540.0)
        er.stack_rasters([self.ref, coarse], self.out, [['a', 'b'], ['x']], resampling='nearest')
        values = set(np.unique(read_band(coarse)))
        with rasterio.open(self.out) as src:
            self.assertTrue(set(np.unique(src.read(3))) <= values)

    def test_partial_coverage_leaves_nodata(self):
        half = self.path('half.tif')
        write_gradient(half, 20, 40, 1.0, 100.0, 540.0)             # solo la mitad izquierda
        er.stack_rasters([self.ref, half], self.out, [['a', 'b'], ['x']])
        data = read_band(self.out, 3)
        self.assertTrue((data[:, :20] != er.REGRESSION_NODATA).all())
        self.assertTrue((data[:, 22:] == er.REGRESSION_NODATA).all())

    def test_other_crs_is_reprojected(self):
        constant = self.path('utm_wgs84.tif')
        data = np.full((1, 60, 60), 7.0, dtype='float32')
        with rasterio.open(constant, 'w', driver='GTiff', height=60, width=60, count=1, dtype='float32',
                           crs='EPSG:32630', transform=from_origin(90.0, 550.0, 1, 1), nodata=-9999) as dst:
            dst.write(data)
        er.stack_rasters([self.ref, constant], self.out, [['a', 'b'], ['c']])
        inner = read_band(self.out, 3)[5:35, 5:35]
        self.assertTrue(np.allclose(inner, 7.0))

    def test_prefixes_and_unique_names(self):
        other = self.path('other.tif')
        write_gradient(other, 40, 40, 1.0, 100.0, 540.0, bands=2)
        names = er.stack_rasters([self.ref, other], self.out, [['Rojo', 'Verde'], ['Rojo', 'Verde']],
                                 prefixes=['', 'Fecha 2'])
        self.assertEqual(names, ['rojo', 'verde', 'fecha_2_rojo', 'fecha_2_verde'])
        names = er.stack_rasters([self.ref, other], self.out, [['x', 'y'], ['x', 'y']])
        self.assertEqual(names, ['x', 'y', 'x_2', 'y_2'])

    def test_result_does_not_depend_on_block_size(self):
        fine = self.path('fine.tif')
        write_gradient(fine, 80, 80, 0.5, 100.0, 540.0)
        er.stack_rasters([self.ref, fine], self.out, [['a', 'b'], ['x']], block=7)
        small = read_band(self.out, 3)
        er.stack_rasters([self.ref, fine], self.out, [['a', 'b'], ['x']], block=512)
        self.assertTrue(np.array_equal(small, read_band(self.out, 3)))

    def test_errors(self):
        other = self.path('other.tif')
        write_gradient(other, 10, 10, 1.0, 100.0, 540.0)
        with self.assertRaisesRegex(ValueError, 'al menos dos'):
            er.stack_rasters([self.ref], self.out, [[]])
        with self.assertRaisesRegex(ValueError, 'como máximo'):
            er.stack_rasters([self.ref] * 5, self.out, [[]] * 5)
        with self.assertRaisesRegex(ValueError, 'remuestreo'):
            er.stack_rasters([self.ref, other], self.out, [[], []], resampling='cubic')
        far = self.path('far.tif')
        write_gradient(far, 10, 10, 1.0, 900000.0, 4000000.0)
        with self.assertRaisesRegex(ValueError, 'no se solapa'):
            er.stack_rasters([self.ref, far], self.out, [[], []])
        nocrs = self.path('nocrs.tif')
        with rasterio.open(nocrs, 'w', driver='GTiff', height=5, width=5, count=1, dtype='float32') as dst:
            dst.write(np.ones((1, 5, 5), dtype='float32'))
        with self.assertRaisesRegex(ValueError, 'sistema de coordenadas'):
            er.stack_rasters([self.ref, nocrs], self.out, [[], []])
        with self.assertRaisesRegex(ValueError, 'sistema de coordenadas'):
            er.stack_rasters([nocrs, self.ref], self.out, [[], []])

    def test_node(self):
        other = self.path('other.tif')
        write_gradient(other, 40, 40, 1.0, 100.0, 540.0)
        er.write_meta(self.ref, {'band_names': ['rojo', 'ir'], 'crs': CRS})
        er.write_meta(other, {'band_names': ['mdt']})
        res = er.trans_RasterStack({'id': 'zzstk', 'data': [self.ref, other], 'resampling': 'nearest',
                                    'prefix-1': '', 'prefix-2': 'terreno'})
        try:
            self.assertEqual(er.read_meta(res[0])['band_names'], ['rojo', 'ir', 'terreno_mdt'])
            self.assertEqual(er.read_meta(res[0])['crs'], CRS)
            with self.assertRaisesRegex(Exception, 'al menos dos'):
                er.trans_RasterStack({'id': 'zzstk', 'data': [self.ref]})
        finally:
            er.remove_artifact(res[0])


class StableColorsTest(SimpleTestCase):
    """Las clases conservan su color entre ejecuciones y el rango de la rampa se puede fijar."""

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        from gvsigol_plugin_geoetl import etl_raster_publish as pub
        self.pub = pub
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def classified(self, class_map):
        path = os.path.join(self.tmp, 'c%d.tif' % len(os.listdir(self.tmp)))
        write_classified(path, np.ones((4, 4)), class_map)
        return path

    def test_without_previous_colors_the_palette_is_unchanged(self):
        for n in (1, 3, 8, 11):
            labels = ['c%d' % i for i in range(n)]
            self.assertEqual(self.pub.assign_class_colors(labels), self.pub.class_palette(n))

    def test_known_classes_keep_their_color_and_new_ones_get_free_colors(self):
        first = self.pub.assign_class_colors(['agua', 'suelo', 'vegetacion'])
        previous = dict(zip(['agua', 'suelo', 'vegetacion'], first))
        # aparece una clase que va alfabéticamente antes de las demás
        again = self.pub.assign_class_colors(['arena', 'agua', 'suelo', 'vegetacion'], previous)
        self.assertEqual(again[1:], first)                          # las conocidas no cambian de color
        self.assertNotIn(again[0], first)                           # la nueva no repite ninguno en uso
        # desaparece una clase: las demás siguen igual
        fewer = self.pub.assign_class_colors(['agua', 'vegetacion'], previous)
        self.assertEqual(fewer, [first[0], first[2]])

    def test_many_classes_stay_distinct(self):
        labels = ['c%02d' % i for i in range(15)]
        colors = self.pub.assign_class_colors(labels, {'c03': '#123456'})
        self.assertEqual(len(set(c.upper() for c in colors)), 15)
        self.assertEqual(colors[3], '#123456')

    def test_style_entries_use_previous_colors_by_label(self):
        path = self.classified({'1': 'Agua', '2': 'Suelo'})
        entries, kind = self.pub.style_entries(path, {'Suelo': '#ABCDEF'})
        self.assertEqual(kind, 'values')
        self.assertEqual([e['label'] for e in entries], ['Agua', 'Suelo'])
        self.assertEqual(entries[1]['color'], '#ABCDEF')
        self.assertNotEqual(entries[0]['color'].upper(), '#ABCDEF')

    def test_ramp_range_can_be_fixed(self):
        path = os.path.join(self.tmp, 'reg.tif')
        with rasterio.open(path, 'w', driver='GTiff', height=1, width=3, count=1, dtype='float32', crs=CRS,
                           transform=from_origin(0, 1, 1, 1), nodata=er.REGRESSION_NODATA) as dst:
            dst.write(np.array([[2.0, 8.0, er.REGRESSION_NODATA]], dtype='float32'), 1)
        er.write_meta(path, {'problem': 'regression'})
        entries, kind = self.pub.style_entries(path)
        self.assertEqual((kind, [e['quantity'] for e in entries]), ('ramp', [2.0, 8.0]))
        entries, _ = self.pub.style_entries(path, ramp_range=(0.0, 100.0))
        self.assertEqual([e['quantity'] for e in entries], [0.0, 100.0])
        entries, _ = self.pub.style_entries(path, ramp_range=(5.0, 5.0))          # rango degenerado: se corrige
        self.assertGreater(entries[1]['quantity'], entries[0]['quantity'])

    def test_style_signature_detects_changes(self):
        a = self.pub.style_entries(self.classified({'1': 'A', '2': 'B'}))[0]
        b = self.pub.style_entries(self.classified({'1': 'A', '2': 'B'}))[0]
        c = self.pub.style_entries(self.classified({'1': 'A', '2': 'B', '3': 'C'}))[0]
        self.assertEqual(self.pub._entries_signature(a), self.pub._entries_signature(b))
        self.assertNotEqual(self.pub._entries_signature(a), self.pub._entries_signature(c))

    def test_float_parameters(self):
        self.assertIsNone(self.pub._float_or_none(''))
        self.assertIsNone(self.pub._float_or_none(None))
        self.assertEqual(self.pub._float_or_none('0,5'), 0.5)
        with self.assertRaisesRegex(Exception, 'no es un número válido'):
            self.pub._float_or_none('abc')


class ExtractBandTest(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, 'in.tif')
        write_raster(self.src)
        er.write_meta(self.src, {'band_names': ['rojo', 'verde', 'ir'], 'crs': CRS})
        self.out = os.path.join(self.tmp, 'out.tif')

    def test_by_name_and_by_number(self):
        er.extract_band(self.src, 'verde', self.out)
        with rasterio.open(self.out) as src, rasterio.open(self.src) as ref:
            self.assertEqual((src.count, src.crs, src.nodata, src.dtypes[0]), (1, ref.crs, ref.nodata, ref.dtypes[1]))
            self.assertTrue((src.read(1) == ref.read(2)).all())
        self.assertEqual(er.read_meta(self.out)['band_names'], ['verde'])
        er.extract_band(self.src, '3', self.out, block=7)
        with rasterio.open(self.out) as src, rasterio.open(self.src) as ref:
            self.assertTrue((src.read(1) == ref.read(3)).all())

    def test_unknown_band(self):
        for bad in ('nope', '0', '4'):
            with self.assertRaisesRegex(ValueError, 'no tiene la banda'):
                er.extract_band(self.src, bad, self.out)

    def test_class_map_is_kept(self):
        cls = os.path.join(self.tmp, 'cls.tif')
        write_classified(cls, np.ones((6, 6)), {'1': 'A', '2': 'B'})
        er.extract_band(cls, '1', self.out)
        self.assertEqual(er.read_meta(self.out)['class_map'], {'1': 'A', '2': 'B'})


class EditorServerParityTest(SimpleTestCase):
    """Lo que el editor (JS) calcula por su cuenta debe coincidir con el servidor: si no, los desplegables mienten."""

    JS = os.path.join(os.path.dirname(er.__file__), 'static', 'js', 'PredictiveShapes.js')

    # (texto, existentes, resultado): los mismos casos se prueban en tests/js/run.js
    # (los nombres vacíos no llegan nunca a este punto: cada nodo usa antes un nombre por defecto)
    BAND_NAMES = [('NDVI Año 1', [], 'ndvi_ano_1'), ('1x', [], 'b_1x'), ('Rojo', ['rojo'], 'rojo_2'), ('  Infrarrojo cercano ', [], 'infrarrojo_cercano'),
                  ('a-b/c', [], 'a_b_c'), ('Ñandú', [], 'nandu'), ('fecha 2_rojo', ['fecha_2_rojo'], 'fecha_2_rojo_2')]

    def test_band_name_normalisation_matches_the_editor(self):
        for text, existing, expected in self.BAND_NAMES:
            names = er.parse_band_names(list(existing) + [text], len(existing) + 1)
            self.assertEqual(names[-1], expected, repr(text))

    def test_spectral_indices_match_the_editor(self):
        import re
        source = open(self.JS, encoding='utf-8').read()
        block = source[source.index('var ETL_INDICES = {'):]
        block = block[:block.index('};')]
        js = {m.group(1): re.findall(r"'(\w+)'", m.group(2))
              for m in re.finditer(r"(\w+): \{roles: \[([^\]]*)\]", block)}
        server = {name: list(spec['roles']) for name, spec in er.INDEX_DEFS.items()}
        self.assertEqual(js, server)

    def test_every_node_the_server_runs_is_defined_in_the_editor(self):
        import re
        source = open(self.JS, encoding='utf-8').read()
        defined = set(re.findall(r"defineEtlNode\(\{\s*name: '(\w+)'", source))
        from gvsigol_plugin_geoetl import etl_tasks
        for name in defined:
            self.assertTrue(callable(getattr(etl_tasks, name, None)), '%s no tiene función en el motor' % name)

    def test_validation_modes_and_stack_limits_match_the_editor(self):
        source = open(self.JS, encoding='utf-8').read()
        for mode in er.VALIDATION_MODES:
            self.assertIn("value: '%s'" % mode, source)
        self.assertEqual(er.STACK_MAX_INPUTS, source.count("kind: 'raster'}") and 4)
        for resampling in er.STACK_RESAMPLING:
            self.assertIn("value: '%s'" % resampling, source)


class PnoaLikeRasterTest(SimpleTestCase):
    """
    Ortofotos como las del PNOA: GeoTIFF de 8 bits comprimido en JPEG con color YCbCr. Su perfil no se puede
    copiar al resultado (otra compresión, otro tipo de dato, otro número de bandas): error real detectado
    con datos reales ("PHOTOMETRIC=YCBCR requires COMPRESS=JPEG").
    """

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.rgb = os.path.join(self.tmp, 'pnoa_rgb.tif')
        rng = np.random.RandomState(0)
        data = rng.randint(30, 220, (3, 64, 64)).astype('uint8')
        data[:, :, 32:] = np.clip(data[:, :, 32:] + 20, 0, 255)
        try:
            with rasterio.open(self.rgb, 'w', driver='GTiff', height=64, width=64, count=3, dtype='uint8', crs=CRS,
                               transform=from_origin(0, 64, 1, 1), compress='jpeg', photometric='ycbcr',
                               tiled=True, blockxsize=16, blockysize=16) as dst:
                dst.write(data)
        except Exception as e:           # GDAL sin soporte JPEG: no se puede reproducir el caso
            self.skipTest('GDAL no puede escribir JPEG/YCbCr: %s' % e)
        with rasterio.open(self.rgb) as src:
            self.assertEqual(src.profile.get('photometric', '').lower(), 'ycbcr')   # el original es realmente así
        self.nir = os.path.join(self.tmp, 'nir.tif')
        with rasterio.open(self.nir, 'w', driver='GTiff', height=32, width=32, count=1, dtype='uint8', crs=CRS,
                           transform=from_origin(0, 64, 2, 2), compress='lzw') as dst:
            dst.write(rng.randint(10, 250, (1, 32, 32)).astype('uint8'))
        er.write_meta(self.rgb, {'band_names': ['rojo', 'verde', 'azul']})
        er.write_meta(self.nir, {'band_names': ['nir']})

    def path(self, name):
        return os.path.join(self.tmp, name)

    def test_the_output_profile_does_not_inherit_the_color_model(self):
        with rasterio.open(self.rgb) as src:
            profile = er.output_profile(src)
        self.assertNotIn('photometric', profile)
        self.assertNotIn('compress', profile)
        self.assertEqual((profile['width'], profile['height'], profile['count'], profile['dtype']), (64, 64, 3, 'uint8'))

    def test_combine_a_jpeg_ycbcr_orthophoto_with_a_nir_band(self):
        names = er.stack_rasters([self.rgb, self.nir], self.path('stk.tif'), [['rojo', 'verde', 'azul'], ['nir']])
        self.assertEqual(names, ['rojo', 'verde', 'azul', 'nir'])
        with rasterio.open(self.path('stk.tif')) as src:
            self.assertEqual((src.count, src.dtypes[0], src.width), (4, 'float32', 64))

    def test_every_step_accepts_such_a_raster(self):
        names = er.stack_rasters([self.rgb, self.nir], self.path('stk.tif'), [['rojo', 'verde', 'azul'], ['nir']])
        er.write_meta(self.path('stk.tif'), {'band_names': names})
        # índice sobre la propia ortofoto JPEG/YCbCr (sin combinar)
        out = er.add_index_file(self.rgb, self.path('idx.tif'), 'brightness', ['rojo', 'verde', 'azul'], [])
        self.assertEqual(out[-1], 'brightness')
        # banda suelta de la ortofoto
        er.extract_band(self.rgb, 'verde', self.path('band.tif'))
        with rasterio.open(self.path('band.tif')) as src:
            self.assertEqual((src.count, src.dtypes[0]), (1, 'uint8'))
        # entrenar con la ortofoto y predecirla
        samples = gpd.GeoDataFrame({'clase': ['A', 'B']}, geometry=[box(2, 2, 14, 14), box(40, 40, 60, 60)], crs=CRS)
        df = er.sample_raster_pixels(self.rgb, samples, 'clase', band_names=['rojo', 'verde', 'azul'])
        bundle, _, _ = er.train_model(df, 'clase', ['rojo', 'verde', 'azul'], n_estimators=10)
        er.predict_raster_file(self.rgb, bundle, self.path('pred.tif'), confidence_path=self.path('conf.tif'))
        er.majority_filter_file(self.path('pred.tif'), self.path('maj.tif'), size=3)
        er.sieve_file(self.path('pred.tif'), self.path('sv.tif'), 4)
        for name in ('pred.tif', 'conf.tif', 'maj.tif', 'sv.tif'):
            with rasterio.open(self.path(name)) as src:
                self.assertEqual(src.count, 1, name)

    def test_input_node_accepts_it(self):
        with override_settings(FILEMANAGER_DIRECTORY=self.tmp):
            res = er.input_Raster({'id': 'zzpnoa', 'raster-file': 'file://' + self.rgb, 'band-names': 'Rojo,Verde,Azul'})
        try:
            self.assertEqual(er.read_meta(res[0])['band_names'], ['rojo', 'verde', 'azul'])
        finally:
            er.remove_artifact(res[0])


class ClipRasterTest(SimpleTestCase):
    """Recorte de un ráster con una máscara vectorial (con o sin cambio de tamaño de píxel)."""

    W, H = 80, 60

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio / shapely')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, 'in.tif')
        # 3 bandas de 8 bits sin valor de sin dato: cada píxel vale (columna, fila, columna+fila)
        cols = np.tile(np.arange(self.W), (self.H, 1))
        rows = np.tile(np.arange(self.H)[:, None], (1, self.W))
        self.data = np.stack([cols, rows, (cols + rows) % 256]).astype('uint8')
        with rasterio.open(self.src, 'w', driver='GTiff', height=self.H, width=self.W, count=3, dtype='uint8',
                           crs=CRS, transform=from_origin(0, self.H, 1, 1)) as dst:
            dst.write(self.data)
        er.write_meta(self.src, {'band_names': ['a', 'b', 'c'], 'crs': CRS})
        self.out = os.path.join(self.tmp, 'out.tif')

    def clip(self, geoms, **kw):
        return er.clip_raster_file(self.src, geoms, self.out, **kw)

    def read(self, path=None):
        with rasterio.open(path or self.out) as src:
            return src.read(), src.transform, src.nodata, src.dtypes[0]

    def test_polygon_mask_keeps_inside_and_blanks_outside(self):
        # triángulo dentro del rectángulo (10,10)-(30,30)
        from shapely.geometry import Polygon
        tri = Polygon([(10, 10), (30, 10), (10, 30)])
        w, h, inside, added = self.clip([tri])
        data, transform, nodata, dtype = self.read()
        self.assertEqual((w, h), (20, 20))
        self.assertEqual((dtype, nodata, added), ('uint8', 0, True))
        self.assertEqual(data.shape, (3, 20, 20))
        self.assertAlmostEqual(inside, 200, delta=12)                      # la mitad del cuadrado
        # lo que queda dentro es idéntico al original; lo de fuera es sin dato
        self.assertEqual(int(data[0, -1, 0]), int(self.data[0, self.H - 30, 10]))   # esquina inferior izquierda, dentro
        self.assertTrue((data[:, 0, -1] == 0).all())                                # esquina superior derecha, fuera
        self.assertEqual(transform.c, 10.0)
        self.assertEqual(transform.f, 30.0)

    def test_bbox_mode_is_a_plain_crop_without_inventing_nodata(self):
        from shapely.geometry import box as sbox
        w, h, inside, added = self.clip([sbox(10, 10, 30, 30)], mode='bbox')
        data, _, nodata, _ = self.read()
        self.assertEqual((w, h, inside, added), (20, 20, 400, False))
        self.assertIsNone(nodata)
        self.assertTrue((data == self.data[:, self.H - 30:self.H - 10, 10:30]).all())

    def test_fractional_bounds_are_snapped_to_the_source_grid(self):
        from shapely.geometry import box as sbox
        w, h, _, _ = self.clip([sbox(10.4, 10.4, 30.6, 30.6)], mode='bbox')
        data, transform, _, _ = self.read()
        self.assertEqual((w, h), (21, 21))                                  # píxeles 10..30 completos
        self.assertEqual((transform.c, transform.f), (10.0, 31.0))
        self.assertTrue((data == self.data[:, self.H - 31:self.H - 10, 10:31]).all())

    def test_mask_partly_outside_is_clipped_to_the_overlap(self):
        from shapely.geometry import box as sbox
        w, h, _, _ = self.clip([sbox(70, 50, 200, 200)], mode='bbox')
        self.assertEqual((w, h), (10, 10))

    def test_several_polygons_use_their_joint_extent(self):
        from shapely.geometry import box as sbox
        w, h, inside, _ = self.clip([sbox(5, 5, 10, 10), sbox(40, 30, 45, 35)])
        self.assertEqual((w, h), (40, 30))
        self.assertEqual(inside, 50)                                         # dos recuadros de 5 x 5

    def test_new_pixel_size_averages_the_source(self):
        from shapely.geometry import box as sbox
        const = os.path.join(self.tmp, 'blocks.tif')
        blocks = np.kron(np.arange(15 * 20).reshape(15, 20), np.ones((4, 4), dtype=int)).astype('uint8')[None]
        with rasterio.open(const, 'w', driver='GTiff', height=60, width=80, count=1, dtype='uint8', crs=CRS,
                           transform=from_origin(0, 60, 1, 1)) as dst:
            dst.write(blocks)
        er.write_meta(const, {'band_names': ['b']})
        w, h, _, _ = er.clip_raster_file(const, [sbox(0, 0, 80, 60)], self.out, mode='bbox', pixel_size=4)
        data, transform, _, dtype = self.read()
        self.assertEqual((w, h, dtype, transform.a), (20, 15, 'uint8', 4.0))
        self.assertTrue((data[0] == np.arange(15 * 20).reshape(15, 20).astype('uint8')).all())   # cada bloque de 4x4 -> su valor

    def test_classified_raster_keeps_its_classes_when_resampled(self):
        from shapely.geometry import box as sbox
        cls = os.path.join(self.tmp, 'cls.tif')
        rng = np.random.RandomState(0)
        write_classified(cls, rng.randint(1, 4, (60, 80)), {'1': 'A', '2': 'B', '3': 'C'})
        er.clip_raster_file(cls, [sbox(0, 0, 80, 60)], self.out, mode='bbox', pixel_size=3, resampling='bilinear')
        data, _, _, dtype = self.read()
        self.assertEqual(dtype, 'uint16')
        self.assertTrue(set(np.unique(data)) <= {0, 1, 2, 3})                  # sin valores intermedios inventados
        self.assertEqual(er.read_meta(self.out)['class_map'], {'1': 'A', '2': 'B', '3': 'C'})

    def test_metadata_and_band_names_are_kept(self):
        from shapely.geometry import box as sbox
        self.clip([sbox(10, 10, 30, 30)], pixel_size=2)
        meta = er.read_meta(self.out)
        self.assertEqual(meta['band_names'], ['a', 'b', 'c'])
        self.assertEqual(meta['pixel_size'], 2.0)

    def test_result_does_not_depend_on_block_size(self):
        from shapely.geometry import Polygon
        poly = Polygon([(5, 5), (60, 12), (40, 50), (8, 40)])
        self.clip([poly], block=7)
        small = self.read()[0]
        self.clip([poly], block=512)
        self.assertTrue((small == self.read()[0]).all())
        self.clip([poly], pixel_size=3, block=5)
        small = self.read()[0]
        self.clip([poly], pixel_size=3, block=512)
        self.assertTrue((small == self.read()[0]).all())

    def test_float_and_signed_rasters_get_a_sensible_nodata(self):
        from shapely.geometry import Polygon
        for dtype, expected in (('float32', er.REGRESSION_NODATA), ('int16', -32768)):
            path = os.path.join(self.tmp, dtype + '.tif')
            with rasterio.open(path, 'w', driver='GTiff', height=20, width=20, count=1, dtype=dtype, crs=CRS,
                               transform=from_origin(0, 20, 1, 1)) as dst:
                dst.write(np.ones((1, 20, 20), dtype=dtype))
            er.write_meta(path, {})
            er.clip_raster_file(path, [Polygon([(2, 2), (18, 2), (2, 18)])], self.out)
            data, _, nodata, _ = self.read()
            self.assertEqual(nodata, expected, dtype)
            self.assertIn(expected, set(np.unique(data)))

    def test_declared_nodata_is_respected(self):
        from shapely.geometry import Polygon
        path = os.path.join(self.tmp, 'nd.tif')
        with rasterio.open(path, 'w', driver='GTiff', height=20, width=20, count=1, dtype='uint8', crs=CRS,
                           transform=from_origin(0, 20, 1, 1), nodata=255) as dst:
            dst.write(np.full((1, 20, 20), 7, dtype='uint8'))
        er.write_meta(path, {})
        _, _, _, added = er.clip_raster_file(path, [Polygon([(2, 2), (18, 2), (2, 18)])], self.out)
        data, _, nodata, _ = self.read()
        self.assertEqual((nodata, added), (255, False))
        self.assertEqual(set(np.unique(data)), {7, 255})

    def test_jpeg_ycbcr_orthophoto_can_be_clipped(self):
        from shapely.geometry import box as sbox
        pnoa = os.path.join(self.tmp, 'pnoa.tif')
        try:
            with rasterio.open(pnoa, 'w', driver='GTiff', height=64, width=64, count=3, dtype='uint8', crs=CRS,
                               transform=from_origin(0, 64, 1, 1), compress='jpeg', photometric='ycbcr',
                               tiled=True, blockxsize=16, blockysize=16) as dst:
                dst.write(np.random.RandomState(1).randint(20, 200, (3, 64, 64)).astype('uint8'))
        except Exception as e:
            self.skipTest('GDAL sin JPEG/YCbCr: %s' % e)
        er.write_meta(pnoa, {})
        w, h, _, _ = er.clip_raster_file(pnoa, [sbox(10, 10, 40, 40)], self.out, pixel_size=2)
        self.assertEqual((w, h), (15, 15))

    def test_errors(self):
        from shapely.geometry import box as sbox
        with self.assertRaisesRegex(ValueError, 'no se solapa'):
            self.clip([sbox(500, 500, 600, 600)])
        with self.assertRaisesRegex(ValueError, 'ningún polígono'):
            self.clip([])
        with self.assertRaisesRegex(ValueError, 'Modo de recorte'):
            self.clip([sbox(0, 0, 5, 5)], mode='raro')
        with self.assertRaisesRegex(ValueError, 'remuestreo'):
            self.clip([sbox(0, 0, 5, 5)], resampling='cubic')
        with self.assertRaisesRegex(ValueError, 'mayor que 0'):
            self.clip([sbox(0, 0, 5, 5)], pixel_size=0)
        with self.assertRaisesRegex(ValueError, 'más pequeña que un píxel'):
            self.clip([sbox(10.2, 10.2, 10.4, 10.4)])                 # cabe en un píxel pero no contiene su centro
        self.assertFalse(os.path.exists(self.out))                    # y no deja un fichero vacío
        nocrs = os.path.join(self.tmp, 'nocrs.tif')
        with rasterio.open(nocrs, 'w', driver='GTiff', height=5, width=5, count=1, dtype='uint8') as dst:
            dst.write(np.ones((1, 5, 5), dtype='uint8'))
        with self.assertRaisesRegex(ValueError, 'sistema de coordenadas'):
            er.clip_raster_file(nocrs, [sbox(0, 0, 5, 5)], self.out)

    def test_limits_apply_to_the_result(self):
        from unittest import mock
        from shapely.geometry import box as sbox
        with mock.patch.object(er.plugin_settings, 'ETL_RASTER_MAX_PIXELS', 100, create=True):
            with self.assertRaisesRegex(ValueError, 'máximo permitido'):
                self.clip([sbox(0, 0, 80, 60)], mode='bbox')


class PaletteTest(SimpleTestCase):
    """Cada nodo del editor aparece una sola vez en la paleta, y en su categoría."""

    BASE = os.path.dirname(er.__file__)

    def palette(self):
        import re
        html = open(os.path.join(self.BASE, 'templates', 'etl.html'), encoding='utf-8').read()
        groups = {}
        for m in re.finditer(r'id="button-([\w-]+)".*?<div class="dropdown-menu">(.*?)</div>', html, re.S):
            groups[m.group(1)] = re.findall(r'data-shape="(\w+)"', m.group(2))
        return groups

    def test_every_editor_node_is_in_the_palette_exactly_once(self):
        import re
        js = open(os.path.join(self.BASE, 'static', 'js', 'PredictiveShapes.js'), encoding='utf-8').read()
        defined = re.findall(r"defineEtlNode\(\{\s*name: '(\w+)'", js)
        shapes = [s for nodes in self.palette().values() for s in nodes]
        for name in defined:
            self.assertEqual(shapes.count(name), 1, '%s aparece %d veces en la paleta' % (name, shapes.count(name)))

    def test_categories(self):
        groups = self.palette()
        self.assertEqual(groups['raster'], ['trans_RasterClip', 'trans_RasterStack', 'trans_RasterIndex',
                                            'trans_RasterMajority', 'trans_RasterPolygonize'])
        self.assertEqual(groups['predictive'], ['trans_RasterSample', 'trans_RandomForest', 'trans_RasterPredict',
                                                'trans_TablePredict', 'trans_ClassAssess', 'trans_StratifiedSample',
                                                'trans_AreaEstimate'])
        self.assertIn('input_Raster', groups['inputs'])
        self.assertIn('input_Model', groups['inputs'])
        self.assertIn('output_RasterPublish', groups['outputs'])
        self.assertIn('output_ModelSave', groups['outputs'])

    def test_raster_button_is_locked_in_restricted_mode_like_the_others(self):
        import re
        html = open(os.path.join(self.BASE, 'templates', 'etl.html'), encoding='utf-8').read()
        button = re.search(r'<button[^>]*id="button-raster"[^>]*>', html, re.S).group(0)
        self.assertIn("editablerestrictedly == 'true'", button)


class ScientificRigorTest(SimpleTestCase):
    """Correcciones de método: reflectancia con offset, rango del EVI, max_features, validación automática, permutación."""

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio / scikit-learn')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def raster(self, values, dtype='uint16'):
        """Ráster de 1 x N píxeles con bandas (nir, rojo, azul) dadas como listas."""
        path = os.path.join(self.tmp, 'r%d.tif' % len(os.listdir(self.tmp)))
        data = np.array(values, dtype=dtype)[:, None, :]
        with rasterio.open(path, 'w', driver='GTiff', height=1, width=data.shape[2], count=data.shape[0], dtype=dtype,
                           crs=CRS, transform=from_origin(0, 1, 1, 1)) as dst:
            dst.write(data)
        return path

    def index(self, path, index, selected, **kw):
        out = os.path.join(self.tmp, 'out%d.tif' % len(os.listdir(self.tmp)))
        er.add_index_file(path, out, index, ['nir', 'rojo', 'azul'], selected, **kw)
        return read_band(out, 4)

    def test_sentinel2_offset_changes_ndvi_as_it_should(self):
        # Sentinel-2 L2A desde 2022: reflectancia = (DN - 1000) / 10000. NIR 0,30 -> DN 4000; rojo 0,05 -> DN 1500
        path = self.raster([[4000], [1500], [1200]])
        scale, offset = er.REFLECTANCE_PRESETS['sentinel2_l2a']
        right = self.index(path, 'ndvi', ['nir', 'rojo'], scale=scale, offset=offset)[0, 0]
        wrong = self.index(path, 'ndvi', ['nir', 'rojo'])[0, 0]
        self.assertAlmostEqual(float(right), (0.30 - 0.05) / (0.30 + 0.05), places=5)
        self.assertGreater(abs(float(right) - float(wrong)), 0.1)            # sin offset el NDVI sale sesgado

    def test_landsat_c2_preset_is_dn_times_gain_plus_offset(self):
        scale, offset = er.REFLECTANCE_PRESETS['landsat_c2_l2']
        dn = 20000
        self.assertAlmostEqual((dn + offset) / scale, dn * 0.0000275 - 0.2, places=9)

    def test_without_offset_normalized_indices_do_not_depend_on_the_scale(self):
        path = self.raster([[150], [50], [10]])
        a = self.index(path, 'ndvi', ['nir', 'rojo'])
        b = self.index(path, 'ndvi', ['nir', 'rojo'], scale=255.0)
        np.testing.assert_allclose(a, b, rtol=1e-6)

    def test_evi_outside_its_physical_range_is_nodata(self):
        # El 2.º píxel tiene el denominador casi nulo -> EVI enorme -> sin dato; el 1.º es una vegetación normal
        path = self.raster([[3000, 1000], [500, 100], [300, 1550]])     # 2.º: 0,1 + 6·0,01 - 7,5·0,155 + 1 ≈ 0
        evi = self.index(path, 'evi', ['nir', 'rojo', 'azul'], scale=10000.0)[0]
        nir, red, blue = 0.3, 0.05, 0.03
        self.assertAlmostEqual(float(evi[0]), 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1), places=5)
        self.assertEqual(float(evi[1]), er.REGRESSION_NODATA)

    def test_reflectance_conversion_parameters(self):
        self.assertEqual(er.reflectance_conversion({'reflectance': 'uint8'}), (255.0, 0.0))
        self.assertEqual(er.reflectance_conversion({'reflectance': 'custom', 'scale': '100', 'offset': '-5'}), (100.0, -5.0))
        self.assertEqual(er.reflectance_conversion({'scale': '255'}), (255.0, 0.0))     # flujos guardados antes: sin preset
        with self.assertRaisesRegex(ValueError, 'desconocida'):
            er.reflectance_conversion({'reflectance': 'otra'})

    def test_regression_uses_a_third_of_the_variables_like_breiman(self):
        rng = np.random.RandomState(0)
        df = pd.DataFrame(rng.uniform(size=(200, 6)), columns=list('abcdef'))
        df['y'] = df['a'] * 3 + rng.normal(0, 0.1, 200)
        reg, _, _ = er.train_model(df, 'y', list('abcdef'), problem='regression')
        self.assertAlmostEqual(reg['model'].max_features, 1 / 3.0)
        df['c'] = (df['a'] > 0.5).astype(int)
        clf, _, _ = er.train_model(df, 'c', list('abdef'))
        self.assertEqual(clf['model'].max_features, 'sqrt')
        bag, _, _ = er.train_model(df, 'y', list('abcdef'), problem='regression', max_features='all')
        self.assertEqual(bag['model'].max_features, 1.0)
        with self.assertRaisesRegex(ValueError, 'entre 0 y 1'):
            er.train_model(df, 'y', list('abcdef'), max_features='1.5')

    def test_auto_validation_uses_polygons_when_possible(self):
        df = clustered_frame()
        _, report, _ = er.train_model(df, 'clase', ['v'], validation='auto')
        self.assertEqual(report[report.section == 'validation'].name.tolist(), ['polygon'])
        _, report, _ = er.train_model(df.drop(columns=[er.AUX_POLY]), 'clase', ['v'], validation='auto')
        self.assertEqual(report[report.section == 'validation'].name.tolist(), ['random'])
        _, report, _ = er.train_model(clustered_frame(polygons=3), 'clase', ['v'], validation='auto')   # B solo tiene 1 polígono
        self.assertEqual(report[report.section == 'validation'].name.tolist(), ['random'])

    def test_permutation_importance_is_measured_on_evaluation_data(self):
        rng = np.random.RandomState(1)
        df = pd.DataFrame({'util': np.r_[rng.normal(0, 1, 150), rng.normal(5, 1, 150)], 'ruido': rng.normal(0, 1, 300),
                           'y': ['A'] * 150 + ['B'] * 150})
        _, report, _ = er.train_model(df, 'y', ['util', 'ruido'])
        perm = report[report.section == 'importance_permutation']
        self.assertEqual(perm.name.tolist()[0], 'util')
        self.assertGreater(float(perm.value.iloc[0]), 0.3)
        self.assertLess(abs(float(perm[perm.name == 'ruido'].value.iloc[0])), 0.05)
        _, report, _ = er.train_model(df, 'y', ['util', 'ruido'], test_percent=0)           # sin evaluación, sin permutación
        self.assertEqual(len(report[report.section == 'importance_permutation']), 0)
        self.assertIn('permutacion', er.summarize_report(er.train_model(df, 'y', ['util', 'ruido'])[1]))


class AssessmentConfidenceTest(SimpleTestCase):
    """Intervalos por bootstrap de unidades de muestreo (polígonos o puntos), no de píxeles."""

    def test_more_units_give_narrower_intervals(self):
        rng = np.random.RandomState(0)

        def width(n_units, pixels_per_unit):
            # el acierto se decide por polígono entero (como en la realidad: los píxeles de una muestra se parecen)
            labels = rng.choice(['A', 'B'], n_units)
            right = rng.rand(n_units) < 0.8
            truth = np.repeat(labels, pixels_per_unit).astype(object)
            pred = np.repeat(np.where(right, labels, np.where(labels == 'A', 'B', 'A')), pixels_per_unit).astype(object)
            units = np.repeat(np.arange(n_units), pixels_per_unit)
            rows = dict(((n, v) for s, n, v in er.cluster_bootstrap_ci(truth, pred, units, ['A', 'B']) if s == 'ci'))
            return rows['accuracy:high'] - rows['accuracy:low']
        self.assertGreater(width(10, 100), width(200, 5))

    def test_whole_polygons_are_resampled_not_pixels(self):
        # 2 polígonos: uno perfecto y otro todo mal. Con píxeles independientes el intervalo saldría estrechísimo
        truth = np.array(['A'] * 500 + ['B'] * 500, dtype=object)
        pred = np.array(['A'] * 500 + ['A'] * 500, dtype=object)
        units = np.array([1] * 500 + [2] * 500)
        rows = dict(((n, v) for s, n, v in er.cluster_bootstrap_ci(truth, pred, units, ['A', 'B']) if s == 'ci'))
        self.assertLess(rows['accuracy:low'], 0.1)
        self.assertGreater(rows['accuracy:high'], 0.9)

    def test_one_unit_gives_no_interval(self):
        rows = er.cluster_bootstrap_ci(np.array(['A', 'B'], dtype=object), np.array(['A', 'A'], dtype=object),
                                       np.array([1, 1]), ['A', 'B'])
        self.assertEqual([r for r in rows if r[0] == 'ci'], [])


class AreaEstimationTest(SimpleTestCase):
    """Estimador estratificado de Olofsson et al. (2014) y muestreo estratificado."""

    NAMES = ['deforestacion', 'ganancia', 'bosque', 'no_bosque']
    MAP = [200000, 150000, 3200000, 6450000]
    MATRIX = [[66, 0, 5, 4], [0, 55, 8, 12], [1, 0, 153, 11], [2, 1, 9, 313]]

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan rasterio')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def olofsson(self):
        samples = [(self.NAMES[i], self.NAMES[j]) for i in range(4) for j in range(4) for _ in range(self.MATRIX[i][j])]
        rows, summary = er.estimate_areas(dict(zip(self.NAMES, self.MAP)), 0.09, samples)
        return {r['class']: r for r in rows}, summary

    def test_reproduces_the_worked_example_of_olofsson_2014(self):
        rows, summary = self.olofsson()
        for name, area in (('deforestacion', 21158), ('ganancia', 11686), ('bosque', 285770), ('no_bosque', 581386)):
            self.assertAlmostEqual(rows[name]['estimated_area'], area, delta=1, msg=name)        # hectáreas
        for name, users in (('deforestacion', 0.88), ('ganancia', 0.73), ('bosque', 0.93), ('no_bosque', 0.96)):
            self.assertAlmostEqual(rows[name]['users_accuracy'], users, delta=0.005)
        self.assertAlmostEqual(rows['deforestacion']['producers_accuracy'], 0.75, delta=0.005)
        self.assertAlmostEqual(summary['overall_accuracy'], 0.947, delta=0.001)
        self.assertAlmostEqual(summary['total_area'], 900000, delta=1)
        # Intervalo de la deforestación calculado a mano con la ecuación de la varianza (±1,96 · error típico)
        self.assertAlmostEqual(1.96 * rows['deforestacion']['se_area'], 6158, delta=2)
        self.assertAlmostEqual(rows['deforestacion']['producers_ci'], 0.213, delta=0.002)
        self.assertAlmostEqual(rows['deforestacion']['ci_low'], 21158 - 6158, delta=3)

    def test_estimated_areas_add_up_to_the_map_total(self):
        rows, summary = self.olofsson()
        self.assertAlmostEqual(sum(r['estimated_area'] for r in rows.values()), summary['total_area'], delta=1e-6)
        self.assertAlmostEqual(sum(r['map_area'] for r in rows.values()), summary['total_area'], delta=1e-6)

    def test_perfect_map_has_no_uncertainty(self):
        samples = [('a', 'a')] * 50 + [('b', 'b')] * 50
        rows, summary = er.estimate_areas({'a': 300, 'b': 700}, 1.0, samples)
        self.assertEqual({r['class']: round(r['estimated_area']) for r in rows}, {'a': 300, 'b': 700})
        self.assertTrue(all(r['se_area'] == 0 for r in rows))
        self.assertEqual(summary['overall_accuracy'], 1.0)

    def test_reference_class_missing_from_the_map_gets_an_area(self):
        samples = [('a', 'a')] * 45 + [('a', 'c')] * 5 + [('b', 'b')] * 50
        rows, _ = er.estimate_areas({'a': 500, 'b': 500}, 1.0, samples)
        c = [r for r in rows if r['class'] == 'c'][0]
        self.assertAlmostEqual(c['estimated_area'], 50, delta=1e-6)
        self.assertIsNone(c['users_accuracy'])

    def test_needs_two_samples_per_map_class(self):
        with self.assertRaisesRegex(ValueError, 'al menos 2 muestras'):
            er.estimate_areas({'a': 10, 'b': 10}, 1.0, [('a', 'a'), ('a', 'a'), ('b', 'b')])

    def test_stratified_sample_takes_n_per_class_and_is_reproducible(self):
        src = os.path.join(self.tmp, 'cls.tif')
        a = np.ones((60, 60), dtype=int)
        a[:, 50:] = 2                       # la clase 2 es pequeña (600 píxeles)
        a[0, 0] = 3                         # la clase 3 solo tiene 1 píxel
        a[59, :] = 0
        write_classified(src, a, {'1': 'A', '2': 'B', '3': 'C'})
        pts = er.stratified_sample_points(src, per_class=30, seed=7, block=16)
        codes = [c for c, _, _ in pts]
        self.assertEqual((codes.count(1), codes.count(2), codes.count(3)), (30, 30, 1))
        self.assertEqual(pts, er.stratified_sample_points(src, per_class=30, seed=7, block=16))
        self.assertEqual(pts, er.stratified_sample_points(src, per_class=30, seed=7, block=16))
        for code, x, y in pts:                                # cada punto cae en un píxel de su clase
            self.assertEqual(a[int(60 - y), int(x)], code)
        self.assertEqual(len(set((x, y) for _, x, y in pts)), len(pts))   # sin repetir píxel
        with self.assertRaisesRegex(ValueError, 'al menos 2'):
            er.stratified_sample_points(src, per_class=1)

    def test_stratified_sample_is_uniform_within_a_class(self):
        src = os.path.join(self.tmp, 'cls.tif')
        write_classified(src, np.ones((100, 100), dtype=int), {'1': 'A'})
        xs = []
        for seed in range(40):
            xs += [x for _, x, _ in er.stratified_sample_points(src, per_class=20, seed=seed, block=32)]
        left = sum(1 for x in xs if x < 50) / float(len(xs))
        self.assertAlmostEqual(left, 0.5, delta=0.05)          # los bloques del principio no salen favorecidos

    def test_map_class_areas_require_a_projected_crs(self):
        src = os.path.join(self.tmp, 'geo.tif')
        with rasterio.open(src, 'w', driver='GTiff', height=5, width=5, count=1, dtype='uint16', crs='EPSG:4326',
                           transform=from_origin(0, 5, 1, 1), nodata=0) as dst:
            dst.write(np.ones((1, 5, 5), dtype='uint16'))
        er.write_meta(src, {'class_map': {'1': 'A'}})
        with self.assertRaisesRegex(ValueError, 'geográficas'):
            er.map_class_areas(src)
        utm = os.path.join(self.tmp, 'utm.tif')
        write_classified(utm, np.array([[1, 1, 2], [2, 2, 0]]), {'1': 'A', '2': 'B'})
        self.assertEqual(er.map_class_areas(utm), ({'A': 2, 'B': 3}, 1.0))
