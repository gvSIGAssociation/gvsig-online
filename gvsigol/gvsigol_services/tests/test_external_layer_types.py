# -*- coding: utf-8 -*-
"""Registro de tipos de capa externa de plugins y su efecto en can_read_layer."""
from unittest import mock

from django.test import SimpleTestCase

from gvsigol_services import external_layer_types as elt
from gvsigol_services.models import Layer
from gvsigol_services.utils import can_read_layer


class _Protected(elt.ExternalLayerTypeHandler):
    code = 'TEST_PROTECTED'
    label = 'Protegido'
    enforce_read_roles = True


class _Open(elt.ExternalLayerTypeHandler):
    code = 'TEST_OPEN'
    label = 'Abierto'


class ExternalLayerTypeRegistryTest(SimpleTestCase):
    def tearDown(self):
        elt.unregister_external_layer_type('TEST_PROTECTED')
        elt.unregister_external_layer_type('TEST_OPEN')

    def test_register_and_get(self):
        self.assertIsNone(elt.get_handler('TEST_PROTECTED'))
        elt.register_external_layer_type(_Protected())
        self.assertIsInstance(elt.get_handler('TEST_PROTECTED'), _Protected)
        self.assertIn('TEST_PROTECTED', elt.get_registered_types())

    def test_register_requires_code(self):
        with self.assertRaises(ValueError):
            elt.register_external_layer_type(elt.ExternalLayerTypeHandler())

    def test_default_serialize_params_is_identity(self):
        params = {'url': 'x'}
        self.assertIs(_Open().serialize_params(None, params, {}), params)


class CanReadExternalLayerTest(SimpleTestCase):
    """El comportamiento previo (externas de lectura libre) solo cambia para tipos que lo piden."""

    def tearDown(self):
        elt.unregister_external_layer_type('TEST_PROTECTED')
        elt.unregister_external_layer_type('TEST_OPEN')

    def _layer(self, type_, public=False):
        return Layer(id=999999, external=True, type=type_, public=public)

    def test_unregistered_external_type_is_readable(self):
        self.assertTrue(can_read_layer('anyone', self._layer('WMS')))

    def test_registered_type_without_enforcement_is_readable(self):
        elt.register_external_layer_type(_Open())
        self.assertTrue(can_read_layer('anyone', self._layer('TEST_OPEN')))

    @mock.patch('gvsigol_services.authorization.PlainAuthorizationService.can_read_layer', return_value=False)
    def test_protected_type_uses_read_roles(self, plain_can_read):
        elt.register_external_layer_type(_Protected())
        layer = self._layer('TEST_PROTECTED')
        self.assertFalse(can_read_layer('someone', layer))
        plain_can_read.assert_called_once_with('someone', layer)

    @mock.patch('gvsigol_services.authorization.PlainAuthorizationService.can_read_layer', return_value=True)
    def test_protected_type_granted_by_role(self, _):
        elt.register_external_layer_type(_Protected())
        self.assertTrue(can_read_layer('someone', self._layer('TEST_PROTECTED')))

    @mock.patch('gvsigol_services.authorization.PlainAuthorizationService.can_read_layer', return_value=False)
    def test_public_protected_layer_is_readable(self, plain_can_read):
        elt.register_external_layer_type(_Protected())
        self.assertTrue(can_read_layer('anyone', self._layer('TEST_PROTECTED', public=True)))
        plain_can_read.assert_not_called()
