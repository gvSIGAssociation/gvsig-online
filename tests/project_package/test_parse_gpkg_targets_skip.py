# -*- coding: utf-8 -*-
"""Skipped GPKG layers must not require a datastore for their connection."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

from gvsigol_core.project_package.import_service import _parse_gpkg_connection_targets


class ParseGpkgConnectionTargetsSkipTests(TestCase):
    def _layout(self):
        return {
            'gpkg_layers': [
                {
                    'export_id': 'keep-1',
                    'connection_key': 'conn_1',
                    'is_foreign_source': True,
                },
                {
                    'export_id': 'skip-1',
                    'connection_key': 'conn_1',
                    'is_foreign_source': True,
                },
                {
                    'export_id': 'skip-all-a',
                    'connection_key': 'conn_2',
                    'is_foreign_source': True,
                },
                {
                    'export_id': 'skip-all-b',
                    'connection_key': 'conn_2',
                    'is_foreign_source': True,
                },
            ],
            'gpkg_connection_targets': [
                {
                    'connection_key': 'conn_1',
                    'connection_label': 'foreign_conn_1',
                    'is_foreign_source': True,
                },
                {
                    'connection_key': 'conn_2',
                    'connection_label': 'foreign_conn_2',
                    'is_foreign_source': True,
                },
            ],
        }

    def test_fully_skipped_connection_does_not_require_datastore(self):
        layout = self._layout()
        wizard = {
            'gpkg_foreign_datastores': {'conn_1': 42},
        }
        ds = MagicMock()
        ds.workspace.server_id = 1
        ds.workspace.name = 'ws'
        ds.name = 'ds'
        ds.id = 42

        with patch(
            'gvsigol_core.project_package.import_service.Datastore.objects.select_related'
        ) as m_sel, patch(
            'gvsigol_core.project_package.import_service.is_foreign_postgis_datastore',
            return_value=False,
        ):
            m_sel.return_value.get.return_value = ds
            out = _parse_gpkg_connection_targets(
                wizard,
                layout,
                server_id=1,
                skipped_layer_ids={'skip-1', 'skip-all-a', 'skip-all-b'},
            )

        self.assertIn('conn_1', out)
        self.assertNotIn('conn_2', out)
        self.assertEqual(out['conn_1']['datastore_id'], 42)

    def test_active_foreign_connection_still_requires_datastore(self):
        layout = self._layout()
        wizard = {}
        with self.assertRaises(ValueError) as ctx:
            _parse_gpkg_connection_targets(
                wizard,
                layout,
                server_id=1,
                skipped_layer_ids={'skip-all-a', 'skip-all-b'},
            )
        self.assertIn('foreign_conn_1', str(ctx.exception))
