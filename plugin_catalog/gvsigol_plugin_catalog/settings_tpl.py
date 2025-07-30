# -*- coding: utf-8 -*-
CATALOG_URL = '##CATALOG_URL##'
CATALOG_BASE_URL = '##CATALOG_BASE_URL##'
CATALOG_QUERY_URL = CATALOG_BASE_URL + '/srv/eng/q'
CATALOG_USER = '##GEONETWORK_USER##'
CATALOG_PASSWORD = '##GEONETWORK_PASS##'
# valid values: 'legacy3.2', 'api0.1'
CATALOG_API_VERSION = '##CATALOG_API_VERSION##'
# examples:
# CATALOG_FACETS_CONFIG = '{"orgName": {"title": "Organization"}, "sourceCatalog": {"title": "Source Catalog"}, "createDateYear": {"title": "Year"}, "spatialRepresentationType": {"title": "Representation type"}, "maintenanceAndUpdateFrequency": {"title": "Update frequencies"}, "denominator": {"title": "Scale"}, "serviceType": {"title": "Service type"}, "gemetKeyword": {"title": "GEMET keywords"}, "panaceaKeyword": [{"name": "interregMedProjects", "title": "INTERREG Med Projects", "labelPattern": ".* project$"}, {"name": "panaceaWorkingGroups", "title": "Working group", "labelPattern": "^(.(?! project$))+$"}]}'
# CATALOG_FACETS_ORDER = '["panaceaWorkingGroups", "interregMedProjects", "type", "spatialRepresentationType"]'
# CATALOG_DISABLED_FACETS = '["mdActions"]'
CATALOG_FACETS_CONFIG = '##CATALOG_FACETS_CONFIG##'
CATALOG_FACETS_ORDER = '##CATALOG_FACETS_ORDER##'
CATALOG_DISABLED_FACETS = '##CATALOG_DISABLED_FACETS##'
CATALOG_SEARCH_FIELD = '##CATALOG_SEARCH_FIELD##'
CATALOG_CUSTOM_FILTER_URL = '##CATALOG_CUSTOM_FILTER_URL##'

# allowed values: LINK, FULL, BRIEF
METADATA_VIEWER_BUTTON = '##METADATA_VIEWER_BUTTON##'
CATALOG_TIMEOUT = ##CATALOG_TIMEOUT##
GEONETWORK_USE_KEEPALIVE = '##GEONETWORK_USE_KEEPALIVE##'.lower() == 'true'