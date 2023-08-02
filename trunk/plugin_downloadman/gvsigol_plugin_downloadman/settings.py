# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_noop as _

APP_TITLE = 'Gestor de descargas'
APP_DESCRIPTION = 'Gestor de descargas'
TMP_DIR="/tmp/gol-downman"
#TARGET_ROOT='/var/www/downloads'
TARGET_ROOT='/var/www/sites/gvsigol.localhost/media/downloads'
from gvsigol.settings import BASE_URL
TARGET_URL = BASE_URL + '/media/downloads'
DOWNLOADS_URL = BASE_URL + '/downloads'
#DOWNLOADS_ROOT = '/var/www/downloads'
DOWNLOADS_ROOT = '/opt/descargas/datos'
DOWNMAN_PACKAGING_BEHAVIOUR = 'DYNAMIC'
DOWNMAN_EMAIL_HOST_USER = ''
DOWNMAN_EMAIL_HOST_PASSWORD = ''

STATISTICS=[
{
    'id': 'gvsigol_plugin_downloadman',
    'count': 1,
    'operation': 'layer_resource_downloaded',
    'reverse_petition': False,
    'title': _('Layer resource downloads'),
    'target_title': _('LayerResourceProxy'),
    'target_field': 'fq_title_name'
},
{
    'id': 'gvsigol_plugin_downloadman',
    'count': 2,
    'operation': 'layer_downloaded',
    'reverse_petition': False,
    'title': _('Layer downloads'),
    'target_title': _('LayerProxy'),
    'target_field': 'title'
},
]

#LOCAL_PATHS_WHITELIST = ["/var/www/downloads"]
LOCAL_PATHS_WHITELIST = ["/tmp/downmanwhitelist/", '/var/www/sites/gvsigol.localhost/media/downloads', '/opt/descargas']
