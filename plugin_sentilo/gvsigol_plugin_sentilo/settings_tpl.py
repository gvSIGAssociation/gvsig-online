# -*- coding: utf-8 -*-
import logging
import environ
from gvsigol import settings

env = environ.Env()

LOGGER = logging.getLogger('gvsigol')

SENTILO_URL = '/sentilo'

env_plugin_sentilo = {
    'SENTILO_DB_HOST': settings.DATABASES['default']['HOST'],
    'SENTILO_DB_PORT': settings.DATABASES['default']['PORT'],
    'SENTILO_DB_NAME': settings.DATABASES['default']['NAME'],
    'SENTILO_DB_USER': settings.DATABASES['default']['USER'],
    'SENTILO_DB_PASSWD': settings.DATABASES['default']['PASSWORD']
}

MUNICIPALITY = '##MUNICIPALITY##'

SENTILO_DB = {
    'host': env_plugin_sentilo['SENTILO_DB_HOST'],
    'port': env_plugin_sentilo['SENTILO_DB_PORT'],
    'database': env_plugin_sentilo['SENTILO_DB_NAME'],
    'user': env_plugin_sentilo['SENTILO_DB_USER'],
    'password': env_plugin_sentilo['SENTILO_DB_PASSWD'],
    'schema': 'public'
}

# Cleanup output behavior: 'suffix' creates <table>_clean; 'overwrite' writes back into source
CLEAN_OUTPUT_MODE = getattr(settings, 'SENTILO_CLEAN_OUTPUT_MODE', 'overwrite')  # 'suffix' | 'overwrite'
CLEAN_OUTPUT_SUFFIX = getattr(settings, 'SENTILO_CLEAN_OUTPUT_SUFFIX', '_clean')
SENTILO_SCHEMA = SENTILO_DB.get('schema', 'public')

# Logging de valores
LOGGER.info("SENTILO_DB_HOST= %s", SENTILO_DB['host'])
LOGGER.info("SENTILO_DB_PORT= %s", SENTILO_DB['port'])
LOGGER.info("SENTILO_DB_NAME= %s", SENTILO_DB['database'])
LOGGER.info("SENTILO_DB_USER= %s", SENTILO_DB['user'])
LOGGER.info("MUNICIPALITY= %s", MUNICIPALITY)
LOGGER.info("SENTILO CLEAN OUTPUT MODE= %s", CLEAN_OUTPUT_MODE)
LOGGER.info("SENTILO CLEAN OUTPUT SUFFIX= %s", CLEAN_OUTPUT_SUFFIX)

