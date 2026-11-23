"""Parada a petición del usuario de una ejecución ETL en marcha.

El botón Detener pone el ETLstatus en STOPPING y cancela en PostgreSQL las
consultas de esa ejecución. El motor lo comprueba entre nodos (y los nodos
largos entre lotes con check()) y termina dejando el estado en CANCELLED.

Las conexiones de la ejecución se reconocen por su application_name: begin()
fija PGAPPNAME en el proceso, y libpq lo aplica a toda conexión que se abra
después sin tocar cada psycopg2.connect de los nodos.
"""
import os
import threading
import time

import psycopg2

from .settings import GEOETL_DB

RUNNING = 'Running'
STOPPING = 'Stopping'
CANCELLED = 'Cancelled'
CANCELLED_MESSAGE = 'Process stopped by user'

_APP_PREFIX = 'geoetl-run-'
_CHECK_INTERVAL = 2.0

_local = threading.local()


class EtlCancelled(Exception):
    pass


def app_name(status_id):
    return '%s%s' % (_APP_PREFIX, status_id)


def current_app_name():
    status_id = getattr(_local, 'status_id', None)
    return app_name(status_id) if status_id is not None else None


def begin(status_id):
    if getattr(_local, 'status_id', None) is None:
        _local.saved_appname = os.environ.get('PGAPPNAME')
    _local.status_id = status_id
    _local.last_check = 0.0
    os.environ['PGAPPNAME'] = app_name(status_id)


def end():
    if getattr(_local, 'status_id', None) is None:
        return
    saved = getattr(_local, 'saved_appname', None)
    if saved is None:
        os.environ.pop('PGAPPNAME', None)
    else:
        os.environ['PGAPPNAME'] = saved
    _local.status_id = None


def stop_requested(status_id):
    from .models import ETLstatus
    return ETLstatus.objects.filter(pk=status_id, status=STOPPING).exists()


def check(force=False):
    """Lanza EtlCancelled si han pedido parar la ejecución en curso.

    Sin force consulta la BD como mucho cada pocos segundos, para poder
    llamarla dentro de bucles.
    """
    status_id = getattr(_local, 'status_id', None)
    if status_id is None:
        return
    now = time.monotonic()
    if not force and now - _local.last_check < _CHECK_INTERVAL:
        return
    _local.last_check = now
    if stop_requested(status_id):
        raise EtlCancelled(CANCELLED_MESSAGE)


def _connect():
    return psycopg2.connect(
        user=GEOETL_DB['user'], password=GEOETL_DB['password'],
        host=GEOETL_DB['host'], port=GEOETL_DB['port'],
        database=GEOETL_DB['database'],
    )


def cancel_queries(status_id):
    """Cancela las consultas en curso de la ejecución. Devuelve cuántas."""
    conn = _connect()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FILTER (WHERE pg_cancel_backend(pid)) FROM pg_stat_activity "
                "WHERE application_name = %s AND state = 'active' AND pid <> pg_backend_pid()",
                [app_name(status_id)],
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def request_stop(status_model):
    """Marca la ejecución para parar y corta su consulta actual.

    Devuelve False si no estaba en marcha.
    """
    from .models import ETLstatus
    updated = ETLstatus.objects.filter(pk=status_model.pk, status=RUNNING).update(status=STOPPING)
    if not updated and not ETLstatus.objects.filter(pk=status_model.pk, status=STOPPING).exists():
        return False
    cancel_queries(status_model.pk)
    return True
