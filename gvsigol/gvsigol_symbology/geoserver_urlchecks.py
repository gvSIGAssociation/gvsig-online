# -*- coding: utf-8 -*-
'''
Iconos de las bibliotecas de símbolos y las «URL External Access Checks» de GeoServer.

GeoServer 2.24+ puede bloquear en silencio los gráficos externos (ExternalGraphic) que no
estén en su propio directorio de datos: el símbolo sale como un cuadrado gris en WMS y en
la impresión. Las bibliotecas de gvSIG guardan sus iconos en MEDIA_ROOT/symbol_libraries y
el SLD los referencia como file:<MEDIA_ROOT>/symbol_libraries/... (utils.geoserver_online_resource).

ensure_symbol_library_urlcheck(gs) añade, si no hay ya una regla que lo permita, UNA regla
que permite solo esa carpeta. Nunca modifica ni quita reglas existentes, y si las
comprobaciones están desactivadas en GeoServer la regla no tiene efecto.

NO se ejecuta sola salvo que se active GEOSERVER_ENSURE_SYMBOL_URLCHECK (por defecto False):
en los despliegues donde los iconos ya se ven no cambia nada. Para aplicarla a mano:
    python manage.py ensure_symbol_urlcheck
'''
import logging
import re
from urllib.parse import quote

from django.conf import settings

LOG = logging.getLogger('gvsigol')

RULE_NAME = 'gvsigol_symbol_libraries'
RULE_DESCRIPTION = 'gvSIG Online: iconos de las bibliotecas de símbolos (MEDIA_ROOT/symbol_libraries)'

_done = set()   # servidores ya comprobados en este proceso


def _media_root():
    return (getattr(settings, 'MEDIA_ROOT', '') or '').rstrip('/')


def library_regex():
    '''Expresión que admite file:/…, file:///… y file:///…//… de la carpeta de bibliotecas.'''
    root = _media_root().lstrip('/')
    return r'^file:/+' + re.escape(root) + r'/symbol_libraries/.*$'


def sample_urls():
    root = _media_root()
    return ['file:' + root + '/symbol_libraries/x/y.svg', 'file://' + root + '/symbol_libraries/x/y.svg']


def _rule_names(payload):
    '''Nombres de las reglas en GET /rest/urlchecks.json ({"urlChecks":{"urlCheck":[{"name",…}]}}).'''
    checks = (payload or {}).get('urlChecks') or {}
    if not isinstance(checks, dict):
        return []
    items = checks.get('urlCheck') or []
    items = items if isinstance(items, list) else [items]
    return [it.get('name') for it in items if isinstance(it, dict) and it.get('name')]


def rule_allows(rule, url):
    if not isinstance(rule, dict) or str(rule.get('enabled', 'true')).lower() == 'false':
        return False
    regex = rule.get('regex') or ''
    try:
        return re.match(regex, url) is not None
    except re.error:
        return False


def _base(gs):
    return gs.rest_url.rstrip('/') + '/urlchecks'


def check_symbol_library_urlcheck(gs, timeout=20):
    '''
    'exists' si alguna regla activa ya permite la carpeta de bibliotecas, 'missing' si no,
    'error' si no se pudo consultar. No modifica nada.
    '''
    if not _media_root():
        return 'error'
    try:
        r = gs.rest_catalog.session.get(_base(gs) + '.json', auth=(gs.user, gs.password), timeout=timeout)
        if r.status_code != 200:
            LOG.warning('URL checks de GeoServer no disponibles (HTTP %s)', r.status_code)
            return 'error'
        samples = sample_urls()
        for name in _rule_names(r.json()):
            d = gs.rest_catalog.session.get('%s/%s.json' % (_base(gs), quote(name, safe='')),
                                            auth=(gs.user, gs.password), timeout=timeout)
            if d.status_code != 200:
                continue
            rule = (d.json() or {}).get('regexUrlCheck')
            if rule and all(rule_allows(rule, u) for u in samples):
                return 'exists'
        return 'missing'
    except Exception as exc:  # noqa: BLE001
        LOG.warning('No se pudieron consultar las URL checks de GeoServer: %s', type(exc).__name__)
        return 'error'


def ensure_symbol_library_urlcheck(gs, timeout=20):
    '''
    'exists' si ya estaba permitido, 'created' si se ha añadido la regla, 'error' si no se pudo
    (no lanza: nunca debe impedir publicar un estilo). Nunca toca las reglas existentes.
    '''
    state = check_symbol_library_urlcheck(gs, timeout)
    if state != 'missing':
        return state
    body = {'regexUrlCheck': {'name': RULE_NAME, 'description': RULE_DESCRIPTION,
                              'enabled': True, 'regex': library_regex()}}
    try:
        r = gs.rest_catalog.session.post(_base(gs), json=body, auth=(gs.user, gs.password), timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        LOG.warning('No se pudo crear la regla de URL checks en GeoServer: %s', type(exc).__name__)
        return 'error'
    if r.status_code not in (200, 201):
        LOG.warning('No se pudo crear la regla de URL checks en GeoServer (HTTP %s)', r.status_code)
        return 'error'
    LOG.info('Añadida la regla «%s» a las URL checks de GeoServer', RULE_NAME)
    return 'created'


def maybe_ensure_for_sld(gs, sld_text):
    '''
    Gancho para la publicación de estilos: solo si GEOSERVER_ENSURE_SYMBOL_URLCHECK está
    activado y el SLD usa iconos de las bibliotecas. Una vez por servidor y proceso.
    '''
    if not getattr(settings, 'GEOSERVER_ENSURE_SYMBOL_URLCHECK', False):
        return None
    text = sld_text.decode('utf-8', 'ignore') if isinstance(sld_text, (bytes, bytearray)) else str(sld_text or '')
    if '/symbol_libraries/' not in text:
        return None
    key = getattr(gs, 'rest_url', id(gs))
    if key in _done:
        return None
    result = ensure_symbol_library_urlcheck(gs)
    if result != 'error':
        _done.add(key)
    return result
