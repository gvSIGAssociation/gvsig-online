# -*- coding: utf-8 -*-
import environ

env = environ.Env(
    BASE_URL=(str,'https://localhost'),
    GEONETWORK_USE_KEEPALIVE=(bool, True),
)

APP_TITLE = 'Catálogo de metadatos'
APP_DESCRIPTION = 'Catálogo de metadatos'
BASE_URL = env('BASE_URL')
CATALOG_BASE_URL = env('GEONETWORK_BASE_URL', default=f'{BASE_URL}/geonetwork')
CATALOG_URL = CATALOG_BASE_URL + '/srv/eng/'
CATALOG_QUERY_URL = CATALOG_BASE_URL + '/srv/eng/q'
CATALOG_USER = env('GEONETWORK_USER', default='admin')
CATALOG_PASSWORD = env('GEONETWORK_PASS', default='admin')
# valid values: 'legacy3.2', 'api0.1'
CATALOG_API_VERSION = 'api0.1'
CATALOG_FACETS_CONFIG = env('CATALOG_FACETS_CONFIG', default='{}')
CATALOG_FACETS_ORDER = env('CATALOG_FACETS_ORDER', default='[]')
CATALOG_DISABLED_FACETS = env('CATALOG_DISABLED_FACETS', default='[]')
CATALOG_SEARCH_FIELD = env('CATALOG_SEARCH_FIELD', default='any')
CATALOG_CUSTOM_FILTER_URL = env('CATALOG_CUSTOM_FILTER_URL', default='')

METADATA_VIEWER_BUTTON = env('METADATA_VIEWER_BUTTON', default='LINK')
DISABLE_CATALOG_NAVBAR_MENUS = env('DISABLE_CATALOG_NAVBAR_MENUS', default='False')
CATALOG_TIMEOUT = env('CATALOG_TIMEOUT', default=10)

GEONETWORK_USE_KEEPALIVE = env('GEONETWORK_USE_KEEPALIVE')
