"""
Operaciones de ficheros del gestor para la API JSON: listar, crear carpeta, renombrar, mover,
copiar, papelera y descarga en zip.

No conoce la petición HTTP: los permisos se comprueban en api.py. Todas las rutas que recibe son
relativas a FILEMANAGER_DIRECTORY ('' es la raíz). Los .shp se tratan siempre junto a sus ficheros
asociados (.dbf, .shx, .prj...).

La papelera vive en FILEMANAGER_DIRECTORY/.gvsigol_trash (mismo disco: mover es instantáneo).
Cada elemento borrado ocupa una carpeta <id>/ con meta.json y los ficheros en items/. No usa la BD.
"""
import datetime
import json
import logging
import os
import re
import shutil
import uuid
import zipfile

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.utils.translation import gettext as _

from gvsigol.settings import FILEMANAGER_DIRECTORY, FILEMANAGER_STORAGE

from .core import RESERVED_NAMES, TRASH_DIRNAME, file_group, get_extension, _rmtree
from .utils import sizeof_fmt

logger = logging.getLogger("gvsigol")

DEFAULT_TRASH_RETENTION_DAYS = 30
DEFAULT_ZIP_DOWNLOAD_MAX_SIZE = 10 * 1024 ** 3
_TRASH_ID_RE = re.compile(r'^[0-9a-f]{32}$')


class OperationError(Exception):
    """Error con un mensaje para el usuario y el estado HTTP que le corresponde."""

    def __init__(self, message, status=400, **extra):
        super().__init__(message)
        self.message = str(message)
        self.status = status
        # Datos para la interfaz, p. ej. {'conflict': True} o {'received': 1234}
        self.extra = extra


# --- Rutas --------------------------------------------------------------------------------------

def root():
    return os.path.abspath(FILEMANAGER_DIRECTORY)


def normalize(rel):
    """'/a//b/' -> 'a/b'. Las barras invertidas cuentan como separador."""
    return '/'.join(part for part in (rel or '').replace('\\', '/').split('/') if part)


def to_abs(rel):
    """Ruta absoluta de una ruta relativa. Falla si sale de la raíz o entra en algo reservado."""
    rel = normalize(rel)
    base = root()
    path = os.path.abspath(os.path.join(base, rel))
    if path != base and not path.startswith(base + os.sep):
        raise OperationError(_('Invalid path'), 400)
    if path != base and os.path.relpath(path, base).split(os.sep)[0] in RESERVED_NAMES:
        raise OperationError(_('Invalid path'), 400)
    return path


def to_rel(path):
    rel = os.path.relpath(path, root())
    return '' if rel == '.' else rel.replace(os.sep, '/')


def existing(rel):
    path = to_abs(rel)
    if path == root() or not os.path.lexists(path):
        raise OperationError(_('The item does not exist'), 404)
    return path


def existing_dir(rel):
    path = to_abs(rel)
    if not os.path.isdir(path):
        raise OperationError(_('The destination is not a folder'), 400)
    return path


def clean_name(name):
    """Normaliza un nombre nuevo como lo hace la subida (espacios a _, sin caracteres raros)."""
    try:
        cleaned = FILEMANAGER_STORAGE.get_valid_name((name or '').strip())
    except SuspiciousFileOperation:
        cleaned = ''
    if not cleaned or cleaned in ('.', '..') or cleaned in RESERVED_NAMES or '/' in cleaned:
        raise OperationError(_('Invalid name'), 400)
    return cleaned


# --- Listado ------------------------------------------------------------------------------------

def _iso(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).isoformat()


def entry(path):
    """Datos de un fichero o carpeta para la API."""
    is_dir = os.path.isdir(path)
    try:
        st = os.stat(path)
        size, modified = (None if is_dir else st.st_size), _iso(st.st_mtime)
    except OSError:
        size, modified = None, None
    name = os.path.basename(path)
    return {
        'name': name,
        'path': to_rel(path),
        'type': 'directory' if is_dir else 'file',
        'extension': '' if is_dir else get_extension(name).lower(),
        'size': size,
        'size_display': '' if size is None else sizeof_fmt(size),
        'modified': modified,
    }


def _has_subdirs(path):
    """True si la carpeta tiene alguna subcarpeta visible (para el árbol). Para en la primera."""
    try:
        with os.scandir(path) as it:
            return any(item.is_dir() and not item.name.startswith('.') for item in it)
    except OSError:
        return False


def list_dir(rel, dirs_only=False):
    """
    Contenido de una carpeta: primero carpetas y luego ficheros, sin distinguir mayúsculas.
    Con dirs_only, solo las carpetas y si tienen subcarpetas (para el árbol). Cada .shp lleva en
    'companions' los nombres de sus ficheros asociados.
    """
    path = existing_dir(rel)
    dirs, files = [], []
    with os.scandir(path) as it:
        for item in it:
            if path == root() and item.name in RESERVED_NAMES:
                continue
            if item.is_dir():
                data = entry(item.path)
                if dirs_only:
                    data['has_subdirs'] = _has_subdirs(item.path)
                dirs.append(data)
            elif not dirs_only:
                files.append(entry(item.path))
    names = {f['name'] for f in files}
    for f in files:
        if f['extension'] == 'shp':
            f['companions'] = sorted(os.path.basename(p) for p in file_group(os.path.join(path, f['name']))[1:]
                                     if os.path.basename(p) in names)
    key = lambda e: e['name'].lower()
    return sorted(dirs, key=key) + sorted(files, key=key)


def total_size(paths):
    size = 0
    for path in paths:
        if os.path.isdir(path) and not os.path.islink(path):
            for current, _dirs, names in os.walk(path):
                for name in names:
                    try:
                        size += os.lstat(os.path.join(current, name)).st_size
                    except OSError:
                        pass
        else:
            try:
                size += os.lstat(path).st_size
            except OSError:
                pass
    return size


# --- Grupos (un fichero, o un .shp con sus asociados) -------------------------------------------

def group(path):
    """Rutas que se tratan juntas: la carpeta, o el fichero con sus asociados si es un .shp."""
    if os.path.isdir(path) and not os.path.islink(path):
        return [path]
    return file_group(path)


def _split_stem(name):
    """('datos', '.shp') para 'datos.shp'; los asociados comparten la raíz ('datos')."""
    stem, ext = os.path.splitext(name)
    return (stem, ext) if stem else (name, '')


def _targets(paths, dest_dir, stem):
    """Destinos de un grupo en dest_dir cambiando la raíz común de los nombres por `stem`."""
    main_stem = _split_stem(os.path.basename(paths[0]))[0]
    targets = []
    for path in paths:
        name = os.path.basename(path)
        suffix = name[len(main_stem):] if name.startswith(main_stem) else name
        targets.append(os.path.join(dest_dir, stem + suffix))
    return targets


def _free_targets(paths, dest_dir, on_conflict, stem=None):
    """
    Destinos libres para un grupo. Con on_conflict='rename' prueba raiz_1, raiz_2...; con
    'error' falla si alguno existe.
    """
    stem = stem if stem is not None else _split_stem(os.path.basename(paths[0]))[0]
    targets = _targets(paths, dest_dir, stem)
    if not any(os.path.lexists(t) for t in targets):
        return targets
    if on_conflict != 'rename':
        raise OperationError(_('An item with that name already exists'), 409, conflict=True)
    i = 1
    while True:
        targets = _targets(paths, dest_dir, '%s_%d' % (stem, i))
        if not any(os.path.lexists(t) for t in targets):
            return targets
        i += 1


def _check_not_inside(src, dest_dir):
    if os.path.isdir(src) and (dest_dir == src or dest_dir.startswith(src + os.sep)):
        raise OperationError(_('A folder cannot be moved or copied into itself'), 400)


def _check_space(paths, dest_dir):
    if shutil.disk_usage(dest_dir).free < total_size(paths):
        raise OperationError(_('Not enough free disk space'), 507)


# --- Operaciones --------------------------------------------------------------------------------

def mkdirs(path):
    """
    Crea la carpeta y las que falten por encima con los permisos de FILEMANAGER_STORAGE
    (FOLDER_DEFAULT_PERMISSIONS), como las crean la subida y «Crear directorio» clásicos.
    """
    mode = getattr(FILEMANAGER_STORAGE, 'directory_permissions_mode', None)
    missing = []
    current = path
    while not os.path.isdir(current):
        missing.append(current)
        current = os.path.dirname(current)
    for directory in reversed(missing):
        os.mkdir(directory)
        if mode is not None:
            os.chmod(directory, mode)


def make_dir(parent_rel, name):
    parent = existing_dir(parent_rel)
    path = os.path.join(parent, clean_name(name))
    if os.path.lexists(path):
        raise OperationError(_('An item with that name already exists'), 409, conflict=True)
    mkdirs(path)
    return entry(path)


def rename(rel, new_name):
    """Renombra en la misma carpeta. Un .shp renombra también sus asociados y conserva .shp."""
    src = existing(rel)
    name = clean_name(new_name)
    parent = os.path.dirname(src)
    if not os.path.isdir(src) and get_extension(src).lower() == 'shp':
        # 'rios' o 'rios.shp' -> rios.shp, rios.dbf, rios.shx...
        paths = file_group(src)
        stem, ext = _split_stem(name)
        targets = _targets(paths, parent, stem if ext.lower() == '.shp' else name)
    else:
        paths = [src]
        targets = [os.path.join(parent, name)]
    if [os.path.basename(t) for t in targets] == [os.path.basename(p) for p in paths]:
        return entry(src)
    # Permite cambiar solo mayúsculas/minúsculas aunque el sistema de ficheros no las distinga
    for path, target in zip(paths, targets):
        if os.path.lexists(target) and not os.path.samefile(path, target):
            raise OperationError(_('An item with that name already exists'), 409)
    for path, target in zip(paths, targets):
        os.rename(path, target)
    return entry(targets[0])


def move(rel, dest_rel, on_conflict='error'):
    src = existing(rel)
    dest_dir = existing_dir(dest_rel)
    _check_not_inside(src, dest_dir)
    if os.path.dirname(src) == dest_dir:
        return entry(src)
    paths = group(src)
    targets = _free_targets(paths, dest_dir, on_conflict)
    done = []
    try:
        for path, target in zip(paths, targets):
            shutil.move(path, target)
            done.append((path, target))
    except Exception:
        # Deja el grupo como estaba
        for path, target in reversed(done):
            try:
                shutil.move(target, path)
            except Exception:
                logger.exception("Filemanager: could not undo move of %s", path)
        raise
    return entry(targets[0])


def copy(rel, dest_rel, on_conflict='rename'):
    src = existing(rel)
    dest_dir = existing_dir(dest_rel)
    _check_not_inside(src, dest_dir)
    paths = group(src)
    _check_space(paths, dest_dir)
    targets = _free_targets(paths, dest_dir, on_conflict)
    done = []
    try:
        for path, target in zip(paths, targets):
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.copytree(path, target, symlinks=True)
            else:
                shutil.copy2(path, target, follow_symlinks=False)
            done.append(target)
    except Exception:
        for target in done:
            try:
                _rmtree(target) if os.path.isdir(target) and not os.path.islink(target) else os.remove(target)
            except Exception:
                logger.exception("Filemanager: could not clean up partial copy %s", target)
        raise
    return entry(targets[0])


# --- Papelera -----------------------------------------------------------------------------------

def trash_root():
    return os.path.join(root(), TRASH_DIRNAME)


def retention_days():
    return getattr(settings, 'FILEMANAGER_TRASH_RETENTION_DAYS', DEFAULT_TRASH_RETENTION_DAYS)


def _trash_entry(trash_id):
    if not _TRASH_ID_RE.match(trash_id or ''):
        raise OperationError(_('The item is no longer in the trash'), 404)
    path = os.path.join(trash_root(), trash_id)
    if not os.path.isfile(os.path.join(path, 'meta.json')):
        raise OperationError(_('The item is no longer in the trash'), 404)
    return path


def _read_meta(entry_dir):
    with open(os.path.join(entry_dir, 'meta.json'), encoding='utf-8') as f:
        return json.load(f)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def to_trash(rel, username):
    """Mueve a la papelera el elemento (y sus asociados si es un .shp). Devuelve su ficha."""
    src = existing(rel)
    paths = group(src)
    trash_id = uuid.uuid4().hex
    entry_dir = os.path.join(trash_root(), trash_id)
    items_dir = os.path.join(entry_dir, 'items')
    os.makedirs(items_dir)
    meta = {
        'id': trash_id,
        'name': os.path.basename(src),
        'original_path': to_rel(src),
        'original_dir': to_rel(os.path.dirname(src)),
        'names': [os.path.basename(p) for p in paths],
        'type': 'directory' if os.path.isdir(src) and not os.path.islink(src) else 'file',
        'size': total_size(paths),
        'deleted_by': username,
        'deleted_at': _now().isoformat(),
    }
    moved = []
    try:
        for path in paths:
            # rename si es el mismo disco (lo normal); si no (carpeta enlazada a otro), copia y borra
            shutil.move(path, os.path.join(items_dir, os.path.basename(path)))
            moved.append(path)
        with open(os.path.join(entry_dir, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False)
    except Exception:
        for path in moved:
            try:
                shutil.move(os.path.join(items_dir, os.path.basename(path)), path)
            except Exception:
                logger.exception("Filemanager: could not undo trash of %s", path)
        shutil.rmtree(entry_dir, ignore_errors=True)
        raise
    return _public_meta(meta)


def _public_meta(meta):
    deleted_at = datetime.datetime.fromisoformat(meta['deleted_at'])
    data = dict(meta)
    data['size_display'] = sizeof_fmt(meta.get('size') or 0)
    data['expires_at'] = (deleted_at + datetime.timedelta(days=retention_days())).isoformat()
    data['extension'] = '' if meta.get('type') == 'directory' else get_extension(meta['name']).lower()
    return data


def trash_items():
    """Fichas de todo lo que hay en la papelera, lo último borrado primero."""
    base = trash_root()
    if not os.path.isdir(base):
        return []
    items = []
    for trash_id in os.listdir(base):
        entry_dir = os.path.join(base, trash_id)
        if not _TRASH_ID_RE.match(trash_id):
            continue
        try:
            items.append(_public_meta(_read_meta(entry_dir)))
        except Exception:
            logger.warning("Filemanager: unreadable trash entry %s", entry_dir)
    return sorted(items, key=lambda m: m['deleted_at'], reverse=True)


def trash_get(trash_id):
    return _public_meta(_read_meta(_trash_entry(trash_id)))


def restore(trash_id):
    """
    Devuelve el elemento a su carpeta (la vuelve a crear si ya no existe). Si allí ya hay algo
    con el mismo nombre, restaura como nombre_1... Devuelve la ficha del elemento restaurado.
    """
    entry_dir = _trash_entry(trash_id)
    meta = _read_meta(entry_dir)
    dest_dir = to_abs(meta['original_dir'])
    items_dir = os.path.join(entry_dir, 'items')
    paths = [os.path.join(items_dir, name) for name in meta['names']]
    paths = [p for p in paths if os.path.lexists(p)]
    if not paths:
        shutil.rmtree(entry_dir, ignore_errors=True)
        raise OperationError(_('The item is no longer in the trash'), 404)
    mkdirs(dest_dir)
    targets = _free_targets(paths, dest_dir, 'rename')
    for path, target in zip(paths, targets):
        shutil.move(path, target)
    shutil.rmtree(entry_dir, ignore_errors=True)
    return entry(targets[0])


def delete_forever(trash_id):
    entry_dir = _trash_entry(trash_id)
    _rmtree(entry_dir)


def purge_expired(now=None):
    """Borra lo que lleva en la papelera más días de los configurados. Devuelve cuántos."""
    base = trash_root()
    if not os.path.isdir(base):
        return 0
    now = now or _now()
    limit = datetime.timedelta(days=retention_days())
    purged = 0
    for trash_id in os.listdir(base):
        entry_dir = os.path.join(base, trash_id)
        if not _TRASH_ID_RE.match(trash_id) or not os.path.isdir(entry_dir):
            continue
        try:
            deleted_at = datetime.datetime.fromisoformat(_read_meta(entry_dir)['deleted_at'])
        except Exception:
            # Entrada sin ficha válida (p. ej. un borrado interrumpido): se usa su fecha en disco
            deleted_at = datetime.datetime.fromtimestamp(os.stat(entry_dir).st_mtime, datetime.timezone.utc)
        if now - deleted_at > limit:
            try:
                _rmtree(entry_dir)
                purged += 1
            except Exception:
                logger.exception("Filemanager: could not purge trash entry %s", entry_dir)
    return purged


# --- Descarga de una selección en zip -----------------------------------------------------------

def zip_entries(rels):
    """
    (ruta absoluta, nombre dentro del zip) de todo lo seleccionado. Cada elemento va con su nombre
    en la raíz del zip; las carpetas, con su contenido. Comprueba el tamaño máximo.
    """
    entries, used = [], set()
    for rel in rels:
        src = existing(rel)
        top = os.path.basename(src)
        base_top, n = top, 1
        while top in used:
            stem, ext = _split_stem(base_top)
            top = '%s_%d%s' % (stem, n, ext)
            n += 1
        used.add(top)
        if os.path.isdir(src):
            entries.append((src, top + '/'))
            for current, dirs, names in os.walk(src):
                dirs.sort()
                rel_dir = os.path.relpath(current, src)
                prefix = top if rel_dir == '.' else top + '/' + rel_dir.replace(os.sep, '/')
                if rel_dir != '.' and not names and not dirs:
                    entries.append((current, prefix + '/'))
                for name in sorted(names):
                    entries.append((os.path.join(current, name), prefix + '/' + name))
        else:
            entries.append((src, top))
    size = total_size([path for path, arcname in entries if not arcname.endswith('/')])
    max_size = getattr(settings, 'FILEMANAGER_ZIP_DOWNLOAD_MAX_SIZE', DEFAULT_ZIP_DOWNLOAD_MAX_SIZE)
    if max_size and size > max_size:
        raise OperationError(_('The selection takes %(size)s, more than the allowed %(limit)s') % {
            'size': sizeof_fmt(size), 'limit': sizeof_fmt(max_size)}, 413)
    return entries


class _Sink(object):
    """Destino de zipfile sin seek: acumula lo escrito para ir enviándolo."""

    def __init__(self):
        self._chunks = []
        self._pos = 0

    def write(self, data):
        self._chunks.append(bytes(data))
        self._pos += len(data)
        return len(data)

    def tell(self):
        return self._pos

    def flush(self):
        pass

    def pop(self):
        data = b''.join(self._chunks)
        self._chunks = []
        return data


def stream_zip(entries, chunk_size=1024 * 1024):
    """Genera el zip por trozos, sin escribirlo en disco ni tenerlo entero en memoria."""
    sink = _Sink()
    with zipfile.ZipFile(sink, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for path, arcname in entries:
            try:
                if arcname.endswith('/'):
                    zf.writestr(zipfile.ZipInfo.from_file(path, arcname), b'')
                    continue
                info = zipfile.ZipInfo.from_file(path, arcname)
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(path, 'rb') as src, zf.open(info, 'w') as dst:
                    while True:
                        chunk = src.read(chunk_size)
                        if not chunk:
                            break
                        dst.write(chunk)
                        data = sink.pop()
                        if data:
                            yield data
            except OSError:
                logger.exception("Filemanager: could not add %s to the zip", path)
            data = sink.pop()
            if data:
                yield data
    yield sink.pop()
