# -*- coding: utf-8 -*-

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
from celery.utils.log import get_task_logger
from gvsigol_plugin_downloadman.models import DownloadRequest, DownloadLink, ResourceLocator
from gvsigol_plugin_downloadman.models import get_packaging_max_retry_time, get_mail_max_retry_time, get_max_public_download_size, get_notifications_admin_emails, get_notifications_from_email, get_notifications_from_pass
from datetime import date, timedelta, datetime

import os, glob
import tempfile
import zipfile
import requests
import logging
from gvsigol_plugin_downloadman.models import FORMAT_PARAM_NAME, SPATIAL_FILTER_GEOM_PARAM_NAME, SPATIAL_FILTER_TYPE_PARAM_NAME, SPATIAL_FILTER_BBOX_PARAM_NAME
import json
from django.core import mail
from django.template.loader import render_to_string
from django.utils.translation import override
from django.urls import reverse
from django.utils.formats import date_format
from django.utils import timezone
from gvsigol import settings as core_settings
import re
from numpy import genfromtxt
from django.utils.translation import ugettext as _
from django.utils.crypto import get_random_string

from gvsigol_plugin_downloadman.utils import getLayer

import shutil
from gvsigol.celery import app as celery_app
from django.contrib.auth.models import User
from django.db.models import Q
from collections import namedtuple
from lxml import etree as ET
import email

from gvsigol_plugin_downloadman.settings import TMP_DIR,TARGET_ROOT
from gvsigol_plugin_downloadman.settings import DOWNLOADS_URL
from django.contrib.gis.gdal import SpatialReference, CoordTransform, OGRGeometry
import gdaltools
import sys
from io import StringIO
try:
    from gvsigol.settings import PROXIES
except:
    PROXIES = {}

try:
    from gvsigol.settings import GVSIGOL_NAME
except:
    GVSIGOL_NAME = 'gvsigol'
try:
    from gvsigol_plugin_downloadman.settings import LOCAL_PATHS_WHITELIST
except:
    LOCAL_PATHS_WHITELIST = []


#logger = logging.getLogger("gvsigol-celery")
#logger = get_task_loggerlogging.getLogger("gvsigol")
logger = get_task_logger(__name__)


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
# - DYNAMIC: dynamic links (e.g. WFS and WCS requests) will be async processed and packaged
# - ALL: all the downloads will be async processed and packaged
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
        logger.debug("getFreeSpace path: "+path)
        usage  = os.statvfs(path)
        return (usage.f_frsize * usage.f_bfree)
    except OSError:
        logger.exception("Error getting free space for path: " + path)
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
    if __TMP_DIR is None:
        try:
            if not os.path.exists(TMP_DIR):
                os.makedirs(TMP_DIR, 0o700)
        except:
            pass
        __TMP_DIR = TMP_DIR
    return __TMP_DIR

def getTargetDir():
    global __TARGET_ROOT
    if __TARGET_ROOT is None:
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
        
def _getParamValue(params, name, default_value=None):
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

INVERSE_AXIS_CRS_LIST = None
def _getCrsReverseAxisList():
    global INVERSE_AXIS_CRS_LIST
    if INVERSE_AXIS_CRS_LIST is None:
        INVERSE_AXIS_CRS_LIST = genfromtxt(os.path.join(core_settings.BASE_DIR, 'gvsigol_core/static/crs_axis_order/mapaxisorder.csv'), skip_header=1)
    return INVERSE_AXIS_CRS_LIST

def reprojectExtent(xmin, ymin, xmax, ymax, sourceCrs, targetCrs):
    try:
        if sourceCrs != targetCrs:
            sourceCrsOgr = SpatialReference(sourceCrs)
            targetCrsOgr = SpatialReference(targetCrs)
            coordTransform = CoordTransform(sourceCrsOgr, targetCrsOgr)
            ogrExtentPolygon = OGRGeometry.from_bbox((xmin, ymin, xmax, ymax))
            ogrExtentPolygon.transform(coordTransform)
            # extent tuple: xmin, ymin, xmax, ymax
            return ogrExtentPolygon.extent
    except:
        logger.exception('Error reprojecting extent')
        raise

def isRestricted(onlineResource, max_public_size):
    if onlineResource.app_profile.startswith("gvsigol:download:restricted"):
        return True
    if onlineResource.transfer_size is not None and onlineResource.transfer_size > max_public_size:
        return True
    return False

def getMetadataUuid(layer_id):
    try:
        from gvsigol_plugin_catalog.models import LayerMetadata 
        theId = int(layer_id)
        lm = LayerMetadata.objects.get(id=theId)
        return lm.uuid
    except:
        return layer_id

def getRawMetadata(layer_id):
    metadata_uuid = getMetadataUuid(layer_id)
    if metadata_uuid:
        try:
            import gvsigol_plugin_catalog.service as geonetwork_service
            geonetwork_instance = geonetwork_service.get_instance()
            return geonetwork_instance.get_metadata_raw(metadata_uuid)
        except:
            pass

def getRawMetadataUrl(layer_id):
    metadata_uuid = getMetadataUuid(layer_id)
    if metadata_uuid:
        try:
            import gvsigol_plugin_catalog.service as geonetwork_service
            geonetwork_instance = geonetwork_service.get_instance()
            return geonetwork_instance.get_raw_metadata_url(metadata_uuid)
        except:
            pass

def checkCatalogPermissions(metadata_uuid, res_type, url):
    try:
        xml_md = getRawMetadata(metadata_uuid)
        from gvsigol_plugin_catalog.mdstandards import registry
        reader = registry.get_reader(xml_md)
        onlineResources = reader.get_transfer_options()
        max_public_size = float(get_max_public_download_size())

        #onlineResources = geonetwork_instance.get_online_resources(metadata_uuid)
        protocol = None
        if res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE:
            protocol = 'OGC:WFS'
        elif res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE:
            protocol = 'OGC:WCS'
        if protocol:
            for onlineResource in onlineResources:
                if protocol in onlineResource.protocol:
                    if url == onlineResource.url:
                        logger.debug("permissions OK - " + metadata_uuid + " - " + res_type)
                        return isRestricted(onlineResource, max_public_size)
        elif res_type == ResourceLocator.HTTP_LINK_RESOURCE_TYPE:
            for onlineResource in onlineResources:
                if (onlineResource.protocol.startswith('WWW:DOWNLOAD-') and onlineResource.protocol.endswith('-download')) \
                        or (onlineResource.protocol.startswith('WWW:LINK-') and onlineResource.protocol.endswith('-link')) \
                        or onlineResource.protocol.startswith('FILE:'):
                    if url == onlineResource.url:
                        logger.debug("permissions OK - " + metadata_uuid + " - " + res_type)
                        return isRestricted(onlineResource, max_public_size)
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
        return (resource_url, True)
    elif res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE:
        return (resource_url, True)
    return (None, False)

def getGvsigolResourceURL(res_type, layer, params):
    if layer:
        if res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE and layer.datastore.workspace.wfs_endpoint:
            baseUrl = layer.datastore.workspace.wfs_endpoint
            return (baseUrl, True)
        elif res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE and layer.datastore.workspace.wcs_endpoint:
            baseUrl = layer.datastore.workspace.wcs_endpoint
            return (baseUrl, True)
    return (None, False)

def retrieveLinkLocator(url):
    # TODO: authentication and permissions
    GVSIGOL_NAME.lower()
    (fd, tmp_path) = tempfile.mkstemp('.tmp', GVSIGOL_NAME.lower()+"dm", dir=getTmpDir())
    tmp_file = os.fdopen(fd, "wb")
    try:
        r = requests.get(url, stream=True, verify=False, timeout=DEFAULT_TIMEOUT, proxies=PROXIES)
        if r.status_code != 200:
            tmp_file.close()
            raise PreparationError('Error retrieving link. HTTP status code: '+text(r.status_code) + ". Url: " + url)
        for chunk in r.iter_content(chunk_size=128):
            tmp_file.write(chunk)
        tmp_file.close()
    except PreparationError:
        raise
    except:
        logger.exception('error retrieving link: ' + url)
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
    raise ForbiddenAccessError(url)

def preprocessLocator(resourceLocator, resource_descriptor):
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
        restricted = checkCatalogPermissions(res_id, res_type, resource_url)
        (resourceLocator.resolved_url, resourceLocator.is_dynamic) = getCatalogResourceURL(res_type, resource_name, resource_url, params)
        if restricted:
            resourceLocator.authorization = ResourceLocator.AUTHORIZATION_PENDING
        else:
            resourceLocator.authorization = ResourceLocator.AUTHORIZATION_NOT_REQUIRED
    elif resourceLocator.layer_id_type == ResourceLocator.GVSIGOL_LAYER_ID:
        # TODO: check user permissions on the layer
        layer = getLayer(resourceLocator.layer_id)
        (resourceLocator.resolved_url, resourceLocator.is_dynamic) = getGvsigolResourceURL(res_type, layer, params)
        resourceLocator.authorization = ResourceLocator.AUTHORIZATION_NOT_REQUIRED
    
    if not resourceLocator.resolved_url:
        raise PermanentPreparationError("Url could not be resolved for resource locator: " + text(resourceLocator.pk))

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

class WCSClient():
    def __init__(self, url, layer_name, params):
        self.url = url
        self.layer_name = layer_name
        self.params = params
        self.output_dir = tempfile.mkdtemp('-tmp', GVSIGOL_NAME.lower()+"dm", dir=getTmpDir())
        self.nativeSrsCode = None
        self.wcs200Namespaces = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'gml': 'http://www.opengis.net/gml/3.2', 'wcs': 'http://www.opengis.net/wcs/2.0', 'xlink': "http://www.w3.org/1999/xlink", 'ows': 'http://www.opengis.net/ows/2.0'}
        self.gmlCoverageNamespaces =  {
                'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'wcscrs': "http://www.opengis.net/wcs/service-extension/crs/1.0",
                'int': "http://www.opengis.net/WCS_service-extension_interpolation/1.0",
                'gmlcov': "http://www.opengis.net/gmlcov/1.0",
                'swe': "http://www.opengis.net/swe/2.0",
                'xlink': "http://www.w3.org/1999/xlink", 
                 'gml': 'http://www.opengis.net/gml/3.2',
                 'wcs': 'http://www.opengis.net/wcs/2.0'
            }

    def _getDescribeWcsCoverageTree(self, layer_name, baseUrl):
        try:
            url = _normalizeWxsUrl(baseUrl) + '?service=WCS&version=2.0.0&request=DescribeCoverage&CoverageId=' + layer_name
            logger.debug(url)
            r = requests.get(url, verify=False, timeout=DEFAULT_TIMEOUT, proxies=PROXIES)
            if r.status_code != 200:
                logger.debug('Error getting DescribeCoverage. HTTP status code: '+text(r.status_code) + ". Url: " + url)
                return
            describeCoverageXml = r.content
            incorrectGeoserverNamespaces = '<wcs:CoverageDescriptions xsi:schemaLocation=" http://www.opengis.net/wcs/2.0 http://schemas.opengis.net/wcs/2.0/wcsDescribeCoverage.xsd">'
            fixedGeoserverWCS2Namespaces = '<wcs:CoverageDescriptions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmlcov="http://www.opengis.net/gmlcov/1.0" xmlns:swe="http://www.opengis.net/swe/2.0" xsi:schemaLocation="http://schemas.opengis.net/swe/2.0 http://schemas.opengis.net/sweCommon/2.0/swe.xsd http://www.opengis.net/wcs/2.0 http://schemas.opengis.net/wcs/2.0/wcsDescribeCoverage.xsd" xmlns:wcs="http://www.opengis.net/wcs/2.0">'
            if describeCoverageXml.startswith(incorrectGeoserverNamespaces):
                describeCoverageXml = describeCoverageXml.replace(incorrectGeoserverNamespaces, fixedGeoserverWCS2Namespaces)
            return ET.fromstring(describeCoverageXml)
        except:
            logger.exception("Error retrieving or parsing describeCoverageXml")

    def _getDescribeWcsCoverageAxes(self, envelopeNode):
        if envelopeNode is not None:
            axis = envelopeNode.get('axisLabels')
            return axis.split(" ")

    def _getEnvelopeSrsCode(self, envelopeNode):
        if envelopeNode is not None:
            srs = envelopeNode.get('srsName')
            if srs.startswith('http://www.opengis.net/def/crs/EPSG/'):
                return re.sub('http://www.opengis.net/def/crs/EPSG/[^/]+/', '', srs)
            if srs.startswith('EPSG:'):
                return srs[5:]

    def _getWcsCoverageEnvelope(self, describeCoverageTree, namespaces):
        if describeCoverageTree is not None:
            return describeCoverageTree.find('./gml:boundedBy/gml:Envelope', namespaces)

    def getCapabilitiesTree(self, baseUrl, version='2.0.1'):
        url = _normalizeWxsUrl(baseUrl) + '?service=WCS&version=' + version +'&request=GetCapabilities'
        logger.debug(url)
        r = requests.get(url, verify=False, timeout=DEFAULT_TIMEOUT, proxies=PROXIES)
        if r.status_code != 200:
            raise PreparationError("Error retrieving getCapabilities")
        return ET.fromstring(r.content)

    def getGetOperationUrl_v2_0_1(self, capabilitiesTree, operationName):
        try:
            if capabilitiesTree is not None:
                findExpr = './ows:OperationsMetadata/ows:Operation[@name="' + operationName + '"]/ows:DCP/ows:HTTP/ows:Get'
                operationHttpGetList = capabilitiesTree.findall(findExpr, self.wcs200Namespaces)
                for operationHttpGet in operationHttpGetList:
                    operationHttpGetUrl = operationHttpGet.get('{' + self.wcs200Namespaces.get('xlink') +'}href')
                    if operationHttpGetUrl:
                        return operationHttpGetUrl
        except:
            logger.exception("Error getting the URL of operation: " + operationName)
        return self.url

    def getWcsRequest(self):
        capabilitiesTree = self.getCapabilitiesTree(self.url)
        getCoverageUrl = self.getGetOperationUrl_v2_0_1(capabilitiesTree, 'GetCoverage')
        url = _normalizeWxsUrl(getCoverageUrl) + '?service=WCS&version=2.0.0&request=GetCoverage&CoverageId=' + self.layer_name
        self.file_format = _getParamValue(self.params, FORMAT_PARAM_NAME)
        if self.isMultipartResult():
            url += '&mediatype=multipart/related'
        if self.file_format:
            url += '&format=' + self.file_format
        spatial_filter_type = _getParamValue(self.params, SPATIAL_FILTER_TYPE_PARAM_NAME)
        if spatial_filter_type == 'bbox':
            spatial_filter_bbox = _getParamValue(self.params, SPATIAL_FILTER_BBOX_PARAM_NAME)
            if spatial_filter_bbox:
                describeCoverageUrl = self.getGetOperationUrl_v2_0_1(capabilitiesTree, 'DescribeCoverage')
                describeCoverageTree = self._getDescribeWcsCoverageTree(self.layer_name, describeCoverageUrl)
                if describeCoverageTree is not None:
                    describeCoverageRoot = describeCoverageTree.find('./wcs:CoverageDescription', self.wcs200Namespaces)
                    envelopeNode = self._getWcsCoverageEnvelope(describeCoverageRoot, self.wcs200Namespaces)
                    axes = self._getDescribeWcsCoverageAxes(envelopeNode)
                    self.nativeSrsCode = self._getEnvelopeSrsCode(envelopeNode)
                    bboxElements = spatial_filter_bbox.split(",")
                    spatial_subset = ''
                    if axes is not None and bboxElements is not None and len(axes) == 2 and len(bboxElements) == 5:
                        srs = bboxElements[4]
                        if float(bboxElements[0]) <= float(bboxElements[2]):
                            xmin = bboxElements[0]
                            xmax = bboxElements[2]
                        else:
                            xmin = bboxElements[2]
                            xmax = bboxElements[0]
                        if float(bboxElements[1]) <= float(bboxElements[3]):
                            ymin = bboxElements[1]
                            ymax = bboxElements[3]
                        else:
                            ymin = bboxElements[3]
                            ymax = bboxElements[1]
                            
                        axis0_min, axis1_min, axis0_max, axis1_max = reprojectExtent(xmin, ymin, xmax, ymax, srs, self.nativeSrsCode)
                        if self.nativeSrsCode and int(self.nativeSrsCode) in _getCrsReverseAxisList():
                            spatial_subset = '&subset=' + text(axes[0]) + '%28%22' + text(axis1_min) + '%22%2C%22' + text(axis1_max) + '%22%29'
                            spatial_subset += '&subset=' + text(axes[1]) + '%28%22' + text(axis0_min) + '%22%2C%22' + text(axis0_max) + '%22%29'
                        else:
                            spatial_subset = '&subset=' + text(axes[0]) + '%28%22' + text(axis0_min) + '%22%2C%22' + text(axis0_max) + '%22%29'
                            spatial_subset += '&subset=' + text(axes[1]) + '%28%22' + text(axis1_min) + '%22%2C%22' + text(axis1_max) + '%22%29'
                    url += spatial_subset
        logger.debug(url)
        return url
    
    def _createPrjFile(self, nativeSrsObj):
        try:
            if nativeSrsObj is not None:
                outfile = os.path.join(self.output_dir, self.layer_name + ".prj")
                f = open(outfile, 'w')
                f.write(nativeSrsObj.wkt.encode('UTF-8'))
                f.close()
        except:
            logger.exception("Error creating PRJ file")
    
    def _getWCSCoverageDescTree(self):
        try:
            wcsCoverageDescPath = os.path.join(self.output_dir, 'wcs')
            return ET.parse(wcsCoverageDescPath)
        except:
            logger.exception("Error parsing WCS Coverge Desc XML")

    def _getDomainSetValues(self, wcsCoverageDescTree):
        if wcsCoverageDescTree is not None:
            rectifiedGridNode = wcsCoverageDescTree.find('./gml:domainSet/gml:RectifiedGrid', self.gmlCoverageNamespaces)
            offsetVectors =  rectifiedGridNode.findall('./gml:offsetVector', self.gmlCoverageNamespaces)
            values = []
            for offvec in offsetVectors:
                values = values + offvec.text.split(" ")
            envelopeNode = self._getWcsCoverageEnvelope(wcsCoverageDescTree, self.gmlCoverageNamespaces)
            envelope_lower = envelopeNode.find('./gml:lowerCorner', self.gmlCoverageNamespaces)
            envelope_upper = envelopeNode.find('./gml:upperCorner', self.gmlCoverageNamespaces)
            if len(values)>0 and envelope_lower is not None and envelope_upper is not None:
                # FIXME: consider axis order
                topleft_x = envelope_lower.text.split(" ")[0]
                topleft_y = envelope_upper.text.split(" ")[1]
                values.append(topleft_x)
                values.append(topleft_y)
                return values
            
    def _createWldFile(self, domainSetValues):
        try:
            if domainSetValues is not None:
                outfile = os.path.join(self.output_dir, self.layer_name + ".wld")
                f = open(outfile, 'w')
                for val in domainSetValues:
                    f.write(val + '\n')
                f.close()
        except:
            logger.exception("Error creating WLD file")
    
    def _createPamDatasetFile(self, nativeSrsObj, values, mainFileName):
        root = ET.Element('PAMDataset')
        srs = ET.SubElement(root, 'SRS')
        srs.text = nativeSrsObj.wkt
        if len(values) == 6:
            transform = ET.SubElement(root, 'GeoTransform')
            transform.text = values[4] + ", " + values[0] + ", " + values[1] + ", " + values[5] + ", " + values[2] + ", " + values[3]
        outxml = os.path.join(self.output_dir, mainFileName) + ".aux.xml"
        tree = ET.ElementTree(root)
        tree.write(outxml)
    
    def getMainFile(self, wcsCoverageDescTree):
        fileReference = wcsCoverageDescTree.find('./gml:rangeSet/gml:File/gml:fileReference', self.gmlCoverageNamespaces)
        if fileReference is not None:
            return os.path.basename(fileReference.text)
        
    def _retrieveResource(self, url):
        # TODO: authentication and permissions
        (fd, tmp_path) = tempfile.mkstemp('.tmp', GVSIGOL_NAME.lower()+"dm", dir=getTmpDir())
        tmp_file = os.fdopen(fd, "wb")
        try:
            r = requests.get(url, stream=True, verify=False, timeout=DEFAULT_TIMEOUT, proxies=PROXIES)
            if r.status_code != 200:
                try:
                    error_root = ET.fromstring(r.content)
                    exc = error_root.find('ows:Exception', self.wcs200Namespaces)
                    if exc:
                        code = exc.get('exceptionCode')
                        message = "".join(exc.itertext())
                        if code == 'InvalidSubsetting':
                            raise PermanentPreparationError('The provided spatial filter does not overlap the layer. Layer could not be retrieved. Error code: ' + code + ' - Error message: ' + message.strip())
                except ET.LxmlError:
                    pass
                tmp_file.close()
                raise PreparationError('Error retrieving link. HTTP status code: '+text(r.status_code) + ". Url: " + url)
            for chunk in r.iter_content(chunk_size=128):
                tmp_file.write(chunk)
            tmp_file.close()
            if r.headers.get('content-type') == 'application/xml':
                # check we get the expected document and not a OGC error
                for event, element in ET.iterparse(tmp_path, events=("start",)):
                    # use iterpase to avoid parsing the whole document (it could be a big GML file for instance)
                    ns, sep, tag = element.tag.rpartition('}') # get the tag name
                    if 'www.opengis.net/ows' in ns and tag == 'ExceptionReport':
                        error_text = ET.parse(tmp_path).tostring()
                        raise PreparationError('Error retrieving WCS resource. Url: ' + url + 'OWS error message: ' + error_text)
                    break

        except PreparationError:
            raise
        except:
            logger.exception('error retrieving link: ' + url)
        return tmp_path
    
    def isSelfreferencedFormat(self, mainFileName):
        """
        Returns true if the format of the provided file name contains CRS information
        in its internal structure. The format is determined by examining the file
        extension.
        """
        name, ext = os.path.splitext(mainFileName)
        extlow = ext.lower()
        if '.tif' == extlow or '.tiff' == extlow or 'geotif' in extlow:
            return True
        return False
    
    def isMultipartResult(self):
        if not self.file_format:
            return True
        file_format = self.file_format.lower()
        if file_format == 'geotiff' or file_format == 'image/geotiff':
            return False
        return True

    def retrieveResources(self):
        """
        Retrieves resources on a temporary folder.
        Returns the path to the temporary folder containing the resources
        """
        url = self.getWcsRequest()
        local_path = self._retrieveResource(url)
        if not self.isMultipartResult():
            return local_path
        parseMultipart(local_path, self.output_dir)
        os.remove(local_path)
        try:
            # now write auxiliary files to improve compatibility with traditional GIS software
            wcsCoverageDescTree = self._getWCSCoverageDescTree()
            mainFileName = self.getMainFile(wcsCoverageDescTree)
            selfReferencedFormat = self.isSelfreferencedFormat(mainFileName)
            envelopeNode = self._getWcsCoverageEnvelope(wcsCoverageDescTree, self.gmlCoverageNamespaces)
            values = self._getDomainSetValues(wcsCoverageDescTree)
            nativeSrsCode = self._getEnvelopeSrsCode(envelopeNode)
            if nativeSrsCode is not None:
                nativeSrsObj = SpatialReference(nativeSrsCode)
                self._createPrjFile(nativeSrsObj)
                if not selfReferencedFormat:
                    self._createPamDatasetFile(nativeSrsObj, values, mainFileName)
            # name, ext = os.path.splitext(nameext)
            if not selfReferencedFormat:
                self._createWldFile(values)
        except:
            logger.exception("Error creating auxiliary files for resource: " + url)
        return self.output_dir

class WFSClient():
    def __init__(self, url, layer_name, params):
        self.url = url
        self.layer_name = layer_name
        self.params = params
        self.file_format = _getParamValue(self.params, FORMAT_PARAM_NAME)
        self.output_dir = tempfile.mkdtemp('-tmp', GVSIGOL_NAME.lower()+"dm", dir=getTmpDir())
        self.nativeSrsCode = None
        self.canceled = False
        self.wfs200Namespaces = {'wfs': 'http://www.opengis.net/wfs/2.0', 'gml': 'http://www.opengis.net/gml/3.2', 'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'ows': 'http://www.opengis.net/ows/1.1', 'xlink': "http://www.w3.org/1999/xlink"}
        self.wfs100Namespaces = {'wfs': 'http://www.opengis.net/wfs', 'ogc': 'http://www.opengis.net/ogc', 'gml': 'http://www.opengis.net/gml/3.2', 'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}

    def cancel(self):
        self.canceled = True
        
    def _getEpsgValue(self, epsgString):
        if epsgString is not None:
            if epsgString.startswith('http://www.opengis.net/def/crs/EPSG/'):
                return re.sub('http://www.opengis.net/def/crs/EPSG/[^/]+/', '', epsgString)
            if epsgString.startswith('EPSG:'):
                return epsgString[5:]
            if epsgString.startswith('urn:ogc:def:crs:EPSG:'):
                return re.sub('urn:ogc:def:crs:EPSG:[^:]*:', '', epsgString)

    def getLayerCrs_v1_0_0(self, capabilitiesTree, layerName):
        try:
            if capabilitiesTree is not None:
                findExpr = "./wfs:FeatureTypeList/wfs:FeatureType/wfs:Name"
                featureTypes = capabilitiesTree.findall(findExpr, self.wfs100Namespaces)
                for featureTypeNameNode in featureTypes:
                    if featureTypeNameNode.text == layerName:
                        srsNode = featureTypeNameNode.find("../wfs:SRS", self.wfs100Namespaces)
                        if srsNode is not None:
                            return srsNode.text
        except:
            logger.exception("Error getting the CRS of the WFS layer: " + layerName)

    def getGetOperationUrl_v1_0_0(self, capabilitiesTree, operationName):
        try:
            if capabilitiesTree is not None:
                findExpr = "./wfs:Capability/wfs:Request/wfs:" + operationName + "/wfs:DCPType/wfs:HTTP/wfs:Get"
                operationHttpGetList = capabilitiesTree.findall(findExpr, self.wfs100Namespaces)
                for operationHttpGet in operationHttpGetList:
                    operationHttpGetUrl = operationHttpGet.get("onlineResource")
                    if operationHttpGetUrl:
                        return operationHttpGetUrl
        except:
            logger.exception("Error getting the URL of operation: " + operationName)
        return self.url

    def getGetOperationUrl_v2_0_0(self, capabilitiesTree, operationName):
        try:
            if capabilitiesTree is not None:
                findExpr = './ows:OperationsMetadata/ows:Operation[@name="' + operationName + '"]/ows:DCP/ows:HTTP/ows:Get'
                operationHttpGetList = capabilitiesTree.findall(findExpr, self.wfs200Namespaces)
                for operationHttpGet in operationHttpGetList:
                    operationHttpGetUrl = operationHttpGet.get('{' + self.wfs200Namespaces.get('xlink') +'}href')
                    if operationHttpGetUrl:
                        return operationHttpGetUrl
        except:
            logger.exception("Error getting the URL of operation: " + operationName)
        return self.url

    def getLayerCrs_v2_0_0(self, capabilitiesTree, layerName):
        try:
            if capabilitiesTree is not None:
                findExpr = "./wfs:FeatureTypeList/wfs:FeatureType/wfs:Name"
                featureTypes = capabilitiesTree.findall(findExpr, self.wfs200Namespaces)
                for featureTypeNameNode in featureTypes:
                    if featureTypeNameNode.text == layerName:
                        srsNode = featureTypeNameNode.find("../wfs:DefaultCRS", self.wfs200Namespaces)
                        if srsNode is not None:
                            return srsNode.text
        except:
            logger.exception("Error getting the CRS of the WFS layer" + layerName)
    
    def getCapabilitiesTree(self, baseUrl, version='2.0.0'):
        url = _normalizeWxsUrl(baseUrl) + '?service=WFS&version=' + version +'&request=GetCapabilities'
        logger.debug(url)
        r = requests.get(url, verify=False, timeout=DEFAULT_TIMEOUT, proxies=PROXIES)
        if r.status_code != 200:
            raise PreparationError("Error retrieving getCapabilities")
        return ET.fromstring(r.content)

    def getWfsGetFeatureRequest_v1_0_0(self, baseUrl, layer_name, params, file_format ='shape-zip', startIndex=None, count=None, hits=False):
        """
        # TODO:
        - usar el parámetro SPATIAL_FILTER_BBOX_PARAM_NAME para filtrar usando el atributo BBOX de WFS
        - de momento no permitiremos filtrar por polígono (usando WFS Filter encoding) porque es complicado obtener el
          nombre del atributo que contiene la geometría para montar el filtro.
        - Usar filter encoding requiere hacer un describeFeatureType y parsear la respuesta, que puede ser un XSD muy complejo
         de interpretar
        
        https://gvsigol.localhost/geoserver/wfs?request=GetFeature&service=WFS&version=1.0.0&typeName=ws_cmartinez:countries4326&BBOX=18
    ,21,40,42
        
        spatial_filter_type = _getParamValue(params, SPATIAL_FILTER_TYPE_PARAM_NAME)
        spatial_filter_geom = _getParamValue(params, SPATIAL_FILTER_GEOM_PARAM_NAME)
        
        getFeature = ET.Element("wfs:GetFeature")
        query = ET.SubElement(getFeature, "wfs:query")
        ET.SubElement(query, "fes:Filter")
        
        OJO! Podemos usar el filter BBOX sin necesidad de saber el campo de geometry (se puede omitir propertyName en el operador BBOX)
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
        <ogc:BBOX>
          <gml:Box xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:3785">
              <gml:coordinates decimal="." cs="," ts=" ">
                -8033496.4863128,5677373.0653376 -7988551.5136872,5718801.9346624
              </gml:coordinates>
            </gml:Box>
          </ogc:BBOX>
        </ogc:Filter>
        """
    
        url = _normalizeWxsUrl(baseUrl) + '?service=WFS&version=1.0.0&request=GetFeature&typeName=' + layer_name
        if hits:
            url += '&RESULTTYPE=hits'
        else:
            url += '&OUTPUTFORMAT='+ file_format
        spatial_filter_type = _getParamValue(params, SPATIAL_FILTER_TYPE_PARAM_NAME)
        if spatial_filter_type == 'bbox':
            spatial_filter_bbox = _getParamValue(params, SPATIAL_FILTER_BBOX_PARAM_NAME)
            if spatial_filter_bbox:
                bboxElements = spatial_filter_bbox.split(",")
                if len(bboxElements) == 5:
                    sourceCrs = bboxElements[4]
                    nativeExtent = reprojectExtent(float(bboxElements[0]), float(bboxElements[1]), float(bboxElements[2]), float(bboxElements[3]), sourceCrs, self.nativeSrs)
                    url += '&BBOX=' + text(nativeExtent[0]) + "," + text(nativeExtent[1])  + "," + text(nativeExtent[2]) + "," + text(nativeExtent[3])
        if not hits and count is not None:
            url += '&MAXFEATURES=' + text(count)
            if startIndex is not None:
                url += '&STARTINDEX=' + text(startIndex)
    
        return url

    def getWfsGetFeatureRequest_v2_0_0(self, baseUrl, layer_name, params, file_format ='shape-zip', startIndex=None, count=None, hits=False):
        """
        # TODO:
        - de momento no permitiremos filtrar por polígono (usando WFS Filter encoding) porque es complicado obtener el
          nombre del atributo que contiene la geometría para montar el filtro.
        - Usar filter encoding requiere hacer un describeFeatureType y parsear la respuesta, que puede ser un XSD muy complejo
         de interpretar
        
        https://gvsigol.localhost/geoserver/wfs?request=GetFeature&service=WFS&version=1.0.0&typeName=ws_cmartinez:countries4326&BBOX=18,21,40,42
        
        spatial_filter_type = _getParamValue(params, SPATIAL_FILTER_TYPE_PARAM_NAME)
        spatial_filter_geom = _getParamValue(params, SPATIAL_FILTER_GEOM_PARAM_NAME)
        
        getFeature = ET.Element("wfs:GetFeature")
        query = ET.SubElement(getFeature, "wfs:query")
        ET.SubElement(query, "fes:Filter")
        
        OJO! Podemos usar el filter BBOX sin necesidad de saber el campo de geometry (se puede omitir propertyName en el operador BBOX)
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
        <ogc:BBOX>
          <gml:Box xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:3785">
              <gml:coordinates decimal="." cs="," ts=" ">
                -8033496.4863128,5677373.0653376 -7988551.5136872,5718801.9346624
              </gml:coordinates>
            </gml:Box>
          </ogc:BBOX>
        </ogc:Filter>
        """
        url = _normalizeWxsUrl(baseUrl) + '?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAME=' + layer_name
        if hits:
            url += '&RESULTTYPE=hits'
        else:
            url += '&OUTPUTFORMAT='+ file_format
        spatial_filter_type = _getParamValue(params, SPATIAL_FILTER_TYPE_PARAM_NAME)
        if spatial_filter_type == 'bbox':
            spatial_filter_bbox = _getParamValue(params, SPATIAL_FILTER_BBOX_PARAM_NAME)
            if spatial_filter_bbox:
                bboxElements = spatial_filter_bbox.split(",")
                if len(bboxElements) == 5:
                    sourceCrs = bboxElements[4]
                    if float(bboxElements[0]) <= float(bboxElements[2]):
                        xmin = bboxElements[0]
                        xmax = bboxElements[2]
                    else:
                        xmin = bboxElements[2]
                        xmax = bboxElements[0]
                    if float(bboxElements[1]) <= float(bboxElements[3]):
                        ymin = bboxElements[1]
                        ymax = bboxElements[3]
                    else:
                        ymin = bboxElements[3]
                        ymax = bboxElements[1]
                    
                    epsgCodeValue = self._getEpsgValue(self.nativeSrs)
                    axis0_min, axis1_min, axis0_max, axis1_max = reprojectExtent(xmin, ymin, xmax, ymax, sourceCrs, epsgCodeValue)
                    if epsgCodeValue and self.nativeSrs != 'urn:ogc:def:crs:OGC:1.3:CRS:84' and int(epsgCodeValue) in _getCrsReverseAxisList():
                        url += '&BBOX=' + text(axis1_min) + "," + text(axis0_min)  + "," + text(axis1_max) + "," + text(axis0_max)
                    else:
                        url += '&BBOX=' + text(axis0_min) + "," + text(axis1_min)  + "," + text(axis0_max) + "," + text(axis1_max)
        if not hits and count is not None:
            url += '&COUNT=' + text(count)
            if startIndex is not None:
                url += '&STARTINDEX=' + text(startIndex)
        logger.debug(url)
        return url

    def _retrieveResource(self, url, suffix=''):
        # TODO: authentication and permissions
        resource_path = self.output_dir + "/" + self.layer_name + suffix + _getExtension(self.file_format)
        resource_file = open(resource_path, "wb")
        try:
            r = requests.get(url, stream=True, verify=False, timeout=DEFAULT_TIMEOUT, proxies=PROXIES)
            if r.status_code != 200:
                resource_file.close()
                os.remove(resource_file)
                raise PreparationError('Error retrieving link. HTTP status code: '+text(r.status_code) + ". Url: " + url)
            for chunk in r.iter_content(chunk_size=1024*1024):
                resource_file.write(chunk)
                # logger.debug("got 1MB")
            resource_file.close()
            logger.debug("resource download completed")
            if r.headers.get('content-type') == 'application/xml':
                # check we get the expected document and not a OGC error
                for event, element in ET.iterparse(resource_path, events=("start",)):
                    # use iterpase to avoid parsing the whole document (it could be a big GML file for instance)
                    ns, sep, tag = element.tag.rpartition('}') # get the tag name
                    if 'www.opengis.net/ows' in ns and tag == 'ExceptionReport':
                        error_text = ET.parse(resource_path).tostring()
                        raise PreparationError('Error retrieving WFS resource. Url: ' + url + 'OWS error message: ' + error_text)
                    break

        except PreparationError:
            logger.exception("Preparation error")
            raise
        except:
            logger.exception('error retrieving link: ' + url)
        return resource_path
    
    def _getLayerPlainName(self, layer_fqname):
        parts = layer_fqname.split(":")
        if len(parts) > 1:
            return parts[-1]
        return parts[0]

    def getFileRecordsCount(self, local_path, layer_name, file_type):
        try:
            logger.debug('getFileRecordsCount:')
            logger.debug(local_path)
            logger.debug(layer_name)
            logger.debug(file_type)
            if file_type == 'shape-zip':
                layer_name = self._getLayerPlainName(layer_name)
                try:
                    virtual_path = '/vsizip/{' + local_path + '}/' + layer_name + ".shp"
                    info_str = gdaltools.ogrinfo(virtual_path, layer_name, summary=True, readonly=True)
                except:
                    # for ogr version < 2.2
                    logger.debug('Falling back to ogr < 2.2 command')
                    virtual_path = '/vsizip/' + local_path + '/' + layer_name + ".shp"
                    info_str = gdaltools.ogrinfo(virtual_path, layer_name, summary=True, readonly=True)
            else:
                info_str = gdaltools.ogrinfo(local_path, alltables=True, summary=True, readonly=True)
            try:
                sys_encoding = sys.stdout.encoding or 'utf-8'
            except:
                sys_encoding = 'utf-8'
            info_str = info_str.decode(sys_encoding)
            buf = StringIO(info_str)
            line = buf.readline()
            while line != "":
                if line.startswith('Feature Count: '):
                    return int(line[15:])
                line = buf.readline()
            logger.error("Error getting feature count: " + local_path)
            logger.debug(info_str)
            return None
        except:
            logger.exception("Error getting feature count: " + local_path)

    def parseHits(self, response):
        try:
            logger.debug(response)
            collection = ET.fromstring(response)
            if collection is not None:
                logger.debug(collection.tag)
                return int(collection.get('numberMatched'))
            """
            hitsTree = ET.fromstring(response)
            if hitsTree is not None:
                findExpr = "/wfs:FeatureCollection"
                collection = hitsTree.find(findExpr, self.wfs200Namespaces)
                if collection is not None:
                    return int(collection.get('numberMatched'))
            """ 
        except:
            logger.exception("Error parsing the hits response")
        return 0
    
    def getHits(self):
        hitsUrl = self.getWfsGetFeatureRequest_v1_0_0(self.url, self.layer_name, self.params,  file_format='text/xml', hits=True)
        r = requests.get(hitsUrl, verify=False, timeout=DEFAULT_TIMEOUT, proxies=PROXIES)
        if r.status_code != 200:
            raise PreparationError("Error retrieving hits")
        return self.parseHits(r.content)
    
    def _addDownloadWarningFile(self, count, url):
        out_file = os.path.join(self.output_dir, _('wfs_download_warning')+'.txt')
        with open(out_file, "w") as thefile:
            thefile.write(_("Could not check the last file of the WFS download. Maybe the result is incomplete.").encode("utf-8"))
            thefile.write("\n".encode("utf-8"))
            thefile.write(_("Layer name: ").encode("utf-8"))
            thefile.write(text(self.layer_name).encode("utf-8"))
            thefile.write("\n".encode("utf-8"))
            thefile.write(_("Total downloaded geometries: ").encode("utf-8"))
            thefile.write(text(count).encode("utf-8"))
            thefile.write("\n".encode("utf-8"))
            thefile.write(_("Url of last downloaded file: ").encode("utf-8"))
            thefile.write(text(url).encode("utf-8"))
            thefile.write("\n".encode("utf-8"))

    def retrieveResources(self):
        """
        Retrieves the WFS resource. If the number of matched features is bigger than the
        maximum allowed number of features, the layer will be split in several parts.
        Returns a list of paths pointing the downloaded resources.
        
        """
        logger.debug(self.url)
        try:
            self.capabilitiesTree = self.getCapabilitiesTree(self.url, version='1.0.0')
            # in case the server does not support the requested version and returns a different one
            capabilitiesVersion = self.capabilitiesTree.get('version')
            if capabilitiesVersion[0] == '1':
                self.nativeSrs = self.getLayerCrs_v1_0_0(self.capabilitiesTree, self.layer_name)
                getFeatureUrl = self.getGetOperationUrl_v1_0_0(self.capabilitiesTree, 'GetFeature')
            else:
                self.nativeSrs = self.getLayerCrs_v2_0_0(self.capabilitiesTree, self.layer_name)
                getFeatureUrl = self.getGetOperationUrl_v2_0_0(self.capabilitiesTree, 'GetFeature')
            print("getFeatureUrl")
            print(getFeatureUrl)
            
            paramDict = {}
            if self.file_format is not None:
                paramDict['file_format'] = self.file_format
            #hits = self.getHits()
            #logger.debug(u"Hits:" + text(hits))
            totalReturnedCount = 0
            returnedCount = 0
            partCount = 1
            ## Since hits is not reliable in Geoserver when maxFeatures is reached,
            ## we will ask for more features until we don't get any
            while partCount == 1 or returnedCount > 0:
                """
                We use WFS 1.0 because it is easier to get consistent axis order results
                for Shapefiles, GeoJSONs, etc, as expected by most of the existing GIS software.
                """
                url = self.getWfsGetFeatureRequest_v1_0_0(getFeatureUrl, self.layer_name, self.params, **paramDict)
                if partCount > 1:
                    suffix = '_part{:02}'.format(partCount)
                else:
                    suffix = ''
                local_path = self._retrieveResource(url, suffix)
                returnedCount = self.getFileRecordsCount(local_path, self.layer_name, self.file_format)
                if returnedCount is None:
                    if partCount > 1:
                        logger.debug('The downloaded resource could not be checked')
                        logger.debug(url)
                        self._addDownloadWarningFile(totalReturnedCount, url)
                        break
                    else:
                        logger.debug(url)
                        raise PreparationError('The downloaded resource could not be checked')
                elif partCount == 1 or returnedCount > 0:
                    totalReturnedCount += returnedCount
                    paramDict['count'] = paramDict.get('count', returnedCount) # maxFeatures
                    paramDict['startIndex'] = totalReturnedCount
                else:
                    os.remove(local_path)
                partCount += 1
                if self.canceled:
                    return []
            """
            TODO:
            - comprobar el caso en el que el shape sea > 2 GB y volver a pedirlo en subconjuntos menores
            """
        except:
            shutil.rmtree(self.output_dir, ignore_errors=True)
            logger.exception("Error retrieving resource: " + self.url)
            raise
        return self.output_dir


def normalizeOutname(name):
    resource_name = name.replace(":", "_")
    return re.sub('[^\w\s_-]', '', resource_name).strip().lower()

def guessResourceName(resource_name, params, suffix='', extension=None):
    # remove non-a-z_ or numeric characters
    resource_name = normalizeOutname(resource_name)
    if '.' in resource_name:
        return resource_name
    file_format = _getParamValue(params, FORMAT_PARAM_NAME, '')
    if extension is not None:
        return resource_name + suffix + extension
    return resource_name + suffix + _getExtension(file_format)

def retrieveMetadata(layer_id, md_name, output_dir=None):
    try:
        mdbytes = getRawMetadata(layer_id)
        if mdbytes is not None:
            if output_dir is None:
                output_dir = tempfile.mkdtemp('-tmp', GVSIGOL_NAME.lower()+"dm", dir=getTmpDir())
            # FIXME: should sanitize md_name
            md_path = output_dir + "/" + md_name
            f = open(md_path, "wb")
            f.write(mdbytes)
            f.close()
            return md_path
    except:
        logger.exception("Error retrieving metadata")
    
def retrieveResources(resource_descriptor):
    """
    Returns the resource pointed by the resourceLocator as a local file path,
    wrapped in a ResourceDescription object.
    If the resource is a remote resource, it is first copied as a local file. 
    """
    res_type = resource_descriptor.get('resource_type')
    layer_id = resource_descriptor.get('layer_id')
    resource_name = resource_descriptor.get('name', '')
    resource_url = resource_descriptor.get('url')
    params = resource_descriptor.get('params', [])
    metadata_name = guessResourceName(resource_name, params, extension=".metadata.xml")
    if res_type == ResourceLocator.OGC_WCS_RESOURCE_TYPE:
        client = WCSClient(resource_url, resource_name, params)
        output_file_or_folder = client.retrieveResources()
        if os.path.isdir(output_file_or_folder):
            retrieveMetadata(layer_id, metadata_name, output_file_or_folder)
            return [ResourceDescription(guessResourceName(resource_name, params), output_file_or_folder, True)]
        else:
            resources = [ResourceDescription(guessResourceName(resource_name, params), output_file_or_folder, True)]
            md_path = retrieveMetadata(layer_id, metadata_name)
            if md_path:
                    resources.append(ResourceDescription(metadata_name, md_path, True))
            return resources
    elif res_type == ResourceLocator.OGC_WFS_RESOURCE_TYPE:
        client = WFSClient(resource_url, resource_name, params)
        output_folder = client.retrieveResources()
        retrieveMetadata(layer_id, metadata_name, output_folder)
        return [ResourceDescription(guessResourceName(resource_name, params, extension=''), output_folder, True)]
    elif res_type == ResourceLocator.HTTP_LINK_RESOURCE_TYPE:
        url = resource_url
    resources = []
    md_path = retrieveMetadata(layer_id, metadata_name)
    if md_path:
        resources.append(ResourceDescription(metadata_name, md_path, True))
    if (url.startswith("http://") or url.startswith("https://")):
        local_path = retrieveLinkLocator(url)
        resources.insert(0, ResourceDescription(guessResourceName(resource_name, params), local_path, True))
    elif url.startswith("file://"):
        local_path = resolveFileUrl(url)
        if url.endswith("/"):
            resources.insert(0, ResourceDescription(guessResourceName(resource_name, params), local_path)) 
        else:
            resources.insert(0, ResourceDescription(os.path.basename(url), local_path))
    # TODO: error management
    return resources

def _addResources(zipobj, resource_desc_list, count):
    i = 0
    for resourceDesc in resource_desc_list:
        if len(resource_desc_list) > 1:
            res_name = text(count) + "-" + text(i) + "-" + resourceDesc.name
        else:
            res_name = text(count) + "-" + resourceDesc.name
        if os.path.isdir(resourceDesc.res_path):
            for root, dirs, files in os.walk(resourceDesc.res_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    # TODO FIXME: use res_name as a folder to contain the resource in the zipfile
                    rel_file_path = res_name + '/' + file_name
                    zipobj.write(file_path, rel_file_path)
                    if resourceDesc.temporary:
                        os.remove(os.path.join(root, file_name))
            if resourceDesc.temporary:
                os.rmdir(resourceDesc.res_path)
        else:
            zipobj.write(resourceDesc.res_path, res_name)
            if resourceDesc.temporary:
                os.remove(resourceDesc.res_path)
        i = i + 1

"""
def _addResource(zipobj, resource_descriptor, resolved_url, count):
    resourceDescList = retrieveResource(resolved_url, resource_descriptor)
    i = 0
    for resourceDesc in resourceDescList:
        if len(resourceDescList) > 1:
            res_name = text(count) + u"-" + text(i) + u"-" + resourceDesc.name
        else:
            res_name = text(count) + u"-" + resourceDesc.name
        zipobj.write(resourceDesc.res_path, res_name)
        if resourceDesc.temporary:
            os.remove(resourceDesc.res_path)
        i = i + 1
"""

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
        request = DownloadRequest.objects.get(pk=request_id)
        if only_if_queued and request.request_status != DownloadRequest.REQUEST_QUEUED_STATUS:
            return
        with override(get_language(request)):
            tracking_url = core_settings.BASE_URL + reverse('download-request-tracking', args=(request.request_random_id,))
            subject = _('Download service: your request has been received - %(requestid)s') % {'requestid': request.request_random_id}
            statusdetails = _('\nYou can use this tracking link to check the status of your request: {0}').format(tracking_url)
            htmlContext = {
                "statusdesc": subject,
                "statusdetails": statusdetails,
                'locators': []
                }
            plain_message = _('Your download request has been received.')
            plain_message += '\n' + statusdetails + '\n'
            plain_message += '\n' + _('Included resources:')
            for locator in request.resourcelocator_set.all():
                plain_message += ' - {0!s} [{1!s}]\n'.format(locator.fq_title, locator.name)
                htmlContext['locators'].append({'name': '{0!s} [{1!s}]\n'.format(locator.fq_title, locator.name),
                                                'status': _(locator.status_detail)})
                
            html_message = render_to_string('request_received_email.html', htmlContext)
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                user = User.objects.get(username=request.requested_by_user)
                to = user.email
            else:
                to = request.requested_by_external
            from_email = get_notifications_from_email()
            from_pass = get_notifications_from_pass()
            if not from_email or not from_pass:
                logger.error("DOWNMAN_EMAIL_HOST_USER or EMAIL_HOST_USER has not been configured")
                raise Error("Error getting email auth credentials")
            mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message, auth_user=from_email, auth_password=from_pass)
            request.notification_status = DownloadRequest.INITIAL_NOTIFICATION_COMPLETED_STATUS
            request.save(update_fields=['notification_status'])

    except Exception as exc:
        logger.exception("Download request completed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.notification_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.package_retry_count = request.notify_retry_count + 1 
            request.save(update_fields=['notification_status', 'package_retry_count'])
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.notification_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save(update_fields=['notification_status'])

@shared_task(bind=True)
def notifyRequestProgress(self, request_id):
    try:
        from_email = get_notifications_from_email()
        from_pass = get_notifications_from_pass()
        if not from_email or not from_pass:
            logger.error("DOWNMAN_EMAIL_HOST_USER or EMAIL_HOST_USER has not been configured")
            raise Error("Error getting email auth credentials")
        request = DownloadRequest.objects.get(pk=request_id)
        with override(get_language(request)):
            tracking_url = core_settings.BASE_URL + reverse('download-request-tracking', args=(request.request_random_id,))
            if request.request_status == DownloadRequest.COMPLETED_STATUS:
                subject = _('Download service: your request is ready - %(requestid)s') % {'requestid': request.request_random_id}
                statusdetails = _('Your download request is ready.')
            elif request.request_status == DownloadRequest.COMPLETED_WITH_ERRORS:
                subject = _('Download service: your request is ready - %(requestid)s') % {'requestid': request.request_random_id}
                statusdetails = _('Your download request is ready. Some resources failed to be processed and are not available for download at the moment.')
            else:
                subject = _('Download service: request progress - %(requestid)s') % {'requestid': request.request_random_id}
                statusdetails = _('Your download request has been partially processed.')
            
            plain_message = statusdetails + '\n'
            plain_message +=  _('You can use the following links to download the requested resources:') + '\n'
            
            htmlContext = {
                "statusdesc": _('Download service: request progress - {0}').format(request.request_random_id),
                "statusdetails": statusdetails,
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
                linkHtmlContext['validto'] = valid_to
                if len(linkResources)==1:
                    if link.is_auxiliary:
                        plain_message += ' {0:2d}- {1!s} [{2!s}]: {3!s}\n'.format(count, linkResources[0].fq_title, link.name, link_url)
                        linkHtmlContext['name'] = '{0!s} [{0!s}]'.format(linkResources[0].fq_title, link.name)
                    else:
                        plain_message += ' {0:2d}- {1!s} [{2!s}]: {3!s}\n'.format(count, linkResources[0].fq_title, linkResources[0].name, link_url)
                        linkHtmlContext['name'] = '{0!s} [{0!s}]'.format(linkResources[0].fq_title, linkResources[0].name)
                    linkHtmlContext['url'] = link_url
                else:
                    plain_message += ' {0:2d}- {1!s}: {2!s}\n'.format(count, _('Multiresource package'), link_url)
                    plain_message += _('    -- Link valid until {0!s}:\n').format(valid_to)
                    plain_message += _('    -- Contents:')
                    linkHtmlContext['name'] = _('Multiresource package')
                    linkHtmlContext['url'] = link_url
                    linkHtmlContext['locators'] = []
                    for linkResource in linkResources:
                        plain_message += _('     -- {0!s} [{1!s}]\n').format(linkResource.fq_title, linkResource.name)
                        linkHtmlContext['locators'].append({'name': _('{0!s} [{1!s}]\n').format(linkResource.fq_title, linkResource.name)})
                count += 1
                links.append(linkHtmlContext)
            htmlContext['links'] = links
            locators =  request.resourcelocator_set.filter(download_links__isnull=True).exclude(status=ResourceLocator.PERMANENT_ERROR_STATUS)
            if len(locators)>0:
                htmlContext['pendinglocators'] = []
                plain_message += '\n' + _('The following resources are still being processed:') + '\n'
                for locator in locators:
                    plain_message += ' - {0!s} [{1!s}]\n'.format(locator.fq_title, locator.name)
                    plain_message += ('   -- ' + _('Status:') + '{0!s}\n').format(_(locator.status_detail))
                    htmlContext['pendinglocators'].append({'name': '{0!s} [{1!s}]\n'.format(locator.fq_title, locator.name),
                                                           'status': _(locator.status_detail)})
            locators =  request.resourcelocator_set.filter(download_links__isnull=True).filter(status=ResourceLocator.PERMANENT_ERROR_STATUS)
            if len(locators)>0:
                htmlContext['failedlocators'] = []
                plain_message += '\n' + _("The following resources could not be processed:") + '\n'
                for locator in locators:
                    plain_message += ' - {0!s} [{1!s}]\n'.format(locator.fq_title, locator.name)
                    plain_message += ('   -- ' + _('Status:') + '{0!s}\n').format(_(locator.status_detail))
                    htmlContext['failedlocators'].append({'name': '{0!s} [{1!s}]\n'.format(locator.fq_title, locator.name),
                                                           'status': _(locator.status_detail)})
            plain_message += '\n' + _('You can also use this tracking link to check the status of your request:') + ' ' + tracking_url + '\n'
            htmlContext['request_url'] = tracking_url
            html_message = render_to_string('progress_notif_email.html', context=htmlContext)
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                user = User.objects.get(username=request.requested_by_user)
                to = user.email
            else:
                to = request.requested_by_external
            logger.debug("mailing: " + to)
            #mail.send_mail(subject, plain_message, from_email, [to])
            mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message, auth_user=from_email, auth_password=from_pass)
            request.notification_status = DownloadRequest.NOTIFICATION_COMPLETED_STATUS
            request.save(update_fields=['notification_status'])

    except Exception as exc:
        logger.exception("Download request completed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.notification_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.package_retry_count = request.notify_retry_count + 1 
            request.save(update_fields=['notification_status', 'package_retry_count'])
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.notification_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save(update_fields=['notification_status'])

@shared_task(bind=True)
def notifyApprovalRequired(self, request_id):
    try:
        from_email = get_notifications_from_email()
        from_pass = get_notifications_from_pass()
        if not from_email or not from_pass:
            logger.error("DOWNMAN_EMAIL_HOST_USER or EMAIL_HOST_USER has not been configured")
            raise Error("Error getting email auth credentials")
        request = DownloadRequest.objects.get(pk=request_id)
        with override(get_language(request)):
            manage_request_url = core_settings.BASE_URL + reverse('downman-update-request', args=(request.id,))
            subject = _('Download service: a new request is awaiting approval - %(requestid)s') % {'requestid': request.request_random_id}
            statusdetails = _('A new request has been registered and is awaiting approval.')
            plain_message = statusdetails + '\n'
            htmlContext = {
                "statusdesc": _('Download service: received request - {0}').format(request.request_random_id),
                "statusdetails": statusdetails,
                }
            plain_message += '\n' + _('Use the following link to manage the request:') + ' ' + manage_request_url + '\n'
            htmlContext['request_url'] = manage_request_url
            html_message = render_to_string('awaiting_approval_email.html', context=htmlContext)
            #plain_message = strip_tags(html_message)
            logger.debug("mailing: " + str(get_notifications_admin_emails()))
            #mail.send_mail(subject, plain_message, from_email, [to])
            mail.send_mail(subject, plain_message, from_email, get_notifications_admin_emails(), html_message=html_message, auth_user=from_email, auth_password=from_pass)

    except Exception as exc:
        logger.exception("Error notifying adminstrator. Request is awaiting approval")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.save(update_fields=['notification_status', 'package_retry_count'])
            self.retry(exc=exc, countdown=delay)

@shared_task(bind=True)
def notifyGenericRequestRegistered(self, request_id):
    try:
        from_email = get_notifications_from_email()
        from_pass = get_notifications_from_pass()
        if not from_email or not from_pass:
            logger.error("DOWNMAN_EMAIL_HOST_USER or EMAIL_HOST_USER has not been configured")
            raise Error("Error getting email auth credentials")
        request = DownloadRequest.objects.get(pk=request_id)
        with override(get_language(request)):
            tracking_url = core_settings.BASE_URL + reverse('download-request-tracking', args=(request.request_random_id,))
            subject = _('Download service: your request has been received - %(requestid)s') % {'requestid': request.request_random_id}
            statusdetails = _('Our team will contact you when your request has been analysed.')
            plain_message = statusdetails + '\n'
            htmlContext = {
                "statusdesc": _('Download service: received request - {0}').format(request.request_random_id),
                "statusdetails": statusdetails,
                }
            plain_message += '\n' + _('You can also use this tracking link to check the status of your request:') + ' ' + tracking_url + '\n'
            htmlContext['request_url'] = tracking_url
            html_message = render_to_string('progress_notif_email.html', context=htmlContext)
            #plain_message = strip_tags(html_message)
            if request.requested_by_user:
                user = User.objects.get(username=request.requested_by_user)
                to = user.email
            else:
                to = request.requested_by_external
            logger.debug("mailing: " + to)
            #mail.send_mail(subject, plain_message, from_email, [to])
            mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message, auth_user=from_email, auth_password=from_pass)
            request.notification_status = DownloadRequest.NOTIFICATION_COMPLETED_STATUS
            request.save(update_fields=['notification_status'])

    except Exception as exc:
        logger.exception("Download request completed: error notifying the user")
        delay = getNextMailRetryDelay(request)
        if delay:
            request.notification_status = DownloadRequest.NOTIFICATION_ERROR_STATUS
            request.package_retry_count = request.notify_retry_count + 1 
            request.save(update_fields=['notification_status', 'package_retry_count'])
            self.retry(exc=exc, countdown=delay)
        else:
            # maximum retry time reached
            request.notification_status = DownloadRequest.PERMANENT_NOTIFICATION_ERROR_STATUS
            request.save(update_fields=['notification_status'])


def parseMultipart(input_file_path, output_dir):
    parser = email.parser.Parser()
    fp = open(input_file_path, 'r')
    mainPart = parser.parse(fp)
    out_files = []
    if mainPart.is_multipart():
        i = 0
        for part in mainPart.walk():
            if part.is_multipart():
                continue
            out_path = output_dir + '/' + os.path.basename(part.get_filename(part.get('Content-ID', 'part'+text(i))))
            f = open(out_path, "wb")
            payload = part.get_payload(decode=1)
            f.write(payload)
            f.close()
            i += 1
            out_files.append(out_path)
    else:
        out_path = output_dir + '/' + os.path.basename(mainPart.get_filename(mainPart.get('Content-ID', 'mainpart')))
        f = open(out_path, "wb")
        f.write(part.get_payload(decode=1))
        f.close()
        out_files.append(out_path)
    fp.close()
    return out_files

def processLocators(request, zipobj=None, zip_path=None):
    locators = request.resourcelocator_set.filter((Q(status=ResourceLocator.RESOURCE_QUEUED_STATUS) | \
                                                   Q(status=ResourceLocator.HOLD_STATUS) | \
                                                   Q(status=ResourceLocator.WAITING_SPACE_STATUS) | \
                                                   Q(status=ResourceLocator.TEMPORAL_ERROR_STATUS)) & \
                                                   (Q(authorization=ResourceLocator.AUTHORIZATION_ACCEPTED) | \
                                                    Q(authorization=ResourceLocator.AUTHORIZATION_NOT_PROCESSED) | \
                                                    Q(authorization=ResourceLocator.AUTHORIZATION_NOT_REQUIRED)))
            
    temporal_errors = 0
    permanent_errors = 0
    packaged_locators = []
    completed_locators = 0
    to_package = 0
    waiting_space = 0
    ResultTuple = namedtuple('ResultTuple', ['completed', 'packaged', 'waiting_space', 'to_package', 'temporal_error', 'permanent_error'])
    count = 0
    for resourceLocator in locators:
        logger.debug('resourceLocator: ' + text(resourceLocator.id))
        try:
            if resourceLocator.status == ResourceLocator.HOLD_STATUS:
                continue

            resource_descriptor = json.loads(resourceLocator.data_source)
            if not resourceLocator.resolved_url:
                preprocessLocator(resourceLocator, resource_descriptor)
            if resourceLocator.authorization == ResourceLocator.AUTHORIZATION_PENDING:
                logger.debug("AUTHORIZATION_PENDING")
                resourceLocator.save()
                continue
            if DOWNMAN_PACKAGING_BEHAVIOUR == 'ALL' or \
                (resourceLocator.is_dynamic and DOWNMAN_PACKAGING_BEHAVIOUR == 'DYNAMIC'):
                logger.debug('packaging')
                if zipobj is not None:
                    if getFreeSpace(getTmpDir()) < MIN_TMP_SPACE:
                        waiting_space += 1
                        resourceLocator.status = ResourceLocator.WAITING_SPACE_STATUS
                    else:
                        # ensure the locator has not been cancelled before starting packaging
                        resourceLocator.refresh_from_db(fields=['canceled'])
                        if resourceLocator.canceled:
                            continue 
                        #_addResource(zipobj, resource_descriptor, resourceLocator.resolved_url, count)
                        with override(get_language(request)):
                            resource_desc_list = retrieveResources(resource_descriptor)
                            _addResources(zipobj, resource_desc_list, count)
                        count += 1
                        packaged_locators.append(resourceLocator)
                        completed_locators += 1
                else:
                    to_package += 1
            else:
                logger.debug('creating links')
                # store a direct download link instead of packaging the resource
                createDownloadLinks(request, resourceLocator)
                # add metadata link
                md_url = getRawMetadataUrl(resourceLocator.layer_id)
                if md_url:
                    createDownloadLink(request, resourceLocator, resolved_url=md_url, name='metadata', is_auxiliary=True)
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
        new_link = createDownloadLink(request, packaged_locators, prepared_download_path=zip_path, is_temporary=True)
        for resourceLocator in packaged_locators:
            resourceLocator.status = ResourceLocator.PROCESSED_STATUS
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

def createDownloadLink(downloadRequest, resourceLocators, prepared_download_path=None, resolved_url=None, name=None, is_auxiliary=False, is_temporary=False):
    try:
        new_link = DownloadLink()
        new_link.request = downloadRequest
        link_uuid = date.today().strftime("%Y%m%d") + get_random_string(length=32)
        new_link.valid_to = timezone.now() + timedelta(seconds = downloadRequest.validity)
        new_link.link_random_id = link_uuid
        new_link.prepared_download_path = prepared_download_path
        new_link.resolved_url = resolved_url
        new_link.is_auxiliary = is_auxiliary
        new_link.is_temporary = is_temporary
        if name:
            new_link.name = name
        elif prepared_download_path:
            new_link.name = os.path.basename(prepared_download_path)
        elif resolved_url:
            new_link.name = os.path.basename(resolved_url)
        else:
            new_link.name = link_uuid
        new_link.save()
        if isinstance(resourceLocators, ResourceLocator):
            resourceLocators.download_links.add(new_link)
        else:
            for resourceLocator in resourceLocators:
                resourceLocator.download_links.add(new_link)
        return new_link
    except ForbiddenAccessError:
        logger.exception("Error creating download link")
        raise PermanentPreparationError()

def getAuxiliaryFiles(local_path):
    """
    Gets a list of paths which are considered to be auxiliary files of the provided
    local_path. In this method, an auxiliary file is any file that shares the same name
    of the provided local_path with a different extension. The provided local_path is
    also included in the list of returned paths.
    
    Example:
    
    getAuxiliaryFiles('/mnt/data/vuelo2019/vuelo2019.tif) may return a list such as:
    
    [
        '/mnt/data/vuelo2019/vuelo2019.tif',
        '/mnt/data/vuelo2019/vuelo2019.tfw',
        '/mnt/data/vuelo2019/vuelo2019.tif.xml'
    ]
    
    """
    pathdir = os.path.dirname(local_path)
    fnameext = os.path.basename(local_path)
    fname = fnameext.split(".", 1)[0] # don't use path.splitext to consider extensions such us .shp.xml
    return glob.glob(pathdir + "/" + fname + "*") 

def createDownloadLinks(downloadRequest, resourceLocator):
    try:
        if resourceLocator.resolved_url.startswith("file://"):
            local_path = resolveFileUrl(resourceLocator.resolved_url)
            paths = getAuxiliaryFiles(local_path)
            if len(paths) == 0:
                # file can't be found
                logger.error("Error locating file for download")
                logger.debug(resourceLocator.resolved_url)
                logger.debug(local_path)
                raise PermanentPreparationError()
            for p in paths:
                is_auxiliary = (p != local_path)
                createDownloadLink(downloadRequest, resourceLocator, prepared_download_path=p, is_auxiliary=is_auxiliary)
            return
        elif resourceLocator.resolved_url.startswith("http://") or resourceLocator.resolved_url.startswith("https://"):
            createDownloadLink(downloadRequest, resourceLocator, resolved_url=resourceLocator.resolved_url)
            return
    except ForbiddenAccessError:
        logger.exception("Error creating download link")
    raise PermanentPreparationError()

def updatePendingAuthorization(request):
    pending_authorization = request.resourcelocator_set.filter(authorization=ResourceLocator.AUTHORIZATION_PENDING).count()
    if pending_authorization > 0:
        request.pending_authorization = True
    else:
        request.pending_authorization = False
    request.save(update_fields=getPackageManagedFields(request))

def getPackageManagedFields(requestInstance):
    """
    To avoid race conditions, we manage a different set of field in each  
    """
    excluded_fields = ['id', 'notification_status', 'package_retry_count']
    fields = [ f.name for f in requestInstance._meta.fields if not f.name in excluded_fields ]
    logger.debug(fields)
    return [ f.name for f in requestInstance._meta.fields if not f.name in excluded_fields ]

@shared_task(bind=True)
def packageRequest(self, request_id):
    try:
        logger.debug('starting packageRequest')
        logger.info('request ID: ' + text(request_id))
        request = DownloadRequest.objects.get(id=request_id)
        logger.info('request UUID: ' + request.request_random_id)
        if (request.request_status != DownloadRequest.REQUEST_QUEUED_STATUS) and (request.request_status != DownloadRequest.PROCESSING_STATUS):
            logger.debug("Task already processed: " + text(request_id))
            return
        result = None
        zip_file = None
    
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
    
    try:
        updatePendingAuthorization(request)
        
        if not result:
            delay = getNextPackagingRetryDelay(request)
            if delay:
                request.package_retry_count = request.package_retry_count + 1 
                request.save(update_fields=getPackageManagedFields(request))
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
                request.save(update_fields=getPackageManagedFields(request))
                if result.completed > 0:
                    notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
                self.retry(countdown=delay)
    except Retry:
        logger.debug("raising retry")
        raise
    except:
        logger.exception("Error packaging request")

    try:
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
                request.save(update_fields=getPackageManagedFields(request))
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
            else:
                request.request_status = DownloadRequest.COMPLETED_STATUS
                request.save(update_fields=getPackageManagedFields(request))
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
        elif result and result.completed > 0:
            notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
    except:
        logger.exception("Error packaging request")
    
@shared_task(bind=True)
def processDownloadRequest(self, request_id):
    try:
        logger.info("starting processDownloadRequest")
        logger.info('request ID: ' + text(request_id)) 
        result = None
        # 1 get request
        request = DownloadRequest.objects.get(id=request_id)
        logger.info('request UUID: ' + request.request_random_id)
        if request.generic_request == True:
            notifyApprovalRequired.apply_async(args=[request.pk], queue='notify')
            logger.debug("Skipping generic request")
            return
        if (request.request_status != DownloadRequest.REQUEST_QUEUED_STATUS) and (request.request_status != DownloadRequest.PROCESSING_STATUS):
            logger.debug("Task already processed: " + request_id)
            return
        
        request.request_status = DownloadRequest.PROCESSING_STATUS
        request.save(update_fields=getPackageManagedFields(request))
        result = processLocators(request)
    except Exception:
        logger.exception("Error preparing download request")

    try:
        updatePendingAuthorization(request)
        if request.pending_authorization:
            notifyApprovalRequired.apply_async(args=[request.pk], queue='notify')
        if not result:
            delay = getNextPackagingRetryDelay(request)
            if delay:
                request.package_retry_count = request.package_retry_count + 1 
                request.save(update_fields=getPackageManagedFields(request))
                if result.completed > 0:
                    notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
                self.retry(countdown=delay)
    
        if result.to_package > 0:
            if result.completed > 0:
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
            packageRequest.apply_async(args=[request.pk], queue='package')
            return
        if result.temporal_error > 0:
            delay = getNextPackagingRetryDelay(request)
            if delay:
                request.package_retry_count = request.package_retry_count + 1
                 
                request.save(update_fields=getPackageManagedFields(request))
                if result.completed > 0:
                    notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
                self.retry(countdown=delay)
    except Retry:
        logger.debug("raising retry")
        raise
    except:
        logger.exception("Error processing request")

    try:
    # if there are no locators waiting for admin feedback and we reach the maximum amount of retries,
    # then we need to update locators and request status
        """
        waiting_feedback = request.resourcelocator_set.filter( \
                                                      Q(authorization=ResourceLocator.AUTHORIZATION_PENDING) | \
                                                      Q(status=ResourceLocator.HOLD_STATUS)).count()
        """
        on_hold = request.resourcelocator_set.filter(status=ResourceLocator.HOLD_STATUS).count()
        if not request.pending_authorization and on_hold == 0:
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
                request.save(update_fields=getPackageManagedFields(request))
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
            else:
                request.request_status = DownloadRequest.COMPLETED_STATUS
                request.save(update_fields=getPackageManagedFields(request))
                notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
        #elif result and result.completed > 0:
        else:
            notifyRequestProgress.apply_async(args=[request.pk], queue='notify')
    except:
        logger.exception("Error processing request")

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    sender.add_periodic_task(CLEAN_TASK_FREQUENCY, cleanOutdatedRequests.s(), options={'queue' : 'celery'})

@task(bind=True)
def cleanOutdatedRequests(self):
    for root, dirs, files in os.walk(getTargetDir()):
        for f in files:
            fullpath = os.path.join(root, f)
            link_uuid = ''
            try:
                link_uuid = _parseLinkUiid(f)
                link = DownloadLink.objects.get(link_random_id=link_uuid)
                if link.is_temporary:
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
                    logger.exception("error getting link: " + fullpath + " - " + link_uuid)
                    # if older than UNKNOWN_FILES_MAX_AGE days, remove the file
                    #modified_time = os.path.getmtime(fullpath)
                    #if date.fromtimestamp(modified_time) < (date.today() - timedelta(days=UNKNOWN_FILES_MAX_AGE)):
                    #    os.remove(fullpath)
                except:
                    logger.exception("Error cleaning request package")
            