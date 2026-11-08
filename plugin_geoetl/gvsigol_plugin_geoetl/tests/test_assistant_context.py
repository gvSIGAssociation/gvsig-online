# -*- coding: utf-8 -*-
"""Permisos del asistente sin request (fase 1): el contexto que viaja al worker da lo mismo que el request."""
import json
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_plugin_geoetl.assistant import agent
from gvsigol_plugin_geoetl.assistant.context import AssistantContext, as_context
from gvsigol_plugin_geoetl.assistant.tools import build_tools

CONNECTIONS = [{'name': 'gis', 'type': 'PostGIS'}, {'name': 'ora', 'type': 'Oracle'}]


def _user(superuser=False, staff=True, roles=(), uid=7, username='ana'):
    return SimpleNamespace(id=uid, username=username, is_superuser=superuser, is_staff=staff, roles=roles)


def _manage(req, path):
    return req.user.is_superuser or path.split('/')[0] in getattr(req.user, 'roles', ())


class ContextPayloadTests(SimpleTestCase):

    def test_round_trip_is_json(self):
        request = SimpleNamespace(user=_user(superuser=True))
        context = AssistantContext.from_request(request, CONNECTIONS, True, language='en')
        payload = json.loads(json.dumps(context.to_payload()))
        again = AssistantContext.from_payload(payload)
        self.assertEqual(again.user_id, 7)
        self.assertEqual(again.username, 'ana')
        self.assertTrue(again.is_superuser)
        self.assertTrue(again.restricted)
        self.assertEqual(again.language, 'en')
        self.assertEqual(again.connections, CONNECTIONS)
        self.assertIsNone(payload['file_dirs'])          # superusuario: todas

    def test_as_context_keeps_a_context(self):
        context = AssistantContext.from_payload({'connections': CONNECTIONS})
        self.assertIs(as_context(context, None, None), context)

    def test_payload_without_dirs_gives_no_folders(self):
        context = AssistantContext.from_payload({'is_staff': True})
        self.assertFalse(context.can_manage_dir('rol_a'))

    def test_connections_come_from_the_context(self):
        context = AssistantContext.from_payload({'is_superuser': True, 'connections': CONNECTIONS})
        tools = {t.name: t for t in build_tools(context, {}, {}, None, None, [])}
        out = json.loads(tools['list_connections'].invoke({}))
        self.assertEqual([c['name'] for c in out['connections']], ['gis', 'ora'])
        out = json.loads(tools['list_tables'].invoke({'connection': 'otra'}))
        self.assertEqual(out['error'], 'Conexión no disponible.')


class ListFilesEquivalenceTests(SimpleTestCase):
    """list_files con el request y con el contexto ya resuelto devuelven lo mismo."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        for rel in ('rol_a/datos/municipios.csv', 'rol_a/orto.tif', 'rol_b/secreto.csv',
                    'rol_a/.oculto/x.csv', '.geoetl_models/m.joblib', 'suelto.csv'):
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'w').close()

    def _patched(self):
        return [
            self.settings(FILEMANAGER_DIRECTORY=self.root),
            mock.patch('gvsigol_filemanager.views.can_manage_path', side_effect=_manage),
            mock.patch('gvsigol_filemanager.views.can_browse_path',
                       side_effect=lambda req, path: path == '' or _manage(req, path)),
        ]

    def _both(self, user, **args):
        request = SimpleNamespace(user=user)
        patches = self._patched()
        for patch in patches:
            patch.__enter__()
        try:
            by_request = {t.name: t for t in build_tools(request, {}, {}, [], False, [])}
            first = json.loads(by_request['list_files'].invoke(args))
            payload = AssistantContext.from_request(request, [], False).to_payload()
        finally:
            for patch in reversed(patches):
                patch.__exit__(None, None, None)
        # En el worker: sin request ni mocks de permisos, solo la raíz del gestor
        with self.settings(FILEMANAGER_DIRECTORY=self.root):
            context = AssistantContext.from_payload(json.loads(json.dumps(payload)))
            by_context = {t.name: t for t in build_tools(context, {}, {}, None, None, [])}
            second = json.loads(by_context['list_files'].invoke(args))
        return first, second, payload

    def test_staff_with_one_role(self):
        staff = _user(roles=('rol_a',))
        for args in ({}, {'extensions': 'csv'}, {'folder': 'rol_a/datos'}, {'folder': 'rol_b'},
                     {'folder': '../etc'}, {'folder': 'no_existe'}):
            with self.subTest(args=args):
                first, second, payload = self._both(staff, **args)
                self.assertEqual(first, second)
        self.assertEqual(payload['file_dirs'], ['rol_a'])

    def test_superuser(self):
        admin = _user(superuser=True)
        for args in ({}, {'extensions': 'csv'}, {'folder': 'rol_b'}):
            with self.subTest(args=args):
                first, second, _ = self._both(admin, **args)
                self.assertEqual(first, second)

    def test_staff_without_roles(self):
        first, second, payload = self._both(_user(roles=()))
        self.assertEqual(first, second)
        self.assertEqual(first['files'], [])
        self.assertEqual(payload['file_dirs'], [])


@override_settings(LANGUAGE_CODE='es')
class RunWithContextTests(SimpleTestCase):

    def test_language_of_the_context_reaches_the_prompt(self):
        seen = {}

        class Executor(object):
            def invoke(self, payload):
                return {'output': 'Hola.'}

        def fake_executor(llm, tools, prompt):
            seen['system'] = prompt.format_messages(input='x', chat_history=[], agent_scratchpad=[])[0].content
            seen['tools'] = [t.name for t in tools]
            return Executor()

        context = AssistantContext.from_payload({'is_superuser': True, 'connections': CONNECTIONS,
                                                 'language': 'en'})
        with mock.patch.object(agent, '_build_llm', return_value=None), \
                mock.patch.object(agent, '_executor', side_effect=fake_executor):
            result = agent.run_assistant(context, 'hola', [], {}, None, None)
        self.assertEqual(result['reply'], 'Hola.')
        self.assertIn('Respondes en inglés', seen['system'])
        self.assertIn('list_files', seen['tools'])
