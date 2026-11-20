"""
Registro de las tareas en segundo plano del gestor (de momento, descomprimir) para el visor de
procesos: así se ven aunque se haya cerrado la página que las lanzó.

Cada tarea es un JSON en FILEMANAGER_DIRECTORY/.gvsigol_uploads/tasks/<task_id>.json con el
usuario, el tipo y el fichero. El estado se consulta a Celery. Se borran a las STALE_HOURS horas.
"""
import datetime
import json
import logging
import os
import re

from . import uploads

logger = logging.getLogger("gvsigol")

STALE_HOURS = 24
_TASK_ID_RE = re.compile(r'^[0-9a-f-]{32,36}$')


def tasks_root():
    return os.path.join(uploads.uploads_root(), 'tasks')


def record(task_id, username, kind, name, path):
    if not _TASK_ID_RE.match(task_id or ''):
        return
    os.makedirs(tasks_root(), exist_ok=True)
    data = {
        'task_id': task_id, 'username': username, 'kind': kind, 'name': name, 'path': path,
        'started': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(os.path.join(tasks_root(), task_id + '.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def owner(task_id):
    """Usuario que lanzó la tarea, o None si no está registrada."""
    if not _TASK_ID_RE.match(task_id or ''):
        return None
    try:
        with open(os.path.join(tasks_root(), task_id + '.json'), encoding='utf-8') as f:
            return json.load(f).get('username')
    except Exception:
        return None


def state(task_id):
    """(estado, progreso 0-100, resultado o None) según Celery."""
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    st = result.state
    if st == 'PROCESSING' and isinstance(result.info, dict):
        return st, result.info.get('progress', 0), None
    if st == 'SUCCESS':
        return st, 100, result.result if isinstance(result.result, dict) else {}
    if st in ('FAILURE', 'REVOKED'):
        return st, 0, {'ok': False}
    return st, 0, None


def list_tasks(username):
    base = tasks_root()
    if not os.path.isdir(base):
        return []
    items = []
    for name in os.listdir(base):
        if not name.endswith('.json'):
            continue
        try:
            with open(os.path.join(base, name), encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        if data.get('username') != username:
            continue
        try:
            st, progress, result = state(data['task_id'])
        except Exception:
            logger.exception("Filemanager: could not read task %s", data.get('task_id'))
            st, progress, result = 'UNKNOWN', 0, None
        data.update({'state': st, 'progress': progress, 'result': result})
        items.append(data)
    return sorted(items, key=lambda i: i['started'], reverse=True)


def purge_stale(hours=STALE_HOURS):
    base = tasks_root()
    if not os.path.isdir(base):
        return 0
    limit = datetime.datetime.now().timestamp() - hours * 3600
    purged = 0
    for name in os.listdir(base):
        path = os.path.join(base, name)
        if name.endswith('.json') and os.path.getmtime(path) < limit:
            try:
                os.remove(path)
                purged += 1
            except OSError:
                logger.exception("Filemanager: could not purge task record %s", path)
    return purged


FINISHED_STATES = ('SUCCESS', 'FAILURE', 'REVOKED')


def clear_finished(username):
    """Borra los registros de las tareas terminadas del usuario (visor de procesos). Devuelve cuántos."""
    base = tasks_root()
    if not os.path.isdir(base):
        return 0
    cleared = 0
    for name in os.listdir(base):
        path = os.path.join(base, name)
        if not name.endswith('.json'):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            if data.get('username') != username or state(data['task_id'])[0] not in FINISHED_STATES:
                continue
            os.remove(path)
            cleared += 1
        except Exception:
            logger.exception("Filemanager: could not clear task record %s", path)
    return cleared
