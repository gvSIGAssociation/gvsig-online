# -*- coding: utf-8 -*-
"""Usabilidad, fase 3: suposiciones sobre un parámetro que el usuario cambia con un clic."""
import json
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, tools as tools_module
from gvsigol_plugin_geoetl.assistant.alternatives import split_assumptions
from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.assistant.prompt import _ASSUMPTIONS_OPTIONS, system_prompt
from gvsigol_plugin_geoetl.assistant.tools import build_tools

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}, {'name': 'pg', 'type': 'PostgreSQL'},
               {'name': 'ora', 'type': 'Oracle'}]
CANVAS = {'nodes': [{'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Csv', 'label': 'CSV',
                     'parameters': {'csv-file': 'file:///a.csv', 'separator': ';'}, 'schema': []}], 'edges': []}


def _context():
    return AssistantContext.from_payload({'is_superuser': True, 'is_staff': True, 'connections': CONNECTIONS})


def _proposal(assumptions, ops=None):
    return json.dumps({'mode': 'patch', 'assumptions': assumptions, 'ops': ops or [
        {'op': 'update_node', 'id': 'n1', 'parameters': {'separator': ','}},
        {'op': 'add_node', 'node': {'id': 'n2', 'type': 'input_Postgis',
                                    'parameters': {'db': 'gis', 'schema-name': 'public', 'tablename': 'padron'}}}]})


class ToolTests(SimpleTestCase):

    def _propose(self, assumptions, alternatives=True, ops=None):
        holder = []
        tools = {t.name: t for t in build_tools(_context(), load_catalog(), CANVAS, None, None, holder,
                                                alternatives=alternatives)}
        out = json.loads(tools['propose_workspace'].invoke({'proposal_json': _proposal(assumptions, ops)}))
        return out, (holder[-1] if holder else None)

    def test_choices_of_an_updated_node(self):
        _, result = self._propose([{'text': 'n1: separador coma', 'node': 'n1', 'param': 'separator',
                                    'source': 'choices'}, 'n2: lee padron'])
        self.assertEqual(result['assumptions'], ['n1: separador coma', 'n2: lee padron'])
        choice = result['assumption_choices'][0]
        self.assertEqual((choice['node'], choice['param'], choice['value']), ('n1', 'separator', ','))
        self.assertEqual([o['value'] for o in choice['options']], [';', ','])

    def test_connections_of_a_new_node(self):
        _, result = self._propose([{'text': 'n2: conexión gis', 'node': 'n2', 'param': 'db',
                                    'source': 'connections'}])
        choice = result['assumption_choices'][0]
        self.assertEqual(choice['value'], 'gis')
        self.assertEqual([o['value'] for o in choice['options']], ['gis', 'pg'])     # sin Oracle

    def test_columns_with_the_current_value_first_if_missing(self):
        with mock.patch.object(tools_module, '_list_level', return_value=['municipios', 'otra']):
            _, result = self._propose([{'text': 'n2: tabla padron', 'node': 'n2', 'param': 'tablename',
                                        'source': 'tables', 'connection': 'gis', 'schema': 'public'}])
        options = [o['value'] for o in result['assumption_choices'][0]['options']]
        self.assertEqual(options, ['padron', 'municipios', 'otra'])

    def test_a_file_is_changed_in_the_file_manager(self):
        _, result = self._propose([{'text': 'n1: fichero a', 'node': 'n1', 'param': 'csv-file', 'source': 'files'}])
        choice = result['assumption_choices'][0]
        self.assertEqual(choice['file_picker'], {'extensions': 'csv,txt'})
        self.assertEqual((choice['value'], choice['options']), ('file:///a.csv', []))
        _, result = self._propose([{'text': 'n1: fichero a', 'node': 'n1', 'param': 'csv-file'}])    # sin source
        self.assertIn('file_picker', result['assumption_choices'][0])

    def test_invalid_ones_are_ignored_but_the_text_stays(self):
        _, result = self._propose([
            {'text': 'n9: no existe', 'node': 'n9', 'param': 'separator'},
            {'text': 'n1: parámetro inventado', 'node': 'n1', 'param': 'inventado'},
            {'text': 'n1: sin alternativas', 'node': 'n1', 'param': 'folder', 'source': 'custom'},
            {'text': 'n2: sin valor', 'node': 'n2', 'param': 'query', 'source': 'choices'},
            {'node': 'n1', 'param': 'separator'},                                       # sin texto
        ])
        self.assertEqual(result['assumption_choices'], [])
        self.assertEqual(result['assumptions'], ['n9: no existe', 'n1: parámetro inventado',
                                                 'n1: sin alternativas', 'n2: sin valor'])

    def test_a_reading_failure_does_not_break_the_proposal(self):
        with mock.patch.object(tools_module, '_list_level', side_effect=RuntimeError('sin red')):
            out, result = self._propose([{'text': 'n2: tabla padron', 'node': 'n2', 'param': 'tablename',
                                          'source': 'tables', 'connection': 'gis'}])
        self.assertTrue(out['accepted'])
        self.assertEqual(result['assumption_choices'], [])

    def test_without_the_flag_nothing_changes(self):
        _, result = self._propose([{'text': 'n1: separador coma', 'node': 'n1', 'param': 'separator'},
                                   'n2: lee padron'], alternatives=False)
        self.assertNotIn('assumption_choices', result)
        self.assertEqual(result['assumptions'], ['n2: lee padron'])        # como siempre: los objetos se ignoran

    def test_split_keeps_strings_and_order(self):
        payload, structured = split_assumptions({'assumptions': ['a', {'text': ' b '}, {'node': 'x'}, 3]})
        self.assertEqual(payload['assumptions'], ['a', 'b', 3])
        self.assertEqual([s['text'] for s in structured], ['b'])
        self.assertEqual(split_assumptions('x'), ('x', []))


class PromptAndHistoryTests(SimpleTestCase):

    def test_prompt_only_with_the_flag(self):
        catalog = load_catalog()
        self.assertNotIn(_ASSUMPTIONS_OPTIONS.strip(), system_prompt(catalog, 'es'))
        prompt = system_prompt(catalog, 'es', alternatives=True)
        self.assertIn('El panel deja cambiarla con un clic', prompt)
        both = system_prompt(catalog, 'es', questions=True, alternatives=True)
        self.assertIn('pregunta con ask_user', both)
        self.assertIn('El panel deja cambiarla con un clic', both)

    def test_history_note_of_the_changes(self):
        messages = agent._history([
            {'role': 'user', 'content': 'cruza'},
            {'role': 'assistant', 'content': 'Hecho.', 'summary': ['Añado Join (n3).'], 'status': 'applied',
             'changes': [{'node': 'n3', 'param': 'field', 'value': 'cod_ine'}, 'x', {'node': 'n3'}]}])
        self.assertIn('[El usuario cambió: n3 field = cod_ine]', messages[1].content)

    def test_public_json(self):
        from gvsigol_plugin_geoetl.assistant.views import _public
        self.assertNotIn('assumption_choices', _public({'reply': 'x'}))
        self.assertEqual(_public({'reply': 'x', 'assumption_choices': []})['assumption_choices'], [])


class ScriptedExecutor(object):
    def __init__(self, tools, calls):
        self.tools = {t.name: t for t in tools}
        self.calls = calls

    def invoke(self, payload, config=None):
        for name, args in self.calls:
            self.tools[name].invoke(args)
        return {'output': 'Propuesta lista.'}


@override_settings(LANGUAGE_CODE='es')
class RunTests(SimpleTestCase):

    def test_end_to_end_with_the_flag(self):
        calls = [('propose_workspace', {'proposal_json': _proposal(
            [{'text': 'n1: separador coma', 'node': 'n1', 'param': 'separator', 'source': 'choices'}])})]
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ALTERNATIVES', True, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor', side_effect=lambda llm, tools, prompt: ScriptedExecutor(tools, calls)):
            result = agent.run_assistant(_context(), 'usa coma', [], CANVAS, None, None)
        self.assertEqual(result['assumption_choices'][0]['value'], ',')
        from gvsigol_plugin_geoetl.assistant.views import _public
        self.assertIn('assumption_choices', _public(result))
        json.dumps(result)
