# -*- coding: utf-8 -*-
APP_TITLE = 'Gestor de descargas'
APP_DESCRIPTION = 'Gestor de descargas'
TMP_DIR="/tmp/gol-downman"
TARGET_ROOT='/var/www/downloads'
from gvsigol.settings import BASE_URL
TARGET_URL = BASE_URL + '/media/downloads'
DOWNLOADS_URL = BASE_URL + '/downloads'
DOWNLOADS_ROOT = '/var/www/downloads'
DOWNMAN_PACKAGING_BEHAVIOUR = 'DYNAMIC'

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

LOCAL_PATHS_WHITELIST = ["/var/www/downloads"]


