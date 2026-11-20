from gvsigol.celery import app as celery_app
from gvsigol_plugin_sentilo.services.sentilo import fetch_sentilo_api
from gvsigol_plugin_sentilo.services.cleanup import clean_all_configured_tables
import logging

LOGGER = logging.getLogger('gvsigol')

@celery_app.task(bind=True)
def fetch_sentilo_api_task(_, url, identity_key, db_table, sensors_string ):
    sensors = sensors_string.split(",")
    fetch_sentilo_api(url, identity_key, db_table, sensors)


@celery_app.task(bind=True)
def sentilo_daily_cleanup_task(_):
    LOGGER.info("[Sentilo Cleanup] Starting daily cleanup task")
    clean_all_configured_tables()
    LOGGER.info("[Sentilo Cleanup] Finished daily cleanup task")