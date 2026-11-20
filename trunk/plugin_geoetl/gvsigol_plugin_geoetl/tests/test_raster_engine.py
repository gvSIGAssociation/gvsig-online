# -*- coding: utf-8 -*-
"""
Prueba de integración de extremo a extremo: motor de ejecución real + PostGIS + GeoServer.

No se ejecuta por defecto. Crea (y borra al terminar) un workspace, un grupo y capas temporales con el
prefijo "zz_it", tablas "zzit_*" y un modelo guardado. Necesita un GeoServer funcionando. Dentro del
contenedor del backend (con PYTHONPATH y GVSIGOL_PLUGINS del proceso de la aplicación):

    GEOETL_INTEGRATION_GEOSERVER=1 python manage.py test gvsigol_plugin_geoetl.tests.test_raster_engine

Comprueba, ejecutando canvas completos como lo haría el editor:
  1. flujo completo: combinar ráster, índice, muestrear, entrenar (validación por polígonos), guardar el
     modelo, predecir, limpiar, vectorizar, evaluar con muestras independientes y publicar clasificación y
     confianza;
  2. reutilización: un canvas nuevo que usa el modelo guardado y reemplaza la capa;
  3. el estilo conserva los colores de las clases al reemplazar la capa con clases nuevas;
  4. un canvas guardado antes de los últimos cambios de puertos sigue funcionando.
"""
import glob
import io
import os
import shutil
import unittest

import numpy as np

ENABLED = bool(os.environ.get('GEOETL_INTEGRATION_GEOSERVER'))

try:
    import psycopg2
    import rasterio
    import requests
    from rasterio.transform import from_origin
    DEPS = True
except ImportError:  # pragma: no cover
    DEPS = False

PFX = 'zzit'
WS = 'zz_it_ws'
CRS = 'EPSG:25830'


def box_wkt(x0, y0, x1, y1):
    return 'POLYGON((%d %d,%d %d,%d %d,%d %d,%d %d))' % (x0, y0, x1, y0, x1, y1, x0, y1, x0, y0)


@unittest.skipUnless(ENABLED and DEPS, 'Define GEOETL_INTEGRATION_GEOSERVER=1 (y un GeoServer disponible)')
class EngineFlowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import django
        from django.conf import settings
        from django.contrib.auth import get_user_model
        from gvsigol_services import geographic_servers, utils as services_utils
        from gvsigol_services.models import Layer, LayerGroup, Server, Workspace
        from gvsigol_plugin_geoetl import etl_models, etl_raster, tasks, views  # noqa: F401 (views antes que tasks)
        from gvsigol_plugin_geoetl.models import ETLstatus
        from gvsigol_plugin_geoetl.settings import GEOETL_DB

        cls.tasks, cls.er, cls.em = tasks, etl_raster, etl_models
        cls.ETLstatus, cls.Layer, cls.LayerGroup, cls.Workspace = ETLstatus, Layer, LayerGroup, Workspace
        cls.services_utils, cls.DB = services_utils, GEOETL_DB
        cls.user = get_user_model().objects.filter(is_superuser=True).first()
        cls.server = Server.objects.first()
        cls.gs = geographic_servers.get_instance().get_server_by_id(cls.server.id)
        cls.data_dir = os.path.join(settings.FILEMANAGER_DIRECTORY, 'zz_it_tmp')
        os.makedirs(cls.data_dir, exist_ok=True)
        cls.status_name = 'current_canvas.' + cls.user.username
        cls.had_status = ETLstatus.objects.filter(name=cls.status_name).exists()
        cls.conn = psycopg2.connect(user=GEOETL_DB['user'], password=GEOETL_DB['password'], host=GEOETL_DB['host'],
                                    port=GEOETL_DB['port'], database=GEOETL_DB['database'])
        cls.conn.autocommit = True
        cls.cur = cls.conn.cursor()
        assert not Workspace.objects.filter(name=WS).exists(), 'ya existe el workspace de prueba %s' % WS
        ref = Workspace.objects.first()
        cls.ws = services_utils.create_workspace(cls.server.id, WS, 'http://' + WS, dict(
            server=cls.server, name=WS, description='temporal', uri='http://' + WS, wms_endpoint=ref.wms_endpoint,
            wfs_endpoint=ref.wfs_endpoint, wcs_endpoint=ref.wcs_endpoint, wmts_endpoint=ref.wmts_endpoint,
            cache_endpoint=ref.cache_endpoint, created_by=cls.user.username, is_public=False), cls.user.username)
        cls.group = LayerGroup(name=WS + '_group', title=WS, server_id=cls.server.id, created_by=cls.user.username)
        cls.group.save()
        cls.make_data()

    @classmethod
    def tearDownClass(cls):
        try:
            try:
                cls.gs.deleteGeoserverLayerGroup(cls.group)
            except Exception:
                pass
            for layer in cls.Layer.objects.filter(datastore__workspace__name=WS):
                for fn in (lambda: cls.gs.deleteResource(layer.datastore.workspace, layer.datastore, layer),
                           lambda: cls.gs.deleteLayerStyles(layer), lambda: cls.gs.deleteLayerRules(layer)):
                    try:
                        fn()
                    except Exception:
                        pass
                layer.delete()
            try:
                cls.gs.deleteGeoserverLayerGroup(cls.group)
            except Exception:
                pass
            cls.group.delete()
            cls.services_utils._workspace_delete(cls.ws, delete_data=True, reload_nodes=True)
        except Exception as e:  # pragma: no cover
            print('Error limpiando GeoServer/gvSIG:', type(e).__name__, e)
        cls.cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_name LIKE %s",
                        (cls.DB['schema'], PFX + '%'))
        for (t,) in cls.cur.fetchall():
            cls.cur.execute('DROP TABLE IF EXISTS "%s"."%s"' % (cls.DB['schema'], t))
        from gvsigol_plugin_geoetl.models import TempETLTable
        TempETLTable.objects.filter(table_name__startswith=PFX).delete()
        shutil.rmtree(cls.data_dir, True)
        for p in glob.glob(os.path.join(cls.er.artifacts_root(), PFX + '*')):
            os.remove(p)
        for model in cls.em.list_models(cls.user.username):
            if model['name'].startswith(PFX):
                cls.em.delete_model(cls.user.username, model['name'])
        if not cls.had_status:
            cls.ETLstatus.objects.filter(name=cls.status_name).delete()
        cls.conn.close()

    # ------------------------------------------------------------------ datos
    @classmethod
    def make_data(cls):
        rng = np.random.RandomState(0)
        data = np.zeros((3, 40, 40), dtype='float32')
        data[:, :, :20] = rng.normal(50, 5, (3, 40, 20))
        data[:, :, 20:] = rng.normal(200, 5, (3, 40, 20))
        cls.tif = os.path.join(cls.data_dir, 'ortho.tif')
        with rasterio.open(cls.tif, 'w', driver='GTiff', height=40, width=40, count=3, dtype='float32', crs=CRS,
                           transform=from_origin(500000, 4300040, 1, 1), nodata=-9999) as dst:
            dst.write(data)
        # modelo del terreno con otra resolución (0,5 m): la banda vale la coordenada X
        xs = 500000 + (np.arange(80) + 0.5) * 0.5
        cls.dem = os.path.join(cls.data_dir, 'dem.tif')
        with rasterio.open(cls.dem, 'w', driver='GTiff', height=80, width=80, count=1, dtype='float32', crs=CRS,
                           transform=from_origin(500000, 4300040, 0.5, 0.5), nodata=-9999) as dst:
            dst.write(np.tile(xs, (80, 1)).astype('float32')[None])

        def csv(name, boxes):
            path = os.path.join(cls.data_dir, name)
            with open(path, 'w') as f:
                f.write('clase;wkt\n')
                for label, b in boxes:
                    f.write('%s;%s\n' % (label, box_wkt(*b)))
            return path
        cls.train_csv = csv('train.csv', [('Clase A', (500002, 4300002, 500012, 4300012)),
                                          ('Clase A', (500002, 4300020, 500012, 4300030)),
                                          ('Clase B', (500026, 4300002, 500036, 4300012)),
                                          ('Clase B', (500026, 4300020, 500036, 4300030))])
        cls.valid_csv = csv('valid.csv', [('Clase A', (500013, 4300013, 500018, 4300018)),
                                          ('Clase B', (500037, 4300031, 500039, 4300038))])

    # ------------------------------------------------------------------ canvas
    _n = [0]

    @staticmethod
    def node(ntype, nid, params, n_in, n_out):
        ports = [{'name': 'input_%s_%d' % (nid, i)} for i in range(n_in)]
        ports += [{'name': 'output_%s_%d' % (nid, i)} for i in range(n_out)]
        return {'type': ntype, 'id': nid, 'entities': [{'parameters': [params] if params is not None else []}], 'ports': ports}

    def edge(self, src, sp, dst, dp):
        self._n[0] += 1
        return {'type': 'draw2d.Connection', 'id': 'e%d' % self._n[0],
                'source': {'node': src, 'port': 'output_%s_%d' % (src, sp)},
                'target': {'node': dst, 'port': 'input_%s_%d' % (dst, dp)}}

    def run_canvas(self, canvas):
        """Ejecuta el canvas con el motor real y devuelve los nombres de tabla que iba a borrar al final."""
        captured, real = [], self.tasks.delete_tables
        self.tasks.delete_tables = lambda nodes: captured.append(nodes)
        try:
            self.tasks._run_canvas_background_impl({'concat': False, 'id_ws': None, 'jsonCanvas': canvas,
                                                    'username': self.user.username, 'parameters': None})
        finally:
            self.tasks.delete_tables = real
        status = self.ETLstatus.objects.filter(name=self.status_name).first()
        self.assertEqual(status.status, 'Success', status.message)
        real(captured[0])           # la limpieza normal del motor, después de leer lo que hace falta
        return status

    def query(self, sql_text, *args):
        self.cur.execute(sql_text, args)
        return self.cur.fetchall()

    def wms_pixel(self, layer, x, y):
        from PIL import Image
        base = self.gs.rest_catalog.service_url.replace('/rest', '')
        r = requests.get(base + '/wms', params=dict(
            service='WMS', version='1.1.1', request='GetMap', layers='%s:%s' % (WS, layer), styles='',
            bbox='500000,4300000,500040,4300040', width=40, height=40, srs='EPSG:25830', format='image/png',
            transparent='true'), auth=(self.gs.user, self.gs.password), timeout=60, verify=False)
        return Image.open(io.BytesIO(r.content)).convert('RGBA').getpixel((x, y))

    def csv_nodes(self, prefix, path):
        return [self.node('input_Csv', prefix + '_csv', {'csv-file': 'file://' + path, 'separator': ';', 'header': '0',
                                                         'schema-option': 'has-schema', 'reading': 'single', 'move': '', 'folder': ''}, 0, 1),
                self.node('trans_WktGeom', prefix + '_wkt', {'attr': 'wkt', 'epsg': '25830'}, 1, 1)], \
               [self.edge(prefix + '_csv', 0, prefix + '_wkt', 0)]

    # ------------------------------------------------------------------ pruebas
    def test_1_full_flow_then_reuse_of_the_saved_model_then_style_stays_stable(self):
        e = self.edge
        model_name = PFX + '_modelo'
        train_nodes, train_edges = self.csv_nodes(PFX + 't', self.train_csv)
        valid_nodes, valid_edges = self.csv_nodes(PFX + 'v', self.valid_csv)
        canvas = train_nodes + valid_nodes + [
            self.node('input_Raster', PFX + '_ras', {'raster-file': 'file://' + self.tif, 'band-names': 'Rojo,Verde,IR'}, 0, 1),
            self.node('input_Raster', PFX + '_dem', {'raster-file': 'file://' + self.dem, 'band-names': 'Altura'}, 0, 1),
            self.node('trans_RasterStack', PFX + '_stk', {'resampling': 'bilinear', 'prefix-1': '', 'prefix-2': ''}, 4, 1),
            self.node('trans_RasterIndex', PFX + '_idx', {'index': 'ndvi', 'band-1': 'ir', 'band-2': 'rojo', 'band-3': '',
                                                           'name': 'ndvi', 'scale': '1', 'savi-l': '0.5'}, 1, 1),
            self.node('trans_RasterSample', PFX + '_sam', {'class-attr': 'clase', 'max-per-class': '', 'seed': '42'}, 2, 1),
            self.node('trans_RandomForest', PFX + '_rf', {
                'target': 'clase', 'features': ['rojo', 'verde', 'ir', 'altura', 'ndvi'], 'problem': 'auto',
                'n-estimators': '50', 'max-depth': '', 'min-samples-leaf': '1', 'test-percent': '20', 'seed': '42',
                'validation': 'polygon', 'folds': '4', 'block-size': ''}, 1, 3),
            self.node('output_ModelSave', PFX + '_save', {'model-name': model_name, 'description': 'prueba', 'on-existing': 'version'}, 1, 0),
            self.node('trans_RasterPredict', PFX + '_pre', {'configured': 'true'}, 2, 2),
            self.node('trans_RasterMajority', PFX + '_maj', {'mode': 'majority', 'window': '3', 'iterations': '1',
                                                             'min-pixels': '4', 'connectivity': '4'}, 1, 1),
            self.node('trans_RasterPolygonize', PFX + '_pol', {'classes': 'Clase A', 'min-area': '1', 'simplify': '0',
                                                              'connectivity': '4'}, 1, 1),
            self.node('trans_ClassAssess', PFX + '_as', {'class-attr': 'clase'}, 2, 2),
            self.node('output_RasterPublish', PFX + '_pub', {
                'workspace': WS, 'layer-group': WS + '_group', 'title': 'Clasificación', 'layer-name': 'it_clasificacion',
                'on-existing': 'replace', 'public': '', 'update-style': 'auto', 'band': '', 'ramp-min': '', 'ramp-max': '',
                'abstract': 'prueba'}, 1, 0),
            self.node('output_RasterPublish', PFX + '_pub2', {
                'workspace': WS, 'layer-group': WS + '_group', 'title': 'Confianza', 'layer-name': 'it_confianza',
                'on-existing': 'replace', 'public': '', 'update-style': 'auto', 'band': '', 'ramp-min': '', 'ramp-max': '',
                'abstract': ''}, 1, 0),
        ] + train_edges + valid_edges + [
            e(PFX + '_ras', 0, PFX + '_stk', 0), e(PFX + '_dem', 0, PFX + '_stk', 1),
            e(PFX + '_stk', 0, PFX + '_idx', 0),
            e(PFX + '_idx', 0, PFX + '_sam', 0), e(PFX + 't_wkt', 0, PFX + '_sam', 1),
            e(PFX + '_sam', 0, PFX + '_rf', 0),
            e(PFX + '_rf', 1, PFX + '_save', 0),
            e(PFX + '_idx', 0, PFX + '_pre', 0), e(PFX + '_rf', 1, PFX + '_pre', 1),
            e(PFX + '_pre', 0, PFX + '_maj', 0),
            e(PFX + '_maj', 0, PFX + '_pol', 0), e(PFX + '_maj', 0, PFX + '_pub', 0),
            e(PFX + '_maj', 0, PFX + '_as', 0), e(PFX + 'v_wkt', 0, PFX + '_as', 1),
            e(PFX + '_pre', 1, PFX + '_pub2', 0),
        ]
        captured = []
        real_delete = self.tasks.delete_tables
        self.tasks.delete_tables = lambda nodes: captured.append(nodes)
        try:
            self.tasks._run_canvas_background_impl({'concat': False, 'id_ws': None, 'jsonCanvas': canvas,
                                                    'username': self.user.username, 'parameters': None})
            status = self.ETLstatus.objects.filter(name=self.status_name).first()
            self.assertEqual(status.status, 'Success', status.message)

            # --- informes y tablas producidas
            rows = dict(((s, n), v) for s, n, v in self.query(
                'SELECT section, name, value FROM "%s"."%s_rf_0"' % (self.DB['schema'], PFX)))
            self.assertEqual(rows[('training', 'folds')], 4)
            self.assertGreater(rows[('metric', 'accuracy')], 0.9)
            matrix = self.query('SELECT * FROM "%s"."%s_rf_2" ORDER BY real' % (self.DB['schema'], PFX))
            self.assertEqual([r[0] for r in matrix], ['Clase A', 'Clase B'])
            self.assertEqual(self.query('SELECT class_name, ST_SRID(wkb_geometry) FROM "%s"."%s_pol"' % (self.DB['schema'], PFX)),
                             [('Clase A', 25830)])
            assess = dict(((s, n), v) for s, n, v in self.query(
                'SELECT section, name, value FROM "%s"."%s_as_0"' % (self.DB['schema'], PFX)))
            self.assertEqual(assess[('metric', 'accuracy')], 1.0)
            self.assertGreater(assess[('assessment', 'validation_pixels')], 0)
        finally:
            self.tasks.delete_tables = real_delete
        real_delete(captured[0])
        self.assertEqual(glob.glob(os.path.join(self.er.artifacts_root(), PFX + '_*')), [],
                         'el motor debe borrar los artefactos temporales')

        # --- capas publicadas
        layer = self.Layer.objects.get(datastore__workspace=self.ws, name='it_clasificacion')
        self.assertEqual(layer.abstract, 'prueba')
        left, right = self.wms_pixel('it_clasificacion', 5, 20), self.wms_pixel('it_clasificacion', 35, 20)
        self.assertNotEqual(left[:3], right[:3])
        self.assertNotEqual(self.wms_pixel('it_confianza', 10, 20)[3], 0)

        # --- el modelo quedó guardado y firmado
        saved = [m for m in self.em.list_models(self.user.username) if m['name'] == model_name]
        self.assertEqual(len(saved[0]['versions']), 1)
        self.assertEqual(saved[0]['versions'][0]['features'], ['rojo', 'verde', 'ir', 'altura', 'ndvi'])

        # --- segundo canvas: reutiliza el modelo guardado y reemplaza la capa (sin entrenar)
        reuse = [
            self.node('input_Raster', PFX + '_ras', {'raster-file': 'file://' + self.tif, 'band-names': 'Rojo,Verde,IR'}, 0, 1),
            self.node('input_Raster', PFX + '_dem', {'raster-file': 'file://' + self.dem, 'band-names': 'Altura'}, 0, 1),
            self.node('trans_RasterStack', PFX + '_stk', {'resampling': 'bilinear'}, 4, 1),
            self.node('trans_RasterIndex', PFX + '_idx', {'index': 'ndvi', 'band-1': 'ir', 'band-2': 'rojo', 'band-3': '',
                                                           'name': 'ndvi', 'scale': '1', 'savi-l': '0.5'}, 1, 1),
            self.node('input_Model', PFX + '_mod', {'model-name': model_name, 'model-version': 'latest'}, 0, 1),
            self.node('trans_RasterPredict', PFX + '_pre', {'configured': 'true'}, 2, 2),
            self.node('output_RasterPublish', PFX + '_pub', {
                'workspace': WS, 'layer-group': WS + '_group', 'title': 'Clasificación', 'layer-name': 'it_clasificacion',
                'on-existing': 'replace', 'public': '', 'update-style': 'auto', 'band': '', 'ramp-min': '', 'ramp-max': '',
                'abstract': ''}, 1, 0),
            e(PFX + '_ras', 0, PFX + '_stk', 0), e(PFX + '_dem', 0, PFX + '_stk', 1), e(PFX + '_stk', 0, PFX + '_idx', 0),
            e(PFX + '_idx', 0, PFX + '_pre', 0), e(PFX + '_mod', 0, PFX + '_pre', 1), e(PFX + '_pre', 0, PFX + '_pub', 0),
        ]
        self.run_canvas(reuse)
        self.assertEqual(self.Layer.objects.filter(datastore__workspace=self.ws, name='it_clasificacion').count(), 1)
        self.assertEqual(self.wms_pixel('it_clasificacion', 5, 20)[:3], left[:3])        # mismo resultado, mismos colores
        self.assertEqual(self.wms_pixel('it_clasificacion', 35, 20)[:3], right[:3])

        # --- predecir una tabla con el modelo guardado, conservando la geometría
        self.cur.execute('CREATE TABLE "%s"."%s_tab" (rojo double precision, verde double precision, ir double precision, '
                         'altura double precision, ndvi double precision, wkb_geometry geometry(Point, 25830))' % (self.DB['schema'], PFX))
        for i in range(10):
            v = 50.0 if i < 5 else 200.0
            self.cur.execute('INSERT INTO "%s"."%s_tab" VALUES (%%s,%%s,%%s,%%s,%%s,ST_SetSRID(ST_MakePoint(%%s,4300000),25830))'
                             % (self.DB['schema'], PFX), (v, v, v, 500000.0 + i * 4, 0.0, 500000 + i))
        payload, _ = self.em.load_verified(self.user.username, model_name)
        model_path = self.er.new_artifact_path(PFX + '_m', '.joblib')
        with open(model_path, 'wb') as f:
            f.write(payload)
        try:
            self.er.trans_TablePredict({'id': PFX + '_tp', 'data': [PFX + '_tab', model_path], 'column': 'clase_prevista'})
        finally:
            self.er.remove_artifact(model_path)
        got = self.query('SELECT clase_prevista, ST_SRID(wkb_geometry) FROM "%s"."%s_tp" ORDER BY altura' % (self.DB['schema'], PFX))
        self.assertEqual({r[1] for r in got}, {25830})
        self.assertEqual(len({r[0] for r in got}), 2)

        # --- reemplazo con clases nuevas: las clases que ya estaban conservan su color
        from gvsigol_plugin_geoetl import etl_raster_publish as pub
        from gvsigol_symbology.models import ColorMap, ColorMapEntry, Style, StyleLayer
        layer = self.Layer.objects.get(datastore__workspace=self.ws, name='it_clasificacion')

        def colors():
            style = Style.objects.get(name='%s_it_clasificacion_classes' % WS, pk__in=StyleLayer.objects.filter(layer=layer).values('style'))
            cmap = ColorMap.objects.get(rastersymbolizer__rule__style=style)
            return {e.label: e.color for e in ColorMapEntry.objects.filter(color_map=cmap)}
        before = colors()
        self.assertEqual(sorted(before), ['Clase A', 'Clase B'])
        three = os.path.join(self.data_dir, 'three.tif')
        arr = np.ones((40, 40), dtype='uint16')
        arr[:, 14:27] = 2
        arr[:, 27:] = 3
        with rasterio.open(three, 'w', driver='GTiff', height=40, width=40, count=1, dtype='uint16', crs=CRS,
                           transform=from_origin(500000, 4300040, 1, 1), nodata=0) as dst:
            dst.write(arr, 1)
        self.er.write_meta(three, {'problem': 'classification', 'class_map': {'1': 'Clase A', '2': 'Aaa nueva', '3': 'Clase B'}})
        pub.publish_raster_layer(self.user, three, self.ws, self.group, 'it_clasificacion', replace=True, update_style='auto')
        after = colors()
        self.assertEqual(sorted(after), ['Aaa nueva', 'Clase A', 'Clase B'])
        self.assertEqual(after['Clase A'], before['Clase A'])           # no cambian de color aunque cambie el orden
        self.assertEqual(after['Clase B'], before['Clase B'])
        self.assertNotIn(after['Aaa nueva'], (before['Clase A'], before['Clase B']))
        # con "no tocar" el estilo se queda como estaba
        self.er.write_meta(three, {'problem': 'classification', 'class_map': {'1': 'X', '2': 'Y', '3': 'Z'}})
        pub.publish_raster_layer(self.user, three, self.ws, self.group, 'it_clasificacion', replace=True, update_style='no')
        self.assertEqual(sorted(colors()), ['Aaa nueva', 'Clase A', 'Clase B'])

    def test_2_a_canvas_saved_before_the_port_changes_still_runs(self):
        """Random Forest con 2 salidas y Predecir con 1, como se guardaron antes de añadir la matriz y la confianza."""
        e = self.edge
        train_nodes, train_edges = self.csv_nodes(PFX + 'o', self.train_csv)
        canvas = train_nodes + [
            self.node('input_Raster', PFX + '_ras', {'raster-file': 'file://' + self.tif, 'band-names': 'Rojo,Verde,IR'}, 0, 1),
            self.node('trans_RasterSample', PFX + '_sam', {'class-attr': 'clase', 'max-per-class': '', 'seed': '42'}, 2, 1),
            self.node('trans_RandomForest', PFX + '_rf', {
                'target': 'clase', 'features': ['rojo', 'verde', 'ir'], 'problem': 'auto', 'n-estimators': '20',
                'max-depth': '', 'min-samples-leaf': '1', 'test-percent': '20', 'seed': '42'}, 1, 2),   # sin validation/folds
            self.node('trans_RasterPredict', PFX + '_pre', {'configured': 'true'}, 2, 1),
            self.node('trans_RasterPolygonize', PFX + '_pol', {'classes': '', 'min-area': '0', 'simplify': '0', 'connectivity': '4'}, 1, 1),
        ] + train_edges + [
            e(PFX + '_ras', 0, PFX + '_sam', 0), e(PFX + 'o_wkt', 0, PFX + '_sam', 1), e(PFX + '_sam', 0, PFX + '_rf', 0),
            e(PFX + '_ras', 0, PFX + '_pre', 0), e(PFX + '_rf', 1, PFX + '_pre', 1), e(PFX + '_pre', 0, PFX + '_pol', 0),
        ]
        self.run_canvas(canvas)

    def test_3_unconfigured_node_stops_with_a_clear_message(self):
        canvas = [self.node('input_Raster', PFX + '_ras', {'raster-file': 'file://' + self.tif, 'band-names': ''}, 0, 1), None]
        self.tasks._run_canvas_background_impl({'concat': False, 'id_ws': None, 'jsonCanvas': canvas,
                                                'username': self.user.username, 'parameters': None})
        status = self.ETLstatus.objects.filter(name=self.status_name).first()
        self.assertEqual(status.status, 'Error')
        self.assertIn('nodos sin configurar', status.message)
