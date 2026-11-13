"""
Subida de ficheros por trozos, reanudable, para la API (la subida clásica no cambia).

1. init: destino, nombre y tamaño. Comprueba permisos (en api.py), tamaño máximo, espacio libre y
   si el nombre ya existe (según on_conflict). Devuelve un id y el tamaño de trozo.
2. append: añade un trozo en la posición indicada, que debe ser lo ya recibido. Si no coincide
   responde 409 con lo recibido, para que el navegador reanude desde ahí.
3. complete: con todo recibido, lo mueve a su sitio (mismo disco: instantáneo) y envía las
   señales filemanager_pre_upload / filemanager_post_upload como la subida clásica.

Lo pendiente vive en FILEMANAGER_DIRECTORY/.gvsigol_uploads/<id>/ (meta.json y data.part).
Lo abandonado se borra pasadas STALE_HOURS horas sin recibir nada (purge_stale).

El nombre puede llevar subcarpetas ('fotos/2024/a.jpg') para subir carpetas enteras: se crean
al completar.
"""
import datetime
import fcntl
import json
import logging
import os
import re
import shutil
import uuid

from django.conf import settings
from django.utils.translation import gettext as _

from . import fsops, signals
from .core import Filemanager, UPLOADS_DIRNAME, _rmtree
from .fsops import OperationError
from .utils import sizeof_fmt

logger = logging.getLogger("gvsigol")

POLICIES = ('error', 'rename', 'replace', 'skip')
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
DEFAULT_UPLOAD_MAX_SIZE = 50 * 1024 ** 3
STALE_HOURS = 24
_ID_RE = re.compile(r'^[0-9a-f]{32}$')


def uploads_root():
    return os.path.join(fsops.root(), UPLOADS_DIRNAME)


def chunk_size():
    """8 MB, o menos si DATA_UPLOAD_MAX_MEMORY_SIZE no deja (el trozo va en el cuerpo)."""
    limit = getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', None)
    if limit:
        return max(64 * 1024, min(DEFAULT_CHUNK_SIZE, limit - 64 * 1024))
    return DEFAULT_CHUNK_SIZE


def max_size():
    return getattr(settings, 'FILEMANAGER_UPLOAD_MAX_SIZE', DEFAULT_UPLOAD_MAX_SIZE)


# --- Destino ------------------------------------------------------------------------------------

def clean_relative_name(name):
    """'mis fotos/a b.jpg' -> 'mis_fotos/a_b.jpg'. Cada parte se limpia como un nombre."""
    parts = [p for p in (name or '').replace('\\', '/').split('/') if p.strip()]
    if not parts:
        raise OperationError(_('Invalid name'), 400)
    return '/'.join(fsops.clean_name(p) for p in parts)


def _target(dest_rel, name):
    """Ruta absoluta de destino; comprueba que las subcarpetas no choquen con ficheros."""
    dest = fsops.existing_dir(dest_rel)
    target = fsops.to_abs(fsops.to_rel(os.path.join(dest, *name.split('/'))))
    current = dest
    for part in name.split('/')[:-1]:
        current = os.path.join(current, part)
        if os.path.lexists(current) and not os.path.isdir(current):
            raise OperationError(_('An item with that name already exists'), 409, conflict=True)
    return target


def resolve(dest_rel, name, policy):
    """
    (ruta final, decisión) según la política: 'new' si no existía, 'replace', 'rename' (ya con el
    nombre libre) o 'skip' (ruta None). Con 'error' y el nombre ocupado: 409 con conflict=True.
    """
    target = _target(dest_rel, name)
    if not os.path.lexists(target):
        return target, 'new'
    if os.path.isdir(target):
        # Nunca se reemplaza una carpeta por un fichero
        if policy == 'skip':
            return None, 'skip'
        if policy != 'rename':
            raise OperationError(_('An item with that name already exists'), 409, conflict=True)
    if policy == 'skip':
        return None, 'skip'
    if policy == 'replace' and not os.path.isdir(target):
        return target, 'replace'
    if policy == 'rename':
        stem, ext = os.path.splitext(os.path.basename(target))
        if not stem:
            stem, ext = os.path.basename(target), ''
        i = 1
        while True:
            candidate = os.path.join(os.path.dirname(target), '%s_%d%s' % (stem, i, ext))
            if not os.path.lexists(candidate):
                return candidate, 'rename'
            i += 1
    raise OperationError(_('An item with that name already exists'), 409, conflict=True)


# --- Estado -------------------------------------------------------------------------------------

def _entry_dir(upload_id):
    if not _ID_RE.match(upload_id or ''):
        raise OperationError(_('The upload does not exist or has expired'), 404)
    path = os.path.join(uploads_root(), upload_id)
    if not os.path.isfile(os.path.join(path, 'meta.json')):
        raise OperationError(_('The upload does not exist or has expired'), 404)
    return path


def _load(upload_id, username):
    entry_dir = _entry_dir(upload_id)
    with open(os.path.join(entry_dir, 'meta.json'), encoding='utf-8') as f:
        meta = json.load(f)
    if meta.get('username') != username:
        raise OperationError(_('You do not have permission for this location'), 403)
    return entry_dir, meta


def _status(entry_dir, meta):
    part = os.path.join(entry_dir, 'data.part')
    return {
        'id': meta['id'],
        'path': meta['path'],
        'name': meta['name'],
        'size': meta['size'],
        'received': os.path.getsize(part) if os.path.exists(part) else 0,
        'chunk_size': chunk_size(),
        'on_conflict': meta['on_conflict'],
    }


def get(upload_id, username):
    """Estado de una subida (para reanudarla), con sus datos de destino."""
    entry_dir, meta = _load(upload_id, username)
    return _status(entry_dir, meta)


# --- Operaciones --------------------------------------------------------------------------------

def init(dest_rel, name, size, username, policy='error'):
    if policy not in POLICIES:
        raise OperationError(_('Invalid request'), 400)
    try:
        size = int(size)
    except (TypeError, ValueError):
        raise OperationError(_('Invalid request'), 400)
    if size < 0:
        raise OperationError(_('Invalid request'), 400)
    limit = max_size()
    if limit and size > limit:
        raise OperationError(_('The file exceeds the maximum upload size (%(limit)s)') % {
            'limit': sizeof_fmt(limit)}, 413)
    dest_rel = fsops.normalize(dest_rel)
    name = clean_relative_name(name)
    target, decision = resolve(dest_rel, name, policy)
    if decision == 'skip':
        return {'skipped': True, 'name': name, 'path': dest_rel}
    if shutil.disk_usage(fsops.root()).free < size:
        raise OperationError(_('Not enough free disk space'), 507)
    upload_id = uuid.uuid4().hex
    entry_dir = os.path.join(uploads_root(), upload_id)
    os.makedirs(entry_dir)
    meta = {
        'id': upload_id,
        'username': username,
        'path': dest_rel,
        'name': name,
        'size': size,
        'on_conflict': policy,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    open(os.path.join(entry_dir, 'data.part'), 'wb').close()
    with open(os.path.join(entry_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False)
    status = _status(entry_dir, meta)
    status['final_name'] = os.path.basename(target)
    return status


def append(upload_id, username, offset, data):
    """Añade `data` en `offset`, que debe ser lo ya recibido. Devuelve el estado."""
    entry_dir, meta = _load(upload_id, username)
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        raise OperationError(_('Invalid request'), 400)
    part = os.path.join(entry_dir, 'data.part')
    with open(part, 'ab') as f:
        # Dos trozos a la vez de la misma subida no pueden mezclarse
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            received = os.fstat(f.fileno()).st_size
            if offset != received:
                raise OperationError(_('The received data does not match the expected position'), 409,
                                     received=received)
            if received + len(data) > meta['size']:
                raise OperationError(_('Invalid request'), 400, received=received)
            f.write(data)
            f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return _status(entry_dir, meta)


def complete(upload_id, username, check_replace=None):
    """
    Coloca el fichero en su destino. `check_replace(ruta)` se llama antes de reemplazar uno
    existente (p. ej. para impedirlo si lo usa un almacén de datos). Devuelve la ficha del fichero,
    o {'skipped': True} si la política era omitir y el nombre ya estaba ocupado.
    """
    entry_dir, meta = _load(upload_id, username)
    status = _status(entry_dir, meta)
    if status['received'] != meta['size']:
        raise OperationError(_('The upload is not complete'), 409, received=status['received'])
    # Se resuelve de nuevo: el destino puede haber cambiado mientras se subía
    target, decision = resolve(meta['path'], meta['name'], meta['on_conflict'])
    if decision == 'skip':
        _rmtree(entry_dir)
        return {'skipped': True, 'name': meta['name'], 'path': meta['path']}
    if decision == 'replace' and check_replace:
        check_replace(target)
    fsops.mkdirs(os.path.dirname(target))
    filename = os.path.basename(target)
    dir_rel = fsops.to_rel(os.path.dirname(target))
    filepath = fsops.to_rel(target)
    signals.filemanager_pre_upload.send(sender=Filemanager, filename=filename, path=dir_rel, filepath=filepath)
    os.replace(os.path.join(entry_dir, 'data.part'), target)
    _apply_upload_permissions(target)
    signals.filemanager_post_upload.send(sender=Filemanager, filename=filename, path=dir_rel, filepath=filepath)
    _rmtree(entry_dir)
    item = fsops.entry(target)
    item['replaced'] = decision == 'replace'
    return item


def _apply_upload_permissions(path):
    """Los mismos permisos que pone la subida clásica: los de FILEMANAGER_STORAGE (FILE_DEFAULT_PERMISSIONS)."""
    mode = getattr(fsops.FILEMANAGER_STORAGE, 'file_permissions_mode', None)
    if mode is not None:
        try:
            os.chmod(path, mode)
        except OSError:
            logger.warning("Filemanager: could not set permissions on %s", path)


def cancel(upload_id, username):
    entry_dir, _meta = _load(upload_id, username)
    _rmtree(entry_dir)


def purge_stale(hours=STALE_HOURS):
    """Borra las subidas sin actividad desde hace más de `hours` horas. Devuelve cuántas."""
    base = uploads_root()
    if not os.path.isdir(base):
        return 0
    limit = datetime.datetime.now().timestamp() - hours * 3600
    purged = 0
    for upload_id in os.listdir(base):
        entry_dir = os.path.join(base, upload_id)
        if not _ID_RE.match(upload_id) or not os.path.isdir(entry_dir):
            continue
        part = os.path.join(entry_dir, 'data.part')
        last = os.path.getmtime(part if os.path.exists(part) else entry_dir)
        if last < limit:
            try:
                _rmtree(entry_dir)
                purged += 1
            except Exception:
                logger.exception("Filemanager: could not purge upload %s", entry_dir)
    return purged
