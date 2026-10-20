# -*- coding: utf-8 -*-
import environ
import os
import logging
from django.conf import settings

LOGGER = logging.getLogger('gvsigol')

ETL_URL = '/etlurl'

URL_GEOCODER = {
    'icv-direct': "https://descargas.icv.gva.es/00/buscador/?consulta=%s&limite=1&inicio=0",
    'icv-reverse': "https://descargas.icv.gva.es/00/geoprocesos/geocodificador-inverso/?tema=callejero,municipios,catastro,forestal,espacios-protegidos&epsg=25830&x=%s&y=%s"
}

env_plugin_geoetl = environ.Env(
    ETL_DB_HOST=(str,settings.DATABASES['default']['HOST']),
    ETL_DB_PORT=(str,settings.DATABASES['default']['PORT']),
    ETL_DB_NAME=(str,settings.DATABASES['default']['NAME']),
    ETL_DB_USER=(str,settings.DATABASES['default']['USER']),
    ETL_DB_PASSWD=(str,settings.DATABASES['default']['PASSWORD']),
    ETL_EXCEL_MAX_ROWS=(int, 500000),
    ETL_EXCEL_MAX_COLS=(int, 512),
    ETL_EXCEL_READ_CHUNKSIZE=(int, 10000),
    ETL_EXCEL_SQL_CHUNKSIZE=(int, 5000),
    ETL_CANVAS_MAX_DELIVERIES=(int, 2),
)

GEOETL_DB = {
    'host': env_plugin_geoetl('ETL_DB_HOST'),
    'port': env_plugin_geoetl('ETL_DB_PORT'),
    'database': env_plugin_geoetl('ETL_DB_NAME'),
    'user': env_plugin_geoetl('ETL_DB_USER'),
    'password': env_plugin_geoetl('ETL_DB_PASSWD'),
    'schema': 'ds_plugin_geoetl'
}

# Hard caps for Excel loads (guards against openpyxl dimension bombs / OOM).
ETL_EXCEL_MAX_ROWS = env_plugin_geoetl('ETL_EXCEL_MAX_ROWS')
ETL_EXCEL_MAX_COLS = env_plugin_geoetl('ETL_EXCEL_MAX_COLS')
ETL_EXCEL_READ_CHUNKSIZE = env_plugin_geoetl('ETL_EXCEL_READ_CHUNKSIZE')
ETL_EXCEL_SQL_CHUNKSIZE = env_plugin_geoetl('ETL_EXCEL_SQL_CHUNKSIZE')
# After this many Celery deliveries of the same task id, ack and mark Error (poison pill).
ETL_CANVAS_MAX_DELIVERIES = env_plugin_geoetl('ETL_CANVAS_MAX_DELIVERIES')

LOGGER.info("ETL_DB_HOST= %s",GEOETL_DB['host'])
LOGGER.info("ETL_DB_PORT= %s",GEOETL_DB['port'])
LOGGER.info("ETL_DB_NAME= %s",GEOETL_DB['database'])
LOGGER.info("ETL_DB_USER= %s",GEOETL_DB['user'])