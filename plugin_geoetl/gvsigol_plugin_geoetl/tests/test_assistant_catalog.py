# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.prompt import system_prompt
from gvsigol_plugin_geoetl.assistant.scaffold import (
    ScaffoldUsageError,
    draft_for,
    selected_types,
    write_drafts,
)
from gvsigol_plugin_geoetl.assistant.shapes import (
    count_ports,
    node_block,
    palette_labels,
    read_tableshape,
)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.labels = palette_labels()
        cls.source = read_tableshape()

    def test_every_palette_shape_has_a_yaml_spec(self):
        self.assertEqual(set(self.catalog), set(self.labels))
        self.assertEqual(len(self.catalog), 63)

    def test_parameter_keys_and_port_counts_match_tableshape(self):
        for name in self.labels:
            spec = self.catalog[name]
            block = node_block(self.source, name)
            self.assertTrue(block, name)
            inputs, outputs = count_ports(block)
            got_in = sum(1 for port in spec['ports'] if port['direction'] == 'input')
            got_out = sum(1 for port in spec['ports'] if port['direction'] == 'output')
            self.assertEqual((got_in, got_out), (inputs, outputs), name)
            for parameter in spec['parameters']:
                self.assertIn(parameter['name'], block, '%s %s' % (name, parameter['name']))

    def test_join_and_filtergeom_ports(self):
        join = self.catalog['trans_Join']['ports']
        self.assertEqual([port['label'] for port in join], [
            'Input Main', 'Input Sec.', 'Join', 'Main Not Used', 'Sec. Not Used',
        ])
        geom = self.catalog['trans_FilterGeom']['ports']
        self.assertEqual(sum(1 for port in geom if port['direction'] == 'input'), 1)
        self.assertEqual(sum(1 for port in geom if port['direction'] == 'output'), 6)

    def test_prompt_escapes_braces_and_percents(self):
        text = system_prompt(self.catalog)
        self.assertNotIn('{', text.replace('{{', '').replace('}}', ''))
        self.assertNotIn('}', text.replace('{{', '').replace('}}', ''))
        self.assertNotRegex(text, r'(?<!%)%(?!%)')


class ScaffoldTests(unittest.TestCase):
    def test_csv_and_join_drafts(self):
        csv_spec = draft_for('input_Csv')
        names = [item['name'] for item in csv_spec['parameters']]
        self.assertIn('csv-file', names)
        self.assertEqual(
            sum(1 for port in csv_spec['ports'] if port['direction'] == 'output'),
            1,
        )
        self.assertEqual(
            sum(1 for port in csv_spec['ports'] if port['direction'] == 'input'),
            0,
        )
        join = draft_for('trans_Join')
        self.assertEqual(sum(1 for port in join['ports'] if port['direction'] == 'input'), 2)
        self.assertEqual(sum(1 for port in join['ports'] if port['direction'] == 'output'), 3)

    def test_selected_types_rejects_missing_or_mixed_args(self):
        with self.assertRaises(ScaffoldUsageError):
            selected_types(None, False)
        with self.assertRaises(ScaffoldUsageError):
            selected_types('input_Csv', True)
        self.assertEqual(selected_types('input_Csv', False), ['input_Csv'])
        self.assertIsNone(selected_types(None, True))

    def test_unknown_type_writes_nothing_and_existing_files_are_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            written, skipped = write_drafts(directory, types=['no_such_node'], overwrite=True)
            self.assertEqual((written, skipped), ([], []))
            target = os.path.join(directory, 'input_Csv.yaml')
            with open(target, 'w', encoding='utf-8') as handle:
                handle.write('type: input_Csv\n')
            written, skipped = write_drafts(directory, types=['input_Csv'], overwrite=False)
            self.assertEqual(written, [])
            self.assertEqual(skipped, ['input_Csv'])
            with open(target, encoding='utf-8') as handle:
                self.assertEqual(handle.read(), 'type: input_Csv\n')

    def test_command_wraps_usage_errors_when_django_is_installed(self):
        try:
            from django.core.management.base import CommandError
            from gvsigol_plugin_geoetl.management.commands.etl_assistant_scaffold import Command
        except Exception as exc:
            self.skipTest('Django no está instalado en este entorno: %s' % exc)
        command = Command()
        with self.assertRaises(CommandError):
            command.handle(tipo=None, all=False, force=False)
        with self.assertRaises(CommandError):
            command.handle(tipo='no_such_node', all=False, force=False)
