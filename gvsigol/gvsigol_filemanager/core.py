import os

from django.conf import settings
from django.core.files.base import ContentFile

from gvsigol_auth import auth_backend

from . import signals
from gvsigol.settings import FILEMANAGER_DIRECTORY, FILEMANAGER_STORAGE, INSTALLED_APPS
from .utils import sizeof_fmt
from gvsigol_core import utils as core_utils
import zipfile
import shutil


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
        listing = []
        
        visible_extensions = ['shp', 'dbf', 'geotif', 'geotiff', 'tif', 'tiff', 'zip']
        
        if 'gvsigol_plugin_etl' in INSTALLED_APPS:
            visible_extensions = visible_extensions + ['xlsx', 'xls', 'csv']
        
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
        for directoryname in directories:
            '''if first_level:
                if request.user.is_superuser:
                    groups = core_utils.get_groups()
                else:
                    groups = auth_backend.get_roles(request)
                for g in groups:
                    if directoryname == g:
                        listing.append(_helper(directoryname, 'Directory', ''))
            else:
                listing.append(_helper(directoryname, 'Directory', ''))'''
            if request.user.is_superuser:
                listing.append(_helper(directoryname, 'Directory', ''))
            else: 
                if first_level:
                    for g in groups:
                        if directoryname == g:
                            listing.append(_helper(directoryname, 'Directory', ''))
                else:
                    listing.append(_helper(directoryname, 'Directory', ''))

        for filename in files:
            parts = filename.split('.')
            if len(parts) > 1:
                extension = parts[1]
                #if extension.lower() in visible_extensions:
                #    listing.append(_helper(filename, 'File', extension))
                listing.append(_helper(filename, 'File', extension))

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
    
    def delete(self, name):
        try:
            file = name.split('/')[-1]
            filename = file.split('.')[0]
            path = os.path.dirname(name)
            directories, files = FILEMANAGER_STORAGE.listdir(path)
            if len(files) >= 1:
                for f in files:
                    if filename == f.split('.')[0]:
                        FILEMANAGER_STORAGE.delete(os.path.join(path, f))
                        
            if len(directories) >= 1:
                for d in directories:
                    if filename == d.split('.')[0]:
                        FILEMANAGER_STORAGE.delete(os.path.join(path, d))
            return True
            
        except Exception as e:
            if e.errno == 21:
                path = name.replace('file://', '')
                self.set_permission_to_dir(path, 775)
                shutil.rmtree(path)
                return True
            if e.errno == 1:
                path = name.replace('file://', '')
                self.set_permission_to_dir(path, 775)
                shutil.rmtree(path)
                return True
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