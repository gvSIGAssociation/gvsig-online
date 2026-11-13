"""
API JSON del gestor de ficheros (/gvsigonline/filemanager/api/...), para la interfaz nueva.

Es aditiva: las vistas clásicas no cambian. Sesión de Django y CSRF como el resto de la
aplicación; solo usuarios staff. Permisos por ruta con can_browse_path / can_manage_path (los
mismos que las vistas clásicas) y, además, las carpetas del primer nivel (las de cada rol) solo
las puede cambiar un superusuario.

Respuestas: {"ok": true, ...} o {"ok": false, "error": "..."} con el estado HTTP adecuado. Las
operaciones sobre varios elementos devuelven un resultado por elemento en "results".
"""
import json
import logging
import os
import time
from functools import wraps

from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header
from django.utils import translation
from django.utils.translation import gettext as _

from . import fsops, uploads
from .core import Filemanager, UnzipError
from .fsops import OperationError
from .views import can_browse_path, can_manage_path, datastore_using_path, raster_datastore_paths

logger = logging.getLogger("gvsigol")

ON_CONFLICT = ('error', 'rename')
# Como mucho una purga de la papelera por proceso cada hora
_PURGE_INTERVAL = 3600
_last_purge = [0.0]


# --- Infraestructura ----------------------------------------------------------------------------

def _error(message, status, **extra):
    return JsonResponse(dict({'ok': False, 'error': str(message)}, **extra), status=status)


FORM_CONTENT_TYPES = ('application/x-www-form-urlencoded', 'multipart/form-data')


def _data(request):
    """
    Parámetros de la petición: JSON si lo es, los del formulario si lo es y, si no (un trozo de
    subida en el cuerpo), los de la URL.
    """
    if request.method == 'GET':
        return request.GET
    if request.content_type in FORM_CONTENT_TYPES:
        return request.POST
    if request.content_type != 'application/json':
        return request.GET
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body or b'{}')
        except ValueError:
            raise OperationError(_('Invalid request'), 400)
        if not isinstance(data, dict):
            raise OperationError(_('Invalid request'), 400)
        return data
    return request.POST


def _list_param(data, name):
    if hasattr(data, 'getlist'):
        values = data.getlist(name) or data.getlist(name + '[]')
    else:
        values = data.get(name) or []
        if isinstance(values, str):
            values = [values]
    if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
        raise OperationError(_('Invalid request'), 400)
    return [fsops.normalize(v) for v in values]


def _str_param(data, name, default=''):
    value = data.get(name, default)
    if not isinstance(value, str):
        raise OperationError(_('Invalid request'), 400)
    return value


def api_view(methods):
    """Sesión de staff, método permitido y errores en JSON."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return _error(_('Authentication required'), 401)
            if not request.user.is_staff:
                return _error(_('You do not have permission for this location'), 403)
            if request.method not in methods:
                return _error(_('Method not allowed'), 405)
            try:
                return view(request, _data(request), *args, **kwargs)
            except OperationError as e:
                return _error(e.message, e.status, **e.extra)
            except RequestDataTooBig:
                return _error(_('Invalid request'), 413)
            except Exception:
                logger.exception("Filemanager API error in %s", view.__name__)
                return _error(_('Unexpected error'), 500)
        return wrapper
    return decorator


def _run_each(items, operation):
    """Aplica la operación a cada elemento y recoge un resultado por elemento."""
    results = []
    for item in items:
        try:
            results.append(dict({'path': item, 'ok': True}, **(operation(item) or {})))
        except OperationError as e:
            results.append(dict({'path': item, 'ok': False, 'error': e.message, 'status': e.status}, **e.extra))
        except Exception:
            logger.exception("Filemanager API error with %s", item)
            results.append({'path': item, 'ok': False, 'error': _('Unexpected error'), 'status': 500})
    return JsonResponse({'ok': all(r['ok'] for r in results), 'results': results})


# --- Permisos -----------------------------------------------------------------------------------

def _require(condition):
    if not condition:
        raise OperationError(_('You do not have permission for this location'), 403)


def can_write_into(request, dir_rel):
    """Puede crear o traer cosas a esta carpeta. La raíz, solo el superusuario."""
    return bool(can_manage_path(request, dir_rel))


def can_modify(request, rel):
    """Puede borrar, renombrar o mover este elemento. Las carpetas de rol, solo el superusuario."""
    if not rel or not can_manage_path(request, rel):
        return False
    return request.user.is_superuser or '/' in rel


def _check_not_in_use(path, datastores=None):
    for member in fsops.group(path):
        name = datastore_using_path(member, datastores)
        if name:
            raise OperationError(_('In use by the datastore %(name)s') % {'name': name}, 409)


def _maybe_purge_trash():
    now = time.time()
    if now - _last_purge[0] < _PURGE_INTERVAL:
        return
    _last_purge[0] = now
    try:
        purged = fsops.purge_expired()
        stale = uploads.purge_stale()
        if purged or stale:
            logger.info("Filemanager: purged %d expired trash entries and %d stale uploads", purged, stale)
    except Exception:
        logger.exception("Filemanager: error purging the trash")


# --- Listado ------------------------------------------------------------------------------------

def _breadcrumbs(rel):
    crumbs = [{'label': 'data', 'path': ''}]
    path = ''
    for part in [p for p in rel.split('/') if p]:
        path = part if not path else path + '/' + part
        crumbs.append({'label': part, 'path': path})
    return crumbs


@api_view(['GET'])
def list_directory(request, data):
    rel = fsops.normalize(_str_param(data, 'path'))
    path = fsops.to_abs(rel)
    _require(can_browse_path(request, rel))
    if not os.path.isdir(path):
        raise OperationError(_('The item does not exist'), 404)
    dirs_only = data.get('dirs_only') in ('1', 'true')
    items = fsops.list_dir(rel, dirs_only=dirs_only)
    if rel == '' and not request.user.is_superuser:
        # Como el listado clásico: en la raíz, solo las carpetas de sus roles
        items = [i for i in items if i['type'] == 'directory' and can_manage_path(request, i['path'])]
    datastores = raster_datastore_paths()
    for item in items:
        item['can_modify'] = can_modify(request, item['path'])
        item['in_use_by'] = datastore_using_path(fsops.to_abs(item['path']), datastores)
    return JsonResponse({
        'ok': True,
        'path': rel,
        'breadcrumbs': _breadcrumbs(rel),
        'can_write': can_write_into(request, rel),
        'items': items,
    })


# --- Operaciones --------------------------------------------------------------------------------

@api_view(['POST'])
def make_directory(request, data):
    parent = fsops.normalize(_str_param(data, 'path'))
    _require(can_write_into(request, parent))
    return JsonResponse({'ok': True, 'item': fsops.make_dir(parent, _str_param(data, 'name'))}, status=201)


@api_view(['POST'])
def rename(request, data):
    rel = fsops.normalize(_str_param(data, 'path'))
    _require(can_modify(request, rel))
    _check_not_in_use(fsops.existing(rel))
    return JsonResponse({'ok': True, 'item': fsops.rename(rel, _str_param(data, 'name'))})


def _conflict_policy(data, default):
    policy = _str_param(data, 'on_conflict', default)
    if policy not in ON_CONFLICT:
        raise OperationError(_('Invalid request'), 400)
    return policy


@api_view(['POST'])
def move(request, data):
    paths = _list_param(data, 'paths')
    destination = fsops.normalize(_str_param(data, 'destination'))
    _require(can_write_into(request, destination))
    policy = _conflict_policy(data, 'error')
    datastores = raster_datastore_paths()

    def _move(rel):
        _require(can_modify(request, rel))
        _check_not_in_use(fsops.existing(rel), datastores)
        return {'item': fsops.move(rel, destination, policy)}
    return _run_each(paths, _move)


@api_view(['POST'])
def copy(request, data):
    paths = _list_param(data, 'paths')
    destination = fsops.normalize(_str_param(data, 'destination'))
    _require(can_write_into(request, destination))
    policy = _conflict_policy(data, 'rename')

    def _copy(rel):
        _require(rel and can_manage_path(request, rel))
        return {'item': fsops.copy(rel, destination, policy)}
    return _run_each(paths, _copy)


@api_view(['POST'])
def delete(request, data):
    """Envía a la papelera. Para borrar del todo: vaciarla o trash/delete/."""
    paths = _list_param(data, 'paths')
    datastores = raster_datastore_paths()
    _maybe_purge_trash()

    def _delete(rel):
        _require(can_modify(request, rel))
        _check_not_in_use(fsops.existing(rel), datastores)
        return {'trash': fsops.to_trash(rel, request.user.username)}
    return _run_each(paths, _delete)


@api_view(['POST'])
def unzip(request, data):
    rel = fsops.normalize(_str_param(data, 'path'))
    _require(rel and can_manage_path(request, rel))
    parent = rel.rsplit('/', 1)[0] if '/' in rel else ''
    _require(can_write_into(request, parent))
    zip_path = fsops.existing(rel)
    if data.get('background') in (True, 'true', '1', 1):
        # En segundo plano con Celery: el progreso se consulta en task/<id>/
        from .tasks import unzip_task
        result = unzip_task.apply_async(kwargs={'zip_rel': rel, 'language': translation.get_language()})
        return JsonResponse({'ok': True, 'task_id': result.id}, status=202)
    try:
        folder = Filemanager().unzip(zip_path)
    except UnzipError as e:
        raise OperationError(str(e), 400)
    return JsonResponse({'ok': True, 'item': fsops.entry(folder)}, status=201)


@api_view(['GET'])
def task_status(request, data, task_id):
    """Estado de una tarea en segundo plano del gestor (de momento, descomprimir)."""
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    state = result.state
    response = {'ok': True, 'task_id': task_id, 'state': state, 'progress': 0}
    if state == 'PROCESSING' and isinstance(result.info, dict):
        response['progress'] = result.info.get('progress', 0)
    elif state == 'SUCCESS':
        value = result.result if isinstance(result.result, dict) else {}
        response.update({'progress': 100, 'result': value})
    elif state in ('FAILURE', 'REVOKED'):
        response['result'] = {'ok': False, 'error': _('Unexpected error')}
    return JsonResponse(response)


# --- Subida por trozos (ver uploads.py) ---------------------------------------------------------

@api_view(['POST'])
def upload_init(request, data):
    """{path, name, size, on_conflict}: crea la subida, o la omite si on_conflict es skip."""
    dest = fsops.normalize(_str_param(data, 'path'))
    _require(can_write_into(request, dest))
    size = data.get('size')
    policy = _str_param(data, 'on_conflict', 'error')
    _maybe_purge_trash()
    status = uploads.init(dest, _str_param(data, 'name'), size, request.user.username, policy)
    if policy == 'replace' and not status.get('skipped'):
        # Avisa ya de que no se podrá reemplazar algo que usa un almacén de datos
        target, decision = uploads.resolve(dest, status['name'], policy)
        if decision == 'replace':
            try:
                _check_not_in_use(target)
            except OperationError:
                uploads.cancel(status['id'], request.user.username)
                raise
    return JsonResponse(dict({'ok': True}, **status), status=201)


@api_view(['GET'])
def upload_status(request, data, upload_id):
    return JsonResponse(dict({'ok': True}, **uploads.get(upload_id, request.user.username)))


@api_view(['POST'])
def upload_chunk(request, data, upload_id):
    """Cuerpo: los bytes del trozo. ?offset=bytes ya recibidos (409 con received si no cuadra)."""
    status = uploads.append(upload_id, request.user.username, data.get('offset'), request.body)
    return JsonResponse(dict({'ok': True}, **status))


@api_view(['POST'])
def upload_complete(request, data, upload_id):
    status = uploads.get(upload_id, request.user.username)
    # Los permisos pueden haber cambiado mientras se subía
    _require(can_write_into(request, status['path']))
    item = uploads.complete(upload_id, request.user.username, check_replace=_check_not_in_use)
    if item.get('skipped'):
        return JsonResponse({'ok': True, 'skipped': True})
    return JsonResponse({'ok': True, 'item': item}, status=201)


@api_view(['POST'])
def upload_cancel(request, data, upload_id):
    uploads.cancel(upload_id, request.user.username)
    return JsonResponse({'ok': True})


@api_view(['GET'])
def download(request, data):
    """Descarga en un zip los ficheros y carpetas indicados (paths, repetido)."""
    paths = _list_param(data, 'paths')
    for rel in paths:
        _require(rel and can_manage_path(request, rel))
    entries = fsops.zip_entries(paths)
    if data.get('check') in ('1', 'true'):
        # Comprobación previa de la interfaz: permisos y tamaño, sin generar el zip
        return JsonResponse({'ok': True, 'entries': len(entries)})
    name = (paths[0].rsplit('/', 1)[-1] if len(paths) == 1 else 'descarga') + '.zip'
    response = StreamingHttpResponse(fsops.stream_zip(entries), content_type='application/zip')
    response['Content-Disposition'] = content_disposition_header(True, name)
    # Que el proxy no lo acumule: se va enviando según se genera
    response['X-Accel-Buffering'] = 'no'
    return response


# --- Papelera -----------------------------------------------------------------------------------

def _visible_trash_item(request, item):
    """Se ve en la papelera lo que se podría gestionar en su ubicación original."""
    return request.user.is_superuser or bool(can_manage_path(request, item['original_path']))


@api_view(['GET'])
def trash_list(request, data):
    _maybe_purge_trash()
    items = [i for i in fsops.trash_items() if _visible_trash_item(request, i)]
    return JsonResponse({'ok': True, 'retention_days': fsops.retention_days(), 'items': items})


def _trash_operation(request, data, operation):
    ids = _list_param(data, 'ids')

    def _run(trash_id):
        item = fsops.trash_get(trash_id)
        _require(_visible_trash_item(request, item))
        return operation(trash_id, item)
    return _run_each(ids, _run)


@api_view(['POST'])
def trash_restore(request, data):
    def _restore(trash_id, item):
        _require(can_write_into(request, item['original_dir']))
        return {'item': fsops.restore(trash_id)}
    return _trash_operation(request, data, _restore)


@api_view(['POST'])
def trash_delete(request, data):
    def _delete(trash_id, item):
        fsops.delete_forever(trash_id)
        return {}
    return _trash_operation(request, data, _delete)


@api_view(['POST'])
def trash_empty(request, data):
    deleted, errors = 0, 0
    for item in fsops.trash_items():
        if not _visible_trash_item(request, item):
            continue
        try:
            fsops.delete_forever(item['id'])
            deleted += 1
        except Exception:
            logger.exception("Filemanager: could not empty trash entry %s", item['id'])
            errors += 1
    return JsonResponse({'ok': errors == 0, 'deleted': deleted, 'errors': errors})
