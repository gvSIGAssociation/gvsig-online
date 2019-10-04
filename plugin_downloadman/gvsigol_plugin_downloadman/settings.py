# -*- coding: utf-8 -*-
APP_TITLE = 'Gestor de descargas'
APP_DESCRIPTION = 'Gestor de descargas'
TMP_DIR="/tmp/gol-downman"
TARGET_ROOT='/var/www/sites/gvsigol.localhost/media/downloads'
from gvsigol.settings import BASE_URL
TARGET_URL = BASE_URL + '/media/downloads'

LOCAL_PATHS_WHITELIST = ["/tmp/downmanwhitelist/", '/var/www/sites/gvsigol.localhost/media/downloads']