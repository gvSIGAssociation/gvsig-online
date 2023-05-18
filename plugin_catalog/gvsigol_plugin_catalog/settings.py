# -*- coding: utf-8 -*-
APP_TITLE = 'Catálogo de metadatos'
APP_DESCRIPTION = 'Catálogo de metadatos'
CATALOG_BASE_URL = 'http://localhost/geonetwork'
CATALOG_URL = CATALOG_BASE_URL + '/srv/eng/'
CATALOG_QUERY_URL = CATALOG_BASE_URL + '/srv/eng/q'
CATALOG_USER = 'admin'
CATALOG_PASSWORD = 'admin'
# valid values: 'legacy3.2', 'api0.1'
CATALOG_API_VERSION = 'api0.1'
CATALOG_FACETS_CONFIG = '{"orgName": {"title": "Organization"}, "topicCat": {"title": "Categories"}, "spatialRepresentationType": {"title": "Representation type"}, "maintenanceAndUpdateFrequency": {"title": "Update frequency"}, "denominator": {"title": "Scale"}, "gemetKeyword": {"title": "GEMET keywords"}, "panaceaKeyword": [{"name": "interregMedProjects", "title": "INTERREG Med Projects", "labelPattern": ".* project$"}, {"name": "panaceaWorkingGroups", "title": "Working group", "labelPattern": "^(.(?! project$))+$"}]}'
CATALOG_FACETS_ORDER = '["panaceaWorkingGroups", "interregMedProjects", "type", "spatialRepresentationType"]'
CATALOG_DISABLED_FACETS = '["mdActions"]'
CATALOG_SEARCH_FIELD = 'anylight'
CATALOG_CUSTOM_FILTER_URL = ''

METADATA_VIEWER_BUTTON = 'FULL'
DISABLE_CATALOG_NAVBAR_MENUS = 'False'
CATALOG_TIMEOUT = 10
