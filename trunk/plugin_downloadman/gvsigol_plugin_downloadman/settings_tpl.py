# -*- coding: utf-8 -*-
APP_TITLE = 'Gestor de descargas'
APP_DESCRIPTION = 'Gestor de descargas'
TMP_DIR='##DOWNLOADMANAGER_TMP_DIR##'
TARGET_ROOT='##DOWNLOADMANAGER_TARGET_ROOT##'
TARGET_URL = '##DOWNLOADMANAGER_TARGET_URL##'
DOWNLOADS_URL = '##DOWNLOADS_URL##'
DOWNLOADS_ROOT = '##DOWNLOADMANAGER_DOWNLOADS_ROOT##'
DOWNMAN_PACKAGING_BEHAVIOUR = 'DYNAMIC'
DOWNMAN_XSEND_BASEURL = '##DOWNMAN_XSEND_BASEURL##'
DOWNMAN_EMAIL_HOST_USER = '##DOWNMAN_EMAIL_HOST_USER##'
DOWNMAN_EMAIL_HOST_PASSWORD = '##DOWNMAN_EMAIL_HOST_PASSWORD##'

STATISTICS=[
{
    'id': 'gvsigol_plugin_downloadman',
    'count': 1,
    'operation': 'layer_resource_downloaded',
    'reverse_petition': False,
    'title': 'Layer resource downloads',
    'target_title': 'LayerResourceProxy',
    'target_field': 'fq_title_name'
},
{
    'id': 'gvsigol_plugin_downloadman',
    'count': 2,
    'operation': 'layer_downloaded',
    'reverse_petition': False,
    'title': 'Layer downloads',
    'target_title': 'LayerProxy',
    'target_field': 'title'
},
]
LOCAL_PATHS_WHITELIST = [##DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST##]
