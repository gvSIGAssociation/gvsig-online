# -*- coding: utf-8 -*-
'''Registro de asistentes de IA: sin plugin o con un plugin que falla, nunca rompe la pantalla.'''
from django.test import SimpleTestCase

from gvsigol_core import ai_assist


class AiAssistRegistryTests(SimpleTestCase):

    def tearDown(self):
        for feature in ai_assist.FEATURES:
            ai_assist.unregister(feature)

    def test_sin_proveedor_no_disponible(self):
        self.assertIsNone(ai_assist.get(ai_assist.FIELD_TITLES, None))
        self.assertFalse(ai_assist.is_available(ai_assist.STYLE_SUGGESTION, None))

    def test_proveedor_que_falla_se_oculta(self):
        def boom(request, obj):
            raise RuntimeError('fallo')
        ai_assist.register(ai_assist.FIELD_TITLES, boom)
        with self.assertLogs('gvsigol_core.ai_assist', level='WARNING'):
            self.assertIsNone(ai_assist.get(ai_assist.FIELD_TITLES, None, 1))

    def test_respuesta_sin_url_no_cuenta(self):
        ai_assist.register(ai_assist.FIELD_TITLES, lambda r, o: {'x': 1})
        self.assertIsNone(ai_assist.get(ai_assist.FIELD_TITLES, None))
        ai_assist.register(ai_assist.FIELD_TITLES, lambda r, o: None)
        self.assertIsNone(ai_assist.get(ai_assist.FIELD_TITLES, None))

    def test_disponible(self):
        ai_assist.register(ai_assist.FIELD_TITLES, lambda r, o: {'url': '/x/%s/' % o})
        self.assertEqual(ai_assist.get(ai_assist.FIELD_TITLES, None, 7), {'url': '/x/7/'})
        self.assertFalse(ai_assist.is_available(ai_assist.STYLE_SUGGESTION, None, 7))

    def test_funcion_desconocida(self):
        with self.assertRaises(ValueError):
            ai_assist.register('otra', lambda r, o: None)
