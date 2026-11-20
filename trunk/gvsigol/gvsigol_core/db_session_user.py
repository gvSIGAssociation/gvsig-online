# -*- coding: utf-8 -*-
"""
Usuario de la petición en curso como variable de sesión de base de datos.

Las vistas de datastore que deben devolver solo las filas del usuario que consulta
(por ejemplo, la selección de accidentes de Libra Accicar) filtran con
current_setting('gvsigol.user', true). GeoServer la fija con el "Session startup SQL"
del datastore; aquí se fija en las conexiones que abre el backend (Introspect).

Django REST Framework copia el usuario autenticado en la petición de Django, así que
al abrir la conexión ya está disponible aunque la autenticación sea por token.
"""
import contextvars
import logging

logger = logging.getLogger("gvsigol")

SESSION_USER_SETTING = "gvsigol.user"

_current_request = contextvars.ContextVar("gvsigol_current_request", default=None)


class DbSessionUserMiddleware:
    """Guarda la petición en curso para que las conexiones sepan a quién pertenecen."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


def current_username():
    request = _current_request.get()
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return user.get_username()
    return None


def apply_session_user(cursor):
    """Fija gvsigol.user en la conexión del cursor si hay un usuario autenticado."""
    username = current_username()
    if not username:
        return
    try:
        cursor.execute("SELECT set_config(%s, %s, false)", [SESSION_USER_SETTING, username])
    except Exception:
        logger.exception("No se ha podido fijar el usuario en la sesión de base de datos")
