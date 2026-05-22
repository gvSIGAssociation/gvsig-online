# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from gvsigol_core.project_package.report_summary import summarize_import_report


class ReportSummaryTests(SimpleTestCase):
    def test_skipped_definition_layer(self):
        report = [
            {
                'definition_layer_skipped': {
                    'layer': 'Tramos',
                    'reason': 'table_not_found',
                    'message': 'Table not found',
                    'table': 'sigcar.tramos',
                    'connection': 'Wrong DB',
                },
            },
            {'imported': 'vector', 'layer': 'Viña', 'table': 'vina_1'},
        ]
        s = summarize_import_report(report)
        self.assertEqual(s['status'], 'partial')
        self.assertEqual(len(s['skipped_layers']), 1)
        self.assertEqual(s['skipped_layers'][0]['layer'], 'Tramos')
        self.assertEqual(s['counts']['imported'], 1)
        self.assertEqual(s['counts']['skipped'], 1)
