# -*- coding: utf-8 -*-
"""
Registro de tipos de capa externa aportados por plugins.

El core solo conoce los tipos de ``settings.EXTERNAL_LAYER_SUPPORTED_TYPES`` (WMS, WMTS, XYZ...).
Un plugin puede registrar tipos nuevos (p. ej. ``3DTILES`` o ``TERRAIN`` en
``gvsigol_plugin_viewer3d``) para reutilizar todo lo que ya ofrece ``Layer``: grupos de capas,
orden en el TOC, permisos ``LayerReadRole`` y la configuración del proyecto (projectconf).

Si ningún plugin registra tipos, el comportamiento del core no cambia.

Uso desde un plugin (en ``AppConfig.ready()``)::

    from gvsigol_services.external_layer_types import ExternalLayerTypeHandler, register_external_layer_type

    class Tiles3DHandler(ExternalLayerTypeHandler):
        code = '3DTILES'
        label = '3D Tiles'
        enforce_read_roles = True
        ...

    register_external_layer_type(Tiles3DHandler())
"""
import logging

logger = logging.getLogger('gvsigol')

_REGISTRY = {}


class ExternalLayerTypeHandler:
    """Comportamiento de un tipo de capa externa aportado por un plugin.

    Todos los métodos tienen una implementación por defecto neutra.
    """

    #: Valor de ``Layer.type`` (único)
    code = None
    #: Etiqueta para listados y formularios
    label = None
    #: Si True, la lectura de la capa exige ``LayerReadRole`` (o capa pública), como en una capa
    #: interna. Por defecto las capas externas se consideran de lectura libre (servicios públicos).
    enforce_read_roles = False
    #: Si True, el alta y la edición se hacen desde el plugin (no aparece en el formulario del core)
    managed_by_plugin = True

    def admin_edit_url(self, layer):
        """URL de edición de la capa en el plugin (o None para usar la del core)."""
        return None

    def serialize_params(self, layer, params, context):
        """Ajusta ``external_params`` antes de enviarlos al visor (projectconf).

        :param layer: instancia de ``Layer``
        :param params: dict con los ``external_params`` ya decodificados
        :param context: contexto del serializador (``request``, ``projectid``, ``lang``...)
        :return: dict con los parámetros que verá el cliente
        """
        return params


def register_external_layer_type(handler):
    if not isinstance(handler, ExternalLayerTypeHandler) or not handler.code:
        raise ValueError('handler debe ser un ExternalLayerTypeHandler con code')
    previous = _REGISTRY.get(handler.code)
    if previous is not None and type(previous) is not type(handler):
        logger.warning('Tipo de capa externa %s re-registrado por %s', handler.code, type(handler).__name__)
    _REGISTRY[handler.code] = handler


def unregister_external_layer_type(code):
    """Solo para tests."""
    _REGISTRY.pop(code, None)


def get_handler(layer_type):
    """Handler registrado para ``layer_type`` (o None)."""
    if not layer_type:
        return None
    return _REGISTRY.get(layer_type)


def get_registered_types():
    return dict(_REGISTRY)


def enforces_read_roles(layer):
    handler = get_handler(getattr(layer, 'type', None))
    return bool(handler and handler.enforce_read_roles)
