import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _

from gvsigol_auth import auth_backend

from . import signals
from gvsigol.settings import FILEMANAGER_DIRECTORY, FILEMANAGER_STORAGE, INSTALLED_APPS
from .utils import sizeof_fmt
from gvsigol_core import utils as core_utils
import zipfile
import shutil
import logging
import stat
import copy
import re

logger = logging.getLogger("gvsigol")

# Ficheros que acompañan a un .shp y se borran con él (extensión sin el punto, en minúsculas)
SHAPEFILE_COMPANION_EXTENSIONS = frozenset({
    'dbf', 'shx', 'prj', 'cpg', 'qpj', 'sbn', 'sbx', 'qix', 'fix',
    'aih', 'ain', 'atx', 'ixs', 'mxs', 'xml', 'shp.xml',
})

# Nombres reservados en la raíz del gestor: no se listan ni se pueden abrir, crear ni descargar
TRASH_DIRNAME = '.gvsigol_trash'
UPLOADS_DIRNAME = '.gvsigol_uploads'
RESERVED_NAMES = frozenset({TRASH_DIRNAME, UPLOADS_DIRNAME})

# Tamaño máximo descomprimido de un zip. Se puede cambiar con FILEMANAGER_UNZIP_MAX_SIZE en settings.
DEFAULT_UNZIP_MAX_SIZE = 20 * 1024 ** 3
# Número máximo de entradas de un zip (un zip con millones de entradas vacías no ocupa nada pero
# agota el disco de inodos). Se puede cambiar con FILEMANAGER_UNZIP_MAX_ENTRIES en settings.
DEFAULT_UNZIP_MAX_ENTRIES = 200000

# Caracteres que no se dejan en los nombres que trae un zip (la subida ya los quita con
# get_valid_name): los que sirven para inyectar HTML/JS (< > " `), la barra invertida (la API la
# trata como separador) y los de control. Se mantienen espacios, tildes y apóstrofos.
_UNSAFE_ZIP_NAME_CHARS = re.compile(r'[<>"`\\\x00-\x1f\x7f]')


def safe_zip_component(name):
    """Parte de una ruta de un zip con los caracteres peligrosos cambiados por '_'."""
    return _UNSAFE_ZIP_NAME_CHARS.sub('_', name)


def _safe_member_names(members):
    """
    Nombre limpio de cada entrada (lista paralela). Si dos entradas distintas quedan con el mismo
    nombre al limpiarlas, la segunda pasa a nombre_1, nombre_2... para no sobrescribir la primera.
    """
    used = {}
    names = []
    for member in members:
        is_dir = member.filename.endswith('/')
        parts = [safe_zip_component(p) for p in member.filename.split('/')]
        clean = '/'.join(parts)
        key = clean.rstrip('/')
        if key in used and used[key] != member.filename.rstrip('/'):
            stem, ext = os.path.splitext(parts[-2] if is_dir else parts[-1])
            i = 1
            while True:
                candidate_last = '%s_%d%s' % (stem, i, ext)
                candidate = '/'.join(parts[:-2] + [candidate_last, ''] if is_dir else parts[:-1] + [candidate_last])
                if candidate.rstrip('/') not in used:
                    clean = candidate
                    break
                i += 1
        used.setdefault(clean.rstrip('/'), member.filename.rstrip('/'))
        names.append(clean)
    return names


class UnzipError(Exception):
    """Error de descompresión con un mensaje apto para el usuario."""


def get_extension(filename):
    """
    Extensión sin el punto: la última parte del nombre ('varios.puntos.shp' -> 'shp').
    Devuelve '' si no tiene ('notas', '.oculto').
    """
    return os.path.splitext(filename)[1][1:]


def sorter(item):
    return item.get('filename', '').lower()

class Filemanager(object):
    def __init__(self, path=None):
        self.update_path(path)

    def update_path(self, path):
        if path is None or len(path) == 0:
            self.path = ''
            self.abspath = FILEMANAGER_DIRECTORY
        else:
            self.path = self.validate_path(path)
            self.abspath = os.path.join(FILEMANAGER_DIRECTORY, self.path)
        self.location = os.path.join(settings.MEDIA_ROOT, self.abspath)
        self.url = os.path.join(settings.MEDIA_URL, self.abspath)

    def validate_path(self, path):
        # replace backslash with slash
        path = path.replace('\\', '/')
        # remove leading and trailing slashes
        path = '/'.join([i for i in path.split('/') if i])

        return path

    def get_breadcrumbs(self):
        breadcrumbs = [{
            'label': 'data',
            'path': '',
        }]

        parts = [e for e in self.path.split('/') if e]

        path = ''
        for part in parts:
            path = os.path.join(path, part)
            breadcrumbs.append({
                'label': part,
                'path': path,
            })

        return breadcrumbs

    def patch_context_data(self, context):
        context.update({
            'path': self.path,
            'breadcrumbs': self.get_breadcrumbs(),
        })

    def file_details(self):
        filename = self.path.rsplit('/', 1)[-1]
        return {
            'directory': os.path.dirname(self.path),
            'filepath': self.path,
            'filename': filename,
            'filesize': sizeof_fmt(FILEMANAGER_STORAGE.size(self.location)),
            'filedate': FILEMANAGER_STORAGE.get_modified_time(self.location),
            'fileurl': self.url,
        }

    def directory_list(self, request, first_level):
        directories, files = FILEMANAGER_STORAGE.listdir(self.location)

        def _helper(name, filetype, extension):
            return {
                'filepath': os.path.join(self.path, name),
                'extension': extension,
                'filetype': filetype,
                'filename': name,
                'filedate': FILEMANAGER_STORAGE.get_modified_time(os.path.join(self.path, name)),
                'filesize': sizeof_fmt(FILEMANAGER_STORAGE.size(os.path.join(self.path, name))),
            }

        groups = auth_backend.get_roles(request)
        dir_list = []
        if self.path == '':
            directories = [d for d in directories if d not in RESERVED_NAMES]
        for directoryname in directories:
            if request.user.is_superuser:
                dir_list.append(_helper(directoryname, 'Directory', ''))
            else: 
                if first_level:
                    if directoryname in groups:
                        dir_list.append(_helper(directoryname, 'Directory', ''))
                else:
                    dir_list.append(_helper(directoryname, 'Directory', ''))
        file_list = []
        if self.path == '' and not request.user.is_superuser:
            # En la raíz, solo las carpetas de sus roles (como la API): los ficheros sueltos no son suyos
            files = []
        for filename in files:
            file_list.append(_helper(filename, 'File', get_extension(filename)))
        listing = sorted(dir_list, key=sorter) + sorted(file_list, key=sorter)
        return listing

    def upload_file(self, filedata):
        filename = FILEMANAGER_STORAGE.get_valid_name(filedata.name)
        filepath = os.path.join(self.path, filename)
        signals.filemanager_pre_upload.send(sender=self.__class__, filename=filename, path=self.path, filepath=filepath)
        FILEMANAGER_STORAGE.save(filepath, filedata)
        signals.filemanager_post_upload.send(sender=self.__class__, filename=filename, path=self.path, filepath=filepath)
        return filename
    
    def extract_zip(self, file, folder):
        zfile = zipfile.ZipFile(file)
        zfile.extractall(folder)

    def unzip(self, zip_path, progress=None):
        """
        Descomprime un zip junto a él, en una carpeta con su nombre sin la extensión. Si ya existe
        algo con ese nombre usa nombre_1, nombre_2... para no sobrescribir nada. Comprueba antes el
        tamaño descomprimido (límite y espacio libre). Devuelve la ruta de la carpeta creada.
        Lanza UnzipError con un mensaje para el usuario si no se puede.
        `progress(bytes_hechos, bytes_totales)`, si se indica, se llama tras cada fichero.
        """
        zip_path = os.path.abspath(zip_path)
        if not _is_inside_root(zip_path) or not os.path.isfile(zip_path):
            raise UnzipError(_('Error unzipping resource'))
        try:
            with zipfile.ZipFile(zip_path) as zfile:
                members = zfile.infolist()
                max_entries = getattr(settings, 'FILEMANAGER_UNZIP_MAX_ENTRIES', DEFAULT_UNZIP_MAX_ENTRIES)
                if max_entries and len(members) > max_entries:
                    raise UnzipError(_('The zip file has %(count)d items, more than the allowed %(limit)d') % {
                        'count': len(members), 'limit': max_entries})
                total_size = sum(info.file_size for info in members)
                max_size = getattr(settings, 'FILEMANAGER_UNZIP_MAX_SIZE', DEFAULT_UNZIP_MAX_SIZE)
                if max_size and total_size > max_size:
                    raise UnzipError(_('The zip file takes %(size)s uncompressed, more than the allowed %(limit)s') % {
                        'size': sizeof_fmt(total_size), 'limit': sizeof_fmt(max_size)})
                parent = os.path.dirname(zip_path)
                if shutil.disk_usage(parent).free < total_size:
                    raise UnzipError(_('There is not enough free disk space to unzip the file (%(size)s needed)') % {
                        'size': sizeof_fmt(total_size)})
                folder = _unique_path(os.path.join(parent, os.path.splitext(os.path.basename(zip_path))[0]))
                # extract (como extractall) descarta rutas absolutas y componentes '..' de los nombres
                done = 0
                for member, clean_name in zip(members, _safe_member_names(members)):
                    if clean_name != member.filename:
                        # Misma entrada (se lee por orig_filename) con el nombre limpio en disco
                        member = copy.copy(member)
                        member.filename = clean_name
                    zfile.extract(member, folder)
                    done += member.file_size
                    if progress:
                        progress(done, total_size)
                if not os.path.isdir(folder):
                    # Un zip vacío: deja igualmente su carpeta
                    os.makedirs(folder)
                return folder
        except zipfile.BadZipFile:
            raise UnzipError(_('The zip file is damaged or is not a valid zip file'))

    def delete(self, name):
        """
        Borra el fichero o la carpeta (con todo su contenido) de la ruta absoluta `name`, que debe
        estar dentro de FILEMANAGER_DIRECTORY. Al borrar un .shp borra también sus ficheros
        asociados (.dbf, .shx, .prj...). Borrar algo que ya no existe se considera correcto.
        Devuelve True si ha ido bien.
        """
        target = os.path.abspath(name)
        if not _is_inside_root(target):
            logger.warning("Filemanager: refusing to delete outside the file manager: %s", name)
            return False
        try:
            if os.path.isdir(target) and not os.path.islink(target):
                _rmtree(target)
            elif os.path.lexists(target):
                for path in _files_to_delete(target):
                    os.remove(path)
            return True
        except Exception:
            logger.exception("Filemanager: error deleting %s", name)
            return False

    def set_permission_to_dir(self, directory_path, permission):
        for root, dirs, files in os.walk(directory_path):  
            for momo in dirs:  
                self.set_permission_to_dir(os.path.join(root, momo), permission)
            for momo in files:
                try:
                    os.chmod(os.path.join(root, momo), permission)
                except Exception:
                    pass
        
        
        

    def create_directory(self, name):
        name = FILEMANAGER_STORAGE.get_valid_name(name)
        tmpfile = os.path.join(name, '.tmp')

        path = os.path.join(self.path, tmpfile)

        FILEMANAGER_STORAGE.save(path, ContentFile(''))
        FILEMANAGER_STORAGE.delete(path)


def _root():
    return os.path.abspath(FILEMANAGER_DIRECTORY)


def _is_inside_root(path):
    """True si la ruta absoluta está dentro de FILEMANAGER_DIRECTORY, sin ser la propia raíz."""
    return os.path.abspath(path).startswith(_root() + os.sep)


def _unique_path(path):
    """La ruta tal cual si no existe; si no, ruta_1, ruta_2... la primera libre."""
    if not os.path.lexists(path):
        return path
    i = 1
    while os.path.lexists('%s_%d' % (path, i)):
        i += 1
    return '%s_%d' % (path, i)


def file_group(path):
    """El fichero y, si es un .shp, los ficheros de su mismo nombre que lo acompañan."""
    return _files_to_delete(path)


def _files_to_delete(path):
    """El fichero y, si es un .shp, los ficheros de su mismo nombre que lo acompañan."""
    files = [path]
    directory, filename = os.path.split(path)
    stem, extension = os.path.splitext(filename)
    if extension.lower() != '.shp' or not stem:
        return files
    prefix = stem + '.'
    for other in os.listdir(directory):
        if other == filename or not other.startswith(prefix):
            continue
        other_path = os.path.join(directory, other)
        if other[len(prefix):].lower() in SHAPEFILE_COMPANION_EXTENSIONS and not os.path.isdir(other_path):
            files.append(other_path)
    return files


def _rmtree(path):
    """
    Borra una carpeta con todo su contenido. Si falta permiso en alguna subcarpeta, lo da al
    propietario y lo reintenta (como hacía antes set_permission_to_dir).
    """
    def _retry_with_permission(func, failed_path, exc_info):
        if not isinstance(exc_info[1], PermissionError):
            raise exc_info[1]
        parent = os.path.dirname(failed_path)
        for target in (parent, failed_path):
            if os.path.isdir(target) and not os.path.islink(target):
                os.chmod(target, os.stat(target).st_mode | stat.S_IRWXU)
        func(failed_path)

    shutil.rmtree(path, onerror=_retry_with_permission)