# -*- coding: utf-8 -*-
"""Marca de cancelación de un turno del asistente, visible desde todos los procesos.

Se guarda en la caché compartida de GeoCopilot (alias 'geocopilot',
GEOCOPILOT_SHARED_CACHE=True): el proceso web la pone y el worker la lee.

- Fase 3: si ningún worker recoge el turno a tiempo, el web lo marca para que
  un worker que lo recoja tarde no lo ejecute.
- Fase 4: el botón Detener y la desconexión del navegador.
"""

KEY = 'etl_assistant:cancelled:%s'
OWNER_KEY = 'etl_assistant:owner:%s'
TTL_SECONDS = 3600


def _cache():
    from gvsigol_plugin_geocopilot.utils.shared_cache import get_shared_cache
    return get_shared_cache()


def cancel(query_id):
    if query_id:
        _cache().set(KEY % query_id, True, TTL_SECONDS)


def set_owner(query_id, user_id):
    """Quién lanzó el turno: solo él puede detenerlo."""
    if query_id:
        _cache().set(OWNER_KEY % query_id, user_id, TTL_SECONDS)


def owner(query_id):
    if not query_id:
        return None
    try:
        return _cache().get(OWNER_KEY % query_id)
    except Exception:
        return None


def is_cancelled(query_id):
    if not query_id:
        return False
    try:
        return bool(_cache().get(KEY % query_id))
    except Exception:
        return False
