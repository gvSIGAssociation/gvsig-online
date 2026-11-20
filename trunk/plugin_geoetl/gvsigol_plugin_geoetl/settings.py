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
    ETL_ASSISTANT_ENABLED=(bool, False),
    # Traza de cada turno del asistente en el log (herramientas, tiempos, resultado). Sin textos del usuario.
    ETL_ASSISTANT_TRACE=(bool, False),
    # Vacío: se usa el modelo por defecto de GeoCopilot.
    GEOETL_LLM_MODEL=(str, ''),
    # Motor del agente del asistente: legacy (AgentExecutor, el de siempre) o langgraph.
    ETL_ASSISTANT_ENGINE=(str, 'legacy'),
    # Tiempo máximo de un turno del asistente con el motor langgraph (segundos). 0 = sin límite.
    ETL_ASSISTANT_MAX_SECONDS=(int, 120),
    # Dónde se ejecuta el turno: inline (en el proceso web, como siempre) o celery (en un worker; necesita
    # GEOCOPILOT_SHARED_CACHE=True y un worker escuchando ETL_ASSISTANT_CELERY_QUEUE).
    ETL_ASSISTANT_EXECUTION=(str, 'inline'),
    # Cola de Celery del asistente. Por defecto la de GeoCopilot.
    ETL_ASSISTANT_CELERY_QUEUE=(str, 'geocopilot'),
    # Pasos en vivo y Detener real en el panel (endpoint SSE /etl/etl_assistant/stream/).
    ETL_ASSISTANT_STREAMING=(bool, False),
    # Texto de la respuesta en vivo. Solo con ETL_ASSISTANT_STREAMING=True y ETL_ASSISTANT_ENGINE=langgraph.
    ETL_ASSISTANT_TOKEN_STREAMING=(bool, False),
    # Usabilidad: problemas del flujo con botones Configurar / Arreglar en el panel.
    ETL_ASSISTANT_ACTIONS=(bool, True),
    # Usabilidad: el asistente pregunta con opciones para elegir con un clic (herramienta ask_user).
    ETL_ASSISTANT_QUESTIONS=(bool, True),
    # Usabilidad: las suposiciones sobre un parámetro se pueden cambiar con un clic en el panel.
    ETL_ASSISTANT_ALTERNATIVES=(bool, True),
    # Usabilidad: completar desde el chat los parámetros de una lista cerrada. Necesita ETL_ASSISTANT_ACTIONS=True.
    ETL_ASSISTANT_PARAM_PICKER=(bool, True),
    # Usabilidad: sugerencias de siguiente paso (por reglas) y arranque guiado con el canvas vacío.
    ETL_ASSISTANT_NEXT_STEPS=(bool, True),
    # El asistente lee las columnas de las entradas y pregunta por los campos con sus valores reales.
    ETL_ASSISTANT_COLUMNS=(bool, True),
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
ETL_ASSISTANT_ENGINE = env_plugin_geoetl('ETL_ASSISTANT_ENGINE')
ETL_ASSISTANT_MAX_SECONDS = env_plugin_geoetl('ETL_ASSISTANT_MAX_SECONDS')
ETL_ASSISTANT_EXECUTION = env_plugin_geoetl('ETL_ASSISTANT_EXECUTION')
ETL_ASSISTANT_CELERY_QUEUE = env_plugin_geoetl('ETL_ASSISTANT_CELERY_QUEUE')
ETL_ASSISTANT_STREAMING = env_plugin_geoetl('ETL_ASSISTANT_STREAMING')
ETL_ASSISTANT_TOKEN_STREAMING = env_plugin_geoetl('ETL_ASSISTANT_TOKEN_STREAMING')
ETL_ASSISTANT_ACTIONS = env_plugin_geoetl('ETL_ASSISTANT_ACTIONS')
ETL_ASSISTANT_QUESTIONS = env_plugin_geoetl('ETL_ASSISTANT_QUESTIONS')
ETL_ASSISTANT_ALTERNATIVES = env_plugin_geoetl('ETL_ASSISTANT_ALTERNATIVES')
ETL_ASSISTANT_PARAM_PICKER = env_plugin_geoetl('ETL_ASSISTANT_PARAM_PICKER')
ETL_ASSISTANT_NEXT_STEPS = env_plugin_geoetl('ETL_ASSISTANT_NEXT_STEPS')
ETL_ASSISTANT_COLUMNS = env_plugin_geoetl('ETL_ASSISTANT_COLUMNS')

LOGGER.info("ETL_DB_HOST= %s",GEOETL_DB['host'])
LOGGER.info("ETL_DB_PORT= %s",GEOETL_DB['port'])
LOGGER.info("ETL_DB_NAME= %s",GEOETL_DB['database'])
LOGGER.info("ETL_DB_USER= %s",GEOETL_DB['user'])