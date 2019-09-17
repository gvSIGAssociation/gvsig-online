from __future__ import absolute_import, unicode_literals
'''
    gvSIG Online.
    Copyright (C) 2019 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
@author: Cesar Martinez Izquierdo <cmartinez@scolab.es>
'''

from celery import shared_task
from gvsigol_plugin_downloadman.models import DownloadRequest, DownloadLink, ResourceLocator
from gvsigol_plugin_downloadman.models import get_packaging_max_retry_time
import datetime
from . import settings
import os
import tempfile
import zipfile
import requests

__TMP_DIR = None
__TARGET_DIR = None

def getTmpDir():
    if not __TMP_DIR:
        try:
            if not os.path.exists(settings.TMP_DIR):
                os.makedirs(settings.TMP_DIR, 700)
        except:
            pass
        __TMP_DIR = settings.TMP_DIR
    return __TMP_DIR

def getTargetDir():
    if not __TARGET_DIR:
        try:
            if not os.path.exists(settings.TARGET_DIR):
                os.makedirs(settings.TARGET_DIR, 700)
        except:
            pass
        __TARGET_DIR = settings.TARGET_DIR
    return __TARGET_DIR


class ResourceDescription():
    def __init__(self, name, res_path):
        self.name = name
        self.res_path = res_path

def resolveLinkLocator(resourceLocator):
    # TODO: authentication and permissions
    (fd, tmp_path) = tempfile.mkstemp('.tmp', 'ideuydm', dir=getTmpDir())
    tmp_file = os.fdopen(fd, "wb")
    
    r = requests.get(resourceLocator.data_source, stream=True)
    for chunk in r.iter_content(chunk_size=128):
        tmp_file.write(chunk)
    tmp_file.close()
    desc = ResourceDescription(tmp_path, resourceLocator.name)
    return [desc]

def resolveLocator(resourceLocator):
    if resourceLocator.res_type == ResourceLocator.HTTP_LINK_SOURCE_TYPE:
        return resolveLinkLocator(resourceLocator)
    return []

def _addResource(zipobj, resourceLocator):
    resourceDescList = resolveLocator(resourceLocator)
    for resourceDesc in resourceDescList:
        zipobj.write(resourceDesc.res_path, resourceDesc.name)
        os.remove(resourceDesc.res_path)

def packageRequest(downloadRequest):
    zip_file = None
    try:
    # 1. create temporary zip file
        (fd, zip_path) = tempfile.mkstemp('.zip', 'ideuy', getTargetDir())
        zip_file = os.fdopen(fd, "w")
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipobj:
            # 2. add each resource to the zip file
            locators = downloadRequest.resource_locator_set.all()
            for resourceLocator in locators:
                _addResource(zipobj, resourceLocator)
    except:
        try:
            if zip_file:
                zip_file.close()
                os.remove(zip_path)
        except:
            pass
        # remove temp zip file
        # raise an error
        return
    return zip_path

@shared_task
def processDownloadRequest(request_id):
    # 1 get request
    request = DownloadRequest.objects.get(request_id)
    # 2 package
    zip_path = packageRequest(request)
    if zip_path:
            
        request.request_status = request.PACKAGED_STATUS
        request.save()
        # 3. create the link
        new_link = DownloadLink()
        new_link.download_link = zip_path
        new_link.contents = request
        new_link.valid_to = datetime.datetime.now() + datetime.timedelta(seconds = request.validity)
        new_link.request_random_id = request.request_random_id
        new_link.save()
        
        # 4. notify: send the link to the user
        
    else:
        # packaging failed
        if request.retry_count == 0:
            delay = 300 # 5 minutes
        elif request.retry_count == 1:
            delay = 3600 # 60 minutes
        elif request.retry_count == 2:
            delay = 21600 # 6 hours
        elif request.retry_count == 3:
            delay = 43200 # 12 hours
        else:
            delay = 43200 + (request.retry_count - 3)*86400 # 12 hours + 24 hours * number_of_retries_after_first_day 
        if delay > get_packaging_max_retry_time():
            # permanent package error
            request.status = request.PERMANENT_PACKAGE_ERROR_STATUS
            request.save()
            return
        
        request.status = request.PACKAGE_ERROR_STATUS
        request.retry_count = request.retry_count + 1 
        request.save()
        if request.retry_count > 3:
            # notify temporary error to user
            pass
        
        packageRequest.apply_async(queue='downman', countdown=delay, kwargs={'request_id': request_id})

