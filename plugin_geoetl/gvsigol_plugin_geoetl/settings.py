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
    # El asistente del canvas está apagado hasta que la instalación lo active.
    ETL_ASSISTANT_ENABLED=(bool, True),
    # Traza de cada turno del asistente en el log (herramientas, tiempos, resultado). Sin textos del usuario.
    ETL_ASSISTANT_TRACE=(bool, False),
    # Vacío: se usa el modelo por defecto de GeoCopilot.
    GEOETL_LLM_MODEL=(str, ''),
    # --- Nodos predictivos / ráster (etl_raster.py). 0 = sin límite ---
    # Píxeles máximos del ráster que procesa un nodo (alto x ancho).
    ETL_RASTER_MAX_PIXELS=(int, 4000000000),
    # Filas de entrenamiento máximas; si se superan se submuestrea (con aviso) en lugar de fallar.
    ETL_RASTER_MAX_TRAIN_ROWS=(int, 2000000),
    # Procesos para entrenar/predecir (-1 = todos los núcleos).
    ETL_RASTER_N_JOBS=(int, -1),
    # Píxeles por franja al vectorizar un ráster (controla la memoria).
    ETL_RASTER_POLYGONIZE_STRIP_PIXELS=(int, 25000000),
    # Píxeles máximos para el filtro de tamaño mínimo de parche (necesita el ráster entero en memoria).
    ETL_RASTER_SIEVE_MAX_PIXELS=(int, 150000000),
    # Espacio libre mínimo (MB) exigido en el directorio temporal antes de generar un ráster.
    ETL_RASTER_MIN_FREE_MB=(int, 200),
    # Directorio persistente de modelos guardados. Vacío = carpeta oculta ".geoetl_models" dentro del directorio del gestor de ficheros.
    # Si se cambia, debe ser escribible por el usuario con el que corre Celery (www-data en la imagen oficial).
    ETL_MODELS_DIR=(str, ''),
    # Versiones que se conservan de cada modelo guardado (las más antiguas se borran). 0 = todas.
    ETL_MODELS_KEEP_VERSIONS=(int, 10),
    # Clave con la que se firman los modelos. Vacío = se deriva de la SECRET_KEY de Django.
    ETL_MODELS_SIGNING_KEY=(str, ''),
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
ETL_ASSISTANT_ENABLED = env_plugin_geoetl('ETL_ASSISTANT_ENABLED')
ETL_ASSISTANT_TRACE = env_plugin_geoetl('ETL_ASSISTANT_TRACE')

# Nodos predictivos / ráster
ETL_RASTER_MAX_PIXELS = env_plugin_geoetl('ETL_RASTER_MAX_PIXELS')
ETL_RASTER_MAX_TRAIN_ROWS = env_plugin_geoetl('ETL_RASTER_MAX_TRAIN_ROWS')
ETL_RASTER_N_JOBS = env_plugin_geoetl('ETL_RASTER_N_JOBS')
ETL_RASTER_POLYGONIZE_STRIP_PIXELS = env_plugin_geoetl('ETL_RASTER_POLYGONIZE_STRIP_PIXELS')
ETL_RASTER_SIEVE_MAX_PIXELS = env_plugin_geoetl('ETL_RASTER_SIEVE_MAX_PIXELS')
ETL_RASTER_MIN_FREE_MB = env_plugin_geoetl('ETL_RASTER_MIN_FREE_MB')
ETL_MODELS_DIR = env_plugin_geoetl('ETL_MODELS_DIR')
ETL_MODELS_KEEP_VERSIONS = env_plugin_geoetl('ETL_MODELS_KEEP_VERSIONS')
ETL_MODELS_SIGNING_KEY = env_plugin_geoetl('ETL_MODELS_SIGNING_KEY')
GEOETL_LLM_MODEL = env_plugin_geoetl('GEOETL_LLM_MODEL')

LOGGER.info("ETL_DB_HOST= %s",GEOETL_DB['host'])
LOGGER.info("ETL_DB_PORT= %s",GEOETL_DB['port'])
LOGGER.info("ETL_DB_NAME= %s",GEOETL_DB['database'])
LOGGER.info("ETL_DB_USER= %s",GEOETL_DB['user'])