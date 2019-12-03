# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
from builtins import str as text

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
from celery.exceptions import Retry
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
from django.utils.translation import override
from django.core.urlresolvers import reverse
from django.utils.formats import date_format
from django.utils import timezone
from gvsigol import settings as core_settings
import re
from django.utils.translation import ugettext as _
from django.utils.crypto import get_random_string

from gvsigol_plugin_downloadman.utils import getLayer

import shutil
from gvsigol.celery import app as celery_app
from django.contrib.auth.models import User
from django.db.models import Q
from collections import namedtuple

from gvsigol_plugin_downloadman.settings import TMP_DIR,TARGET_ROOT
from gvsigol_plugin_downloadman.settings import DOWNLOADS_URL

try:
    from gvsigol.settings import GVSIGOL_NAME
except:
    GVSIGOL_NAME = 'gvsigol'
try:
    from gvsigol_plugin_downloadman.settings import LOCAL_PATHS_WHITELIST
except:
    LOCAL_PATHS_WHITELIST = []


#logger = logging.getLogger("gvsigol-celery")
logger = logging.getLogger("gvsigol")


__TMP_DIR = None
__TARGET_ROOT = None
LINK_UUID_RANDOM_LENGTH = 32 
LINK_UUID_FULL_LENGTH = 40

try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_DEFAULT_TIMEOUT as DEFAULT_TIMEOUT #@UnresolvedImport
except:
    DEFAULT_TIMEOUT = 900

try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_UNKNOWN_FILES_MAX_AGE as UNKNOWN_FILES_MAX_AGE #@UnresolvedImport
except:
    UNKNOWN_FILES_MAX_AGE = 20 # days

try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_MIN_TARGET_SPACE as MIN_TARGET_SPACE #@UnresolvedImport
except:
    MIN_TARGET_SPACE = 209715200 # bytes == 200 MB

try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_MIN_TMP_SPACE as MIN_TMP_SPACE #@UnresolvedImport
except:
    MIN_TMP_SPACE = 104857600 # bytes == 100 MB
    
try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_FREE_SPACE_RETRY_DELAY as FREE_SPACE_RETRY_DELAY #@UnresolvedImport
except:
    FREE_SPACE_RETRY_DELAY = 60 # seconds == 1 minute
    
try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_CLEAN_TASK_FREQUENCY as CLEAN_TASK_FREQUENCY #@UnresolvedImport
except:
    CLEAN_TASK_FREQUENCY = 1200.0 # seconds == 20 minutes

# valid values:
# - NEVER: a direct link will always be returned, even for non-static URLs (e.g WFS and WCS requests)
# - DYNAMIC [Not implemented yet]: dynamic links (e.g. WFS and WCS requests) will be async processed and packaged
try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_PACKAGING_BEHAVIOUR
except:
    DOWNMAN_PACKAGING_BEHAVIOUR = 'NEVER'


try:
    from gvsigol_plugin_downloadman.settings import DOWNMAN_XSEND_BASEURL as XSEND_BASEURL #@UnresolvedImport
except:
    XSEND_BASEURL = ''


class Error(Exception):
    def __init__(self, message=None):
        super(Error, self).__init__(message)

class PreparationError(Exception):
    def __init__(self, message=None):
        super(PreparationError, self).__init__(message)

class PermanentPreparationError(Exception):
    def __init__(self, message=None):
        super(PermanentPreparationError, self).__init__(message)

class ForbiddenAccessError(Exception):
    def __init__(self, message=None):
        super(ForbiddenAccessError, self).__init__(message)

def getDownloadResourceUrl(request_random_id, link_random_id):
    """
    We check if we need to map the "normal" URL to a special URL in a 
    different domain or path. This mapping is sometimes used to set
    maximum download transfer rates or faster routes.
    """
    if XSEND_BASEURL:
        url = reverse('downman-download-resource', args=(request_random_id, link_random_id))
        urlParts = url.split("/")
        if len(urlParts)>1:
            app_name = urlParts[1]
        return XSEND_BASEURL + url[len(app_name)+1:]
    else:
        return core_settings.BASE_URL + reverse('downman-download-resource', args=(request_random_id, link_random_id))

def getFreeSpace(path):
    try:
        logger.debug(u"getFreeSpace path: "+path)
        usage  = os.statvfs(path)
        return (usage.f_frsize * usage.f_bfree)
    except OSError:
        logger.exception(u"Error getting free space for path: " + path)
        return 0
    except AttributeError: # Python 3
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

def checkCatalogPermissions(metadata_uuid, res_type, url):
    logger.debug("checkCatalogPermissions start")
    try:
        import gvsigol_plugin_catalog.service as geonetwork_service
        geonetwork_instance = geonetwork_service.get_instance()
        onlineResources = geonetwork_instance.get_online_resources(metadata_uuid)
        protocol = None
        if res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE:
            protocol = 'OGC:WFS'
        elif res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE:
            protocol = 'OGC:WCS'
        if protocol:
            for onlineResource in onlineResources:
                resource = None
                if protocol in onlineResource.protocol:
                    if url == onlineResource.url:
                        logger.debug(u"permissions OK - " + metadata_uuid + u" - " + res_type)
                        return
        elif res_type == ResourceLocator.HTTP_LINK_RESOURCE_TYPE:
            for onlineResource in onlineResources:
                if (onlineResource.protocol.startswith('WWW:DOWNLOAD-') and onlineResource.protocol.endswith('-download')) \
                        or (onlineResource.protocol.startswith('WWW:LINK-') and onlineResource.protocol.endswith('-link')) \
                        or onlineResource.protocol.startswith('FILE:'):
                    if url == onlineResource.url:
                        logger.debug(u"permissions OK - " + metadata_uuid + u" - " + res_type)
                        return
    except requests.exceptions.RequestException:
        logger.exception("Error connecting to the catalog")
        raise PreparationError("Error connecting to catalog")
    except:
        logger.exception("Could not check metadata permissions")
    raise PermanentPreparationError("Catalog permissions check failed")

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

def retrieveLinkLocator(url):
    # TODO: authentication and permissions
    GVSIGOL_NAME.lower()
    (fd, tmp_path) = tempfile.mkstemp('.tmp', GVSIGOL_NAME.lower()+"dm", dir=getTmpDir())
    tmp_file = os.fdopen(fd, "wb")
    
    r = requests.get(url, stream=True, verify=False, timeout=DEFAULT_TIMEOUT)
    for chunk in r.iter_content(chunk_size=128):
        tmp_file.write(chunk)
    tmp_file.close()
    return tmp_path

def resolveFileUrl(url):
    local_path = url[7:]
    if not local_path.startswith("/"):
        local_path = "/" + local_path
    # remove any "../.."
    local_path = os.path.abspath(local_path)
    # we only allow local paths that are subfolders of the paths defined in LOCAL_PATHS_WHITELIST variable
    for path in LOCAL_PATHS_WHITELIST:
        if local_path.startswith(path):
            return local_path
    raise ForbiddenAccessError

def resolveLocator(resourceLocator, resource_descriptor):
    """
    Parses the resourceLocator to translate the locator on a concrete URL or local file.
    If the resource described by the locator is static (does not require processing)
    a DownloadLink is also created.
    """
    res_type = resource_descriptor.get('resource_type')
    res_id = resource_descriptor.get('layer_id')
    resource_name = resource_descriptor.get('name', '')

    resource_url = resource_descriptor.get('url')
    params = resource_descriptor.get('params', [])

    if resourceLocator.layer_id_type == ResourceLocator.GEONETWORK_UUID:
        checkCatalogPermissions(res_id, res_type, resource_url)
        (resourceLocator.resolved_url, resourceLocator.is_dynamic) = getCatalogResourceURL(res_type, resource_name, resource_url, params)
    elif resourceLocator.layer_id_type == ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE:
        layer = getLayer(resourceLocator.layer_id)
        (resourceLocator.resolved_url, resourceLocator.is_dynamic) = getGvsigolResourceURL(res_type, layer, params)
    
    if not resourceLocator.resolved_url:
        raise PermanentPreparationError(u"Url could not be resolved for resource locator: " + text(resourceLocator.pk))

def retrieveResource(url, resource_descriptor):
    """
    Returns the resource pointed by the resourceLocator as a local file path,
    wrapped in a ResourceDescription object.
    If the resource is a remote resource, it is first copied as a local file. 
    """
    resource_name = resource_descriptor.get('name')

    params = resource_descriptor.get('params', [])
    file_format = _getParamValue(params, FORMAT_PARAM_NAME)
    # remove non-a-z_ or numeric characters
    resource_name = resource_name.replace(":", "_")
    resource_name = re.sub('[^\w\s_-]', '', resource_name).strip().lower()
    resource_name = resource_name + _getExtension(file_format)
    if (url.startswith("http://") or url.startswith("https://")):
        local_path = retrieveLinkLocator(url)
        return [ResourceDescription(resource_name, local_path, True)]
    if url.startswith("file://"):
        local_path = resolveFileUrl(url)
        if url.endswith("/"):
            return [ResourceDescription(resource_name, local_path)] 
        else:
            return [ResourceDescription(os.path.basename(url), local_path)]
    # TODO: error management
    return []

def _addResource(zipobj, resource_descriptor, resolved_url):
    resourceDescList = retrieveResource(resolved_url, resource_descriptor)
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
            tracking_url = core_settings.BASE_URL + reverse('download-request-tracking', args=(request.request_random_id,))
            subject = _('Download service: your request has been received - %(requestid)s') % {'requestid': request.request_random_id}
            statusdetails = _(u'\nYou can use this tracking link to check the status of your request: {0}').format(tracking_url)
            htmlContext = {
                u"statusdesc": subject,
                u"statusdetails": statusdetails,
                u'locators': []
                }
            plain_message = _(u'Your download request has been received.')
            plain_message += '\n' + statusdetails + '\n'
            plain_message += '\n' + _('Included resources:')
            for locator in request.resourcelocator_set.all():
                plain_message += u' - {0!s} [{1!s}]\n'.format(locator.fq_title, locator.name)
                htmlContext['locators'].append({'name': '{0!s} [{1!s}]\n'.format(locator.fq_title, locator.name),
                                                'status': _(locator.get_status_description())})
                
            html_message = render_to_string('request_received_email.html', htmlContext)
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                user = User.objects.get(username=request.requested_by_user)
                to = user.email
            else:
                to = request.requested_by_external
            try:
                from_email =  core_settings.EMAIL_HOST_USER
            except:
                logger.exception("EMAIL_HOST_USER has not been configured")
                raise
            mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message)
            request.notification_status = DownloadRequest.INITIAL_NOTIFICATION_COMPLETED_STATUS
            request.save()

    except Exception as exc:
        logger.exception("Download request completed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.notification_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.package_retry_count = request.notify_retry_count + 1 
            request.save()
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.notification_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save()

@shared_task(bind=True)
def notifyRequestProgress(self, request_id):
    try:
        logger.debug("starting notify task completed")
        try:
            from_email =  core_settings.EMAIL_HOST_USER
        except:
            logger.exception("EMAIL_HOST_USER has not been configured")
            raise
        request = DownloadRequest.objects.get(pk=request_id)
        with override(get_language(request)):
            tracking_url = core_settings.BASE_URL + reverse('download-request-tracking', args=(request.request_random_id,))
            if request.request_status == DownloadRequest.COMPLETED_STATUS:
                subject = _('Download service: your request is ready - %(requestid)s') % {'requestid': request.request_random_id}
                statusdetails = _(u'Your download request is ready.')
            elif request.request_status == DownloadRequest.COMPLETED_WITH_ERRORS:
                subject = _('Download service: your request is ready - %(requestid)s') % {'requestid': request.request_random_id}
                statusdetails = _(u'Your download request is ready. Some resources failed to be processed and are not available for download at the moment.')
            else:
                subject = _('Download service: request progress - %(requestid)s') % {'requestid': request.request_random_id}
                statusdetails = _(u'Your download request has been partially processed.')
            
            plain_message = statusdetails + '\n'
            plain_message +=  _('You can use the following links to download the requested resources:') + '\n'
            
            htmlContext = {
                u"statusdesc": _(u'Download service: request progress - {0}').format(request.request_random_id),
                u"statusdetails": statusdetails,
                }

            count = 1
            links = []
            for link in request.downloadlink_set.all():
                linkHtmlContext = {}
                link_url = getDownloadResourceUrl(request.request_random_id, link.link_random_id)
                logger.debug(link_url)
                valid_to = date_format(link.valid_to, 'DATETIME_FORMAT')
                link.save()
                linkResources = link.resourcelocator_set.all()
                if len(linkResources)==1:
                    plain_message += u' {0:2d}- {1!s} [{2!s}]: {3!s}\n'.format(count, linkResources[0].fq_title, linkResources[0].name, link_url)
                    linkHtmlContext['name'] = u'{0!s} [{0!s}]'.format(linkResources[0].fq_title, linkResources[0].name)
                    linkHtmlContext['url'] = link_url
                else:
                    plain_message += u' {0:2d}- {1!s}: {2!s}\n'.format(count, _('Multiresource package'), link_url)
                    plain_message += _(u'    -- Link valid until {0!s}:\n').format(valid_to)
                    plain_message += _(u'    -- Contents:')
                    linkHtmlContext['name'] = _('Multiresource package')
                    linkHtmlContext['url'] = link_url
                    linkHtmlContext['validto'] = valid_to
                    linkHtmlContext['locators'] = []
                    for linkResource in linkResources:
                        plain_message += _(u'     -- {0!s} [{1!s}]\n').format(linkResource.fq_title, linkResource.name)
                        linkHtmlContext['locators'].append({'name': _(u'{0!s} [{1!s}]\n').format(linkResource.fq_title, linkResource.name)})
                count += 1
                links.append(linkHtmlContext)
            htmlContext['links'] = links
            locators =  request.resourcelocator_set.filter(download_link__isnull=True).exclude(status=ResourceLocator.PERMANENT_ERROR_STATUS)
            if len(locators)>0:
                htmlContext['pendinglocators'] = []
                plain_message += '\n' + _('The following resources are still being processed:') + '\n'
                for locator in locators:
                    plain_message += u' - {0!s} [{1!s}]\n'.format(locator.fq_title, locator.name)
                    plain_message += (u'   -- ' + _('Status:') + '{0!s}\n').format(_(locator.get_status_description()))
                    htmlContext['pendinglocators'].append({'name': '{0!s} [{1!s}]\n'.format(locator.fq_title, locator.name),
                                                           'status': _(locator.get_status_description())})
            locators =  request.resourcelocator_set.filter(download_link__isnull=True).filter(status=ResourceLocator.PERMANENT_ERROR_STATUS)
            if len(locators)>0:
                htmlContext['failedlocators'] = []
                plain_message += '\n' + _("The following resources could not be processed:") + '\n'
                for locator in locators:
                    plain_message += u' - {0!s} [{1!s}]\n'.format(locator.fq_title, locator.name)
                    plain_message += (u'   -- ' + _('Status:') + '{0!s}\n').format(_(locator.get_status_description()))
                    htmlContext['failedlocators'].append({'name': '{0!s} [{1!s}]\n'.format(locator.fq_title, locator.name),
                                                           'status': _(locator.get_status_description())})
            plain_message += u'\n' + _(u'You can also use this tracking link to check the status of your request:') + u' ' + tracking_url + u'\n'
            htmlContext['request_url'] = tracking_url
            html_message = render_to_string('progress_notif_email.html', context=htmlContext)
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                user = User.objects.get(username=request.requested_by_user)
                to = user.email
            else:
                to = request.requested_by_external
            logger.debug(u"mailing: " + to)
            #mail.send_mail(subject, plain_message, from_email, [to])
            mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message)
            request.notification_status = DownloadRequest.NOTIFICATION_COMPLETED_STATUS
            request.save()

    except Exception as exc:
        logger.exception("Download request completed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.notification_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.package_retry_count = request.notify_retry_count + 1 
            request.save()
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.notification_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save()

def processLocators(request, zipobj=None, zip_path=None):
    logger.debug('processLocators')
    locators = request.resourcelocator_set.filter((Q(status=ResourceLocator.RESOURCE_QUEUED_STATUS) | \
                                                   Q(status=ResourceLocator.HOLD_STATUS) | \
                                                   Q(status=ResourceLocator.WAITING_SPACE_STATUS) | \
                                                   Q(status=ResourceLocator.TEMPORAL_ERROR_STATUS)) & \
                                                   (Q(authorization=ResourceLocator.AUTHORIZATION_ACCEPTED) | \
                                                   Q(authorization=ResourceLocator.AUTHORIZATION_NOT_REQUIRED)))
            
    temporal_errors = 0
    permanent_errors = 0
    packaged_locators = []
    completed_locators = 0
    to_package = 0
    waiting_space = 0
    ResultTuple = namedtuple('ResultTuple', ['completed', 'packaged', 'waiting_space', 'to_package', 'temporal_error', 'permanent_error'])
    for resourceLocator in locators:
        try:
            if resourceLocator.status == ResourceLocator.HOLD_STATUS:
                continue

            resource_descriptor = json.loads(resourceLocator.data_source)
            if not resourceLocator.resolved_url:
                resolveLocator(resourceLocator, resource_descriptor)
            if DOWNMAN_PACKAGING_BEHAVIOUR == 'ALL' or \
                (resourceLocator.is_dynamic and DOWNMAN_PACKAGING_BEHAVIOUR == 'DYNAMIC'):
                if zipobj is not None:
                    if getFreeSpace(getTmpDir()) < MIN_TMP_SPACE:
                        waiting_space += 1
                        resourceLocator.status = ResourceLocator.WAITING_SPACE_STATUS
                    else:
                        # ensure the locator has not been cancelled before starting packaging
                        resourceLocator.refresh_from_db(fields=['canceled'])
                        if resourceLocator.canceled:
                            continue
                        _addResource(zipobj, resource_descriptor, resourceLocator.resolved_url)
                        packaged_locators.append(resourceLocator)
                        completed_locators += 1
                else:
                    to_package += 1
            else:
                # store a direct download link instead of packaging the resource
                new_link = createDownloadLink(request, resourceLocator)
                resourceLocator.download_link = new_link
                resourceLocator.status = ResourceLocator.PROCESSED_STATUS
                completed_locators += 1
            resourceLocator.save()
        except PermanentPreparationError:
            logger.exception("Error resolving locator")
            resourceLocator.status = ResourceLocator.PERMANENT_ERROR_STATUS
            resourceLocator.save()
            permanent_errors += 1
        except: # PreparationError or any other error
            # TODO
            logger.exception("Error resolving locator")
            resourceLocator.status = ResourceLocator.TEMPORAL_ERROR_STATUS
            resourceLocator.save()
            temporal_errors += 1

    if len(packaged_locators) > 0:
        new_link = createDownloadLink(request, resourceLocator, zip_path)
        for resourceLocator in packaged_locators:
            # we need to ensure that locators have not been cancelled while we were processing
            resourceLocator.refresh_from_db(fields=['status'])
            resourceLocator.status = ResourceLocator.PROCESSED_STATUS
            resourceLocator.download_link = new_link
            resourceLocator.save()
        
        # Finally, we need to ensure that locators have not been cancelled while we were processing
        new_link.refresh_from_db()
        locators = new_link.resourcelocator_set.all()
        cancel_link = False
        for resourceLocator in locators:
            #if any of the locators has been cancelled, we need to cancel the link and process again the locators
            if resourceLocator.canceled:
                cancel_link = True
        if cancel_link:
            for resourceLocator in locators:
                #if any of the locators has been cancelled, we need to cancel the link and process again the locators
                if not resourceLocator.canceled and resourceLocator.status == ResourceLocator.PROCESSED_STATUS:
                     resourceLocator.status = ResourceLocator.RESOURCE_QUEUED_STATUS
                     resourceLocator.save()
                new_link.status = DownloadLink.ADMIN_CANCELED_STATUS
                new_link.save()
            return processLocators(request, zipobj, zip_path)
        

    return ResultTuple(completed_locators, len(packaged_locators), waiting_space, to_package, temporal_errors, permanent_errors)

def createDownloadLink(downloadRequest, resourceLocator, prepared_download_path=None):
    try:
        new_link = DownloadLink()
        new_link.request = downloadRequest
        link_uuid = date.today().strftime("%Y%m%d") + get_random_string(length=32)
        new_link.valid_to = timezone.now() + timedelta(seconds = downloadRequest.validity)
        new_link.link_random_id = link_uuid
        if prepared_download_path:
            new_link.prepared_download_path = prepared_download_path
        elif resourceLocator.resolved_url.startswith("file://"):
            if resourceLocator.resolved_url.endswith("/"):
                new_link.prepared_download_path = resolveFileUrl(resourceLocator.resolved_url)
            else:
                new_link.prepared_download_path = resolveFileUrl(resourceLocator.resolved_url)
        new_link.save()
        return new_link
    except ForbiddenAccessError:
        raise PermanentPreparationError()

@shared_task(bind=True)
def packageRequest(self, request_id):
    logger.debug('packageRequest')
    request = DownloadRequest.objects.get(id=request_id)
    if (request.request_status != DownloadRequest.REQUEST_QUEUED_STATUS) and (request.request_status != DownloadRequest.PROCESSING_STATUS):
        logger.debug("Task already processed: " + request_id)
        return
    result = None
    zip_file = None
    try:
        if getFreeSpace(getTargetDir()) < MIN_TARGET_SPACE:
            logger.debug("Scheduling a retry due to not enough space error")
            self.retry(countdown=FREE_SPACE_RETRY_DELAY)
            
        link_uuid = date.today().strftime("%Y%m%d") + get_random_string(length=32)
        
        # 1. create target zip file
        prefix = _getPackagePrefix() + link_uuid + "_"
        (fd, zip_path) = tempfile.mkstemp('.zip', prefix, getTargetDir())
        zip_file = os.fdopen(fd, "w")
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipobj:
            result = processLocators(request, zipobj, zip_path)
        zip_file.close()
        os.chmod(zip_path, 0o444)
        
        if result.packaged == 0:
            os.remove(zip_path)
    except:
        logger.exception("error packaging request")
        
        try:
            if zip_file:
                zip_file.close()
                os.remove(zip_path)
        except:
            logger.exception("error handling packaging error")
    if not result:
        delay = getNextPackagingRetryDelay(request)
        if delay:
            request.package_retry_count = request.package_retry_count + 1 
            request.save()
            self.retry(countdown=delay)
    if result.waiting_space > 0:
        delay = getNextPackagingRetryDelay(request)
        if delay:
            if result.completed > 0:
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
            # we retry forever if the problem is a lack of space
            self.retry(countdown=FREE_SPACE_RETRY_DELAY)
        else:
            pass
    elif result.temporal_error > 0:
        delay = getNextPackagingRetryDelay(request)
        if delay:
            request.package_retry_count = request.package_retry_count + 1 
            request.save()
            if result.completed > 0:
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
            self.retry(countdown=delay)

    # if there are no locators waiting for admin feedback and we reach the maximum amount of retries,
    # then we need to update locators and request status
    waiting_feedback = request.resourcelocator_set.filter( \
                                                  Q(authorization=ResourceLocator.AUTHORIZATION_PENDING) | \
                                                  Q(status=ResourceLocator.HOLD_STATUS)).count()
    if waiting_feedback == 0:
        errors = 0
        locators = ( request.resourcelocator_set.filter(status=ResourceLocator.TEMPORAL_ERROR_STATUS) | \
                     request.resourcelocator_set.filter(status=ResourceLocator.PERMANENT_ERROR_STATUS) | \
                     request.resourcelocator_set.filter(status=ResourceLocator.RESOURCE_QUEUED_STATUS))
        for locator in locators:
            errors += 1
            if locator.status != ResourceLocator.PERMANENT_ERROR_STATUS:
                locator.status = ResourceLocator.PERMANENT_ERROR_STATUS
                locator.save()
            
        if errors > 0:
            request.request_status = DownloadRequest.COMPLETED_WITH_ERRORS
            request.save()
            notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
        else:
            request.request_status = DownloadRequest.COMPLETED_STATUS
            request.save()
            notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
    elif result and result.completed > 0:
        notifyRequestProgress.apply_async(args=[request.pk], queue='notify')

@shared_task(bind=True)
def processDownloadRequest(self, request_id):
    logger.debug("starting processDownloadRequest")
    result = None
    # 1 get request
    try:
        request = DownloadRequest.objects.get(id=request_id)
        if (request.request_status != DownloadRequest.REQUEST_QUEUED_STATUS) and (request.request_status != DownloadRequest.PROCESSING_STATUS):
            logger.debug("Task already processed: " + request_id)
            return
        
        request.request_status = DownloadRequest.PROCESSING_STATUS
        request.save()
        
        result = processLocators(request)
        logger.debug(result)
    except Exception:
        logger.exception("error preparing download request")
    
    try:
        if not result:
            delay = getNextPackagingRetryDelay(request)
            if delay:
                request.package_retry_count = request.package_retry_count + 1 
                request.save()
                if result.completed > 0:
                    notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
                self.retry(countdown=delay)
    
        if result.to_package > 0:
            notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
            packageRequest.apply_async(args=[request.pk], queue='package')
            return
        if result.temporal_error > 0:
            delay = getNextPackagingRetryDelay(request)
            if delay:
                request.package_retry_count = request.package_retry_count + 1 
                request.save()
                if result.completed > 0:
                    notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
                self.retry(countdown=delay)
    except Retry:
        logger.debug("raising retry")
        raise
    except:
        logger.exception("error cmi 02")

    # if there are no locators waiting for admin feedback and we reach the maximum amount of retries,
    # then we need to update locators and request status
    try:
        waiting_feedback = request.resourcelocator_set.filter( \
                                                      Q(authorization=ResourceLocator.AUTHORIZATION_PENDING) | \
                                                      Q(status=ResourceLocator.HOLD_STATUS)).count()
        if waiting_feedback == 0:
            errors = 0
            locators = ( request.resourcelocator_set.filter(status=ResourceLocator.TEMPORAL_ERROR_STATUS) | \
                         request.resourcelocator_set.filter(status=ResourceLocator.PERMANENT_ERROR_STATUS) | \
                         request.resourcelocator_set.filter(status=ResourceLocator.RESOURCE_QUEUED_STATUS))
            for locator in locators:
                errors += 1
                if locator.status != ResourceLocator.PERMANENT_ERROR_STATUS:
                    locator.status = ResourceLocator.PERMANENT_ERROR_STATUS
                    locator.save()
                
            if errors > 0:
                request.request_status = DownloadRequest.COMPLETED_WITH_ERRORS
                request.save()
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
            else:
                request.request_status = DownloadRequest.COMPLETED_STATUS
                request.save()
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
        elif result and result.completed > 0:
            notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
    except:
        logger.exception("Error cmi")

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
                if not link.is_valid:
                    # request is oudated
                    os.remove(link.prepared_download_path)
                else:
                    for resource in link.resourcelocator_set.all():
                        if resource.canceled:
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
            