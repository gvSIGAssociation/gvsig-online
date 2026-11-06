# -*- coding: utf-8 -*-
'''
Proxy de lectura hacia GeoServer para la previsualización de simbologías.

Sustituye el envío de la contraseña de sesión al navegador (autenticación Basic
desde JavaScript) en los despliegues sin Keycloak: el navegador pide los tiles
y el WFS a este proxy y el backend los reenvía a GeoServer con las credenciales
de la sesión del usuario (gvsigol_services.utils.getUserAuthSession), de modo que
GeoServer sigue aplicando los permisos del propio usuario.

Solo se aceptan URLs de un GeoServer configurado (Server.frontend_url) y
peticiones WMS/WFS de lectura, para que no pueda usarse como proxy abierto.
'''
from urllib.parse import urlsplit, parse_qsl

from django.conf import settings

ALLOWED_SERVICES = {'WMS', 'WFS'}
ALLOWED_REQUESTS = {
    'GETMAP', 'GETLEGENDGRAPHIC', 'GETCAPABILITIES', 'GETFEATURE', 'DESCRIBEFEATURETYPE',
}
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 120


class ProxyNotAllowed(Exception):
    pass


def _norm_path(path):
    return (path or '').rstrip('/')


def resolve_target(url, extra_params, servers):
    '''
    Valida la URL pedida y devuelve (url_interna_sin_query, lista_de_parametros).

    url: URL que el navegador habría pedido a GeoServer (absoluta o relativa al host).
    extra_params: lista de (clave, valor) adicionales (p. ej. los que añade $.ajax).
    servers: lista de (frontend_url, internal_url) de los GeoServer configurados.
      La URL se valida contra frontend_url (la que conoce el navegador) y se reenvía
      a internal_url (nodo maestro, la misma base que usa la API REST del backend).
    '''
    if not url:
        raise ProxyNotAllowed('url vacía')
    target = urlsplit(url)
    if target.scheme and target.scheme not in ('http', 'https'):
        raise ProxyNotAllowed('esquema no permitido')

    for frontend_url, internal_url in servers:
        base = urlsplit(frontend_url)
        base_path = _norm_path(base.path)
        if target.netloc:
            if (target.scheme, target.netloc.lower()) != (base.scheme, base.netloc.lower()):
                continue
        if not (target.path == base_path or target.path.startswith(base_path + '/')):
            continue
        if '..' in target.path.split('/'):
            raise ProxyNotAllowed('ruta no permitida')
        params = parse_qsl(target.query, keep_blank_values=True) + list(extra_params)
        upper = {}
        for key, value in params:
            upper.setdefault(key.upper(), value)
        if upper.get('SERVICE', '').upper() not in ALLOWED_SERVICES:
            raise ProxyNotAllowed('servicio no permitido')
        if upper.get('REQUEST', '').upper() not in ALLOWED_REQUESTS:
            raise ProxyNotAllowed('operación no permitida')
        rest_of_path = target.path[len(base_path):]
        return (internal_url or frontend_url).rstrip('/') + rest_of_path, params
    raise ProxyNotAllowed('servidor no permitido')


def forward(session, absolute_url, params):
    return session.get(absolute_url, params=params, verify=False,
                       proxies=getattr(settings, 'PROXIES', None),
                       timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
