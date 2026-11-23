# -*- coding: utf-8 -*-
'''
Registro de asistentes de IA para las pantallas de administración.

El core no importa ningún plugin: un plugin (p. ej. gvsigol_plugin_geoagents) se
apunta aquí desde su AppConfig.ready() y las vistas del core solo preguntan si hay
un asistente disponible para una función y un objeto concretos.

Funciones conocidas:
- FIELD_TITLES: «Generar títulos con IA» en la pestaña de títulos de campo de una capa.
- STYLE_SUGGESTION: «Sugerir estilo con IA» en la simbología de una capa.

Garantías:
- Sin plugin registrado, todo responde «no disponible».
- Un fallo del plugin nunca llega a la vista: se registra en el log y la función
  se da por no disponible (el botón no aparece y la pantalla sigue funcionando).
'''
import logging
import threading

logger = logging.getLogger(__name__)

FIELD_TITLES = 'field_titles'
STYLE_SUGGESTION = 'style_suggestion'
FEATURES = (FIELD_TITLES, STYLE_SUGGESTION)

_lock = threading.Lock()
_providers = {}


def register(feature, provider):
    '''Registra el proveedor de una función.

    `provider(request, obj)` devuelve None (no disponible) o un dict con lo que necesita
    la plantilla, como mínimo {'url': '<endpoint>'}. Un segundo registro de la misma
    función sustituye al anterior.'''
    if feature not in FEATURES:
        raise ValueError('Función de asistente desconocida: %s' % feature)
    if not callable(provider):
        raise ValueError('El proveedor debe ser invocable')
    with _lock:
        _providers[feature] = provider


def unregister(feature):
    with _lock:
        _providers.pop(feature, None)


def get(feature, request, obj=None):
    '''Configuración del asistente (dict con 'url') o None si no está disponible.'''
    provider = _providers.get(feature)
    if provider is None:
        return None
    try:
        conf = provider(request, obj)
    except Exception:  # noqa: BLE001 (un fallo del plugin nunca rompe la pantalla)
        logger.warning('Asistente de IA «%s»: el proveedor ha fallado; se oculta', feature, exc_info=True)
        return None
    if not isinstance(conf, dict) or not conf.get('url'):
        return None
    return conf


def is_available(feature, request, obj=None):
    return get(feature, request, obj) is not None
