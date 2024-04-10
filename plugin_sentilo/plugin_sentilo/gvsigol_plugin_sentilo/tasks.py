from gvsigol.celery import app as celery_app
from gvsigol_plugin_sentilo.services.sentilo import fetch_sentilo_api

@celery_app.task(bind=True)
def fetch_sentilo_api_task(_, url, identity_key, db_table, sensors_string ):
    sensors = sensors_string.split(",")
    fetch_sentilo_api(url, identity_key, db_table, sensors)