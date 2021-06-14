# -*- coding: utf-8 -*-

from django.shortcuts import render
from gvsigol_services.models import Layer
import logging
import json
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import ugettext as _
from django.utils.translation import get_language
from gvsigol_plugin_downloadman.tasks import processDownloadRequest, resolveFileUrl, notifyReceivedRequest, packageRequest, getDownloadResourceUrl, isRestricted
from gvsigol_plugin_downloadman import models as downman_models
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from datetime import date, datetime
from django.utils import timezone
from django.utils.formats import date_format

from django.urls import reverse
from .models import FORMAT_PARAM_NAME, SPATIAL_FILTER_GEOM_PARAM_NAME, SPATIAL_FILTER_TYPE_PARAM_NAME
from .utils import getLayer
from .settings import TARGET_URL, TARGET_ROOT, DOWNLOADS_ROOT, DOWNLOADS_URL
import os
from .tasks import Error
from django_sendfile import sendfile

from django.shortcuts import redirect
from actstream import action
from django.contrib.auth.models import User, AnonymousUser, AbstractBaseUser
from django.contrib.auth.decorators import login_required
from gvsigol_auth.utils import superuser_required, staff_required
from django.db.models import Q

from collections import namedtuple
from django.views.decorators.http import require_POST, require_GET, require_safe
from gvsigol_core.models import GolSettings
from gvsigol_plugin_downloadman.models import SETTINGS_KEY_VALIDITY, SETTINGS_KEY_MAX_PUBLIC_DOWNLOAD_SIZE, SETTINGS_KEY_SHOPPING_CART_MAX_ITEMS, SETTINGS_KEY_NOTIFICATIONS_FROM_EMAIL
from . import apps
from django.http.response import Http404
import gvsigol_core
from gvsigol_plugin_downloadman.settings import TARGET_ROOT

logger = logging.getLogger("gvsigol")

class DownloadParam():
    def __init__(self, name, title):
        self.name = name;
        self.title = title;
    
    def asDict(self):
        return {"name": self.name, "title": self.title}


class ResourceDownloadDescriptor():
    def __init__(self, layer_id, layer_name, layer_title, resource_name, resource_title, dataSourceType=downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE, resourceType=downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE, url='', directDownloadUrl=None, dataFormats=[], spatialFilterType=[], resolutions=[], scales=[], crss=[], restricted=False, size=0, nativeCrs=None):
        self.layer_id = layer_id
        self.layer_name = layer_name
        self.layer_title = layer_title
        self.name = resource_name
        self.title = resource_title
        self.dataSourceType = dataSourceType
        self.resourceType = resourceType
        self.directDownloadUrl = directDownloadUrl
        self.dataFormats = self._processOptions(dataFormats)
        self.spatialFilterType = self._processOptions(spatialFilterType)
        self.resolutions = self._processOptions(resolutions)
        self.scales = self._processOptions(scales)
        self.crss = self._processOptions(crss)
        self.url = url
        self.restricted = False
        self.nativeCrs = nativeCrs
        self.size = size
        # more params: CRSs? imagemode (raster RGB, BYTE, INT16, INT32, FLOAT32, etc)? char encoding?
    
    def _processOptions(self, params):
        processed_params = []
        for p in params:
            if isinstance(p, DownloadParam):
                processed_params.append(p)
            elif isinstance(p, str):
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
          This should produce a JSON object similar to these examples:
          
          - Example 1:
          {
            "layer_id": "asfasfasf234dfasfsa",
            "layer_name": "ortofoto_nvt2010",
            "layer_title": "Ortofoto urbana",
            "resource_type": "HTTP_LINK_TYPE",
            "data_source_type": "GEONET_DATA_SOURCE",
            "name": "RASTER_DATA_TYPE",
            "title": "Datos ráster",
            "url": "http://yourserver/geoserver/service/wms",
            "direct_download_url": '',
            "restricted": true,
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
          }
          
          - Example 2:
          {
            "layer_id": "asfasfasf234dfasfsa",
            "layer_name": "ortofoto_nvt2010",
            "layer_title": "Ortofoto urbana",
            "resource_type": "downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE",
            "data_source_type": "GEONET_DATA_SOURCE",
            "name": "RASTER_DATA_TYPE",
            "title": "Datos ráster",
            "url": "http://yourserver/geoserver/service/wms",
            "direct_download_url": '',
            "restricted": true,
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
            formats.append(f.asDict())
        params = []
        if len(formats)>0:
            params.append({
                "name": FORMAT_PARAM_NAME,
                "title": _("File format"),
                "options": formats
            })
        spatialFilterTypes = [param.asDict() for param in self.spatialFilterType]
        if len(spatialFilterTypes) > 0:
            params.append({
                "name": SPATIAL_FILTER_TYPE_PARAM_NAME,
                "title": _("Spatial filter"),
                "options": spatialFilterTypes
            })
        result = {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "layer_title": self.layer_title,
            "resource_type": self.resourceType,
            "data_source_type": self.dataSourceType,
            "name": self.name,
            "title": self.title,
            "restricted": self.restricted,
            "url": self.url,
            "params": params
        }
        
        if self.directDownloadUrl:
            result["direct_download_url"] = self.directDownloadUrl
        if self.nativeCrs:
            result["native_crs"] = self.nativeCrs
        if self.size:
            result["size"] = self.size
        #print result 
        return result
        #return json.dumps(result)

class CustomJsonEncoder(DjangoJSONEncoder):
     def default(self, obj):
        if isinstance(obj, ResourceDownloadDescriptor):
             return obj.to_json()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def getWsLayerDownloadResources(request, workspace_name, layer_name):
    try:
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace_name)
        resources = doGetLayerDownloadResources(layer, request.user)
    except:
        resources = []
    return JsonResponse(resources, encoder=CustomJsonEncoder, safe=False)


def getLayerDownloadResources(request, layer_id):
    """
    layer_id: can be the id of the layer on gvsigol/Django, or a metadata uuid from geonetwork
    """
    try:
        layer = getLayer(layer_id)
        resources = []
        if not layer or layer.allow_download:
            resources = doGetMetadataDownloadResources(layer_id, layer, request.user)
        if len(resources) == 0:
            resources = doGetLayerDownloadResources(layer, request.user)
    except:
        logger.exception("error getting layer download list")
        # TODO: error handling
        resources = []
        pass
    json_resources = json.dumps(resources, cls=CustomJsonEncoder)
    return JsonResponse(resources, encoder=CustomJsonEncoder, safe=False)

def getOgcDownloadDescriptor(layer_uuid, onlineResource, layer, fallbackTitle, dataSourceType, resourceType, dataFormats, size, nativeCrs):
    if onlineResource.name:
        resource_name = onlineResource.name
    else:
        resource_name = fallbackTitle
    if onlineResource.desc:
        resource_title = onlineResource.desc
    else:
        resource_title = fallbackTitle
    if layer and layer.name:
        layer_name = layer.name
    else:
        layer_name = resource_name
    if layer and layer.title:
        layer_title = layer.title
    else:
        layer_title = resource_title
    if resourceType == downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE:
        """
        spatialFilterType = [
            ['nofilter', _('Do not filter output')],
            ['intersects', _('Include only geometries that intersect the selected area')],
            ['within', _('Include only geometries that are within the selected area')],
            ['contains', _('Include only geometries that contain the selected area')]
        ]
        """
        spatialFilterType = [
            ['bbox', _('Include only geometries that intersect the bounding box of the selected area')],
            ['nofilter', _('Do not filter output')]
        ]
        resource_title += ' (WFS)'
    elif resourceType == downman_models.ResourceLocator.OGC_WCS_RESOURCE_TYPE:
        spatialFilterType = [
            ['bbox', _('Trim result using the bounding box of the selected area')],
            ['nofilter', _('Do not filter output')]
        ]
        resource_title += ' (WCS)'
    else:
        spatialFilterType = []
    return ResourceDownloadDescriptor(layer_uuid, layer_name, layer_title, resource_name, resource_title, dataSourceType=dataSourceType, resourceType=resourceType, dataFormats=dataFormats, spatialFilterType=spatialFilterType, url=onlineResource.url, size=size, nativeCrs=nativeCrs)
    
def doGetMetadataDownloadResources(metadata_uuid, layer = None, user = None):
    all_resources = []
    xml_md = None
    try:
        import gvsigol_plugin_catalog.service as geonetwork_service
        geonetwork_instance = geonetwork_service.get_instance()
        xml_md = geonetwork_instance.get_metadata_raw(metadata_uuid)
        from gvsigol_plugin_catalog.mdstandards import registry
        reader = registry.get_reader(xml_md)
        onlineResources = reader.get_transfer_options()
        nativeCrs = reader.get_crs()
        max_public_size = float(downman_models.get_max_public_download_size())

        if not layer:
            if xml_md:
                layer_title = reader.get_title()
                LayerTuple = namedtuple('LayerTuple', ['name', 'title'])
                layer = LayerTuple('', layer_title)
        #onlineResources = geonetwork_instance.get_online_resources(metadata_uuid)
        for onlineResource in onlineResources:
            resource = None
            if 'OGC:WFS' in onlineResource.protocol:
                resource = getOgcDownloadDescriptor(metadata_uuid,
                                                    onlineResource,
                                                    layer,
                                                    _('Vector data'),
                                                    dataSourceType = downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE,
                                                    resourceType=downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE,
                                                    dataFormats=['shape-zip', 'application/json', 'csv', 'gml2', 'gml3'],
                                                    size = onlineResource.transfer_size,
                                                    nativeCrs=nativeCrs)
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
                                                    size = onlineResource.transfer_size,
                                                    nativeCrs=nativeCrs)
                else: # assume Geoserver
                    resource = getOgcDownloadDescriptor(metadata_uuid,
                                                    onlineResource,
                                                    layer,
                                                    _('Raster data'),
                                                    dataSourceType=downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE,
                                                    resourceType=downman_models.ResourceLocator.OGC_WCS_RESOURCE_TYPE,
                                                    dataFormats=['image/geotiff', 'image/png'],
                                                    size=onlineResource.transfer_size,
                                                    nativeCrs=nativeCrs)
            elif (onlineResource.protocol.startswith('WWW:DOWNLOAD-') and onlineResource.protocol.endswith('-download')) or \
                onlineResource.protocol.startswith('FILE:'):
                # or (onlineResource.protocol.startswith('WWW:LINK-') and onlineResource.protocol.endswith('-link')) \
                #onlineResource.protocol.startswith('FILE:'):
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
                if layer and layer.name:
                    layer_name = layer.name
                else:
                    layer_name = resource_name
                if layer and layer.title:
                    layer_title = layer.title
                else:
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
                resource = ResourceDownloadDescriptor(metadata_uuid,
                                                      layer_name,
                                                      layer_title,
                                                      resource_name,
                                                      resource_title,
                                                      dataSourceType = downman_models.ResourceLocator.GEONETWORK_CATALOG_DATA_SOURCE_TYPE,
                                                      resourceType=downman_models.ResourceLocator.HTTP_LINK_RESOURCE_TYPE,
                                                      url=onlineResource.url,
                                                      directDownloadUrl=directDownloadUrl,
                                                      size = onlineResource.transfer_size,
                                                      nativeCrs=nativeCrs)
            #elif onlineResource.protocol.startswith('WWW:LINK-'):
            if resource:
                resource.restricted = isRestricted(onlineResource, max_public_size)
                all_resources.append(resource)
        if onlineResources is None or len(onlineResources) == 0:
            logger.debug(xml_md)
    except:
        logger.exception("Error getting download resources for layer")
        logger.debug(xml_md)
    return all_resources


def doGetLayerDownloadResources(layer, user):
    all_resources = []
    try:
        if layer.allow_download and layer.external == False:
            # TODO: maybe we should check permissions for request.user
            server = layer.datastore.workspace.server
            if server.type == 'geoserver':
                fqname = layer.datastore.workspace.name + ":" + layer.name if not ":" in layer.name else layer.name
                if layer.type.startswith('c_') and layer.datastore.workspace.wcs_endpoint:
                    resource = ResourceDownloadDescriptor(layer.id, fqname, layer.title, fqname, _("Raster data"), dataSourceType = downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE,  resourceType=downman_models.ResourceLocator.OGC_WCS_RESOURCE_TYPE, url=layer.datastore.workspace.wcs_endpoint, dataFormats=['image/geotiff', 'image/png'], nativeCrs=layer.native_srs)
                    all_resources.append(resource)
                elif layer.type.startswith('v_') and layer.datastore.workspace.wfs_endpoint:
                    resource = ResourceDownloadDescriptor(layer.id, fqname, layer.title, fqname, _("Vector data"),  dataSourceType = downman_models.ResourceLocator.GVSIGOL_DATA_SOURCE_TYPE, resourceType=downman_models.ResourceLocator.OGC_WFS_RESOURCE_TYPE, url=layer.datastore.workspace.wfs_endpoint, dataFormats=['shape-zip', 'application/json', 'csv', 'gml2', 'gml3'], nativeCrs=layer.native_srs)
                    all_resources.append(resource)
            elif server.type == 'mapserver':
                # TODO:
                pass    
    except:
        logger.exception("Error getting download resources for layer")
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
            try:
                downRequest = downman_models.DownloadRequest()
                """
                # if any of the resoures requires authorization:
                usage = json_data.get('downloadAuthorizationUsage', '')
                if not usage:
                    # return an error
                    pass
                """
                if request.user and not request.user.is_anonymous:
                    downRequest.requested_by_user = request.user.username
                else:
                    downRequest.requested_by_external = json_data.get('email', '')
                    if not downRequest.requested_by_external:
                        pass
                downRequest.language = get_language()
                downRequest.validity = downman_models.get_default_validity()
                downRequest.request_random_id = date.today().strftime("%Y%m%d") + get_random_string(length=32)
                downRequest.json_request = request.body.decode("UTF-8")
                tracking_url = reverse('download-request-tracking', args=(downRequest.request_random_id,))
                resources = json_data.get('resources', [])
                if downman_models.get_shopping_cart_max_items()>0 and len(resources) > downman_models.get_shopping_cart_max_items():
                    return JsonResponse({"status": "error", 'error_message': "Invalid request"})
                
                if len(resources) == 0 and json_data.get('request_desc'):
                    downRequest.pending_authorization = True
                    downRequest.generic_request = True
                    shared_view_state = json_data.get('shared_view_state')
                    shv_pid = shared_view_state.get('pid')
                    shv_state = shared_view_state.get('view_state')
                    shv_description = shared_view_state.get('description', '')
                    shv_expiration = date(9999, 12, 31)
                    shv = gvsigol_core.views.do_save_shared_view(shv_pid, shv_description, shv_state, shv_expiration, request.user, True)
                    downRequest.shared_view_url = shv.url
                downRequest.save()
                for resource in json_data.get('resources', []):
                    createResourceLocator(resource, downRequest)
            except:
                logger.exception('error creating DownloadRequest')
                raise
            
            try:
                #processDownloadRequest(downRequest.id)
                # this requires the Celery worker to be started, see README
                processDownloadRequest.apply_async(args=[downRequest.id], queue='resolvreq') #@UndefinedVariable
                notifyReceivedRequest.apply_async(args=[downRequest.id], queue='notify') #@UndefinedVariable
            except:
                logger.exception("error queuing task")
                downRequest.request_status = downman_models.DownloadRequest.QUEUEING_ERROR
                downRequest.save()

            return JsonResponse({"status_code": downRequest.request_status, "status": downRequest.status_desc, 'download_id': downRequest.request_random_id, 'tracking_url': tracking_url})
    # TODO: error handling
    return JsonResponse({"status": "error"})

def requestTracking(request, uuid):
    try:
        logger.debug(request.get_host())
        r = downman_models.DownloadRequest.objects.get(request_random_id=uuid)
        result = {}
        result['download_uuid'] =  r.request_random_id
        result['download_status'] = r.status_desc
        links_info = []
        links = r.downloadlink_set.all()
        if r.generic_request:
            raw_request = json.loads(r.json_request)
            if r.pending_authorization:
                result['pending_authorization'] = True 
            result['request_desc'] = raw_request.get('request_desc', '')
            result['organization'] = raw_request.get('organization', '')
            result['usage'] = raw_request.get('usage', '')
        else:
            count = 1
            for downloadlink in links:
                link = {}
                if timezone.now() > downloadlink.valid_to:
                    link['status'] = _('Expired')
                else:
                    valid_to = date_format(downloadlink.valid_to, 'DATETIME_FORMAT')
                    link['valid_to'] = valid_to
                    link['status'] = downloadlink.status_desc
                    link['authorization_desc'] = _('Approved')
                    if downloadlink.status == downman_models.DownloadLink.PROCESSED_STATUS:
                        url = reverse('downman-download-resource', args=(uuid, downloadlink.link_random_id))
                        logger.debug(request.build_absolute_uri(url))
                        link['download_url'] = getDownloadResourceUrl(uuid, downloadlink.link_random_id)
                        logger.debug(link['download_url']) 
                linkResources = downloadlink.resourcelocator_set.all()
                if len(linkResources)==1:
                    if downloadlink.is_auxiliary:
                        link['name'] = '{0:d}-{1!s} [{2!s}]\n'.format(count, linkResources[0].fq_title, downloadlink.name)
                    else:
                        link['name'] = '{0:d}-{1!s} [{2!s}]\n'.format(count, linkResources[0].fq_title, linkResources[0].name)
                else:
                    link['name'] = '{0:2d}-{1!s}\n'.format(count, _('Multiresource package'))
                    link['locators'] = []
                    locator_count =1
                    for locator in linkResources:
                        link['locators'].append({'name': '{0:d}-{1!s} [{2!s}]\n'.format(locator_count, locator.fq_title, locator.name)})
                        locator_count += 1
                    link['name'] = '{0:2d}-{1!s}\n'.format(count, _('Multiresource package'))
                count += 1
                links_info.append(link)
            #plain_message += _('\nThe following resources are still being processed:|n')
            for locator in r.resourcelocator_set.filter(download_links__isnull=True):
                link = {}
                link['authorization_desc'] = locator.authorization_desc
                link['status'] = locator.status_desc
                link['valid_to'] = '-'
                link['download_url'] = '-'
                link['name'] = '{0:d}-{1!s} [{2!s}]\n'.format(count, locator.fq_title, locator.name)
                links_info.append(link)
                count += 1
            if len(links_info)>0:
                result['links'] = links_info
        return render(request, 'track_request.html', result)
        """
            else:
                result['download_status'] = _('Your download request could not be processed.')
                result['details'] = _('You can create a new request if you are still interested on these datasets')
        elif r.request_status == downman_models.DownloadRequest.PERMANENT_ERROR_STATUS:
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
        download_path = resolveFileUrl(url)
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
        logger.debug("downloadResource")
        link = downman_models.DownloadLink.objects.get(link_random_id=resuuid, request__request_random_id=uuid)
        if not link.is_valid:
            return render(request, 'downman_error_page.html', {'message': _('Your download request has expired'), 'details': _('You can start a new request using the Download Service')})
        if link.status != downman_models.DownloadLink.PROCESSED_STATUS:
            return render(request, 'downman_error_page.html', {'message': _('Your download request has been cancelled'), 'details': _('You can start a new request using the Download Service')})
        link.download_count += 1
        link.save()
        
        # log download statistics
        if not link.is_auxiliary: # we don't log downloads of auxiliary files at the moment
            for resourceLocator in link.resourcelocator_set.all():
                resourceLocator.download_count += 1
                resourceLocator.save()
                # We can't directly send an action based on the ResouceLocatorn, because the same layer and resource is represented using several ResourceLocators,
                # so we need to create proxy log tables
                try: 
                    ldown_log = downman_models.LayerProxy.objects.get(layer_id=resourceLocator.layer_id, layer_id_type=resourceLocator.layer_id_type)
                except:
                    ldown_log = downman_models.LayerProxy()
                    ldown_log.layer_id = resourceLocator.layer_id
                    ldown_log.layer_id_type = resourceLocator.layer_id_type
                ldown_log.name = resourceLocator.layer_name
                ldown_log.title = resourceLocator.layer_title
                ldown_log.title_name = resourceLocator.layer_title + '[' + resourceLocator.name + ']'
                ldown_log.save()
                try:
                    lrdown_log = downman_models.LayerResourceProxy.objects.get(layer=ldown_log, name=resourceLocator.name)
                except:
                    lrdown_log = downman_models.LayerResourceProxy()
                    lrdown_log.name = resourceLocator.name
                    lrdown_log.layer = ldown_log
                lrdown_log.title = resourceLocator.title
                lrdown_log.fq_name = resourceLocator.fq_name
                lrdown_log.fq_title_name = resourceLocator.fq_title_name
                lrdown_log.fq_title = resourceLocator.fq_title
                lrdown_log.save()
                if link.request.requested_by_user:
                    user = User.objects.get(username=link.request.requested_by_user)
                    action.send(user, verb="gvsigol_plugin_downloadman/layer_resource_downloaded", action_object=lrdown_log)
                    action.send(user, verb="gvsigol_plugin_downloadman/layer_downloaded", action_object=ldown_log)
                else:
                    action.send(lrdown_log, verb="gvsigol_plugin_downloadman/layer_resource_downloaded", action_object=lrdown_log)
                    action.send(ldown_log, verb="gvsigol_plugin_downloadman/layer_downloaded", action_object=ldown_log)

        if link.prepared_download_path:
            # ensure the file is contained in DOWNLOADS_ROOT or TARGET_ROOT folders
            if os.path.relpath(link.prepared_download_path, DOWNLOADS_ROOT)[:2] != '..' or os.path.relpath(link.prepared_download_path, TARGET_ROOT)[:2] != '..':
                logger.debug("using sendfile: " + link.prepared_download_path)
                return sendfile(request, link.prepared_download_path, attachment=True)
        else:
            if link.resolved_url:
                return redirect(link.resolved_url) 
            logger.debug("going to use redirect")
            for locator in link.resourcelocator_set.all():
                logger.debug("using redirect: " + locator.resolved_url)
                # we expect a single locator associated to the link if prepared_download_path is not defined
                return redirect(locator.resolved_url)
    except:
        logger.exception("invalid uuid - resuuid pair")
    return render(request, 'downman_error_page.html', {'message': _('The resource could not be found'), 'details': _('Contact the service administrators if you believe this is an error')})


def render_settings(request):
    response = {
        'download_requests': [],
        'activetab': "settings",
        'archived_class': "",
        'validity': downman_models.get_default_validity(),
        'max_public_download_size': downman_models.get_max_public_download_size(),
        'shopping_cart_max_items': downman_models.get_shopping_cart_max_items(),
        'notifications_admin_emails': ",".join(downman_models.get_notifications_admin_emails())
    }
    return render(request, 'downman_index.html', response)

@require_safe
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def dashboard_index(request):
    selected_tab = request.GET.get("tab", "pendingauth")
    now = timezone.now()
    if selected_tab == "settings":
        return render_settings(request)
    elif selected_tab == "pendingauth":
        request_list = downman_models.DownloadRequest.objects.filter(pending_authorization=True)
    elif selected_tab == "archived":
        request_list = downman_models.DownloadRequest.objects.exclude( \
            (Q(downloadlink__valid_to__gte=now) &
             Q(downloadlink__status=downman_models.DownloadLink.PROCESSED_STATUS)) | \
            (Q(resourcelocator__canceled=False) & \
            (Q(resourcelocator__status=downman_models.ResourceLocator.RESOURCE_QUEUED_STATUS) | \
            Q(resourcelocator__status=downman_models.ResourceLocator.WAITING_SPACE_STATUS) | \
            Q(resourcelocator__status=downman_models.ResourceLocator.TEMPORAL_ERROR_STATUS) | \
            Q(resourcelocator__status=downman_models.ResourceLocator.HOLD_STATUS)))).distinct()

    else: # "active"
        request_list = downman_models.DownloadRequest.objects.filter( \
            (Q(downloadlink__valid_to__gte=now) &
             Q(downloadlink__status=downman_models.DownloadLink.PROCESSED_STATUS)) | \
            (Q(resourcelocator__canceled=False) & \
            (Q(resourcelocator__status=downman_models.ResourceLocator.RESOURCE_QUEUED_STATUS) | \
            Q(resourcelocator__status=downman_models.ResourceLocator.WAITING_SPACE_STATUS) | \
            Q(resourcelocator__status=downman_models.ResourceLocator.TEMPORAL_ERROR_STATUS) | \
            Q(resourcelocator__status=downman_models.ResourceLocator.HOLD_STATUS)))).distinct()
    
    if not request.user.is_superuser:
        request_list = request_list.filter(requested_by_user__exact=request.user.username)
    request_list.order_by('-id', 'request_status')
    response = {
        'download_requests': request_list,
        'activetab': selected_tab
    }
    return render(request, 'downman_index.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def update_request(request, request_id):
    try:
        download_request = downman_models.DownloadRequest.objects.get(pk=int(request_id))
        raw_request = json.loads(download_request.json_request)
        usage = raw_request.get('usage')
        organization = raw_request.get('organization')
        request_desc = raw_request.get('request_desc', '')
        response = {
            'download_request': download_request,
            'usage': usage,
            'organization': organization,
            'request_desc': request_desc
            }
        return render(request, 'download_request_update.html', response)
    except:
        logger.exception("Error")
        raise Http404

@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def settings_store(request):
    validity = int(request.POST.get('validity'))
    max_public_download_size = int(request.POST.get('max_public_download_size'))
    shopping_cart_max_items =  int(request.POST.get('shopping_cart_max_items'))
    notifications_admin_emails = request.POST.get('notifications_admin_emails')
    GolSettings.objects.set_value(apps.PLUGIN_NAME, SETTINGS_KEY_VALIDITY, validity)
    GolSettings.objects.set_value(apps.PLUGIN_NAME, SETTINGS_KEY_MAX_PUBLIC_DOWNLOAD_SIZE, max_public_download_size)
    GolSettings.objects.set_value(apps.PLUGIN_NAME, SETTINGS_KEY_SHOPPING_CART_MAX_ITEMS, shopping_cart_max_items)
    GolSettings.objects.set_value(apps.PLUGIN_NAME, SETTINGS_KEY_NOTIFICATIONS_FROM_EMAIL, notifications_admin_emails)
    return redirect(reverse('downman-dashboard-index') + "?tab=settings")

@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def cancel_locator(request, resource_id):
    try:
        resource = downman_models.ResourceLocator.objects.get(pk=int(resource_id))
        resource.canceled = True
        resource.save()
        for link in resource.download_links.all():
            link.status = downman_models.DownloadLink.ADMIN_CANCELED_STATUS
            link.save()
            pending_locators = 0
            for locator in link.resourcelocator_set.all():
                if (not locator.canceled) and locator.status == downman_models.ResourceLocator.PROCESSED_STATUS:
                    locator.status = downman_models.ResourceLocator.RESOURCE_QUEUED_STATUS
                    locator.save()
                    pending_locators += 1
            if pending_locators:
                packageRequest.apply_async(args=[resource.request.pk], queue='package') #@UndefinedVariable
        return redirect(reverse('downman-update-request', args=(resource.request.pk,)))
    except:
        logger.exception("Error")
        raise Http404

@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def cancel_link(request, link_id):
    try:
        download_link = downman_models.DownloadLink.objects.get(pk=int(link_id))
        download_link.status = downman_models.DownloadLink.ADMIN_CANCELED_STATUS
        download_link.save()

        for locator in download_link.resourcelocator_set.all():
            locator.canceled = True
            locator.status = downman_models.ResourceLocator.PROCESSED_STATUS
            locator.save()
        return redirect(reverse('downman-update-request', args=(download_link.request.pk,)))
    except:
        logger.exception("Error")
        raise Http404

@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def cancel_request(request, request_id):
    try:
        download_request = downman_models.DownloadRequest.objects.get(pk=int(request_id))
        download_request.status = downman_models.DownloadRequest.COMPLETED_STATUS
        download_request.save()
        
        for download_link in download_request.downloadlink_set.all():
            download_link.status = downman_models.DownloadLink.ADMIN_CANCELED_STATUS
            download_link.save()

        for locator in download_request.resourcelocator_set.all():
            locator.canceled = True
            locator.status = downman_models.ResourceLocator.PROCESSED_STATUS
            locator.save()
        return redirect(reverse('downman-update-request', args=(locator.request.pk,)))
    except:
        logger.exception("Error")
        raise Http404


@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def accept_resource_authorization(request, resource_id):
    try:
        resource = downman_models.ResourceLocator.objects.get(pk=int(resource_id))
        resource.authorization = downman_models.ResourceLocator.AUTHORIZATION_ACCEPTED
        resource.save()
        processDownloadRequest.apply_async(args=[resource.request.pk], queue='resolvreq') #@UndefinedVariable
        return redirect(reverse('downman-update-request', args=(resource.request.pk,)))
    except:
        logger.exception("Error")
        raise Http404
    

@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def reject_resource_authorization(request, resource_id):
    try:
        resource = downman_models.ResourceLocator.objects.get(pk=int(resource_id))
        resource.authorization = downman_models.ResourceLocator.AUTHORIZATION_REJECTED
        resource.save()
        processDownloadRequest.apply_async(args=[resource.request.pk], queue='resolvreq') #@UndefinedVariable
        return redirect(reverse('downman-update-request', args=(resource.request.pk,)))
    except:
        logger.exception("Error")
        raise Http404
    
@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def complete_generic_request(request, request_id):
    try:
        request = downman_models.DownloadRequest.objects.get(pk=int(request_id))
        logger.debug('complete_generic_request - request.pending_authorization = False')
        request.pending_authorization = False
        request.request_status = downman_models.DownloadRequest.COMPLETED_STATUS
        request.save()
        # processDownloadRequest.apply_async(args=[resource.request.pk], queue='resolvreq') #@UndefinedVariable
        return redirect(reverse('downman-update-request', args=(request.pk,)))
    except:
        logger.exception("Error")
        raise Http404

    
@require_POST
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def reject_generic_request(request, request_id):
    try:
        request = downman_models.DownloadRequest.objects.get(pk=int(request_id))
        logger.debug('reject_generic_request - request.pending_authorization = False')
        request.pending_authorization = False
        request.request_status = downman_models.DownloadRequest.REJECTED_STATUS
        request.save()
        # processDownloadRequest.apply_async(args=[resource.request.pk], queue='resolvreq') #@UndefinedVariable
        return redirect(reverse('downman-update-request', args=(request.pk,)))
    except:
        logger.exception("Error")
        raise Http404

def get_conf(request):
    response = {
        "shopping_cart_max_items": downman_models.get_shopping_cart_max_items()
        }
    return JsonResponse(response)
