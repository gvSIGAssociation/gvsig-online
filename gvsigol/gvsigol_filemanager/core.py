import os

from django.conf import settings
from django.core.files.base import ContentFile

import signals
from gvsigol.settings import FILEMANAGER_DIRECTORY, FILEMANAGER_STORAGE
from utils import sizeof_fmt


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
            'filedate': FILEMANAGER_STORAGE.modified_time(self.location),
            'fileurl': self.url,
        }

    def directory_list(self):
        listing = []

        directories, files = FILEMANAGER_STORAGE.listdir(self.location)

        def _helper(name, filetype):
            return {
                'filepath': os.path.join(self.path, name),
                'fileformat': 'shapefile',
                'filetype': filetype,
                'filename': name,
                'filedate': FILEMANAGER_STORAGE.modified_time(os.path.join(self.path, name)),
                'filesize': sizeof_fmt(FILEMANAGER_STORAGE.size(os.path.join(self.path, name))),
            }

        for directoryname in directories:
            listing.append(_helper(directoryname, 'Directory'))

        for filename in files:
            listing.append(_helper(filename, 'File'))

        return listing

    def upload_file(self, filedata):
        filename = FILEMANAGER_STORAGE.get_valid_name(filedata.name)
        filepath = os.path.join(self.path, filename)
        signals.filemanager_pre_upload.send(sender=self.__class__, filename=filename, path=self.path, filepath=filepath)
        FILEMANAGER_STORAGE.save(filepath, filedata)
        signals.filemanager_post_upload.send(sender=self.__class__, filename=filename, path=self.path, filepath=filepath)
        return filename

    def create_directory(self, name):
        name = FILEMANAGER_STORAGE.get_valid_name(name)
        tmpfile = os.path.join(name, '.tmp')

        path = os.path.join(self.path, tmpfile)

        FILEMANAGER_STORAGE.save(path, ContentFile(''))
        FILEMANAGER_STORAGE.delete(path)
