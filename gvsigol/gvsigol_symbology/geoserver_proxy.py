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

Sesiones de Keycloak (OIDC): el token de acceso guardado en la sesión caduca a
los pocos minutos y Django solo lo renueva al navegar, así que no sirve para
pedir a GeoServer. En ese caso el proxy trabaja en «modo servicio»: comprueba en
gvSIG que el usuario puede leer cada capa pedida (check_service_request) y pide a
GeoServer con las credenciales de servicio del backend. Para que esos permisos no
se puedan saltar, en ese modo no se aceptan GetCapabilities ni parámetros que
puedan leer otras capas o cambiar la consulta (SLD externos, filtros, vistas SQL).
'''
from urllib.parse import urlsplit, parse_qsl

from django.conf import settings

ALLOWED_SERVICES = {'WMS', 'WFS'}
ALLOWED_REQUESTS = {
    'GETMAP', 'GETLEGENDGRAPHIC', 'GETCAPABILITIES', 'GETFEATURE', 'DESCRIBEFEATURETYPE',
}
# Capas técnicas de la vista previa de símbolos (datos sintéticos, ver symbol_preview.py)
PREVIEW_LAYER_NAMES = {'preview_point', 'preview_line', 'preview_polygon'}
PREVIEW_WORKSPACE = 'preview'
# Parámetros que nombran capas en WMS/WFS
LAYER_PARAMS = ('LAYERS', 'LAYER', 'QUERY_LAYERS', 'TYPENAME', 'TYPENAMES')
# En modo servicio: pueden traer datos de otras capas (SLD, funciones de filtro como
# queryCollection) o cambiar la consulta en BD (VIEWPARAMS de las vistas SQL)
SERVICE_FORBIDDEN_PARAMS = {'SLD', 'SLD_BODY', 'CQL_FILTER', 'FILTER', 'VIEWPARAMS', 'FEATUREID',
                            'RESOURCEID', 'STOREDQUERY_ID'}
SERVICE_OWS_ENDPOINTS = {'wms', 'wfs', 'ows'}
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 120


class ProxyNotAllowed(Exception):
    pass


def _norm_path(path):
    return (path or '').rstrip('/')


def path_workspace(url, base_url):
    '''
    Espacio de trabajo de una URL de GeoServer por espacio de trabajo (<base>/<ws>/wms|wfs|ows),
    o None si es el servicio global (<base>/wms). base_url: la URL base del GeoServer.
    '''
    base_path = _norm_path(urlsplit(base_url or '').path)
    path = urlsplit(url or '').path
    if base_path and (path == base_path or path.startswith(base_path + '/')):
        path = path[len(base_path):]
    parts = [p for p in path.split('/') if p]
    if len(parts) == 2 and parts[1].lower() in SERVICE_OWS_ENDPOINTS:
        return parts[0]
    return None


def requested_layers(params, workspace=None):
    '''[(espacio de trabajo o None, nombre)] de las capas que nombra la petición.'''
    layers = []
    for key, value in params:
        if key.upper() not in LAYER_PARAMS:
            continue
        for item in str(value or '').split(','):
            item = item.strip()
            if not item:
                continue
            ws, sep, name = item.rpartition(':')
            layers.append((ws if sep else workspace, name))
    return layers


def is_preview_layer(workspace, name):
    return name in PREVIEW_LAYER_NAMES and workspace in (None, PREVIEW_WORKSPACE)


def check_service_request(params, workspace, can_read):
    '''
    Valida una petición que se va a hacer con las credenciales de servicio.

    can_read(workspace, name) -> bool: si el usuario puede leer esa capa en gvSIG (workspace puede ser None).
    Lanza ProxyNotAllowed si algo no cuadra.
    '''
    upper = {}
    for key, value in params:
        upper.setdefault(key.upper(), value)
    if upper.get('REQUEST', '').upper() == 'GETCAPABILITIES':
        raise ProxyNotAllowed('GetCapabilities no permitido con credenciales de servicio')
    forbidden = sorted(set(upper) & SERVICE_FORBIDDEN_PARAMS)
    if forbidden:
        raise ProxyNotAllowed('parámetros no permitidos con credenciales de servicio: %s' % ', '.join(forbidden))
    layers = requested_layers(params, workspace)
    if not layers:
        raise ProxyNotAllowed('la petición no nombra ninguna capa')
    for ws, name in layers:
        if is_preview_layer(ws, name):
            continue
        if not can_read(ws, name):
            raise ProxyNotAllowed('sin permiso de lectura sobre la capa %s:%s' % (ws or '?', name))


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


def forward_form(session, absolute_url, params):
    """
    Igual que forward, pero por POST (formulario): GeoServer lo trata como KVP. Lo usa la vista previa
    de símbolos, cuyo SLD_BODY puede superar con las cabeceras de la sesión el límite de cabecera de
    Tomcat (8 KB) en una petición GET.
    """
    return session.post(absolute_url, data=params, verify=False,
                        proxies=getattr(settings, 'PROXIES', None),
                        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
