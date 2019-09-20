# -*- coding: utf-8 -*-

from django.shortcuts import render
from gvsigol_services.models import Layer
import gvsigol_plugin_catalog.service as geonetwork_service
import logging
from gvsigol_plugin_catalog.models import LayerMetadata
from owslib import crs
from django.conf.locale.ar import formats
import json
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import ugettext as _
from gvsigol_plugin_downloadman.tasks import processDownloadRequest
from gvsigol_plugin_downloadman import models as downman_models
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from datetime import date
from django.core.urlresolvers import reverse
from django.http import HttpResponse


DATA_TYPE_VECTOR = 'VECTOR_DATA_TYPE'
DATA_TYPE_RASTER = 'RASTER_DATA_TYPE'
DATA_TYPE_OTHER = 'OTHER_DATA_TYPE'

FORMAT_PARAM_NAME = 'format'


logger = logging.getLogger("gvsigol")

class DownloadParam():
    def __init__(self, name, title):
        self.name = name;
        self.title = title;

class ResourceDownloadDescriptor():
    def __init__(self, layer_id, layer_name, layer_title, resource_name, resource_title, dataType=DATA_TYPE_VECTOR, direct_download_url='', dataFormats=[], resolutions=[], scales=[], crss=[]):
        self.layer_id = layer_id;
        self.layer_name = layer_name;
        self.layer_title = layer_title;
        self.name = resource_name;
        self.title = resource_title
        self.dataType = dataType
        self.dataFormats = self._processOptions(dataFormats)
        self.resolutions = self._processOptions(resolutions)
        self.scales = self._processOptions(scales)
        self.crss = self._processOptions(crss)
        self.direct_download_url = direct_download_url
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
    
    def getDataType(self):
        return self.dataType
    
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
            "name": "RASTER_DATA_TYPE",
            "title": "Datos ráster",
            "direct_download": false,
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
        params = [{
                "name": FORMAT_PARAM_NAME,
                "title": _("File format"),
                "options": formats
            }]
        result = {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "layer_title": self.layer_title,
             "name": self.name, "title": self.title, "direct_download_url": self.direct_download_url, "params": params}
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
        resources = doGetLayerDownloadResources(layer, request.user)
    except:
        # TODO: error handling
        resources = []
        pass
    print resources
    json_resources = json.dumps(resources, cls=CustomJsonEncoder)
    print json_resources
    return JsonResponse(resources, encoder=CustomJsonEncoder, safe=False)

    """
    try:
        geonetwork_instance = geonetwork_service.get_instance()
        onlineResources = geonetwork_instance.get_online_resources(metadata_uuid)
        for onlineResource in onlineResources:
            if 'OGC:WFS' in onlineResource.protocol:
                params = DownloadParams(DATA_TYPE_VECTOR, ['shape-zip', 'application/json', 'csv', 'gml2', 'gml3'])
                all_params.append(params)
            if 'OGC:WCS' in onlineResource.protocol:
                if 'Geoserver' in onlineResource.app_profile:
                    params = DownloadParams(DATA_TYPE_RASTER, ['image/geotiff', 'image/png'])
                    all_params.append(params)
                if 'Mapserver' in onlineResource.app_profile:
                    # necesitamos ofrecer el formato adecuado para el tipo de imagen (ortofoto, ráster de temperaturas, ráster cualitativo, etc)
                    params = DownloadParams(DATA_TYPE_RASTER, ['GEOTIFF_16', 'GEOTIFF_32', 'GEOTIFF_8'])
                    all_params.append(params)
    except:
        pass
    return all_params
    """

def doGetLayerDownloadResources(layer, user):
    all_resources = []
    try:
        if layer.allow_download:
            # TODO: maybe we should check permissions for request.user
            server = layer.datastore.workspace.server
            if server.type == 'geoserver':
                if layer.external == False:
                    if layer.type.startswith('c_'):
                        resource = ResourceDownloadDescriptor(layer.id, layer.name, layer.title, DATA_TYPE_RASTER, _("Raster data"), DATA_TYPE_RASTER, dataFormats=['image/geotiff', 'image/png'])
                        all_resources.append(resource)
                    elif layer.type.startswith('v_'):
                        resource = ResourceDownloadDescriptor(layer.id, layer.name, layer.title, DATA_TYPE_VECTOR, _("Vector data"), DATA_TYPE_VECTOR, dataFormats=['shape-zip', 'application/json', 'csv', 'gml2', 'gml3'])
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

def getLayer(id_or_uuid):
    try:
        django_id = int(id_or_uuid)
        return Layer.objects.get(id=django_id)
    except:
        try:
            lm = LayerMetadata.objects.get(metadata_uuid=id_or_uuid)
            return lm.layer
        except:
            logger.exception("Error retrieving layer metadata with uuid: " + id_or_uuid)
            pass

def _getParam(params, name):
    for param in params:
        if param.name == name:
            return param
        
def _getParamValue(params, name):
    for param in params:
        if param.get('name') == name:
            return param.get('value')

def _getWfsRequest(layer_name, baseUrl, params):
    file_format = _getParamValue(params, FORMAT_PARAM_NAME)
    if not file_format:
        file_format = 'shape-zip'
    return baseUrl + '?service=WFS&version=1.0.0&request=GetFeature&typeName=' + layer_name + '&outputFormat='+ file_format

def _getWcsRequest(layer_name, baseUrl, params):
    url = baseUrl + '?service=WCS&version=2.0.0&request=GetCoverage&CoverageId=' + layer_name
    file_format = _getParamValue(params, FORMAT_PARAM_NAME)
    if file_format:
        url += '&format=' + file_format
    return url

def _getMimeType(file_format):
    # TODO
    return file_format

def createResourceLocator(resource, downloadRequest):
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
    #locator.res_id = resource_descriptor.get('layer_id')
    locator.name = resource_descriptor.get('layer_name')
    #locator.res_internal_id = resource.download_id
    locator.ds_type = downman_models.ResourceLocator.HTTP_LINK_SOURCE_TYPE
    locator.layer_id =  resource_descriptor.get('layer_id')
    layer = getLayer(locator.layer_id)
    locator.name =  layer.name
    locator.title = layer.title
    locator.laye_id_type = downman_models.ResourceLocator.GVSIGOL_LAYER_ID
    params = resource.get('param_values', [])
    if layer and resource_descriptor.get('name') == DATA_TYPE_VECTOR:
        baseUrl = layer.datastore.workspace.wfs_endpoint
        locator.data_source = _getWfsRequest(layer.name, baseUrl, params)
    elif layer and resource_descriptor.get('name') == DATA_TYPE_RASTER:
        baseUrl = layer.datastore.workspace.wcs_endpoint
        locator.data_source = _getWcsRequest(layer.name, baseUrl, params)
    else:
        # TODO: error management
        pass

    print locator.data_source
    #file_format = _getParamValue(resource.param_values, FORMAT_PARAM_NAME)
    #locator.mime_type = _getMimeType(file_format)
    locator.request = downloadRequest
    locator.save()
    return locator
    
@csrf_exempt
def requestDownload(request):
    if request.is_ajax():
        if request.method == 'POST':
            print 'Raw Data: "%s"' % request.body
            json_data = json.loads(request.body)
            print json_data
            downRequest = downman_models.DownloadRequest()
            if request.user and not request.user.is_anonymous():
                downRequest.requested_by = request.user.email
            else:
                downRequest.requested_by_external = json_data.get('email', 'anonymous')
            downRequest.validity = downman_models.get_default_validity()
            downRequest.pending_authorization = False
            downRequest.request_status = downman_models.DownloadRequest.PACKAGE_QUEUED_STATUS;
            downRequest.request_random_id = date.today().strftime("%Y%m%d") + get_random_string(length=32)
            downRequest.json_request = request.body.decode("UTF-8")
            downRequest.save()
            
            for resource in json_data.get('resources', []):
                createResourceLocator(resource, downRequest)
            
            try:
                #processDownloadRequest(downRequest.id)
                result = processDownloadRequest.delay(downRequest.id)
                tracking_url = reverse('download-request-tracking', args=(downRequest.request_random_id,))
                print(result.backend)
            except:
                logger.exception("error queuing task")
                downRequest.request_status = downman_models.DownloadRequest.PERMANENT_PACKAGE_ERROR_STATUS
                downRequest.save()
                tracking_url = ''

            print "volviendo"
            status_text = ''
            for (choice_code, choice_desc) in downman_models.DownloadRequest.REQUEST_STATUS_CHOICES:
                if downRequest.request_status == choice_code:
                    _status_text = _(choice_desc)

            return JsonResponse({"status_code": downRequest.request_status, "status": status_text, 'download_id': downRequest.request_random_id, 'tracking_url': tracking_url})
    # TODO: error handling
    return JsonResponse({"status": "error"})

def requestTracking(request, uuid):
    # TODO: return a proper template
    try:
        r = downman_models.DownloadRequest.objects.get(request_random_id=uuid)
        # TODO: contemplar todos los estados
        if r.request_status == downman_models.DownloadRequest.COMPLETED_STATUS:
            return HttpResponse("Ready")
        if r.request_status == downman_models.DownloadRequest.PERMANENT_PACKAGE_ERROR_STATUS:
            return HttpResponse("Error de empaquetado")
        else:
            return HttpResponse("En preparación")
    except:
        logger.exception("error getting the task")
        pass
    return HttpResponse("Petición de descarga no encontrada")

def downloadLink(request, uuid):
    pass
