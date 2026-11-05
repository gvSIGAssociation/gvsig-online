# -*- coding: utf-8 -*-
"""Foreign SQL views + model/public layer packaging helpers."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

from gvsigol_core.project_package.import_service import (
    _foreign_connection_keys_required,
    _is_model_public_layer_entry,
    _is_view_sql_layer_entry,
    _unique_gpkg_table_name,
    extract_snapshot_layout,
)
from gvsigol_core.project_package.export_service import _vector_mode_for_layer


def _layer_entry(
    *,
    name='lyr',
    foreign=False,
    schema='public',
    vmode='embedded',
    gpkg=None,
    view_sql=None,
    connection_key='local_cartodb',
    is_model=None,
):
    ld = {
        'name': name,
        'title': name,
        'source_name': name,
        'schema_name': schema,
        'datastore_is_foreign': foreign,
        'datastore_connection_key': connection_key,
        'datastore_connection_label': connection_key,
        'workspace_name': 'ws',
        'datastore_name': 'ds',
        'external': False,
    }
    if is_model is not None:
        ld['is_model_public_layer'] = is_model
    entry = {
        'export_id': 'eid-%s' % name,
        'layer_type': 'v_PostGIS',
        'layer': ld,
        'vector_data_mode': vmode,
    }
    if gpkg:
        entry['vector_gpkg'] = gpkg
    if view_sql is not None:
        entry['view_sql_definition'] = view_sql
        entry['vector_data_mode'] = 'view_sql_definition'
    return entry


class ModelPublicDetectionTests(TestCase):
    def test_local_public_is_model(self):
        self.assertTrue(_is_model_public_layer_entry(_layer_entry(schema='public')))

    def test_local_other_schema_not_model(self):
        self.assertFalse(
            _is_model_public_layer_entry(_layer_entry(schema='user_schema', is_model=False))
        )

    def test_foreign_not_model(self):
        self.assertFalse(
            _is_model_public_layer_entry(
                _layer_entry(foreign=True, schema='public', connection_key='conn_9')
            )
        )

    def test_explicit_flag(self):
        self.assertTrue(
            _is_model_public_layer_entry(
                _layer_entry(schema='other', is_model=True)
            )
        )


class ForeignViewKeysTests(TestCase):
    def test_foreign_view_requires_connection(self):
        snapshot = {
            'layer_groups': [{
                'layer_group': {'name': 'g'},
                'layers': [
                    _layer_entry(
                        name='v1',
                        foreign=True,
                        connection_key='conn_42',
                        view_sql={'sql': 'SELECT 1', 'schema': 's', 'view_name': 'v1'},
                    ),
                ],
            }],
        }
        keys = _foreign_connection_keys_required(snapshot, skipped_export_ids=set())
        self.assertIn('conn_42', keys)

    def test_skipped_foreign_view_not_required(self):
        entry = _layer_entry(
            name='v1',
            foreign=True,
            connection_key='conn_42',
            view_sql={'sql': 'SELECT 1', 'schema': 's', 'view_name': 'v1'},
        )
        snapshot = {'layer_groups': [{'layer_group': {'name': 'g'}, 'layers': [entry]}]}
        keys = _foreign_connection_keys_required(
            snapshot,
            skipped_export_ids=set(),
            skipped_view_ids={entry['export_id']},
        )
        self.assertNotIn('conn_42', keys)


class ExtractLayoutTests(TestCase):
    def test_layout_marks_foreign_view_and_model_public(self):
        snapshot = {
            'project': {'name': 'p', 'title': 'P'},
            'layer_groups': [{
                'layer_group': {'name': 'g', 'title': 'G'},
                'layers': [
                    _layer_entry(
                        name='foreign_view',
                        foreign=True,
                        connection_key='conn_7',
                        view_sql={
                            'sql': 'SELECT 1 AS id',
                            'schema': 'ext',
                            'view_name': 'foreign_view',
                            'gt_pk_metadata': [],
                        },
                    ),
                    _layer_entry(
                        name='platform_tbl',
                        schema='public',
                        gpkg='data/vector/x.gpkg',
                        is_model=True,
                    ),
                    _layer_entry(
                        name='user_tbl',
                        schema='myschema',
                        gpkg='data/vector/y.gpkg',
                        is_model=False,
                    ),
                ],
            }],
        }
        layout = extract_snapshot_layout(snapshot)
        # Foreign views live in foreign_layers (one row), not in local view_sql_layers.
        self.assertEqual(layout['view_sql_layers'], [])
        foreign_layers = layout['foreign_layers']
        foreign_views = [fl for fl in foreign_layers if fl.get('has_view_sql')]
        self.assertEqual(len(foreign_views), 1)
        self.assertTrue(foreign_views[0]['is_foreign_source'])
        self.assertEqual(foreign_views[0]['connection_key'], 'conn_7')
        fkeys = {fc['connection_key'] for fc in layout['foreign_connections']}
        self.assertIn('conn_7', fkeys)
        models = layout['model_public_layers']
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]['table_name'], 'platform_tbl')
        self.assertTrue(models[0]['has_gpkg'])
        gpkg = layout['gpkg_layers']
        model_gpkg = [g for g in gpkg if g.get('is_model_public_layer')]
        self.assertEqual(len(model_gpkg), 1)
        normal = [g for g in gpkg if not g.get('is_model_public_layer')]
        self.assertEqual(len(normal), 1)
        self.assertEqual(normal[0]['name'], 'user_tbl')


class UniqueNameNeverUsedForModelPathTests(TestCase):
    def test_unique_renames_when_taken(self):
        """Baseline: normal unique helper still renames — model path must not call it."""
        ds = MagicMock()
        intro = MagicMock()
        intro.object_exists.side_effect = lambda schema, name: name == 'platform_tbl'
        ds.get_db_connection.return_value = (intro, {})
        with patch(
            'gvsigol_core.project_package.import_service.Layer.objects.filter'
        ) as m_filter:
            m_filter.return_value.exists.return_value = False
            name = _unique_gpkg_table_name(ds, 'public', 'platform_tbl', [])
        self.assertEqual(name, 'platform_tbl_1')


class VectorModeDefaultsTests(TestCase):
    def test_foreign_default_definition_only(self):
        layer = MagicMock()
        layer.id = 1
        layer.datastore = MagicMock()
        with patch(
            'gvsigol_core.project_package.export_service.is_foreign_postgis_datastore',
            return_value=True,
        ):
            self.assertEqual(_vector_mode_for_layer(layer, {}), 'definition_only')

    def test_explicit_view_sql_honoured(self):
        layer = MagicMock()
        layer.id = 5
        layer.datastore = MagicMock()
        with patch(
            'gvsigol_core.project_package.export_service.is_foreign_postgis_datastore',
            return_value=True,
        ):
            mode = _vector_mode_for_layer(
                layer, {'layer_vector_modes': {'5': 'view_sql_definition'}}
            )
        self.assertEqual(mode, 'view_sql_definition')


class ViewSqlEntryTests(TestCase):
    def test_is_view_sql(self):
        self.assertTrue(
            _is_view_sql_layer_entry(
                _layer_entry(
                    view_sql={'sql': 'SELECT 1', 'schema': 's', 'view_name': 'v'},
                )
            )
        )
        self.assertFalse(_is_view_sql_layer_entry(_layer_entry(vmode='definition_only')))


class AnalyzeForeignViewsTests(TestCase):
    def test_foreign_datastore_views_are_detected(self):
        from gvsigol_core.project_package import connection_utils as cu

        project = MagicMock()
        lg = MagicMock()
        lg.title = 'G'
        lg.name = 'g'
        plg = MagicMock()
        plg.layer_group = lg
        project.projectlayergroup_set.all.return_value = [plg]
        project.projectrole_set.exists.return_value = False
        project.id = 1
        project.name = 'p'
        project.is_public = True

        layer = MagicMock()
        layer.id = 10
        layer.type = 'v_PostGIS'
        layer.external = False
        layer.name = 'v_ext'
        layer.source_name = 'v_ext'
        layer.title = 'V Ext'
        ds = MagicMock()
        ds.id = 99
        layer.datastore = ds

        with patch.object(cu.Layer.objects, 'filter') as m_filter, \
             patch.object(cu, 'is_foreign_postgis_datastore', return_value=True), \
             patch.object(cu, 'datastore_connection_key', return_value='conn_9'), \
             patch.object(cu, 'datastore_connection_label', return_value='Ext DB'), \
             patch.object(cu, '_layer_postgis_schema', return_value='ext'), \
             patch.object(cu, '_detect_views_in_datastore', return_value=({'v_ext'}, None)):
            m_filter.return_value.order_by.return_value = [layer]
            out = cu.analyze_project_layers(project)

        layers = out['vector_layers']
        self.assertEqual(len(layers), 1)
        self.assertTrue(layers[0]['is_foreign'])
        self.assertTrue(layers[0]['is_view'])
        self.assertEqual(layers[0]['default_vector_mode'], 'definition_only')
