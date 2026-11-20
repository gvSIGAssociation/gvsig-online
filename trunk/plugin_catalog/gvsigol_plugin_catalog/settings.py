# -*- coding: utf-8 -*-
import environ

env = environ.Env(
    BASE_URL=(str,'https://localhost'),
    GEONETWORK_USE_KEEPALIVE=(bool, True),
    CATALOG_AUTO_CREATE_METADATA=(bool, True),
)

APP_TITLE = 'Catálogo de metadatos'
APP_DESCRIPTION = 'Catálogo de metadatos'
BASE_URL = env('BASE_URL')
CATALOG_BASE_URL = env('GEONETWORK_BASE_URL', default=f'{BASE_URL}/geonetwork')
# URL used by the backend to reach GeoNetwork (Docker: internal hostname)
CATALOG_SERVICE_URL = env('GEONETWORK_INTERNAL_URL', default=CATALOG_BASE_URL)
# GeoNetwork 4.x SPA UI path (GN 3.x used /srv/eng/catalog.search)
CATALOG_EDITOR_PATH = env('GEONETWORK_EDITOR_PATH', default='/srv/spa/catalog.search')
CATALOG_URL = CATALOG_BASE_URL + '/srv/eng/'
# GeoNetwork 4.x no longer exposes /srv/eng/q; search is proxied via gvSIGOL backend.
CATALOG_QUERY_URL = '/gvsigonline/catalog/get_query/'
# Local GeoNetwork account. Used only when GEONETWORK_AUTH_TYPE=basic.
CATALOG_USER = env('GEONETWORK_USER', default='admin')
CATALOG_PASSWORD = env('GEONETWORK_PASS', default='admin')
# Auth against GeoNetwork API: 'basic' (local DB user) or 'bearer' (OIDC service account)
GEONETWORK_AUTH_TYPE = env('GEONETWORK_AUTH_TYPE', default='bearer').lower()

if env('OIDC_OP_TOKEN_ENDPOINT', default=''):
    DEFAULT_GEONETWORK_OIDC_TOKEN_URL=env('OIDC_OP_TOKEN_ENDPOINT')
else:
    OIDC_OP_BASE_URL = env('OIDC_OP_BASE_URL', default='')
    OIDC_OP_REALM_NAME = env('OIDC_OP_REALM_NAME', default='gvsigonline')
    if OIDC_OP_BASE_URL and OIDC_OP_REALM_NAME:
        DEFAULT_GEONETWORK_OIDC_TOKEN_URL = f'{OIDC_OP_BASE_URL}/realms/{OIDC_OP_REALM_NAME}/protocol/openid-connect/token'
    else:
        DEFAULT_GEONETWORK_OIDC_TOKEN_URL = ''
GEONETWORK_OIDC_TOKEN_URL = env('GEONETWORK_OIDC_TOKEN_URL', default=DEFAULT_GEONETWORK_OIDC_TOKEN_URL)
GEONETWORK_OIDC_CLIENT_ID = env('GEONETWORK_OIDC_CLIENT_ID', default='geonetwork-client')
GEONETWORK_OIDC_CLIENT_SECRET = env('GEONETWORK_OIDC_CLIENT_SECRET', default='')
GEONETWORK_OIDC_SCOPE = env(
    'GEONETWORK_OIDC_SCOPE',
    default='openid email profile offline_access',
)
# Workspace group that owns new metadata records. GeoNetwork 4.4 rejects
# an insert without it. Value is the group name. Creation fails if that
# group does not exist or is not a workspace group.
GEONETWORK_GROUP = env('GEONETWORK_GROUP', default='gvsigol')
# valid values: 'legacy3.2', 'api0.1', 'gn4'
CATALOG_API_VERSION = env('CATALOG_API_VERSION', default='gn4')
CATALOG_FACETS_CONFIG = env('CATALOG_FACETS_CONFIG', default='{}')
CATALOG_FACETS_ORDER = env('CATALOG_FACETS_ORDER', default='[]')
CATALOG_DISABLED_FACETS = env('CATALOG_DISABLED_FACETS', default='[]')
CATALOG_SEARCH_FIELD = env('CATALOG_SEARCH_FIELD', default='any')
CATALOG_CUSTOM_FILTER_URL = env('CATALOG_CUSTOM_FILTER_URL', default='')

METADATA_VIEWER_BUTTON = env('METADATA_VIEWER_BUTTON', default='LINK')
DISABLE_CATALOG_NAVBAR_MENUS = env('DISABLE_CATALOG_NAVBAR_MENUS', default='False')
CATALOG_TIMEOUT = env('CATALOG_TIMEOUT', default=25)

GEONETWORK_USE_KEEPALIVE = env('GEONETWORK_USE_KEEPALIVE')
# Si es False, no se crearán metadatos automáticamente para ninguna capa (ni públicas ni privadas)
# Los metadatos deberán crearse manualmente desde gvsigonline
# Por defecto True para mantener el comportamiento actual
CATALOG_AUTO_CREATE_METADATA = env('CATALOG_AUTO_CREATE_METADATA')
# Used when the client app does not ship an mdtemplates file, and to choose
# among several client templates of different standards.
# Empty + no client template keeps the plugin ISO 19139:2007 template.
# Aliases: iso19139, iso19115-3, iso19115-1, iso19115-3.mgb, mgb, mgb2, mgb-2.0
CATALOG_METADATA_STANDARD = env('CATALOG_METADATA_STANDARD', default='')
