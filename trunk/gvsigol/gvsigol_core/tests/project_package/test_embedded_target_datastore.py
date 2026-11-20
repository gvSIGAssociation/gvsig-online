# -*- coding: utf-8 -*-
"""Local GPKG layers sharing connection_key must keep per-layer workspace/datastore."""
from unittest import TestCase
from unittest.mock import MagicMock

from gvsigol_core.project_package.import_service import (
    _embedded_target_datastore,
    _ensure_local_gpkg_layer_datastores,
)


class EmbeddedTargetDatastoreTests(TestCase):
    def test_local_layers_use_own_workspace_not_connection_group(self):
        # gpkg_targets still keyed by connection_key (legacy / foreign); for local
        # the first group entry must NOT override a later layer's ws/ds.
        gpkg_targets = {
            'local_cartodb': {
                'workspace': 'ws_admin_guat',
                'datastore': 'ds_guiat_schema_public',
            },
        }
        ds_admin = MagicMock(name='ds_admin')
        ds_emerg = MagicMock(name='ds_emerg')
        datastore_map = {
            ('ws_admin_guat', 'ds_guiat_schema_public'): ds_admin,
            ('ws_emergencias', 'ds_emergencias'): ds_emerg,
        }
        ld_comarcas = {
            'datastore_connection_key': 'local_cartodb',
            'datastore_is_foreign': False,
            'workspace_name': 'ws_emergencias',
            'datastore_name': 'ds_emergencias',
            'name': 'comarcas',
        }
        self.assertIs(
            _embedded_target_datastore(ld_comarcas, 'ws_default', gpkg_targets, datastore_map),
            ds_emerg,
        )

    def test_foreign_layers_still_use_connection_target(self):
        gpkg_targets = {
            'foreign_conn': {
                'workspace': 'ws_target',
                'datastore': 'ds_target',
            },
        }
        ds_target = MagicMock(name='ds_target')
        datastore_map = {
            ('ws_target', 'ds_target'): ds_target,
            ('ws_other', 'ds_other'): MagicMock(),
        }
        ld = {
            'datastore_connection_key': 'foreign_conn',
            'datastore_is_foreign': True,
            'workspace_name': 'ws_other',
            'datastore_name': 'ds_other',
            'name': 'foreign_layer',
        }
        self.assertIs(
            _embedded_target_datastore(ld, 'ws_default', gpkg_targets, datastore_map),
            ds_target,
        )


class EnsureLocalGpkgDatastoresTests(TestCase):
    def test_collects_extra_local_targets_beyond_connection_group(self):
        layout = {
            'gpkg_layers': [
                {
                    'export_id': 'a',
                    'is_foreign_source': False,
                    'exported_workspace': 'ws_admin_guat',
                    'exported_datastore': 'ds_guiat_schema_public',
                    'title': 'Emergencias',
                },
                {
                    'export_id': 'b',
                    'is_foreign_source': False,
                    'exported_workspace': 'ws_emergencias',
                    'exported_datastore': 'ds_emergencias',
                    'title': 'Comarcas',
                },
                {
                    'export_id': 'c',
                    'is_foreign_source': False,
                    'exported_workspace': 'ws_admin_guat',
                    'exported_datastore': 'ds_guiat_schema_public',
                    'title': 'skipped',
                },
            ],
        }
        datastore_map = {
            ('ws_admin_guat', 'ds_guiat_schema_public'): MagicMock(name='already'),
        }
        ws_objs = {'ws_admin_guat': MagicMock(name='ws_admin')}
        report = []
        created_ws = MagicMock(name='ws_emerg')
        created_ds = MagicMock(name='ds_emerg')

        from unittest.mock import patch

        with patch(
            'gvsigol_core.project_package.import_service._get_or_create_workspace',
            return_value=(created_ws, True),
        ) as m_ws, patch(
            'gvsigol_core.project_package.import_service._get_or_create_datastore',
            return_value=(created_ds, True),
        ) as m_ds:
            _ensure_local_gpkg_layer_datastores(
                server_id=1,
                username='root',
                layout=layout,
                datastore_map=datastore_map,
                ws_objs=ws_objs,
                report=report,
                skipped_export_ids={'c'},
            )

        m_ws.assert_called_once_with(1, 'ws_emergencias', 'root')
        m_ds.assert_called_once()
        self.assertIn(('ws_emergencias', 'ds_emergencias'), datastore_map)
        self.assertIs(datastore_map[('ws_emergencias', 'ds_emergencias')], created_ds)
        self.assertEqual(ws_objs['ws_emergencias'], created_ws)
