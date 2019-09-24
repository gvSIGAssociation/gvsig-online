# -*- coding: utf-8 -*-

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
import logging
from gvsigol_plugin_downloadman.models import FORMAT_PARAM_NAME
import json
from gvsigol_plugin_downloadman.utils import getLayer

#logger = logging.getLogger("gvsigol-celery")
logger = logging.getLogger("gvsigol")


__TMP_DIR = None
__TARGET_DIR = None
DEFAULT_TIMEOUT = 60

class Error(Exception):
    pass

class PreparationException(Exception):
    pass


def getTmpDir():
    global __TMP_DIR
    if not __TMP_DIR:
        try:
            if not os.path.exists(settings.TMP_DIR):
                os.makedirs(settings.TMP_DIR, 0o700)
        except:
            pass
        __TMP_DIR = settings.TMP_DIR
    return __TMP_DIR

def getTargetDir():
    global __TARGET_DIR
    if not __TARGET_DIR:
        try:
            if not os.path.exists(settings.TARGET_DIR):
                os.makedirs(settings.TARGET_DIR, 0o700)
        except:
            pass
        __TARGET_DIR = settings.TARGET_DIR
    return __TARGET_DIR


class ResourceDescription():
    def __init__(self, name, res_path):
        self.name = name
        self.res_path = res_path

        
def _getParamValue(params, name):
    for param in params:
        if param.get('name') == name:
            return param.get('value')

def _normalizeWxsUrl(url):
        return url.split("?")[0]

def _getWfsRequest(layer_name, baseUrl, params):
    file_format = _getParamValue(params, FORMAT_PARAM_NAME)
    if not file_format:
        file_format = 'shape-zip'
    return _normalizeWxsUrl(baseUrl) + '?service=WFS&version=1.0.0&request=GetFeature&typeName=' + layer_name + '&outputFormat='+ file_format

def _getWcsRequest(layer_name, baseUrl, params):
    url = _normalizeWxsUrl(baseUrl) + '?service=WCS&version=2.0.0&request=GetCoverage&CoverageId=' + layer_name
    file_format = _getParamValue(params, FORMAT_PARAM_NAME)
    if file_format:
        url += '&format=' + file_format
    return url

def getCatalogResourceURL(res_type, resource_name, resource_url, params):
    # We must get the catalog online resources again and ensure the provided URL is in the catalog
    if res_type == ResourceLocator.HTTP_LINK_RESOURCE_TYPE:
        return resource_url
    elif res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE:
        return _getWcsRequest(resource_name, resource_url, params)
    elif res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE:
        return _getWfsRequest(resource_name, resource_url, params)

def getGvsigolResourceURL(res_type, layer, params):
    if layer:
        if res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE and layer.datastore.workspace.wfs_endpoin:
            baseUrl = layer.datastore.workspace.wfs_endpoint
            return _getWfsRequest(layer.name, baseUrl, params)
        elif res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE and layer.datastore.workspace.wcs_endpoint:
            baseUrl = layer.datastore.workspace.wcs_endpoint
            return _getWcsRequest(layer.name, baseUrl, params)

def resolveLinkLocator(url, resource_name):
    # TODO: authentication and permissions
    (fd, tmp_path) = tempfile.mkstemp('.tmp', 'ideuydm', dir=getTmpDir())
    tmp_file = os.fdopen(fd, "wb")
    
    logger.debug(url)
    r = requests.get(url, stream=True, verify=False, timeout=DEFAULT_TIMEOUT)
    for chunk in r.iter_content(chunk_size=128):
        tmp_file.write(chunk)
    tmp_file.close()
    desc = ResourceDescription(resource_name, tmp_path)
    # returns an array because a GIS dataset may be composed of several files (e.g. SHP, DBF, SHX, PRJ etc for a shapefile resource)
    return [desc]

def resolveLocator(resourceLocator):
    resource_descriptor = json.loads(resourceLocator.data_source)
    res_type = resource_descriptor.get('resource_type')
    resource_name = resource_descriptor.get('name')
    resource_url = resource_descriptor.get('url')
    params = resource_descriptor.get('param_values', [])
    if resourceLocator.layer_id_type == ResourceLocator.GEONETWORK_UUID:
        url = getCatalogResourceURL(res_type, resource_name, resource_url, params)
    elif resourceLocator.layer_id_type == ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE:
        layer = getLayer(resourceLocator.layer_id)
        url = getGvsigolResourceURL(res_type, layer, params)
    else:
        return []
    
    if url:
        return resolveLinkLocator(url, resource_name)
    # TODO: error management
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
            locators = downloadRequest.resourcelocator_set.all()
            for resourceLocator in locators:
                _addResource(zipobj, resourceLocator)
    except:
        logger.exception("error packaing request")
        print "error packaging request"
        try:
            if zip_file:
                zip_file.close()
                os.remove(zip_path)
        except:
            logger.exception("error packaing request")
            pass
        raise PreparationException
    return zip_path

import os
def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)
        
def getNextRetryDelay(request):
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
        delay = 0
    return delay

@shared_task(bind=True)
def processDownloadRequest(self, request_id):
    logger.debug("starting processDownloadRequest")
    print "starting processDownloadRequest"
    # 1 get request
    try:
        touch('/tmp/cmi00001')
    except:
        pass
    print request_id
    try:
        request = DownloadRequest.objects.get(id=request_id)
        if request.request_status == DownloadRequest.COMPLETED_STATUS or request.request_status == DownloadRequest.PERMANENT_PACKAGE_ERROR_STATUS or \
                request.request_status == DownloadRequest.CANCELLED_STATUS or request.request_status == DownloadRequest.REJECTED_STATUS or \
                request.request_status == DownloadRequest.HOLD_STATUS or request.request_status == DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS:
            return
        # 2 package
        zip_path = packageRequest(request)
        print zip_path
        if zip_path:
            # 3. create the link
            new_link = DownloadLink()
            new_link.contents = request
            new_link.valid_to = datetime.datetime.now() + datetime.timedelta(seconds = request.validity)
            new_link.request_random_id = request.request_random_id
            new_link.prepared_download_path = zip_path
            new_link.save()
            
            request.request_status = DownloadRequest.PACKAGED_STATUS
            request.save()
            # 4. notify: send the link to the user
            print "done"
    except Exception as exc:
        logger.exception("error preparing download request")
        print "error preparing download request"
        delay = getNextRetryDelay(request)
        if delay:
            request.request_status = DownloadRequest.PACKAGING_ERROR_STATUS
            request.retry_count = request.retry_count + 1 
            request.save()
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.request_status = DownloadRequest.PERMANENT_PACKAGE_ERROR_STATUS
            request.save()
