# -*- coding: utf-8 -*-
"""Usabilidad, fase 2: preguntas con opciones (ask_user). Las opciones salen de los datos reales."""
import importlib.util
import json
import unittest
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, tools as tools_module
from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.assistant.prompt import _DOUBTS_OPTIONS, _DOUBTS_TEXT, system_prompt
from gvsigol_plugin_geoetl.assistant.questions import MAX_CUSTOM_OPTIONS, resolve_questions
from gvsigol_plugin_geoetl.assistant.tools import build_tools

HAS_LANGGRAPH = importlib.util.find_spec('langgraph') is not None

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}, {'name': 'ora', 'type': 'Oracle'},
               {'name': 'pg', 'type': 'PostgreSQL'}]
CANVAS = {'nodes': [{'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Csv', 'label': 'CSV',
                     'parameters': {}, 'schema': []},
                    {'alias': 'n2', 'id': 'uuid-n2', 'type': 'input_Postgis', 'label': 'PostGIS',
                     'parameters': {}, 'schema': []}], 'edges': []}


def _context():
    return AssistantContext.from_payload({'is_superuser': True, 'is_staff': True, 'connections': CONNECTIONS,
                                          'language': 'es'})


class ResolveTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalog = load_catalog()

    def resolve(self, raw, proposal=None):
        return resolve_questions(raw, self.catalog, CANVAS, _context(), proposal)

    def values(self, question):
        return [o['value'] for o in question['options']]

    def test_choices_of_a_canvas_node(self):
        questions, notes = self.resolve([{'label': 'Separador', 'text': '¿Qué separador?', 'node': 'n1',
                                          'param': 'separator', 'source': 'choices'}])
        self.assertEqual(self.values(questions[0]), [';', ','])
        self.assertEqual(questions[0]['id'], 'q1')
        self.assertEqual(notes, [])

    def test_choices_of_a_proposed_node(self):
        proposal = {'mode': 'patch', 'ops': [{'op': 'add_node', 'node': {'alias': 'n7', 'type': 'input_Csv'}}]}
        questions, _ = self.resolve([{'label': 'Lectura', 'text': '¿Cómo lo leo?', 'node': 'n7',
                                      'param': 'reading', 'source': 'choices'}], proposal)
        self.assertEqual(self.values(questions[0]), ['single', 'multiple'])

    def test_connections_filtered_by_node_type(self):
        questions, _ = self.resolve([{'label': 'Conexión', 'text': '¿Cuál?', 'node': 'n2', 'source': 'connections'}])
        self.assertEqual(self.values(questions[0]), ['gis', 'pg'])            # sin Oracle
        questions, _ = self.resolve([{'label': 'Conexión', 'text': '¿Cuál?', 'source': 'connections'}])
        self.assertEqual(self.values(questions[0]), ['gis', 'ora', 'pg'])

    def test_tables_and_columns_from_the_connection(self):
        with mock.patch.object(tools_module, '_list_level', return_value=['municipios', 'padron']) as level, \
                mock.patch.object(tools_module, '_columns',
                                  return_value=[['cod_mun', 'text'], ['geom', 'geometry'], 'nombre']):
            questions, _ = self.resolve([
                {'label': 'Tabla', 'text': '¿Qué tabla?', 'source': 'tables', 'connection': 'gis', 'schema': 'public'},
                {'label': 'Campo de cruce', 'text': '¿Por qué campo?', 'source': 'columns', 'connection': 'gis',
                 'schema': 'public', 'table': 'municipios', 'options': ['cod_mun', 'nombre']},
            ])
        self.assertEqual(level.call_args[0][2], 'public')
        self.assertEqual(self.values(questions[0]), ['municipios', 'padron'])
        self.assertEqual(self.values(questions[1]), ['cod_mun', 'nombre'])    # las que eligió el modelo

    def test_unknown_connection_or_bad_identifiers_give_free_text(self):
        with mock.patch.object(tools_module, '_list_level') as level:
            questions, notes = self.resolve([
                {'label': 'Tabla', 'text': '¿Qué tabla?', 'source': 'tables', 'connection': 'no_existe'},
                {'label': 'Tabla 2', 'text': '¿Y esta?', 'source': 'tables', 'connection': 'gis',
                 'schema': 'public; drop'},
            ])
        level.assert_not_called()
        self.assertEqual([q['options'] for q in questions], [[], []])
        self.assertEqual(len(notes), 2)

    def test_files_are_chosen_in_the_file_manager(self):
        with mock.patch.object(tools_module, '_list_files') as files:
            questions, notes = self.resolve([{'label': 'Fichero', 'text': '¿Qué fichero?', 'source': 'files',
                                              'extensions': 'csv', 'options': ['inventado.csv']}])
        files.assert_not_called()
        self.assertEqual(questions[0]['options'], [])
        self.assertEqual(questions[0]['file_picker'], {'extensions': 'csv'})
        self.assertNotIn('empty', questions[0])
        self.assertEqual(notes, [])

    def test_workspaces_and_layer_groups_only_those_of_the_user(self):
        targets = {'workspaces': [{'id': 1, 'name': 'ws_a'}],
                   'layer_groups': [{'id': 2, 'name': 'lg_a', 'title': 'Grupo A'}]}
        context = AssistantContext.from_payload({'is_staff': True, 'connections': [], 'publish_targets': targets})
        questions, _ = resolve_questions([
            {'label': 'W', 'text': '¿Dónde?', 'source': 'workspaces', 'options': ['ws_ajeno', 'ws_a']},
            {'label': 'G', 'text': '¿En qué grupo de capas publico?'},
            {'label': 'W2', 'text': '¿En qué workspace?'},
        ], self.catalog, CANVAS, context)
        self.assertEqual(questions[0]['options'], [{'value': 'ws_a', 'label': 'ws_a'}])
        self.assertEqual(questions[1]['options'], [{'value': 'lg_a', 'label': 'Grupo A'}])
        self.assertEqual(questions[2]['source'], 'workspaces')

    def test_invented_options_are_dropped(self):
        questions, notes = self.resolve([{'label': 'Separador', 'text': '¿Separador?', 'node': 'n1',
                                          'param': 'separator', 'source': 'choices', 'options': [';', '|']}])
        self.assertEqual(self.values(questions[0]), [';'])
        self.assertIn('|', notes[0])

    def test_custom_options_are_capped(self):
        options = ['opción %d' % i for i in range(12)] + ['x' * 500, 'opción 1']
        questions, _ = self.resolve([{'label': 'Duplicados', 'text': '¿Qué fila conservo?', 'source': 'custom',
                                      'options': options}])
        self.assertEqual(len(questions[0]['options']), MAX_CUSTOM_OPTIONS)
        questions, _ = self.resolve([{'label': 'L', 'text': 'T', 'source': 'otra', 'options': ['x' * 500]}])
        self.assertEqual(len(questions[0]['options'][0]['label']), 120)       # origen desconocido = custom

    def test_reading_failure_gives_free_text(self):
        with mock.patch.object(tools_module, '_list_level', side_effect=RuntimeError('sin red')):
            questions, notes = self.resolve([{'label': 'Tabla', 'text': '¿Qué tabla?', 'source': 'tables',
                                              'connection': 'gis'}])
        self.assertEqual(questions[0]['options'], [])
        self.assertIn('respuesta libre', notes[0])

    def test_limits_and_bad_input(self):
        raw = [{'label': 'L%d' % i, 'text': 'T%d' % i, 'source': 'custom', 'options': ['a']} for i in range(6)]
        questions, notes = self.resolve(raw + ['x'])
        self.assertEqual([q['id'] for q in questions], ['q1', 'q2', 'q3', 'q4'])
        self.assertTrue(notes)
        questions, _ = self.resolve([{'label': 'sin texto'}, 'x', {'text': 'Solo texto', 'source': 'custom'}])
        self.assertEqual([q['label'] for q in questions], ['Solo texto'])
        self.assertEqual(self.resolve('no es lista'), ([], ['questions tiene que ser una lista.']))


class InferenceTests(SimpleTestCase):
    """El caso real: el modelo no indica bien de dónde salen las opciones."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalog = load_catalog()

    def resolve(self, raw):
        return resolve_questions(raw, self.catalog, CANVAS, _context())

    def test_the_questions_of_the_screenshot(self):
        for source in ('custom', None, 'texto'):
            with self.subTest(source=source):
                questions, _ = self.resolve([
                    {'label': 'Shapefile', 'text': '¿Qué shapefile quieres unir?', 'source': source},
                    {'label': 'Excel', 'text': '¿Qué fichero Excel quieres unir?', 'source': source},
                    {'label': 'Destino', 'text': '¿En qué conexión quieres crear la nueva tabla?', 'source': source},
                ])
                self.assertEqual([q['source'] for q in questions], ['files', 'files', 'datastores'])
                self.assertEqual([q['file_picker']['extensions'] for q in questions[:2]], ['shp', 'xls,xlsx'])
                self.assertTrue(questions[2]['create_datastore'])

    DATASTORES = [{'name': 'ds_a', 'description': 'Cartografía base', 'workspace': 'ws_general',
                   'connection': 'gis', 'schema': 'carto'},
                  {'name': 'ds_b', 'description': '', 'workspace': 'ws_p', 'connection': 'pg', 'schema': 'datos'}]

    def _with_datastores(self, raw):
        context = AssistantContext.from_payload({'is_staff': True, 'connections': CONNECTIONS,
                                                 'datastores': self.DATASTORES})
        return resolve_questions(raw, self.catalog, CANVAS, context)[0]

    def test_destination_offers_datastores(self):
        for raw in ({'label': 'D', 'text': '¿En qué conexión quieres crear la tabla?', 'source': 'connections'},
                    {'label': 'D', 'text': '¿En qué conexión quieres crear la tabla?'},
                    {'label': 'D', 'text': '¿Dónde?', 'source': 'connections', 'type': 'output_Postgis'},
                    {'label': 'D', 'text': '¿Qué almacén uso?'},
                    {'label': 'D', 'text': '¿Dónde?', 'source': 'datastores', 'options': ['inventado']}):
            with self.subTest(raw=raw):
                question = self._with_datastores([raw])[0]
                self.assertEqual(question['source'], 'datastores')
                self.assertTrue(question['create_datastore'])
                self.assertEqual(question['options'][0], {
                    'value': 'connection=gis; schema=carto', 'label': 'Cartografía base · ws_general',
                    'params': {'db-option': 'gis', 'schema-name-option': 'carto'}})
                self.assertEqual(question['options'][1]['label'], 'ds_b · ws_p')

    def test_reading_or_other_databases_keep_the_connections(self):
        for raw in ({'label': 'O', 'text': '¿De qué conexión leo la tabla?', 'source': 'connections'},
                    {'label': 'O', 'text': '¿Dónde?', 'source': 'connections', 'node': 'n2'},
                    {'label': 'O', 'text': '¿En qué conexión Oracle guardo?', 'source': 'connections'}):
            with self.subTest(raw=raw):
                question = self._with_datastores([raw])[0]
                self.assertEqual(question['source'], 'connections')
                self.assertNotIn('create_datastore', question)

    def test_synonyms_of_the_source(self):
        questions, _ = self.resolve([{'label': 'C', 'text': '¿Cuál?', 'source': 'Connection'}])
        self.assertEqual(questions[0]['source'], 'connections')

    def test_postgis_filters_the_connections(self):
        questions, _ = self.resolve([{'label': 'C', 'text': '¿Qué conexión PostGIS uso?'}])
        self.assertEqual([o['value'] for o in questions[0]['options']], ['gis', 'pg'])

    def _extensions_of(self, raw):
        return self.resolve([raw])[0][0]['file_picker']['extensions']

    def test_files_without_extensions_take_them_from_the_question(self):
        self.assertEqual(self._extensions_of({'label': 'F', 'text': '¿Qué CSV cargo?', 'source': 'files'}), 'csv,txt')

    def test_extensions_in_any_format(self):
        for raw in ('*.shp', '.shp', ['*.shp'], 'shp'):
            with self.subTest(raw=raw):
                self.assertEqual(self._extensions_of({'label': 'F', 'text': 'x', 'source': 'files', 'extensions': raw}), 'shp')

    def test_parameter_of_a_node_wins(self):
        self.assertEqual(self._extensions_of({'label': 'F', 'text': '¿Cuál?', 'node': 'n1', 'param': 'csv-file'}), 'csv,txt')

    def test_options_invented_for_a_real_source_fall_back_to_the_real_list(self):
        questions, notes = self.resolve([{'label': 'C', 'text': '¿Cuál?', 'source': 'connections',
                                          'options': ['Conexión 1', 'Conexión 2']}])
        self.assertEqual(len(questions[0]['options']), 3)
        self.assertTrue(notes)

    def test_business_questions_stay_custom(self):
        questions, _ = self.resolve([{'label': 'Duplicados', 'text': '¿Qué fila conservo?', 'source': 'custom',
                                      'options': ['La primera', 'La última']}])
        self.assertEqual((questions[0]['source'], len(questions[0]['options'])), ('custom', 2))
        questions, _ = self.resolve([{'label': 'Nombre', 'text': '¿Cómo se llama la tabla nueva?'}])
        self.assertEqual((questions[0]['source'], questions[0]['options']), ('custom', []))
        self.assertNotIn('empty', questions[0])

    def test_empty_says_why(self):
        context = AssistantContext.from_payload({'is_superuser': True, 'connections': []})
        questions, _ = resolve_questions([{'label': 'C', 'text': '¿Qué conexión?'}], self.catalog, CANVAS, context)
        self.assertEqual(questions[0]['empty'], 'connections')


class ToolAndPromptTests(SimpleTestCase):

    def test_without_the_flag_nothing_changes(self):
        names = [t.name for t in build_tools(_context(), load_catalog(), {}, None, None, [])]
        self.assertNotIn('ask_user', names)
        prompt = system_prompt(load_catalog(), 'es')
        self.assertIn(_DOUBTS_TEXT, prompt)
        self.assertNotIn('ask_user', prompt)

    def test_with_the_flag(self):
        prompt = system_prompt(load_catalog(), 'es', questions=True)
        self.assertNotIn(_DOUBTS_TEXT, prompt)
        self.assertIn('pregunta con ask_user', prompt)
        self.assertEqual(prompt.count('{{'), system_prompt(load_catalog(), 'es').count('{{'))
        self.assertNotIn('%', _DOUBTS_OPTIONS)

    def test_tool_registers_the_questions(self):
        asked = []
        tools = {t.name: t for t in build_tools(_context(), load_catalog(), CANVAS, None, None, [], asked=asked)}
        out = json.loads(tools['ask_user'].invoke({'questions_json': json.dumps({'questions': [
            {'label': 'Separador', 'text': '¿Separador?', 'node': 'n1', 'param': 'separator',
             'source': 'choices'}]})}))
        self.assertTrue(out['accepted'])
        self.assertEqual(out['questions'], [{'id': 'q1', 'label': 'Separador', 'options': 2}])
        self.assertIn('no llames a propose_workspace', out['instruction'])
        self.assertEqual(asked[0][0]['label'], 'Separador')
        bad = json.loads(tools['ask_user'].invoke({'questions_json': 'no json'}))
        self.assertFalse(bad['accepted'])
        empty = json.loads(tools['ask_user'].invoke({'questions_json': '[]'}))
        self.assertFalse(empty['accepted'])
        self.assertEqual(len(asked), 1)                                      # sigue la válida


class ScriptedExecutor(object):
    def __init__(self, tools, calls, output):
        self.tools = {t.name: t for t in tools}
        self.calls = calls
        self.output = output

    def invoke(self, payload, config=None):
        for name, args in self.calls:
            self.tools[name].invoke(args)
        return {'output': self.output}


ASK = ('ask_user', {'questions_json': json.dumps([{'label': 'Separador', 'text': '¿Qué separador usa?',
                                                   'node': 'n1', 'param': 'separator', 'source': 'choices'}])})


@override_settings(LANGUAGE_CODE='es')
class RunTests(SimpleTestCase):

    def _run(self, flag, calls, history=None):
        seen = {}

        def executor(llm, tools, prompt):
            seen['tools'] = [t.name for t in tools]
            seen['system'] = prompt.format_messages(input='x', chat_history=[], agent_scratchpad=[])[0].content
            usable = [(n, a) for n, a in calls if n in seen['tools']]
            return ScriptedExecutor(tools, usable, 'Necesito un dato.')
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_QUESTIONS', flag, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor', side_effect=executor):
            result = agent.run_assistant(_context(), 'carga el csv', history or [], CANVAS, None, None)
        return result, seen

    def test_off(self):
        result, seen = self._run(False, [ASK])
        self.assertNotIn('questions', result)
        self.assertNotIn('ask_user', seen['tools'])
        self.assertIn(_DOUBTS_TEXT, seen['system'])

    def test_on(self):
        result, seen = self._run(True, [ASK])
        self.assertIn('ask_user', seen['tools'])
        self.assertIn('pregunta con ask_user', seen['system'])
        self.assertEqual(result['reply'], 'Necesito un dato.')
        self.assertEqual([o['value'] for o in result['questions'][0]['options']], [';', ','])
        json.dumps(result)

    def test_on_without_asking(self):
        result, _ = self._run(True, [])
        self.assertNotIn('questions', result)

    def test_history_tells_the_model_what_was_asked(self):
        history = [{'role': 'user', 'content': 'carga el csv'},
                   {'role': 'assistant', 'content': 'Necesito un dato.', 'summary': [], 'status': '',
                    'questions': [{'label': 'Separador', 'text': '¿Qué separador usa?'}]},
                   {'role': 'user', 'content': 'Separador: ;'}]
        messages = agent._history(history)
        self.assertIn('[Pregunté con opciones: Separador: ¿Qué separador usa?]', messages[1].content)
        self.assertEqual(messages[2].content, 'Separador: ;')

    def test_public_json(self):
        from gvsigol_plugin_geoetl.assistant.views import _public
        self.assertNotIn('questions', _public({'reply': 'x'}))
        self.assertEqual(_public({'reply': 'x', 'questions': [{'id': 'q1'}]})['questions'], [{'id': 'q1'}])


@unittest.skipUnless(HAS_LANGGRAPH, 'langgraph no instalado')
@override_settings(LANGUAGE_CODE='es')
class LangGraphQuestionsTests(SimpleTestCase):

    def test_ask_user_with_the_langgraph_engine(self):
        from gvsigol_plugin_geoetl.tests.test_assistant_engine import scripted_model
        model = scripted_model([[ASK], 'Necesito saber el separador.'])
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_QUESTIONS', True, create=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ENGINE', 'langgraph', create=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_MAX_SECONDS', 120, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=model):
            result = agent.run_assistant(_context(), 'carga el csv', [], CANVAS, None, None)
        self.assertEqual(result['reply'], 'Necesito saber el separador.')
        self.assertEqual(result['questions'][0]['param'], 'separator')
        self.assertIn('pregunta con ask_user', model.seen[0][0].content)
