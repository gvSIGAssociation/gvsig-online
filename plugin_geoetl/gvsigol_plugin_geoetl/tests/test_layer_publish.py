# -*- coding: utf-8 -*-
"""Nodo Publicar capa: tipo de geometría, primera publicación, repetición, permisos y vuelta atrás."""
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from gvsigol_plugin_geoetl import etl_layer_publish as publish


class GeometryTypeTests(SimpleTestCase):

    def test_one_family(self):
        self.assertEqual(publish.target_geometry_type(['POINT']), 'Point')
        self.assertEqual(publish.target_geometry_type(['POINT', 'MULTIPOINT']), 'MultiPoint')
        self.assertEqual(publish.target_geometry_type(['POLYGON']), 'MultiPolygon')
        self.assertEqual(publish.target_geometry_type(['LINESTRING', 'MULTILINESTRING']), 'MultiLineString')

    def test_mixed_families_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'mezcla'):
            publish.target_geometry_type(['POINT', 'POLYGON'])
        with self.assertRaisesRegex(ValueError, 'GEOMETRYCOLLECTION'):
            publish.target_geometry_type(['GEOMETRYCOLLECTION'])


def _store():
    return SimpleNamespace(name='ds', schema='esq', connection=SimpleNamespace(name='gis'),
                           workspace=SimpleNamespace(name='ws', server_id=1), type='v_PostGIS')


def _dicc(**extra):
    base = {'id': 'node-1', 'data': ['tmp_a'], '_username': 'ana', 'datastore': 'ws/ds', 'layer-group': 'g',
            'layer-name': 'Mi Capa', 'title': 'Mi capa'}
    base.update(extra)
    return base


class RunBase(SimpleTestCase):
    """Sustituye base de datos, GeoServer y núcleo: se comprueba qué decide y en qué orden."""

    def setUp(self):
        self.store = _store()
        self.existing = None
        self.calls = []
        names = {
            'find_datastore': lambda v: self.store,
            'check_datastore_allowed': lambda u, d: None,
            '_resolve': lambda m, v, w: SimpleNamespace(name='g'),
            'source_geometry': lambda t: (['POLYGON'], 25830),
            'copy_typed': lambda *a: self.calls.append(('copy',) + a),
            'drop_copy': lambda c: self.calls.append(('drop_copy', c)),
            'table_exists': lambda d, n: False,
            'check_replace': lambda *a: self.calls.append(('check',) + a[1:]),
            '_write': lambda t, d, n, op, i: self.calls.append(('write', t, n, op)),
            '_rollback': lambda d, n: self.calls.append(('rollback', n)),
        }
        for name, fn in names.items():
            patcher = mock.patch.object(publish, name, side_effect=fn)
            patcher.start()
            self.addCleanup(patcher.stop)
        extras = [mock.patch('django.contrib.auth.get_user_model', return_value=SimpleNamespace(
                      objects=SimpleNamespace(get=lambda username: SimpleNamespace(username=username)))),
                  mock.patch('gvsigol_services.models.Layer.objects', SimpleNamespace(filter=lambda **k: SimpleNamespace(first=lambda: self.existing)))]
        self.published = mock.patch('gvsigol_services.layer_publish.publish_postgis_resource', return_value=SimpleNamespace(name='mi_capa'))
        extras.append(self.published)
        self.gs = mock.Mock()
        extras.append(mock.patch('gvsigol_services.geographic_servers.get_instance', return_value=SimpleNamespace(get_server_by_id=lambda i: self.gs)))
        self.manage = mock.patch('gvsigol_services.utils.can_manage_layer', return_value=True)
        extras.append(self.manage)
        extras.append(mock.patch.object(publish, '_refresh_extent'))
        self.mocks = [p.start() for p in extras]
        for p in extras:
            self.addCleanup(p.stop)
        self.publish_mock = self.mocks[2]
        self.manage_mock = self.mocks[4]


class FirstPublicationTests(RunBase):

    def test_writes_the_typed_copy_and_publishes(self):
        self.assertEqual(publish.output_LayerPublish(_dicc(abstract='Resumen', public='true')), [])
        self.assertIn(('copy', 'tmp_a', 'node-1_publish', 'MultiPolygon', 25830), self.calls)
        self.assertIn(('write', 'node-1_publish', 'mi_capa', 'CREATE'), self.calls)
        args = self.publish_mock.call_args[1]
        self.assertEqual((args['name'], args['title'], args['is_public'], args['has_geometry']), ('mi_capa', 'Mi capa', True, True))
        self.assertEqual(args['properties'], {'native_srs': 'EPSG:25830', 'abstract': 'Resumen'})
        self.assertEqual(self.calls[-1], ('drop_copy', 'node-1_publish'))    # la copia se borra siempre

    def test_failure_undoes_it_and_removes_the_copy(self):
        self.publish_mock.side_effect = RuntimeError('GeoServer')
        with self.assertRaises(RuntimeError):
            publish.output_LayerPublish(_dicc())
        self.assertIn(('rollback', 'mi_capa'), self.calls)
        self.assertEqual(self.calls[-1], ('drop_copy', 'node-1_publish'))

    def test_an_unpublished_table_is_not_overwritten(self):
        with mock.patch.object(publish, 'table_exists', return_value=True):
            with self.assertRaisesRegex(ValueError, 'no está publicada'):
                publish.output_LayerPublish(_dicc())
        self.assertFalse([c for c in self.calls if c[0] == 'write'])

    def test_no_rows_or_no_srid(self):
        with mock.patch.object(publish, 'source_geometry', return_value=([], None)):
            with self.assertRaisesRegex(ValueError, 'filas con geometría'):
                publish.output_LayerPublish(_dicc())
        with mock.patch.object(publish, 'source_geometry', return_value=(['POINT'], 0)):
            with self.assertRaisesRegex(ValueError, 'sistema de referencia'):
                publish.output_LayerPublish(_dicc())

    def test_missing_inputs(self):
        for extra, message in (({'data': []}, 'Conecta'), ({'_username': ''}, 'usuario'),
                               ({'layer-name': '', 'title': ''}, 'nombre')):
            with self.subTest(extra=extra), self.assertRaisesRegex(Exception, message):
                publish.output_LayerPublish(_dicc(**extra))


class ReplaceTests(RunBase):

    def setUp(self):
        super().setUp()
        self.existing = SimpleNamespace(name='mi_capa')

    def test_replaces_only_the_data(self):
        publish.output_LayerPublish(_dicc())
        check = [c for c in self.calls if c[0] == 'check']
        write = self.calls.index(('write', 'node-1_publish', 'mi_capa', 'OVERWRITE'))
        self.assertLess(self.calls.index(check[0]), write)                    # se comprueba antes de vaciar
        self.publish_mock.assert_not_called()
        self.gs.updateBoundingBoxFromData.assert_called_once()
        self.gs.clearCache.assert_called_once_with('ws', self.existing)

    def test_incompatible_data_changes_nothing(self):
        with mock.patch.object(publish, 'check_replace', side_effect=ValueError('no tiene las columnas')):
            with self.assertRaises(ValueError):
                publish.output_LayerPublish(_dicc())
        self.assertFalse([c for c in self.calls if c[0] == 'write'])

    def test_fail_option(self):
        with self.assertRaisesRegex(Exception, 'Ya existe'):
            publish.output_LayerPublish(_dicc(**{'on-existing': 'fail'}))
        self.assertEqual(self.calls, [])

    def test_needs_permission_on_the_layer(self):
        self.manage_mock.return_value = False
        with self.assertRaises(PermissionError):
            publish.output_LayerPublish(_dicc())
        self.assertFalse([c for c in self.calls if c[0] == 'write'])

    def test_a_geoserver_problem_after_writing_does_not_fail(self):
        self.gs.updateBoundingBoxFromData.side_effect = RuntimeError('caído')
        self.assertEqual(publish.output_LayerPublish(_dicc()), [])


class PermissionTests(SimpleTestCase):

    def test_needs_both_permissions(self):
        store = _store()
        for usable, ok in (([{'name': 'ds', 'workspace': 'ws'}], True), ([], False)):
            with self.subTest(usable=usable), \
                    mock.patch('gvsigol_plugin_geoetl.views.get_etl_connections_list', return_value=[]), \
                    mock.patch('gvsigol_plugin_geoetl.assistant.context.usable_datastores', return_value=usable):
                if ok:
                    publish.check_datastore_allowed(SimpleNamespace(), store)
                else:
                    with self.assertRaises(PermissionError):
                        publish.check_datastore_allowed(SimpleNamespace(), store)
