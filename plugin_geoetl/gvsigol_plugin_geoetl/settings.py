# -*- coding: utf-8 -*-
import environ
import os
import logging
from django.conf import settings

LOGGER = logging.getLogger('gvsigol')

ETL_URL = '/etlurl'

URL_GEOCODER = {
    'icv-direct': "http://descargas.icv.gva.es/server_api/geocodificador/solrgeocoderatmvcv.php?limit=1&query=%s&servicio=rtcv+nomenclator&start=0&",
    'icv-reverse': "http://descargas.icv.gva.es/server_api/geocodificador/geocoder.php?&x=%s&y=%s"
}

env_plugin_geoetl = environ.Env(
    ETL_DB_HOST=(str,settings.DATABASES['default']['HOST']),
    ETL_DB_PORT=(str,settings.DATABASES['default']['PORT']),
    ETL_DB_NAME=(str,settings.DATABASES['default']['NAME']),
    ETL_DB_USER=(str,settings.DATABASES['default']['USER']),
    ETL_DB_PASSWD=(str,settings.DATABASES['default']['PASSWORD'])
)

GEOETL_DB = {
    'host': env_plugin_geoetl('ETL_DB_HOST'),
    'port': env_plugin_geoetl('ETL_DB_PORT'),
    'database': env_plugin_geoetl('ETL_DB_NAME'),
    'user': env_plugin_geoetl('ETL_DB_USER'),
    'password': env_plugin_geoetl('ETL_DB_PASSWD'),
    'schema': 'ds_plugin_geoetl'
}

LOGGER.info("ETL_DB_HOST= %s",GEOETL_DB['host'])
LOGGER.info("ETL_DB_PORT= %s",GEOETL_DB['port'])
LOGGER.info("ETL_DB_NAME= %s",GEOETL_DB['database'])
LOGGER.info("ETL_DB_USER= %s",GEOETL_DB['user'])