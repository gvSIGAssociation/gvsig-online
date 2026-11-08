# -*- coding: utf-8 -*-
"""Usabilidad, fase 4: completar parámetros desde el chat. Opciones reales, con los permisos del usuario."""
import json
from types import SimpleNamespace
from unittest import mock

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase, override_settings

from gvsigol_plugin_geoetl import settings as geoetl_settings
from gvsigol_plugin_geoetl.assistant import agent, param_options, tools as tools_module, views
from gvsigol_plugin_geoetl.assistant.catalog import load_catalog
from gvsigol_plugin_geoetl.assistant.context import AssistantContext
from gvsigol_plugin_geoetl.assistant.tools import build_tools

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}, {'name': 'ora', 'type': 'Oracle'}]
CANVAS = {'nodes': [
    {'alias': 'n1', 'id': 'uuid-n1', 'type': 'input_Csv', 'label': 'CSV', 'parameters': {'separator': ';'}, 'schema': []},
    {'alias': 'n2', 'id': 'uuid-n2', 'type': 'input_Postgis', 'label': 'PostGIS',
     'parameters': {'db': 'no_existe', 'x': 1}, 'schema': []}], 'edges': []}


def _context(restricted=False):
    return AssistantContext.from_payload({'is_superuser': True, 'is_staff': True, 'connections': CONNECTIONS,
                                          'restricted': restricted})


class SourceTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalog = load_catalog()

    def source(self, type_name, param):
        return param_options.picker_source(self.catalog.get(type_name), type_name, param)

    def test_each_kind_of_parameter(self):
        self.assertEqual(self.source('input_Postgis', 'db'), 'connections')
        self.assertEqual(self.source('output_Postgis', 'db-option'), 'datastores')
        self.assertEqual(self.source('input_Csv', 'separator'), 'choices')
        self.assertEqual(self.source('input_Csv', 'csv-file'), 'files')
        self.assertEqual(self.source('input_Postgis', 'schema-name'), 'schemas')
        self.assertEqual(self.source('output_Postgis', 'schema-name-option'), 'schemas')
        self.assertEqual(self.source('input_Postgis', 'tablename'), 'tables')

    def test_what_cannot_be_picked(self):
        self.assertIsNone(self.source('output_Postgis', 'tablename'))        # puede ser una tabla nueva
        self.assertIsNone(self.source('input_Csv', 'inventado'))
        self.assertIsNone(self.source('tipo_inventado', 'db'))
        self.assertIsNone(self.source('input_Csv', None))
        for type_name, spec in self.catalog.items():
            for param in spec.get('sql_parameters') or []:
                self.assertIsNone(self.source(type_name, param), (type_name, param))

    def test_restricted_mode_protects_inputs_outputs_and_sql(self):
        self.assertFalse(param_options.can_pick(self.catalog, 'input_Csv', 'separator', True))
        self.assertTrue(param_options.can_pick(self.catalog, 'input_Csv', 'separator', False))
        self.assertFalse(param_options.can_pick(self.catalog, 'output_Postgis', 'db-option', True))


class OptionsTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalog = load_catalog()

    def options(self, type_name, param, parameters=None):
        return param_options.options_for(self.catalog, type_name, param, parameters or {}, _context())

    def test_connections_are_filtered_by_type(self):
        options, needs = self.options('input_Postgis', 'db')
        self.assertEqual([o['value'] for o in options], ['gis'])
        self.assertIsNone(needs)

    def test_output_postgis_offers_datastores_with_their_parameters(self):
        context = AssistantContext.from_payload({'is_staff': True, 'datastores': [
            {'name': 'ds', 'description': '', 'workspace': 'ws', 'connection': 'gis', 'schema': 'carto'}]})
        options, needs = param_options.options_for(self.catalog, 'output_Postgis', 'db-option', {}, context)
        self.assertIsNone(needs)
        self.assertEqual(options[0]['params'], {'db-option': 'gis', 'schema-name-option': 'carto'})

    def test_workspaces_and_layer_groups(self):
        self.assertEqual(param_options.picker_source(self.catalog['output_RasterPublish'], 'output_RasterPublish',
                                                     'workspace'), 'workspaces')
        self.assertEqual(param_options.picker_source(self.catalog['output_RasterPublish'], 'output_RasterPublish',
                                                     'layer-group'), 'layer_groups')
        context = AssistantContext.from_payload({'is_staff': True, 'publish_targets': {
            'workspaces': [{'name': 'ws_a'}], 'layer_groups': [{'name': 'lg', 'title': 'Grupo'}]}})
        options, needs = param_options.options_for(self.catalog, 'output_RasterPublish', 'layer-group', {}, context)
        self.assertEqual((options, needs), ([{'value': 'lg', 'label': 'Grupo'}], None))

    def test_schemas_need_the_connection(self):
        self.assertEqual(self.options('input_Postgis', 'schema-name'), ([], 'connection'))
        with mock.patch.object(tools_module, '_list_level', return_value=['public']) as level:
            options, needs = self.options('input_Postgis', 'schema-name', {'db': 'gis'})
        self.assertEqual(level.call_args[0][2], '')                           # sin esquema: lista los esquemas
        self.assertEqual(([o['value'] for o in options], needs), (['public'], None))

    def test_tables_need_connection_and_schema(self):
        self.assertEqual(self.options('input_Postgis', 'tablename', {'schema-name': 'public'}), ([], 'connection'))
        self.assertEqual(self.options('input_Postgis', 'tablename', {'db': 'gis'}), ([], 'schema'))
        with mock.patch.object(tools_module, '_list_level', return_value=['padron']) as level:
            options, _ = self.options('input_Postgis', 'tablename', {'db': 'gis', 'schema-name': 'public'})
        self.assertEqual(level.call_args[0][2], 'public')
        self.assertEqual([o['value'] for o in options], ['padron'])

    def test_a_connection_of_other_user_lists_nothing(self):
        with mock.patch.object(tools_module, '_list_level') as level:
            options, _ = self.options('input_Postgis', 'schema-name', {'db': 'ajena'})
        level.assert_not_called()
        self.assertEqual(options, [])

    def test_bad_schema_is_not_used(self):
        with mock.patch.object(tools_module, '_list_level') as level:
            options, _ = self.options('input_Postgis', 'tablename', {'db': 'gis', 'schema-name': 'a; drop'})
        level.assert_not_called()
        self.assertEqual(options, [])


class ScriptedExecutor(object):
    def __init__(self, tools, calls):
        self.tools = {t.name: t for t in tools}
        self.calls = calls

    def invoke(self, payload, config=None):
        for name, args in self.calls:
            self.tools[name].invoke(args)
        return {'output': 'Hecho.'}


@override_settings(LANGUAGE_CODE='es')
class IssuesPickTests(SimpleTestCase):

    def _run(self, picker, restricted=False):
        calls = [('check_workspace', {})]
        with mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_ACTIONS', True, create=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_PARAM_PICKER', picker, create=True), \
                mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor',
                                  side_effect=lambda llm, tools, prompt: ScriptedExecutor(tools, calls)):
            result = agent.run_assistant(_context(restricted), 'revisa', [], CANVAS, None, None)
        return {(i['node'], i['code']): i for i in result['issues']}

    def test_off(self):
        issues = self._run(False)
        self.assertNotIn('pick', issues[('n1', 'missing_parameter')])

    def test_on(self):
        issues = self._run(True)
        self.assertEqual(issues[('n1', 'missing_parameter')]['pick'],
                         {'type': 'input_Csv', 'file_picker': {'extensions': 'csv,txt'}})
        unknown = issues[('n2', 'unknown_connection')]
        self.assertEqual(unknown['param'], 'db')
        self.assertEqual(unknown['pick'], {'type': 'input_Postgis'})

    def test_restricted_edition_gets_no_pick(self):
        issues = self._run(True, restricted=True)
        self.assertNotIn('pick', issues[('n1', 'missing_parameter')])


class UsableDatastoresTests(SimpleTestCase):
    """Hacen falta los dos permisos: usar el almacén y usar su conexión en ETL."""

    def test_both_permissions_are_required(self):
        from gvsigol_plugin_geoetl.assistant.context import usable_datastores

        def store(name, connection):
            return SimpleNamespace(name=name, description=None, schema='s', workspace=SimpleNamespace(name='ws'),
                                   connection=SimpleNamespace(name=connection))
        candidates = [store('propio', 'gis'), store('sin_etl', 'otra'), store('sin_permiso', 'gis'), store('oracle', 'ora')]
        with mock.patch('gvsigol_services.utils.can_use_datastore',
                        side_effect=lambda request, ds: ds.name != 'sin_permiso'):
            found = usable_datastores(object(), CONNECTIONS, candidates)
        self.assertEqual([d['name'] for d in found], ['propio'])
        self.assertEqual(found[0]['connection'], 'gis')


class AlternativesRestrictedTests(SimpleTestCase):
    """Corrección de la fase 3: en edición restringida no se cambia un nodo protegido del canvas."""

    def test_protected_canvas_node_has_no_alternatives(self):
        proposal = json.dumps({'mode': 'patch', 'assumptions': [
            {'text': 'n1: separador', 'node': 'n1', 'param': 'separator', 'source': 'choices'}],
            'ops': [{'op': 'add_node', 'node': {'id': 'n5', 'type': 'trans_Filter', 'parameters': {}}}]})
        for restricted, expected in ((False, 1), (True, 0)):
            holder = []
            tools = {t.name: t for t in build_tools(_context(restricted), load_catalog(), CANVAS, None, None, holder,
                                                    alternatives=True)}
            tools['propose_workspace'].invoke({'proposal_json': proposal})
            self.assertEqual(len(holder[-1]['assumption_choices']), expected, restricted)


def _user(staff=True):
    return SimpleNamespace(id=7, username='ana', is_authenticated=True, is_staff=staff, is_superuser=staff)


class ViewTests(SimpleTestCase):

    def _post(self, body, picker=True, user=None, restricted_error=None):
        request = RequestFactory().post('/o/', data=json.dumps(body), content_type='application/json')
        request.user = user or _user()
        with mock.patch.object(views, 'assistant_feature_enabled', return_value=True), \
                mock.patch.object(geoetl_settings, 'ETL_ASSISTANT_PARAM_PICKER', picker, create=True), \
                mock.patch('gvsigol_plugin_geoetl.views.get_etl_connections_list', return_value=CONNECTIONS), \
                mock.patch.object(views, '_workspace_access', return_value=restricted_error or (None, False)):
            return views.etl_assistant_options(request)

    def test_off_by_default(self):
        with self.assertRaises(Http404):
            self._post({'type': 'input_Postgis', 'param': 'db'}, picker=False)

    def test_only_staff(self):
        self.assertEqual(self._post({'type': 'input_Postgis', 'param': 'db'}, user=_user(staff=False)).status_code, 403)

    def test_connections(self):
        response = self._post({'type': 'input_Postgis', 'param': 'db'})
        self.assertEqual(json.loads(response.content),
                         {'options': [{'value': 'gis', 'label': 'gis'}], 'needs': None, 'error': False,
                          'create_datastore': False})

    def test_unknown_type_or_parameter(self):
        self.assertEqual(self._post({'type': 'inventado', 'param': 'db'}).status_code, 400)
        self.assertEqual(self._post({'type': 'input_Postgis', 'param': 'inventado'}).status_code, 400)
        self.assertEqual(self._post({'type': 5, 'param': []}).status_code, 400)

    def test_restricted_edition(self):
        response = self._post({'type': 'input_Postgis', 'param': 'db'}, restricted_error=(None, True))
        self.assertEqual(response.status_code, 403)

    def test_forbidden_workspace(self):
        denied = views.JsonResponse({'error': 'x'}, status=403)
        response = self._post({'type': 'input_Postgis', 'param': 'db', 'workspace_id': 9}, restricted_error=(denied, None))
        self.assertEqual(response.status_code, 403)

    def test_files_are_not_listed(self):
        self.assertEqual(self._post({'type': 'input_Csv', 'param': 'csv-file'}).status_code, 400)

    def test_reading_failure_does_not_show_details(self):
        with mock.patch.object(param_options, 'options_for', side_effect=RuntimeError('clave secreta')):
            response = self._post({'type': 'input_Postgis', 'param': 'db'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'options': [], 'needs': None, 'error': True})
