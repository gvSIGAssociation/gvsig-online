# -*- coding: utf-8 -*-
"""Modelos guardados: almacenamiento versionado, firma y verificación (sin BD ni GeoServer)."""
import json
import os
import shutil
import tempfile
import threading
from unittest import mock

import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from gvsigol_plugin_geoetl import etl_models as em
from gvsigol_plugin_geoetl import etl_raster as er

try:
    import joblib
    import sklearn  # noqa: F401
    DEPS = True
except ImportError:  # pragma: no cover
    DEPS = False


def train(seed=1):
    rng = np.random.RandomState(seed)
    df = pd.DataFrame({'x': np.r_[rng.normal(0, 1, 100), rng.normal(10, 1, 100)], 'y': ['A'] * 100 + ['B'] * 100})
    bundle, report, _ = er.train_model(df, 'y', ['x'], n_estimators=20)
    return bundle, report


class ModelsTestCase(SimpleTestCase):

    def setUp(self):
        if not DEPS:
            self.skipTest('Faltan scikit-learn / joblib')
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        patcher = mock.patch.multiple(em.plugin_settings, create=True, ETL_MODELS_DIR=self.root,
                                      ETL_MODELS_KEEP_VERSIONS=10, ETL_MODELS_SIGNING_KEY='clave-de-prueba')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.artifacts = []
        self.addCleanup(lambda: [er.remove_artifact(p) for p in self.artifacts])

    def model_file(self, seed=1, **meta):
        bundle, report = train(seed)
        path = er.new_artifact_path('zzmodel', '.joblib')
        joblib.dump(bundle, path)
        info = {'problem': 'classification', 'features': ['x'], 'classes': ['A', 'B'], 'target': 'y',
                'metrics': {'accuracy': 0.99}, 'rows': 200}
        info.update(meta)
        er.write_meta(path, info)
        self.artifacts.append(path)
        return path, bundle

    def save(self, owner='ana', name='Cobertura 2024', **kw):
        path, bundle = self.model_file()
        return em.save_model(owner, name, path, er.read_meta(path), **kw), bundle

    def paths(self, owner='ana', name='cobertura_2024', version=1):
        directory = em.model_dir(owner, name)
        return em._version_paths(directory, version)


class SaveAndLoadTest(ModelsTestCase):

    def test_roundtrip_gives_the_same_predictions(self):
        meta, bundle = self.save(description='Prueba')
        self.assertEqual((meta['name'], meta['version'], meta['owner']), ('cobertura_2024', 1, 'ana'))
        payload, loaded_meta = em.load_verified('ana', 'Cobertura 2024')
        self.assertEqual(loaded_meta['features'], ['x'])
        self.assertEqual(loaded_meta['metrics'], {'accuracy': 0.99})
        restored = joblib.load(__import__('io').BytesIO(payload))
        X = np.array([[0.1], [9.5], [5.0]])
        self.assertEqual(list(restored['model'].predict(X)), list(bundle['model'].predict(X)))
        np.testing.assert_allclose(restored['model'].predict_proba(X), bundle['model'].predict_proba(X))

    def test_files_live_in_a_private_per_user_folder(self):
        self.save('ana')
        self.save('Ana.García@x.es')
        joblib_path, json_path = self.paths('ana')
        self.assertTrue(os.path.isfile(joblib_path) and os.path.isfile(json_path))
        folders = os.listdir(self.root)
        self.assertEqual(len(folders), 2)
        self.assertTrue(all('-' in f and f.startswith(('ana-', 'Ana.Garc')) for f in folders), folders)

    def test_versions_increment_and_latest_is_default(self):
        for _ in range(3):
            self.save()
        self.assertEqual([v['version'] for v in em.list_models('ana')[0]['versions']], [1, 2, 3])
        self.assertEqual(em.load_verified('ana', 'cobertura_2024')[1]['version'], 3)
        self.assertEqual(em.load_verified('ana', 'cobertura_2024', 'latest')[1]['version'], 3)
        self.assertEqual(em.load_verified('ana', 'cobertura_2024', 2)[1]['version'], 2)
        self.assertEqual(em.load_verified('ana', 'cobertura_2024', '1')[1]['version'], 1)

    def test_old_versions_are_pruned(self):
        with mock.patch.object(em.plugin_settings, 'ETL_MODELS_KEEP_VERSIONS', 2, create=True):
            for _ in range(4):
                self.save()
        self.assertEqual([v['version'] for v in em.list_models('ana')[0]['versions']], [3, 4])
        self.assertFalse(os.path.exists(self.paths(version=1)[0]))

    def test_replace_and_fail(self):
        self.save()
        self.save()
        meta, _ = self.save(on_existing='replace')
        self.assertEqual(meta['version'], 3)
        self.assertEqual([v['version'] for v in em.list_models('ana')[0]['versions']], [3])
        with self.assertRaisesRegex(em.ModelError, 'Ya existe un modelo'):
            self.save(on_existing='fail')
        meta, _ = self.save(name='otro', on_existing='fail')            # un nombre nuevo sí se puede crear
        self.assertEqual(meta['version'], 1)
        with self.assertRaisesRegex(em.ModelError, 'desconocida'):
            self.save(on_existing='raro')

    def test_each_user_only_sees_their_own_models(self):
        self.save('ana')
        self.assertEqual(em.list_models('luis'), [])
        with self.assertRaisesRegex(em.ModelError, 'No existe el modelo'):
            em.load_verified('luis', 'cobertura_2024')
        self.assertEqual([m['name'] for m in em.list_models('ana')], ['cobertura_2024'])

    def test_concurrent_saves_get_different_versions(self):
        path, _ = self.model_file()
        info, results = er.read_meta(path), []

        def worker():
            results.append(em.save_model('ana', 'paralelo', path, info)['version'])

        threads = [threading.Thread(target=worker) for _ in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(results), [1, 2, 3, 4, 5, 6])
        for v in range(1, 7):
            em.load_verified('ana', 'paralelo', v)

    def test_no_temporary_files_are_left(self):
        self.save()
        directory = em.model_dir('ana', 'cobertura_2024')
        self.assertEqual(sorted(f for f in os.listdir(directory) if f != '.lock'), ['v0001.joblib', 'v0001.json'])

    def test_missing_model_and_version(self):
        with self.assertRaisesRegex(em.ModelError, 'No existe el modelo'):
            em.load_verified('ana', 'nada')
        self.save()
        with self.assertRaisesRegex(em.ModelError, 'no tiene la versión 9'):
            em.load_verified('ana', 'cobertura_2024', 9)
        with self.assertRaisesRegex(em.ModelError, 'Versión de modelo no válida'):
            em.load_verified('ana', 'cobertura_2024', 'abc')

    def test_save_requires_a_model_file(self):
        with self.assertRaisesRegex(em.ModelError, 'No hay un modelo'):
            em.save_model('ana', 'x', os.path.join(self.root, 'no-existe.joblib'))


class SecurityTest(ModelsTestCase):

    def setUp(self):
        super().setUp()
        self.save()
        self.joblib_path, self.json_path = self.paths()

    def assert_rejected(self, pattern):
        # Lo importante: no se llega a deserializar nada de un modelo que no pasa la verificación
        with mock.patch('joblib.load') as load, mock.patch('pickle.loads') as loads:
            with self.assertRaisesRegex(em.ModelError, pattern):
                em.load_verified('ana', 'cobertura_2024')
            load.assert_not_called()
            loads.assert_not_called()

    def rewrite_meta(self, **changes):
        with open(self.json_path, encoding='utf-8') as f:
            meta = json.load(f)
        meta.update(changes)
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f)

    def test_modified_model_file_is_rejected(self):
        with open(self.joblib_path, 'ab') as f:
            f.write(b'\x00')
        self.assert_rejected('dañado o fue modificado')

    def test_swapped_model_file_is_rejected(self):
        evil = os.path.join(self.root, 'evil.joblib')
        import pickle

        class Boom:
            def __reduce__(self):
                return (os.system, ('echo pwned > %s/pwned' % self.root_dir,))
        Boom.root_dir = self.root
        with open(evil, 'wb') as f:
            pickle.dump(Boom(), f)
        shutil.copyfile(evil, self.joblib_path)
        self.assert_rejected('dañado o fue modificado')
        self.assertFalse(os.path.exists(os.path.join(self.root, 'pwned')))

    def test_modified_metadata_is_rejected(self):
        self.rewrite_meta(features=['otra'])
        self.assert_rejected('firma no es válida')

    def test_unsigned_or_forged_signature_is_rejected(self):
        self.rewrite_meta(signature='0' * 64)
        self.assert_rejected('firma no es válida')
        with open(self.json_path, encoding='utf-8') as f:
            meta = json.load(f)
        del meta['signature']
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f)
        self.assert_rejected('firma no es válida')

    def test_signature_from_another_key_is_rejected(self):
        with mock.patch.object(em.plugin_settings, 'ETL_MODELS_SIGNING_KEY', 'otra-clave', create=True):
            self.assert_rejected('firma no es válida')

    def test_model_copied_into_another_users_folder_is_rejected(self):
        target = em.model_dir('luis', 'cobertura_2024', create=True)
        for src, dst in zip(self.paths(), em._version_paths(target, 1)):
            shutil.copyfile(src, dst)
        with mock.patch('joblib.load') as load:
            with self.assertRaisesRegex(em.ModelError, 'firma no es válida'):
                em.load_verified('luis', 'cobertura_2024')
            load.assert_not_called()
        self.assertEqual(em.list_models('luis'), [])          # ni siquiera se lista

    def test_model_renamed_or_renumbered_is_rejected(self):
        directory = em.model_dir('ana', 'cobertura_2024')
        for ext in ('.joblib', '.json'):
            shutil.copyfile(os.path.join(directory, 'v0001' + ext), os.path.join(directory, 'v0007' + ext))
        with self.assertRaisesRegex(em.ModelError, 'firma no es válida'):
            em.load_verified('ana', 'cobertura_2024', 7)

    def test_symlinked_model_file_is_rejected(self):
        real = os.path.join(self.root, 'real.joblib')
        shutil.move(self.joblib_path, real)
        os.symlink(real, self.joblib_path)
        self.assert_rejected('no es válido')

    def test_unreadable_metadata_and_missing_file(self):
        with open(self.json_path, 'w') as f:
            f.write('{no es json')
        self.assert_rejected('no se pueden leer')
        self.save(name='otro')
        os.remove(self.paths('ana', 'otro')[0])
        with self.assertRaisesRegex(em.ModelError, 'Falta el fichero'):
            em.load_verified('ana', 'otro')

    def test_unsigned_listing_hides_forged_versions(self):
        self.rewrite_meta(description='cambiado')
        self.assertEqual(em.list_models('ana'), [])

    def test_names_cannot_escape_the_models_directory(self):
        for bad in ('../../etc/passwd', '/abs/path', 'a/../../b', '....//x'):
            directory = em.model_dir('ana', bad)
            self.assertTrue(os.path.realpath(directory).startswith(os.path.realpath(self.root) + os.sep), bad)
        for empty in ('..', '.', '/', '../..'):
            with self.assertRaises(em.ModelError):
                em.model_dir('ana', empty)
        with self.assertRaisesRegex(em.ModelError, 'nombre'):
            em.safe_model_name('   ')
        with self.assertRaisesRegex(em.ModelError, 'nombre'):
            em.safe_model_name('../..')
        for bad_owner in ('../x', '/etc', 'a/b', '..'):
            self.assertNotIn(os.sep, em.owner_dir_name(bad_owner))
            self.assertFalse(em.owner_dir_name(bad_owner).startswith('.'))
        with self.assertRaisesRegex(em.ModelError, 'usuario'):
            em.owner_dir_name('')

    def test_similar_usernames_do_not_share_a_folder(self):
        self.assertNotEqual(em.owner_dir_name('a.b'), em.owner_dir_name('a_b'))
        self.assertNotEqual(em.owner_dir_name('Ana'), em.owner_dir_name('ana'))

    def test_symlinked_model_folder_cannot_escape(self):
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside, True)
        owner_dir = os.path.join(self.root, em.owner_dir_name('eva'))
        os.makedirs(owner_dir)
        os.symlink(outside, os.path.join(owner_dir, 'fuga'))
        with self.assertRaisesRegex(em.ModelError, 'no válida'):
            em.model_dir('eva', 'fuga', create=True)
        self.assertEqual(os.listdir(outside), [])


class MiscTest(ModelsTestCase):

    def test_delete_one_version_and_whole_model(self):
        for _ in range(3):
            self.save()
        self.assertEqual(em.delete_model('ana', 'cobertura_2024', 2), 1)
        self.assertEqual([v['version'] for v in em.list_models('ana')[0]['versions']], [1, 3])
        self.assertEqual(em.delete_model('ana', 'cobertura_2024'), 2)
        self.assertEqual(em.list_models('ana'), [])
        self.assertFalse(os.path.exists(em.model_dir('ana', 'cobertura_2024')))
        self.assertEqual(os.listdir(self.root), [])                    # tampoco queda la carpeta vacía del usuario
        with self.assertRaisesRegex(em.ModelError, 'No existe'):
            em.delete_model('ana', 'cobertura_2024')

    def test_delete_cannot_touch_another_users_model(self):
        self.save('ana')
        with self.assertRaisesRegex(em.ModelError, 'No existe'):
            em.delete_model('luis', 'cobertura_2024')
        self.assertEqual(len(em.list_models('ana')), 1)

    def test_runtime_warnings(self):
        meta, _ = self.save()
        self.assertEqual(em.runtime_warnings(meta), [])
        old = dict(meta, runtime={'sklearn': '0.0.1', 'numpy': '0.0.1'})
        warnings = em.runtime_warnings(old)
        self.assertEqual(len(warnings), 2)
        self.assertIn('scikit-learn 0.0.1', warnings[0])

    def test_unconfigured_directory_is_explained(self):
        with mock.patch.object(em.plugin_settings, 'ETL_MODELS_DIR', '/proc/no-se-puede-crear', create=True):
            with self.assertRaisesRegex(em.ModelError, 'directorio de modelos|No se puede crear'):
                em.models_root()

    def test_default_directory_is_inside_the_file_manager_data(self):
        with mock.patch.object(em.plugin_settings, 'ETL_MODELS_DIR', '', create=True):
            from django.test import override_settings
            base = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, base, True)
            with override_settings(FILEMANAGER_DIRECTORY=os.path.join(base, 'data')):
                os.makedirs(os.path.join(base, 'data'))
                self.assertEqual(em.models_root(), os.path.join(os.path.realpath(base), 'data', '.geoetl_models'))


class NodesTest(ModelsTestCase):

    def test_save_and_load_nodes(self):
        path, bundle = self.model_file(metrics={'accuracy': 0.97, 'kappa': 0.9})
        self.assertEqual(em.output_ModelSave({'id': 'n1', 'data': [path], '_models_owner': 'ana',
                                              'model-name': 'Mi modelo', 'description': 'd', 'on-existing': 'version'}), [])
        res = em.input_Model({'id': 'n2', '_models_owner': 'ana', 'model-name': 'mi_modelo', 'model-version': 'latest'})
        self.artifacts.append(res[0])
        self.assertTrue(er.is_model_ref(res[0]))
        meta = er.read_meta(res[0])
        self.assertEqual((meta['features'], meta['classes'], meta['problem']), (['x'], ['A', 'B'], 'classification'))
        loaded = er.load_model_bundle(res[0])
        X = np.array([[0.0], [10.0]])
        self.assertEqual(list(loaded['model'].predict(X)), list(bundle['model'].predict(X)))

    def test_node_errors(self):
        with self.assertRaisesRegex(Exception, 'Conecta un modelo'):
            em.output_ModelSave({'id': 'n', 'data': [], '_models_owner': 'ana', 'model-name': 'x'})
        path, _ = self.model_file()
        with self.assertRaisesRegex(Exception, 'propietario'):
            em.output_ModelSave({'id': 'n', 'data': [path], 'model-name': 'x'})
        with self.assertRaisesRegex(Exception, 'Indica un nombre'):
            em.output_ModelSave({'id': 'n', 'data': [path], '_models_owner': 'ana', 'model-name': ''})
        with self.assertRaisesRegex(Exception, 'Elige el modelo'):
            em.input_Model({'id': 'n', '_models_owner': 'ana'})
        with self.assertRaisesRegex(Exception, 'propietario'):
            em.input_Model({'id': 'n', 'model-name': 'x'})
        with self.assertRaisesRegex(Exception, 'No existe el modelo'):
            em.input_Model({'id': 'n', '_models_owner': 'ana', 'model-name': 'x'})

    def test_loading_a_corrupt_model_file_is_explained(self):
        bad = er.new_artifact_path('zzbad', '.joblib')
        with open(bad, 'wb') as f:
            f.write(b'esto no es un modelo')
        self.artifacts.append(bad)
        with self.assertRaisesRegex(Exception, 'No se ha podido cargar el modelo'):
            er.load_model_bundle(bad)
        import pickle
        notdict = er.new_artifact_path('zzbad2', '.joblib')
        with open(notdict, 'wb') as f:
            pickle.dump([1, 2], f)
        self.artifacts.append(notdict)
        with self.assertRaisesRegex(Exception, 'formato esperado'):
            er.load_model_bundle(notdict)

    def test_random_forest_node_metadata_feeds_the_saved_model(self):
        # El .meta.json del modelo entrenado lleva lo que se guarda: variables, clases, métricas
        source = os.path.join(os.path.dirname(er.__file__), 'etl_raster.py')
        text = open(source, encoding='utf-8').read()
        for key in ("'metrics': metrics", "'params': {'n_estimators'", "'target': bundle['target']"):
            self.assertIn(key, text)


class EnsureDirTest(SimpleTestCase):

    def test_creates_nested_directories_and_is_idempotent(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, True)
        target = os.path.join(base, 'a', 'b', 'c')
        er.ensure_dir(target)
        self.assertTrue(os.path.isdir(target))
        er.ensure_dir(target)

    def test_root_hands_new_directories_to_the_parents_owner(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, True)
        calls = []
        with mock.patch('os.geteuid', return_value=0), mock.patch('os.chown', side_effect=lambda p, u, g: calls.append(p)):
            er.ensure_dir(os.path.join(base, 'x', 'y'))
        self.assertEqual([os.path.basename(c) for c in calls], ['x', 'y'])        # solo los que ha creado, de fuera adentro

    def test_root_uses_owner_from_when_parent_is_roots(self):
        # /tmp es de root: los directorios del ETL deben ser del usuario del servicio, no de root
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, True)
        calls = []
        ref = os.stat(base)
        fake = mock.Mock(st_uid=33, st_gid=33)
        real_stat = os.stat
        with mock.patch('os.geteuid', return_value=0), \
                mock.patch('os.stat', side_effect=lambda p, *a, **k: fake if p == '/srv/owner' else real_stat(p, *a, **k)), \
                mock.patch('os.chown', side_effect=lambda p, u, g: calls.append((os.path.basename(p), u, g))):
            er.ensure_dir(os.path.join(base, 'x', 'y'), owner_from='/srv/owner')
        self.assertEqual(calls, [('x', 33, 33), ('y', 33, 33)])
        self.assertNotEqual(ref.st_uid, 33)

    def test_artifacts_root_repairs_root_owned_dirs_and_reports_unwritable(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, True)
        owner = os.path.join(base, 'files')
        os.makedirs(owner)
        service_stat = mock.Mock(st_uid=33, st_gid=33, st_mode=os.stat(owner).st_mode)
        calls = []

        real_stat = os.stat
        plugin_dirs = {os.path.join(base, 'plugin_geoetl'), os.path.join(base, 'plugin_geoetl', 'artifacts')}

        def fake_stat(p, *a, **k):
            if p == owner:
                return service_stat
            if p in plugin_dirs:
                return mock.Mock(st_uid=0, st_gid=0, st_mode=real_stat(p).st_mode)
            return real_stat(p, *a, **k)
        with self.settings(TEMP_ROOT=base, FILEMANAGER_DIRECTORY=owner):
            root = er.artifacts_root()                     # crea los dos directorios
            with mock.patch('os.geteuid', return_value=0), mock.patch('os.stat', side_effect=fake_stat), \
                    mock.patch('os.chown', side_effect=lambda p, u, g: calls.append((p, u))):
                er.artifacts_root()
            self.assertEqual(calls, [(os.path.dirname(root), 33), (root, 33)])
            with mock.patch('os.access', return_value=False):
                with self.assertRaises(PermissionError) as ctx:
                    er.artifacts_root()
            self.assertIn('chown', str(ctx.exception))

    def test_normal_user_does_not_chown(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, True)
        with mock.patch('os.geteuid', return_value=1000), mock.patch('os.chown') as chown:
            er.ensure_dir(os.path.join(base, 'x'))
        chown.assert_not_called()
