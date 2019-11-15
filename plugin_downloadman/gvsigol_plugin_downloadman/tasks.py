# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
from builtins import str as text
from billiard.compat import resource
from billiard import process
from pydoc import plain
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

from celery import shared_task, task
from gvsigol_plugin_downloadman.models import DownloadRequest, DownloadLink, ResourceLocator
from gvsigol_plugin_downloadman.models import get_packaging_max_retry_time, get_mail_max_retry_time
from datetime import date, timedelta, datetime

import os
import tempfile
import zipfile
import requests
import logging
from gvsigol_plugin_downloadman.models import FORMAT_PARAM_NAME
import json
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import override
from django.core.urlresolvers import reverse
from django.utils.formats import date_format
from django.utils import timezone
from gvsigol import settings as core_settings
import re
from django.utils.translation import ugettext as _
from django.utils.crypto import get_random_string

from gvsigol_plugin_downloadman.utils import getLayer
from gvsigol_plugin_downloadman.settings import TMP_DIR,TARGET_ROOT
from django.conf import settings
import shutil
from gvsigol.celery import app as celery_app

from gvsigol.settings import GVSIGOL_NAME
try:
    from gvsigol_plugin_downloadman.settings import LOCAL_PATHS_WHITELIST
except:
    LOCAL_PATHS_WHITELIST = []

from gvsigol_plugin_downloadman.settings import DOWNLOADS_URL

#logger = logging.getLogger("gvsigol-celery")
logger = logging.getLogger("gvsigol")


__TMP_DIR = None
__TARGET_ROOT = None
DEFAULT_TIMEOUT = 900
LINK_UUID_RANDOM_LENGTH = 32 
LINK_UUID_FULL_LENGTH = 40

if hasattr(settings, 'DOWNMAN_UNKNOWN_FILES_MAX_AGE'):
    UNKNOWN_FILES_MAX_AGE = settings.DOWNMAN_UNKNOWN_FILES_MAX_AGE
else:
    UNKNOWN_FILES_MAX_AGE = 20 # days

if hasattr(settings, 'DOWNMAN_MIN_TARGET_SPACE'):
    MIN_TARGET_SPACE = settings.DOWNMAN_MIN_TARGET_SPACE
else:
    MIN_TARGET_SPACE = 209715200 # bytes == 200 MB

if hasattr(settings, 'DOWNMAN_MIN_TMP_SPACE'):
    MIN_TMP_SPACE = settings.DOWNMAN_MIN_TMP_SPACE
else:
    MIN_TMP_SPACE = 104857600 # bytes == 100 MB

if hasattr(settings, 'DOWNMAN_FREE_SPACE_RETRY_DELAY'):
    FREE_SPACE_RETRY_DELAY = settings.DOWNMAN_FREE_SPACE_RETRY_DELAY
else:
    FREE_SPACE_RETRY_DELAY = 60 # seconds == 1 minute
if hasattr(settings, 'DOWNMAN_CLEAN_TASK_FREQUENCY'):
    CLEAN_TASK_FREQUENCY = settings.DOWNMAN_CLEAN_TASK_FREQUENCY
else:
    CLEAN_TASK_FREQUENCY = 1200.0 # seconds == 20 minutes
    #CLEAN_TASK_FREQUENCY = 20.0 # seconds

# valid values:
# - NEVER: a direct link will always be returned, even for non-static URLs (e.g WFS and WCS requests)
# - DYNAMIC [Not implemented yet]: dynamic links (e.g. WFS and WCS requests) will be async processed and packaged
if hasattr(settings, 'DOWNMAN_PACKAGING_BEHAVIOUR'):
    DOWNMAN_PACKAGING_BEHAVIOUR = settings.DOWNMAN_PACKAGING_BEHAVIOUR
else:
    DOWNMAN_PACKAGING_BEHAVIOUR = 'NEVER'


class Error(Exception):
    pass

class PreparationException(Exception):
    pass

class ForbiddenAccessException(Exception):
    pass

def getFreeSpace(path):
    try:
        usage  = os.statvfs(path)
        return (usage.f_frsize * usage.f_bfree)
    except:
        try:
            usage = shutil.disk_usage(path) #@UndefinedVariable 
            return usage.free
        except:
            logger.exception("Error getting free space")
            return 0

def getTmpDir():
    global __TMP_DIR
    if not __TMP_DIR:
        try:
            if not os.path.exists(TMP_DIR):
                os.makedirs(TMP_DIR, 0o700)
        except:
            pass
        __TMP_DIR = TMP_DIR
    return __TMP_DIR

def getTargetDir():
    global __TARGET_ROOT
    if not __TARGET_ROOT:
        try:
            if not os.path.exists(TARGET_ROOT):
                os.makedirs(TARGET_ROOT, 0o700)
        except:
            pass
        __TARGET_ROOT = TARGET_ROOT
    return __TARGET_ROOT


class ResourceDescription():
    def __init__(self, name, res_path, temporary=False):
        self.name = name
        self.res_path = res_path
        self.temporary = temporary


class ResolvedLocator():
    def __init__(self, url, name, title = "", desc="", processed=False):
        self.url = url
        self.name = name
        self.title = title
        self.desc = desc
        self.processed = processed
        
def _getParamValue(params, name):
    for param in params:
        if param.get('name') == name:
            return param.get('value')


def _getExtension(file_format):
     # FIXME: we should have a more flexible approach to get file extension

    if not file_format:
        return ''
    
    ff_lower = file_format.lower()
    if ff_lower == 'shape-zip':
        return ".shp.zip"
    elif 'jpg' in ff_lower or 'jpeg' in ff_lower:
        return ".jpg"
    elif 'png' in ff_lower:
        return '.png'
    elif 'gml' in ff_lower:
        return '.gml'
    elif 'csv' in ff_lower:
        return '.csv'
    elif 'tif' in ff_lower:
        return '.tif'
    return "." + file_format

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
        return (resource_url, False)
    elif res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE:
        return (_getWcsRequest(resource_name, resource_url, params), True)
    elif res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE:
        return (_getWfsRequest(resource_name, resource_url, params), True)
    return (None, False)

def getGvsigolResourceURL(res_type, layer, params):
    if layer:
        if res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE and layer.datastore.workspace.wfs_endpoin:
            baseUrl = layer.datastore.workspace.wfs_endpoint
            return (_getWfsRequest(layer.name, baseUrl, params), True)
        elif res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE and layer.datastore.workspace.wcs_endpoint:
            baseUrl = layer.datastore.workspace.wcs_endpoint
            return (_getWcsRequest(layer.name, baseUrl, params), True)
    return (None, False)

def retrieveLinkLocator(url, resource_name):
    # TODO: authentication and permissions
    (fd, tmp_path) = tempfile.mkstemp('.tmp', 'ideuydm', dir=getTmpDir())
    tmp_file = os.fdopen(fd, "wb")
    
    logger.debug(url)
    r = requests.get(url, stream=True, verify=False, timeout=DEFAULT_TIMEOUT)
    for chunk in r.iter_content(chunk_size=128):
        tmp_file.write(chunk)
    tmp_file.close()
    desc = ResourceDescription(resource_name, tmp_path, True)
    # returns an array because a GIS dataset may be composed of several files (e.g. SHP, DBF, SHX, PRJ etc for a shapefile resource)
    return [desc]

def resolveFileLocator(url, resource_name):
    logger.debug("starting resolveFileLocator")
    logger.debug(url)
    local_path = url[7:]
    if not local_path.startswith("/"):
        local_path = "/" + local_path
    # remove any "../.."
    local_path = os.path.abspath(local_path)
    logger.debug("local_path")
    logger.debug(local_path)
    # we only allow local paths that are subfolders of the paths defined in LOCAL_PATHS_WHITELIST variable
    for path in LOCAL_PATHS_WHITELIST:
        logger.debug("path")
        logger.debug(path)
        if local_path.startswith(path):
            res = ResourceDescription(resource_name, local_path)
            return res
    logger.debug("local_path")
    logger.debug(local_path)
    logger.debug(LOCAL_PATHS_WHITELIST)
    raise ForbiddenAccessException

def resolveLocator(resourceLocator, download_request):
    """
    Parses the resourceLocator to translate the locator on a concrete URL or local file.
    If the resource described by the locator is static (does not require processing)
    a DownloadLink is also created.
    If the resource is dynamic, then the behaviour depends on DOWNMAN_PACKAGING_BEHAVIOUR
    variable. When DOWNMAN_PACKAGING_BEHAVIOUR is NEVER, the download link is also
    created for dynamic resources.
    When DOWNMAN_PACKAGING_BEHAVIOUR is DYNAMIC [not implemented yet], then the DownloadLink will not be
    created at this stage and a new task will be
    scheduled to create a temporal package for the download link.
    """
    resource_descriptor = json.loads(resourceLocator.data_source)
    res_type = resource_descriptor.get('resource_type')
    resource_name = resource_descriptor.get('name', '')

    resource_url = resource_descriptor.get('url')
    logger.debug(resource_descriptor)
    params = resource_descriptor.get('params', [])

    if resourceLocator.layer_id_type == ResourceLocator.GEONETWORK_UUID:
        (resourceLocator.resolved_url, resourceLocator.is_dynamic) = getCatalogResourceURL(res_type, resource_name, resource_url, params)
    elif resourceLocator.layer_id_type == ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE:
        layer = getLayer(resourceLocator.layer_id)
        (resourceLocator.resolved_url, resourceLocator.is_dynamic) = getGvsigolResourceURL(res_type, layer, params)
    
    if resourceLocator.resolved_url:
        if resourceLocator.is_dynamic and DOWNMAN_PACKAGING_BEHAVIOUR == 'DYNAMIC':
            resourceLocator.status = ResourceLocator.PROCESSING_STATUS
            resourceLocator.save()
        else:
            resourceLocator.status = ResourceLocator.PROCESSED_STATUS
            new_link = DownloadLink()
            new_link.request = download_request
            link_uuid = date.today().strftime("%Y%m%d") + get_random_string(length=32)
            new_link.valid_to = timezone.now() + timedelta(seconds = download_request.validity)
            new_link.link_random_id = link_uuid
            logger.debug("resolved_url")
            logger.debug(resourceLocator.resolved_url)
            if resourceLocator.resolved_url.startswith("file://"):
                if resourceLocator.resolved_url.endswith("/"):
                    new_link.prepared_download_path = resolveFileLocator(resourceLocator.resolved_url, resource_name).res_path
                else:
                    new_link.prepared_download_path = resolveFileLocator(resourceLocator.resolved_url, os.path.basename(resourceLocator.resolved_url)).res_path
            new_link.save()
            resourceLocator.download_link = new_link
            resourceLocator.save()
            return new_link

def resolveLocatorOld(resourceLocator):
    resource_descriptor = json.loads(resourceLocator.data_source)
    res_type = resource_descriptor.get('resource_type')
    resource_name = resource_descriptor.get('name')

    resource_url = resource_descriptor.get('url')
    print resource_descriptor
    params = resource_descriptor.get('params', [])

    if resourceLocator.layer_id_type == ResourceLocator.GEONETWORK_UUID:
        url = getCatalogResourceURL(res_type, resource_name, resource_url, params)
    elif resourceLocator.layer_id_type == ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE:
        layer = getLayer(resourceLocator.layer_id)
        url = getGvsigolResourceURL(res_type, layer, params)
    else:
        return []
    
    if url:
        print url
        print params
        file_format = _getParamValue(params, FORMAT_PARAM_NAME)
        print file_format
        # remove non-a-z_ or numeric characters
        resource_name = resource_name.replace(":", "_")
        resource_name = re.sub('[^\w\s_-]', '', resource_name).strip().lower()
        resource_name = resource_name + _getExtension(file_format)
        print resource_name
        if (url.startswith("http://") or url.startswith("https://")):
            
            return retrieveLinkLocator(url, resource_name)
        if url.startswith("file://"):
            if url.endswith("/"):
                return resolveFileLocator(url, resource_name)
            else:
                return resolveFileLocator(url, os.path.basename(url))
            
    # TODO: error management
    return []

def _addResource(zipobj, resourceLocator):
    resourceDescList = resolveLocator(resourceLocator)
    i = 0
    for resourceDesc in resourceDescList:
        res_name = text(i) + "-" + resourceDesc.name
        zipobj.write(resourceDesc.res_path, res_name)
        if resourceDesc.temporary:
            os.remove(resourceDesc.res_path)
        i = i + 1

def _getPackagePrefix():
    if GVSIGOL_NAME:
        return GVSIGOL_NAME.lower()
    else:
        return "gvsigol"

def _parseLinkUiid(fname):
    return fname[len(_getPackagePrefix()):LINK_UUID_FULL_LENGTH+len(_getPackagePrefix())] 

def packageRequest(downloadRequest, link_uuid):
    zip_file = None
    try:
        # 1. create target zip file
        prefix = _getPackagePrefix() + link_uuid + "_"
        (fd, zip_path) = tempfile.mkstemp('.zip', prefix, getTargetDir())
        print zip_path
        zip_file = os.fdopen(fd, "w")
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipobj:
            # 2. add each resource to the zip file
            locators = downloadRequest.resourcelocator_set.all()
            for resourceLocator in locators:
                _addResource(zipobj, resourceLocator)
        print 'closing'
        zip_file.close()
        print 'closed'
        os.chmod(zip_path, 0o444)
        print 'chmodded'
    except:
        logger.exception("error packaing request")
        print "error packaging request"
        try:
            if zip_file:
                zip_file.close()
                os.remove(zip_path)
        except:
            logger.exception("error packaing request")
        raise PreparationException
    return zip_path

def getNextPackagingRetryDelay(request):
    if request.package_retry_count == 0:
        delay = 300 # 5 minutes
    elif request.package_retry_count == 1:
        delay = 3600 # 60 minutes
    elif request.package_retry_count == 2:
        delay = 21600 # 6 hours
    elif request.package_retry_count == 3:
        delay = 43200 # 12 hours
    else:
        delay = 43200 + (request.package_retry_count - 3)*86400 # 12 hours + 24 hours * number_of_retries_after_first_day 
    if delay > get_packaging_max_retry_time():
        delay = 0
    return delay

def getNextMailRetryDelay(request):
    if request.notify_retry_count < 3:
        delay = 3600 # 60 minutes
    else:
        delay = delay = 21600 # 6 hours
    if delay > get_mail_max_retry_time():
        delay = 0
    return delay

def get_language(request):
    if request.language:
        return request.language
    else:
        try:
            return core_settings.LANGUAGE_CODE
        except:
            return 'en-us'

@shared_task(bind=True)
def notifyReceivedRequest(self, request_id, only_if_queued=True):
    try:
        logger.debug("starting notifyReceivedRequest")
        request = DownloadRequest.objects.get(pk=request_id)
        if only_if_queued and request.request_status != DownloadRequest.REQUEST_QUEUED_STATUS:
            return
        with override(get_language(request)):
            tracking_url = reverse('download-request-tracking', args=(request.request_random_id,))
                    
            subject = _('Download service: your request has been received - %(requestid)s') % {'requestid': request.request_random_id}
            plain_message = _(u'Your download request has been received.')
            plain_message += _('\nYou can use this tracking link to check the status of your request: %(url)s\n') % {'url': tracking_url}
            plain_message += _('\nIncluded resources:')
            for locator in request.resourcelocator_set.all():
                plain_message += u' - {0!s}\n'.format(locator.name)
            # html_message = render_to_string('mail_template.html', {'context': 'values'})
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                to = request.requested_by_user
            else:
                to = request.requested_by_external
            try:
                from_email =  core_settings.EMAIL_HOST_USER
            except:
                logger.exception("EMAIL_HOST_USER has not been configured")
                raise
            mail.send_mail(subject, plain_message, from_email, [to])
            request.request_status = DownloadRequest.COMPLETED_STATUS
            request.notification_status = DownloadRequest.NOTIFICATION_COMPLETED_STATUS
            request.save()
            # TODO: include an HTML version of the email
            #mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message)

    except Exception as exc:
        logger.exception("Download request completed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.request_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.package_retry_count = request.notify_retry_count + 1 
            request.save()
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.request_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save()

@shared_task(bind=True)
def notifyRequestProgress(self, request_id):
    try:
        logger.debug("starting notify task completed")
        request = DownloadRequest.objects.get(pk=request_id)
        with override(get_language(request)):
            tracking_url = reverse('download-request-tracking', args=(request.request_random_id,))
                    
            if request.request_status == DownloadRequest.COMPLETED_STATUS:
                subject = _('Download service: your request is ready - %(requestid)s') % {'requestid': request.request_random_id}
                plain_message = _(u'Your download request is ready.\n')
            elif request.request_status == DownloadRequest.COMPLETED_WITH_ERRORS:
                subject = _('Download service: your request is ready - %(requestid)s') % {'requestid': request.request_random_id}
                plain_message = _(u'Your download request is ready. Some resources failed to be processed and are not available for download at the moment.\n')
            else:
                subject = _('Download service: request progress - %(requestid)s') % {'requestid': request.request_random_id}
                plain_message = _(u'Your download request has been partially processed.\n')
            plain_message +=  _('You can use the following links to download the requested resources:\n')
                
            """
            try:
                base_url = core_settings.BASE_URL
                if base_url.endswith("/"):
                    download_url = base_url + resolvedUrl
                else:
                    download_url = base_url + "/" + resolvedUrl
            except:
                download_url = resolvedUrl
            """
            count = 1
            for link in request.downloadlink_set.all():
                link_url = reverse('downman-download-resource', args=(request.request_random_id, link.link_random_id))
                logger.debug(link_url)
                valid_to = date_format(link.valid_to, 'DATETIME_FORMAT')
                link.save()
                logger.debug(valid_to)
                linkResources = link.resourcelocator_set.all()
                if len(linkResources)==1:
                    plain_message += u' {0:2d}- {1!s}: {2!s}\n'.format(count, linkResources[0].name, link_url)
                else:
                    plain_message += u' {0:2d}- {1!s}: {2!s}\n'.format(count, _('Prepared package'), link_url)
                    plain_message += _(u'    -- Link valid until {0!s}:\n').format(valid_to)
                    plain_message += _(u'    -- Contents:')
                    for linkResource in linkResources:
                        plain_message += _(u'     -- {0!s} - {1!s}\n').format(linkResource.name, linkResource.title)
                count += 1
            locators =  request.resourcelocator_set.filter(download_link__isnull=True)
            if len(locators)>0:
                plain_message += _('\nThe following resources are still being processed:|n')
                for locator in locators:
                    plain_message += u' - {0!s}\n'.format(locator.name)
            plain_message += _('\nYou can also use this tracking link to check the status of your request: %(url)s\n') % {'url': tracking_url}
            # html_message = render_to_string('mail_template.html', {'context': 'values'})
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                to = request.requested_by_user
            else:
                to = request.requested_by_external
            try:
                from_email =  core_settings.EMAIL_HOST_USER
            except:
                logger.exception("EMAIL_HOST_USER has not been configured")
                raise
            logger.debug(u"mailing: " + to)
            mail.send_mail(subject, plain_message, from_email, [to])
            request.request_status = DownloadRequest.COMPLETED_STATUS
            request.notification_status = DownloadRequest.NOTIFICATION_COMPLETED_STATUS
            request.save()
            # TODO: include an HTML version of the email
            #mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message)

    except Exception as exc:
        logger.exception("Download request completed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.request_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.package_retry_count = request.notify_retry_count + 1 
            request.save()
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.request_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save()

@shared_task(bind=True)
def notifyPermanentFailedRequest(self, request_id):
    try:
        request = DownloadRequest.objects.get(pk=request_id)
        with override(get_language(request)):
            subject = _('Download service: your request has failed - %(requestid)s') % {'requestid': request.request_random_id}
            plain_message = _('Sorry, your download request could not be completed. Please, try again or contact the service support.')
            # html_message = render_to_string('mail_template.html', {'context': 'values'})
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                to = request.requested_by_user
            else:
                to = request.requested_by_external
            try:
                from_email =  settings.EMAIL_HOST_USER
            except:
                logger.exception("EMAIL_HOST_USER has not been configured")
                raise
            mail.send_mail(subject, plain_message, from_email, [to])
            # TODO: include an HTML version of the email
            #mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message)

    except Exception as exc:
        logger.exception("Download request failed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.package_retry_count = request.notify_retry_count + 1
            request.notification_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.save()
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached, don't retry again
            request.notification_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save()

            pass


@shared_task(bind=True)
def processDownloadRequest(self, request_id):
    logger.debug("starting processDownloadRequest")
    # 1 get request
    try:
        request = DownloadRequest.objects.get(id=request_id)
        if request.request_status != DownloadRequest.REQUEST_QUEUED_STATUS:
            logger.debug("Task already processed: " + request_id)
            return
        
        request.request_status = DownloadRequest.PROCESSING_STATUS
        request.save()
        
        # 2 classify resources
        locators = request.resourcelocator_set.all()
        processed_locators = 0
        total_locators = 0
        errors = 0
        for resourceLocator in locators:
            total_locators += 1
            try:
                new_link = resolveLocator(resourceLocator, request)
                if new_link:
                    processed_locators += 1
            except:
                logger.exception("Error resolving locator")
                errors += 1
        if total_locators == processed_locators:
            request.request_status = DownloadRequest.COMPLETED_STATUS
            request.save()
        elif errors > 0:
            request.request_status = DownloadRequest.COMPLETED_WITH_ERRORS
            request.save()
        notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
        
        """
        # 2 package
        link_uuid = date.today().strftime("%Y%m%d") + get_random_string(length=32)
        zip_path = packageRequest(request, link_uuid)
        if zip_path:
            # 3. create the link
            new_link = DownloadLink()
            new_link.contents = request
            new_link.valid_to = datetime.utcnow() + timedelta(seconds = request.validity)
            new_link.link_random_id = link_uuid
            new_link.prepared_download_path = zip_path
            new_link.save()
            
            request.request_status = DownloadRequest.COMPLETED_STATUSf                
            request.save()
            # 4. notify: send the link to the user
            notifyCompletedRequest.apply_async(args=[new_link.pk], queue='notify')
            print "done"
        """
    except Exception as exc:
        logger.exception("error preparing download request")
        """
        print "error preparing download request"
        delay = getNextPackagingRetryDelay(request)
        if delay:
            request.request_status = DownloadRequest.PACKAGING_ERROR_STATUS
            request.package_retry_count = request.package_retry_count + 1 
            request.save()
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.request_status = DownloadRequest.PERMANENT_PACKAGE_ERROR_STATUS
            request.save()
            notifyPermanentFailedRequest.apply_async(args=[new_link.id], queue='notify')
        """

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    sender.add_periodic_task(CLEAN_TASK_FREQUENCY, cleanOutdatedRequests.s(), options={'queue' : 'gvsigolperiodic'})

@task(bind=True)
def cleanOutdatedRequests(self):
    for root, dirs, files in os.walk(getTargetDir()):
        for f in files:
            fullpath = os.path.join(root, f)
            link_uuid = ''
            try:
                link_uuid = _parseLinkUiid(f)
                link = DownloadLink.objects.get(link_random_id=link_uuid)
                if fullpath != link.prepared_download_path:
                    raise Error
                if timezone.now() > link.valid_to:
                    # request is oudated
                    os.remove(link.prepared_download_path)
                else:
                    for resource in link.resourcelocator_set.all():
                        if resource.status == ResourceLocator.CANCELLED_STATUS or resource.status == ResourceLocator.REJECTED_STATUS:
                            # for some status value such as cancelled, we should also remove the file
                            os.remove(link.prepared_download_path)
                            break
            except:
                try:
                    logger.exception(u"error getting link: " + fullpath + u" - " + link_uuid)
                    # if older than UNKNOWN_FILES_MAX_AGE days, remove the file
                    modified_time = os.path.getmtime(fullpath)
                    if date.fromtimestamp(modified_time) < (date.today() - timedelta(days=UNKNOWN_FILES_MAX_AGE)):
                        os.remove(fullpath)
                except:
                    logger.exception("Error cleaning request package")
            