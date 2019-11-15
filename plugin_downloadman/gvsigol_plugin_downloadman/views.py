# -*- coding: utf-8 -*-

from django.shortcuts import render
from gvsigol_services.models import Layer
import gvsigol_plugin_catalog.service as geonetwork_service
import logging
import json
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import ugettext as _
from gvsigol_plugin_downloadman.tasks import processDownloadRequest, resolveFileLocator, notifyReceivedRequest
from gvsigol_plugin_downloadman import models as downman_models
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from datetime import date, datetime
from django.utils import timezone
from django.utils.formats import date_format

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from models import FORMAT_PARAM_NAME
from utils import getLayer
from settings import TARGET_URL, TARGET_ROOT, DOWNLOADS_ROOT, DOWNLOADS_URL
import os
from tasks import Error
from sendfile import sendfile
from django.shortcuts import redirect

logger = logging.getLogger("gvsigol")

class DownloadParam():
    def __init__(self, name, title):
        self.name = name;
        self.title = title;

class ResourceDownloadDescriptor():
    def __init__(self, layer_id, layer_name, layer_title, resource_name, resource_title, dataSourceType=downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE, resourceType=downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE, url='', directDownloadUrl=None, dataFormats=[], resolutions=[], scales=[], crss=[]):
        self.layer_id = layer_id
        self.layer_name = layer_name
        self.layer_title = layer_title
        self.name = resource_name
        self.title = resource_title
        self.dataSourceType = dataSourceType
        self.resourceType = resourceType
        self.directDownloadUrl = directDownloadUrl
        self.dataFormats = self._processOptions(dataFormats)
        self.resolutions = self._processOptions(resolutions)
        self.scales = self._processOptions(scales)
        self.crss = self._processOptions(crss)
        self.url = url
        # more params: CRSs? imagemode (raster RGB, BYTE, INT16, INT32, FLOAT32, etc)? char encoding?
    
    def _processOptions(self, params):
        processed_params = []
        for p in params:
            if isinstance(p, DownloadParam):
                processed_params.append(p)
            elif isinstance(p, basestring):
                processed_params.append(DownloadParam(p, p))
            elif isinstance(p, list) and len(p) >= 2:
                processed_params.append(DownloadParam(p[0], p[1]))
        return processed_params
    
        
    def getDataSourceType(self):
        return self.dataSourceType
    
    def getResourceType(self):
        return self.resourceType
    
    def getFormats(self):
        return self.dataFormats
    
    def getResolutions(self):
        return self.resolutions
    
    def getScales(self):
        return self.scaless
    
    def to_json(self):
        """
          We expect an array of objects like this:
          
          [{
            "layer_id": "asfasfasf234dfasfsa",
            "layer_name": "ortofoto_nvt2010",
            "layer_title": "Ortofoto urbana",
            "resource_type": "HTTP_LINK_TYPE",
            "data_source_type": "GEONET_DATA_SOURCE",
            "name": "RASTER_DATA_TYPE",
            "title": "Datos ráster",
            "url": "http://yourserver/geoserver/service/wms",
            "direct_download_url": '',
            "": ""
            "params": [
              {
                "name": "format",
                "title": "Formato de fichero",
                 "options": [{
                   "name": "geotiff",
                   "title": "Geotiff (formato Tiff Georeferenciado)",
                }]
              },
              {
                "name": "crs",
                "title": "Sistema de referencia de coordenadas",
                "options": [{
                  "name": "EPSG:4326",
                  "title": "Coordinadas geográficas WGS84",
                },
                {
                  "name": "EPSG:3857",
                  "title": "Proyección Google Mercator",
                }]
                }]
          },{
            "layer_id": "asfasfasf234dfasfsa",
            "layer_name": "ortofoto_nvt2010",
            "layer_title": "Ortofoto urbana",
            "resource_type": "downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE",
            "data_source_type": "GEONET_DATA_SOURCE",
            "name": "RASTER_DATA_TYPE",
            "title": "Datos ráster",
            "url": "http://yourserver/geoserver/service/wms",
            "direct_download_url": '',
            "": ""
            "params": [
              {
                "name": "format",
                "title": "Formato de fichero",
                 "options": [{
                   "name": "geotiff",
                   "title": "Geotiff (formato Tiff Georeferenciado)",
                }]
              },
              {
                "name": "crs",
                "title": "Sistema de referencia de coordenadas",
                "options": [{
                  "name": "EPSG:4326",
                  "title": "Coordinadas geográficas WGS84",
                },
                {
                  "name": "EPSG:3857",
                  "title": "Proyección Google Mercator",
                }]
                }]
          }]
        """

        formats = []
        for f in self.dataFormats:
            formats.append({"name": f.name, "title": f.title})
        params = []
        if len(formats)>0:
            params.append({
                "name": FORMAT_PARAM_NAME,
                "title": _("File format"),
                "options": formats
            })
        result = {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "layer_title": self.layer_title,
            "resource_type": self.resourceType,
            "data_source_type": self.dataSourceType,
            "name": self.name,
            "title": self.title,
            "url": self.url,
            "params": params}
        if self.directDownloadUrl:
            result["direct_download_url"] = self.directDownloadUrl
        print result 
        return result
        #return json.dumps(result)

class CustomJsonEncoder(DjangoJSONEncoder):
     def default(self, obj):
        if isinstance(obj, ResourceDownloadDescriptor):
             return obj.to_json()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class DownloadRequest():
    def __init__(self, metadata_uuid, dataFormat=None, resolution=None, scale=None, crs=None, imagemode=None):
        self.layer_uuid = metadata_uuid
        self.dataFormat = dataFormat
        self.resolution = resolution
        self.scale = scale
        self.crs = crs
        self.imagemode = None

def getWsLayerDownloadResources(request, workspace_name, layer_name):
    try:
        layers = Layer.objects.filter(name=layer_name, datastore__workspace__name=workspace_name)
        print layers
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace_name)
        print layer
        resources = doGetLayerDownloadResources(layer, request.user)
    except:
        resources = []
    json_resources = json.dumps(resources, cls=CustomJsonEncoder)
    print json_resources
    return JsonResponse(resources, encoder=CustomJsonEncoder, safe=False)


def getLayerDownloadResources(request, layer_id):
    """
    layer_id: can be the id of the layer on gvsigol/Django, or a metadata uuid from geonetwork
    """
    try:
        layer = getLayer(layer_id)
        resources = 0
        if not layer or layer.allow_download:
            resources = doGetMetadataDownloadResources(layer_id, layer, request.user)
        if len(resources) == 0:
            resources = doGetLayerDownloadResources(layer, request.user)
    except:
        logger.exception("error getting layer download list")
        # TODO: error handling
        resources = []
        pass
    print resources
    json_resources = json.dumps(resources, cls=CustomJsonEncoder)
    print json_resources
    return JsonResponse(resources, encoder=CustomJsonEncoder, safe=False)

def getOgcDownloadDescriptor(layer_uuid, onlineResource, layer, fallbackTitle, dataSourceType, resourceType, dataFormats):
    if onlineResource.name:
        resource_name = onlineResource.name
    else:
        resource_name = fallbackTitle
    if onlineResource.desc:
        resource_title = onlineResource.desc
    else:
        resource_title = fallbackTitle
    if layer:
        layer_name = layer.name
        layer_title = layer.title
    else:
        layer_name = resource_name
        layer_title = resource_title
    return ResourceDownloadDescriptor(layer_uuid, layer_name, layer_title, resource_name, resource_title, dataSourceType=dataSourceType, resourceType=resourceType, dataFormats=dataFormats, url=onlineResource.url)
    
def doGetMetadataDownloadResources(metadata_uuid, layer = None, user = None):
    all_resources = []
    try:
        geonetwork_instance = geonetwork_service.get_instance()
        onlineResources = geonetwork_instance.get_online_resources(metadata_uuid)
        for onlineResource in onlineResources:
            resource = None
            if 'OGC:WFS' in onlineResource.protocol:
                resource = getOgcDownloadDescriptor(metadata_uuid,
                                                    onlineResource,
                                                    layer,
                                                    _('Vector data'),
                                                    dataSourceType = downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE,
                                                    resourceType=downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE,
                                                    dataFormats=['shape-zip', 'application/json', 'csv', 'gml2', 'gml3'])
            elif 'OGC:WCS' in onlineResource.protocol:
                if 'Mapserver' in onlineResource.app_profile:
                    # necesitamos ofrecer el formato adecuado para el tipo de imagen (ortofoto, ráster de temperaturas, ráster cualitativo, etc)
                    resource = getOgcDownloadDescriptor(metadata_uuid,
                                                    onlineResource,
                                                    layer,
                                                    _('Raster data'),
                                                    dataSourceType=downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE,
                                                    resourceType=downman_models.ResourceLocator.OGC_WCS_RESOURCE_TYPE,
                                                    dataFormats=['GEOTIFF_16', 'GEOTIFF_32', 'GEOTIFF_8'],
                                                    url=onlineResource.url)
                else: # assume Geoserver
                    resource = getOgcDownloadDescriptor(metadata_uuid,
                                                    onlineResource,
                                                    layer,
                                                    _('Raster data'),
                                                    dataSourceType=downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE,
                                                    resourceType=downman_models.ResourceLocator.OGC_WCS_RESOURCE_TYPE,
                                                    dataFormats=['image/geotiff', 'image/png'],
                                                    url=onlineResource.url)
            elif (onlineResource.protocol.startswith('WWW:DOWNLOAD-') and onlineResource.protocol.endswith('-download')) \
                    or (onlineResource.protocol.startswith('WWW:LINK-') and onlineResource.protocol.endswith('-link')) \
                    or onlineResource.protocol.startswith('FILE:'):
                if onlineResource.name:
                    resource_name = onlineResource.name
                elif onlineResource.url and not onlineResource.url.endswith("/"):
                    resource_name = os.path.basename(onlineResource.url)
                elif onlineResource.desc:
                    resource_name = onlineResource.desc
                else: 
                    resource_name = onlineResource.url
                if onlineResource.desc:
                    resource_title = onlineResource.desc
                else:
                    resource_title = resource_name
                if layer:
                    layer_name = layer.name
                    layer_title = layer.title
                else:
                    layer_name = resource_name
                    layer_title = resource_title

                directDownloadUrl = None
                if onlineResource.url:
                    if onlineResource.url.startswith("http://") or onlineResource.url.startswith("https://"): 
                        directDownloadUrl = onlineResource.url
                    if onlineResource.url.startswith("file://"):
                        try:
                            directDownloadUrl = getDirectDownloadUrl(onlineResource.url, resource_title)
                        except:
                            logger.exception("Error resolving file download resource for layer")
                resource = ResourceDownloadDescriptor(metadata_uuid, layer_name, layer_title, resource_name, resource_title, dataSourceType = downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE, resourceType=downman_models.ResourceLocator.HTTP_LINK_RESOURCE_TYPE, url=onlineResource.url, directDownloadUrl=directDownloadUrl)
            #elif onlineResource.protocol.startswith('WWW:LINK-'):
            if resource:
                all_resources.append(resource)
    except:
        logger.exception("Error getting download resources for layer")
    return all_resources


def doGetLayerDownloadResources(layer, user):
    all_resources = []
    try:
        if layer.allow_download:
            # TODO: maybe we should check permissions for request.user
            server = layer.datastore.workspace.server
            if server.type == 'geoserver':
                if layer.external == False:
                    if layer.type.startswith('c_'):
                        resource = ResourceDownloadDescriptor(layer.id, layer.name, layer.title, downman_models.ResourceLocator.OGC_WCS_RESOURCE_TYPE, _("Raster data"), dataSourceType = downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE,  resourceType=downman_models.ResourceLocator.OGC_WCS_RESOURCE_TYPE, dataFormats=['image/geotiff', 'image/png'])
                        all_resources.append(resource)
                    elif layer.type.startswith('v_'):
                        resource = ResourceDownloadDescriptor(layer.id, layer.name, layer.title, downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE, _("Vector data"),  dataSourceType = downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE, resourceType=downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE, dataFormats=['shape-zip', 'application/json', 'csv', 'gml2', 'gml3'])
                        all_resources.append(resource)
                else:
                    # TODO:
                    pass
            elif server.type == 'mapserver':
                # TODO:
                pass    
    except:
        pass
    return all_resources

def createResourceLocator(resource, downloadRequest):
    # TODO: error management
    locator = downman_models.ResourceLocator()
    #locator.res_type = downman_models.ResourceLocator.HTTP_LINK_SOURCE_TYPE
    """
    try:
        locator.res_id = int(resource.resource_descriptor.layer_id)
        
        locator.res_type = downman_models.ResourceLocator.GVSIGOL_LAYER 
    except:
        pass
    """
    resource_descriptor = resource.get('resource_descriptor', {})
    ds_type = resource_descriptor.get('data_source_type')
    #res_type = resource_descriptor.get('resource_type')
    locator.name = resource_descriptor.get('name', '')
    locator.title = resource_descriptor.get('title', '')
    locator.layer_name = resource_descriptor.get('layer_name', '')
    locator.layer_title = resource_descriptor.get('layer_title', '')
    locator.layer_id =  resource_descriptor.get('layer_id', '')
    
    #resource_url = resource_descriptor.get('url')
    param_values = resource.get('param_values', [])
    #resource_descriptor['params'] = params
    for param in resource_descriptor.get('params', []):
        for value in param_values:
            if value.get('param', {}).get('name') == param.get('name'):
                param['value'] = value.get('value') 
    locator.data_source = json.dumps(resource_descriptor)
    """
    if ds_type == downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE:
        json_resources = json.dumps(resource_descriptor)

        locator.data_source = getCatalogResourceURL(res_type, resource_name, resource_url, params)
    elif ds_type == downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE:
        layer = getLayer(locator.layer_id)
        locator.data_source = getGvsigolResourceURL(res_type, layer, params)
    """
    if ds_type == downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE:
        locator.layer_id_type = downman_models.ResourceLocator.GEONETWORK_UUID
    elif ds_type == downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE:
        locator.layer_id_type = downman_models.ResourceLocator.GVSIGOL_LAYER_ID
    #locator.ds_type = downman_models.ResourceLocator.HTTP_LINK_SOURCE_TYPE_DESC
    #file_format = _getParamValue(resource.param_values, FORMAT_PARAM_NAME)
    #locator.mime_type = _getMimeType(file_format)
    locator.request = downloadRequest
    locator.save()
    return locator
    
@csrf_exempt
def requestDownload(request):
    if request.is_ajax():
        if request.method == 'POST':
            json_data = json.loads(request.body)
            downRequest = downman_models.DownloadRequest()
            if request.user and not request.user.is_anonymous():
                downRequest.requested_by_user = request.user.email
            else:
                downRequest.requested_by_external = json_data.get('email', 'anonymous')
            downRequest.validity = downman_models.get_default_validity()
            downRequest.request_random_id = date.today().strftime("%Y%m%d") + get_random_string(length=32)
            downRequest.json_request = request.body.decode("UTF-8")
            tracking_url = reverse('download-request-tracking', args=(downRequest.request_random_id,))
            downRequest.save()
            for resource in json_data.get('resources', []):
                createResourceLocator(resource, downRequest)
            
            try:
                #processDownloadRequest(downRequest.id)
                # this requires the Celery worker to be started, see README
                processDownloadRequest.apply_async(args=[downRequest.id], queue='resolvreq') #@UndefinedVariable
                notifyReceivedRequest.apply_async(args=[downRequest.id], queue='notify') #@UndefinedVariable
            except:
                logger.exception("error queuing task")
                downRequest.request_status = downman_models.DownloadRequest.QUEUEING_ERROR
                downRequest.save()

            status_text = ''
            for (choice_code, choice_desc) in downman_models.DownloadRequest.REQUEST_STATUS_CHOICES:
                if downRequest.request_status == choice_code:
                    _status_text = _(choice_desc)

            return JsonResponse({"status_code": downRequest.request_status, "status": status_text, 'download_id': downRequest.request_random_id, 'tracking_url': tracking_url})
    # TODO: error handling
    return JsonResponse({"status": "error"})

def requestTracking(request, uuid):
    try:
        r = downman_models.DownloadRequest.objects.get(request_random_id=uuid)
        result = {}
        result['download_uuid'] =  r.request_random_id
        for (choice_code, choice_desc) in downman_models.DownloadRequest.REQUEST_STATUS_CHOICES:
                if r.request_status == choice_code:
                    result['download_status'] = _(choice_desc)
                    
        # TODO: contemplar todos los estados
        """
                    for (choice_code, choice_desc) in downman_models.DownloadRequest.REQUEST_STATUS_CHOICES:
                if downRequest.request_status == choice_code:
                    _status_text = _(choice_desc)
        """

        result['links'] = []
        links = r.downloadlink_set.all()
        result['link_count'] = len(links)
        count = 1
        for downloadlink in links:
            link = {}
            if timezone.now() > downloadlink.valid_to:
                link['status'] = _('Expired')
            else:
                valid_to = date_format(downloadlink.valid_to, 'DATETIME_FORMAT')
                link['valid_to'] = valid_to

                if downloadlink.status == downman_models.DownloadLink.PROCESSED_STATUS:
                    link['download_url'] = reverse('downman-download-resource', args=(uuid, downloadlink.link_random_id,)) 
                for (choice_code, choice_desc) in downman_models.DownloadLink.STATUS_CHOICES:
                    if downloadlink.status == choice_code:
                        link['status'] = _(choice_desc)
                linkResources = downloadlink.resourcelocator_set.all()
                if len(linkResources)==1:
                    link['name'] = u'{0:d}-{1!s}\n'.format(count, linkResources[0].name)
                else:
                    link['name'] = u'{0:2d}-{1!s}\n'.format(count, _('Prepared package'))
                count += 1
            result['links'].append(link)
        return render(request, 'track_request.html', result)
        """
            else:
                result['download_status'] = _('Your download request could not be processed.')
                result['details'] = _('You can create a new request if you are still interested on these datasets')
        elif r.request_status == downman_models.DownloadRequest.PERMANENT_PACKAGE_ERROR_STATUS:
            result['download_status'] = _('Your download request could not be processed.')
            result['details'] = _('You can create a new request if you are still interested on these datasets')
        elif r.request_status == downman_models.DownloadRequest.PENDING_AUTHORIZATION_STATUS:
            result['download_status'] = _('Your download request requires authorization from IDEUY.')
            result['details'] = _('You will receive an email when it becomes available')
        elif r.request_status == downman_models.DownloadRequest.HOLD_STATUS:
            result['download_status'] = _('Your download request requires confirmation from IDEUY.')
            result['details'] = _('You will receive an email when it becomes available')
        elif r.request_status == downman_models.DownloadRequest.REJECTED_STATUS:
            result['download_status'] = _('Sorry, your download request has been rejected.')
            result['details'] = _('You can contact IDEUY if you believe this is a mistake')
        elif r.request_status == downman_models.DownloadRequest.CANCELLED_STATUS:
            result['download_status'] = _('You have cancelled this download request.')
            result['details'] = _('You should create a new request if you are still interested on these datasets')
        else:
            result['download_status'] = _('Your download request is being prepared.')
            result['details'] = _('You will receive an email when it becomes available')
            
        return render(request, 'track_request.html', result)
        """
    except:
        logger.exception("error getting the task")
        pass
    return render(request, 'track_request.html', {'download_status': _('Your download request could not be found'), 'details': '', 'download_uuid':  uuid, 'links': []})

def getRealDownloadUrl(download_path):
    """
    Gets the public download URL for a processed download request
    """
    if os.path.exists(download_path) and download_path.startswith(TARGET_ROOT):
        rel_path = os.path.relpath(download_path, TARGET_ROOT)
        if TARGET_URL.endswith("/"): #@UndefinedVariable
            return TARGET_URL + rel_path
        return TARGET_URL + "/" + rel_path
    raise Error

def getDirectDownloadUrl(url, name):
    try:
        """
        Gets the public download URL for direct download resource
        """
        resources = resolveFileLocator(url, name)
        if len(resources)>0:
            download_path = resources[0].res_path
            if os.path.exists(download_path):
                if download_path.startswith(TARGET_ROOT):
                    rel_path = os.path.relpath(download_path, TARGET_ROOT)
                    if TARGET_URL.endswith("/"): #@UndefinedVariable
                        return TARGET_URL + rel_path
                    return TARGET_URL + "/" + rel_path
                elif download_path.startswith(DOWNLOADS_ROOT):
                    rel_path = os.path.relpath(download_path, DOWNLOADS_ROOT)
                    if DOWNLOADS_URL.endswith("/"): #@UndefinedVariable
                        return DOWNLOADS_URL + rel_path
                    return DOWNLOADS_URL + "/" + rel_path
    except:
        logger.exception("error getting download url")

def downloadResource(request, uuid, resuuid):
    try:
        link = downman_models.DownloadLink.objects.get(link_random_id=resuuid, request__request_random_id=uuid)
        
        # log download statistics
        for resourceLocator in link.resourcelocator_set.all():
            logDownload = downman_models.DownloadLog()
            logDownload.resource = resourceLocator
            logDownload.save()
            resourceLocator.download_count += resourceLocator.download_count
            resourceLocator.save()
        
        # TODO: register stats
        if link.prepared_download_path:
            logger.debug(link.prepared_download_path)
            return sendfile(request, link.prepared_download_path)
        else:
            for locator in link.resourcelocator_set.all():
                # we expect a single locator associated to the link if prepared_download_path is not defined
                return redirect(locator.resolved_url)
    except:
        logger.exception("invalid uuid - resuuid pair")
    # TODO:
    # - register stats
    # - use xsendfile
    return JsonResponse({"status": "Error"})