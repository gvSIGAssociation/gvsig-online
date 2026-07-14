    # -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from gvsigol import settings
import requests
import json
import logging
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)


def _gwc_rest_timeout():
    return int(getattr(settings, 'GWC_REST_TIMEOUT', 20))

class RequestError(Exception):
    def __init__(self, status_code=-1, server_message=""):
        self.status_code = status_code
        self.server_message = server_message
        self.message = None
    
    def set_message(self, message):
        self.message = message
    
    def get_message(self):
        if self.message:
            return self.message
        else:
            return self.server_message

    def get_detailed_message(self):
        from builtins import str as text
        msg = 'Status: ' + text(self.status_code)
        if isinstance(self.server_message, str):
            msg += '\nServer message: ' + self.server_message
        else:
            msg += '\nServer message: ' + self.server_message.decode('utf-8', 'replace')
        if self.message:
            if isinstance(self.message, str):
                msg += '\nMessage: ' + self.message
            else:
                msg += '\nMessage: ' + self.message.decode('utf-8', 'replace')
        return msg

class UploadError(RequestError):
    pass

class ConflictingDataError(RequestError):
    pass

class AmbiguousRequestError(RequestError):
    pass

class FailedRequestError(RequestError):
    pass


def _default_external_wms_style_name(external_params):
    styles = external_params.get('styles') or []
    for style in styles:
        if isinstance(style, dict) and style.get('is_default'):
            name = (style.get('name') or '').strip()
            if name:
                return name
    for style in styles:
        if isinstance(style, dict):
            name = (style.get('name') or '').strip()
            if name:
                return name
    return ''


def _append_external_wms_backend_options(xml, external_params, grid_subsets=None):
    """
    Append GWC backend WMS options for external cached layers.
    external_params.version is stored when the layer is created/updated in views.py
    but was not forwarded to GeoWebCache (defaulted to WMS 1.1.1).

    Do not force a fixed CRS when the cached layer is registered with multiple
    gridsets. GeoWebCache must request the remote WMS using the CRS that matches
    each requested tile matrix. A fixed CRS here can make GWC request, for
    example, EPSG:25830 tiles while forcing CRS=EPSG:3857 in the backend WMS
    request.
    """
    wms_version = (external_params.get('version') or '1.1.1').strip()
    wms_style = _default_external_wms_style_name(external_params)

    if wms_style:
        xml += "<wmsStyles>" + escape(wms_style) + "</wmsStyles>"
    if wms_version:
        xml += "<wmsVersion>" + escape(wms_version) + "</wmsVersion>"

    vendor_parameters = []

    if wms_version.startswith('1.3'):
        selected_gridsets = [_normalize_crs_key(gs) for gs in (grid_subsets or [])]
        selected_gridsets = [gs for gs in selected_gridsets if gs]

        if len(selected_gridsets) == 1:
            vendor_parameters.append('CRS=' + selected_gridsets[0])

        vendor_parameters.append('EXCEPTIONS=XML')

    if vendor_parameters:
        xml += "<vendorParameters>" + escape('&'.join(vendor_parameters)) + "</vendorParameters>"

    return xml


def _normalize_crs_key(value):
    if value is None:
        return ''
    value = str(value).strip().upper()
    if not value:
        return ''
    if value.isdigit():
        return 'EPSG:' + value
    return value


def _crs_bounds_map(crs_list):
    crs_bounds = {}
    for crs in crs_list or []:
        key = _normalize_crs_key(crs.get('key'))
        value = crs.get('value')
        if key and value:
            crs_bounds[key] = value
    return crs_bounds


class APIGeoWebCache():
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        
    def get_session(self):
        return self.session
    
    def get_layer(self, ws, layer, server, master_node_url):
        layer_name = None
        if ws is None:
            layer_name = layer.name
        else:
            layer_name = ws + ":" + layer.name
            
        api_url = master_node_url + "/gwc/rest/layers/" + layer_name + ".json"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.get(api_url, headers=headers, auth=auth, timeout=_gwc_rest_timeout())
        if response.status_code==200:
            return json.loads(response.content)
        
        raise FailedRequestError(response.status_code, response.content)
    
    def get_group(self, group, server, master_node_url):
            
        api_url = master_node_url + "/gwc/rest/layers/" + group.name + ".json"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.get(api_url, headers=headers, auth=auth, timeout=_gwc_rest_timeout())
        if response.status_code==200:
            return json.loads(response.content)
        
        raise FailedRequestError(response.status_code, response.content)
    
    def _get_gridset_names(self, server, master_node_url):
        """Return GeoWebCache gridset names advertised by the target GeoServer.
        Falls back to configured defaults if the REST endpoint cannot be read.
        """
        api_url = master_node_url + "/gwc/rest/gridsets.json"
        auth = (server.user, server.password)
        headers = {'accept': 'application/json'}
        try:
            response = self.session.get(api_url, headers=headers, auth=auth, timeout=_gwc_rest_timeout())
            if response.status_code != 200:
                raise FailedRequestError(response.status_code, response.content)
            data = json.loads(response.content)
            gridsets = data.get('gridSets') or data.get('gridsets') or data
            items = []
            if isinstance(gridsets, dict):
                items = gridsets.get('gridSet') or gridsets.get('gridsets') or gridsets.get('items') or []
            elif isinstance(gridsets, list):
                items = gridsets

            names = []
            for item in items:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('id')
                else:
                    name = item
                name = _normalize_crs_key(name)
                if name:
                    names.append(name)
            if names:
                return set(names)
        except Exception:
            logger.warning("Could not read GeoWebCache gridsets. Falling back to CACHE_OPTIONS['GRID_SUBSETS']", exc_info=True)

        return set(_normalize_crs_key(gs) for gs in settings.CACHE_OPTIONS.get('GRID_SUBSETS', []))

    def _select_external_wms_gridsets(self, layer, crs_list, available_gridsets):
        """Select safe GWC gridsets for an external WMS cached layer.

        External WMS layers should not inherit every GeoWebCache default gridset.
        Prefer global/web gridsets when the remote WMS advertises them, and only
        fall back to the native/local CRS when no preferred global gridset is usable.
        This avoids choosing local gridsets such as EPSG:25830 for base layers when
        EPSG:3857/EPSG:4326 are available.

        For WMS 1.3.x backends, keep a single gridset by default. GeoWebCache
        cannot vary vendorParameters per tile matrix, and some strict WMS 1.3
        services require CRS instead of SRS. Keeping one gridset lets us send a
        CRS vendor parameter that matches the selected cache gridset.
        """
        crs_bounds = _crs_bounds_map(crs_list)
        supported = set(crs_bounds.keys())
        available = set(_normalize_crs_key(gs) for gs in available_gridsets)
        external_params = json.loads(layer.external_params) if layer.external_params else {}
        wms_version = (external_params.get('version') or '1.1.1').strip()
        single_gridset = (
            wms_version.startswith('1.3')
            and getattr(settings, 'EXTERNAL_WMS_CACHE_SINGLE_GRIDSET_WMS13', True)
        )

        explicit = getattr(settings, 'EXTERNAL_WMS_CACHE_GRID_SUBSETS', None)
        priority = explicit or getattr(
            settings,
            'EXTERNAL_WMS_CACHE_GRIDSET_PRIORITY',
            ['EPSG:3857', 'EPSG:4326', 'EPSG:900913'],
        )
        priority = [_normalize_crs_key(gs) for gs in priority]

        selected = [gs for gs in priority if gs in available and gs in supported]
        if selected:
            return (selected[:1] if single_gridset else selected), crs_bounds

        native_srs = _normalize_crs_key(getattr(layer, 'native_srs', None) or external_params.get('srs'))
        if native_srs and native_srs in available and native_srs in supported:
            return [native_srs], crs_bounds

        excluded = set(
            _normalize_crs_key(gs)
            for gs in getattr(settings, 'EXTERNAL_WMS_CACHE_EXCLUDED_GRID_SUBSETS', ['EPSG:4258'])
        )
        configured = [_normalize_crs_key(gs) for gs in settings.CACHE_OPTIONS.get('GRID_SUBSETS', [])]
        selected = [gs for gs in configured if gs in available and gs in supported and gs not in excluded]
        return (selected[:1] if single_gridset else selected), crs_bounds

    def add_layer(self, ws, layer, server, master_node_url, crs_list):
        layer_name = None
        wms_layers = None
        url = None
        external_params = None
        if layer.external:
            layer_name = layer.name
            external_params = json.loads(layer.external_params)
            wms_layers = external_params.get('layers')

            url = (external_params.get('get_map_url') or external_params.get('url') or '').strip()
            if not url:
                logger.error(
                    "GWC add_layer: external layer %s has no get_map_url or url",
                    getattr(layer, "name", layer),
                )
                raise FailedRequestError(
                    -1,
                    "External cached layer needs get_map_url or url (WMS GetMap endpoint) to register in GeoWebCache.",
                )
            if not wms_layers:
                raise FailedRequestError(
                    -1,
                    "External cached layer needs 'layers' (remote WMS layer name)",
                )
        else:
            layer_name = ws + ":" + layer.name
            wms_layers = layer_name
            url = server.getWmsEndpoint()

        if layer.external:
            available_gridsets = self._get_gridset_names(server, master_node_url)
            grid_subsets, crs_bounds = self._select_external_wms_gridsets(layer, crs_list, available_gridsets)
            if not grid_subsets:
                raise FailedRequestError(
                    -1,
                    "No compatible GeoWebCache gridsets found for external WMS layer %s" % layer_name,
                )
            meta_width = int(getattr(settings, 'EXTERNAL_WMS_CACHE_META_TILING_X', 1))
            meta_height = int(getattr(settings, 'EXTERNAL_WMS_CACHE_META_TILING_Y', 1))
            concurrency = int(getattr(settings, 'EXTERNAL_WMS_CACHE_CONCURRENCY', 2))
        else:
            grid_subsets = [_normalize_crs_key(gs) for gs in settings.CACHE_OPTIONS['GRID_SUBSETS']]
            crs_bounds = _crs_bounds_map(crs_list)
            meta_width = None
            meta_height = None
            concurrency = None

        xml = ""
        xml += "<wmsLayer>"
        xml +=  "<name>" + escape(layer_name) + "</name>"
        xml +=  "<mimeFormats>"
        xml +=      "<string>image/png</string>"
        xml +=  "</mimeFormats>"
        xml +=  "<gridSubsets>"
        for gs in grid_subsets:
            xml +=  "<gridSubset>"
            xml +=      "<gridSetName>" + escape(gs) + "</gridSetName>"
            bounds_value = crs_bounds.get(gs)
            if bounds_value:
                bounds = bounds_value.split(';')
                if len(bounds) == 4:
                    xml +=  "<extent>"
                    xml +=      "<coords>"
                    xml +=          "<double>" + escape(bounds[0]) + "</double>"
                    xml +=          "<double>" + escape(bounds[1]) + "</double>"
                    xml +=          "<double>" + escape(bounds[2]) + "</double>"
                    xml +=          "<double>" + escape(bounds[3]) + "</double>"
                    xml +=      "</coords>"
                    xml +=  "</extent>"
            xml +=      "<zoomStart>0</zoomStart>"
            xml +=      "<zoomStop>" + str(settings.MAX_ZOOM_LEVEL) + "</zoomStop>"
            xml +=  "</gridSubset>"
        xml +=  "</gridSubsets>"
        if meta_width is not None and meta_height is not None:
            xml +=  "<metaWidthHeight>"
            xml +=      "<int>" + str(meta_width) + "</int>"
            xml +=      "<int>" + str(meta_height) + "</int>"
            xml +=  "</metaWidthHeight>"
        xml +=  "<wmsUrl>"
        xml +=      "<string>" + escape(url) + "</string>"
        xml +=  "</wmsUrl>"
        xml +=  "<wmsLayers>" + escape(wms_layers) + "</wmsLayers>"
        if layer.external and external_params is not None:
            xml = _append_external_wms_backend_options(
                xml,
                external_params,
                grid_subsets=grid_subsets,
            )
        if concurrency is not None:
            xml += "<gutter>0</gutter>"
            xml += "<concurrency>" + str(concurrency) + "</concurrency>"
        xml += "</wmsLayer>"
        api_url = master_node_url + "/gwc/rest/layers/" + layer_name + ".xml"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'text/xml'}
        response = self.session.put(api_url, data=xml.encode('utf-8'), headers=headers, auth=auth, timeout=_gwc_rest_timeout())
        if response.status_code==200:
            return True
        raise FailedRequestError(response.status_code, response.content)
    
    def modify_layer(self, ws, layer, server, master_node_url):
        layer_name = None
        if ws is None:
            layer_name = layer.name
        else:
            layer_name = ws + ":" + layer.name

        xml = ""
        xml += "<wmsLayer>"
        xml +=  "<name>" + layer_name + "</name>"
        xml +=  "<mimeFormats>"
        xml +=      "<string>image/png</string>"
        xml +=  "</mimeFormats>"
        xml +=  "<gridSubsets>"
        xml +=      "<gridSubset>"
        xml +=          "<gridSetName>EPSG:3857</gridSetName>"
        xml +=      "</gridSubset>"
        xml +=  "</gridSubsets>"
        xml +=  "<wmsUrl>"
        xml +=      "<string>" + server.getWmsEndpoint() + "</string>"
        xml +=  "</wmsUrl>"
        xml +=  "<wmsLayers>" + layer_name + "</wmsLayers>"
        xml += "</wmsLayer>"
        
        api_url = master_node_url + "/gwc/rest/layers/" + layer_name + ".xml"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'text/xml'}
        response = self.session.post(api_url, data=xml.encode(), headers=headers, auth=auth, timeout=_gwc_rest_timeout())
        if response.status_code==200:
            return True
        
        raise FailedRequestError(response.status_code, response.content)
    
    def delete_layer(self, ws, layer, server, master_node_url):
        layer_name = None
        if ws is None:
            layer_name = layer.name
        else:
            layer_name = ws + ":" + layer.name
            
        api_url = master_node_url + "/gwc/rest/layers/" + layer_name + ".xml"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'text/xml'}
        response = self.session.delete(api_url, headers=headers, auth=auth, timeout=_gwc_rest_timeout())
        if response.status_code in (200, 204, 404):
            return True
        
        raise FailedRequestError(response.status_code, response.text)
    
    def execute_cache_operation(self, ws, layer, server, url, minx, miny, maxx, maxy, grid_set, zoom_start, zoom_stop, format, op_type, thread_count):
        layer_name = None
        if ws is None:
            layer_name = layer.name
        else:
            layer_name = ws + ":" + layer.name
            
        xml = ""
        xml += "<seedRequest>"
        xml +=  "<name>" + layer_name + "</name>"
        if minx != 'null' and miny != 'null' and maxx != 'null' and maxy != 'null':
            xml +=  "<bounds>"
            xml +=      "<coords>"
            xml +=          "<double>" + minx + "</double>"
            xml +=          "<double>" + miny + "</double>"
            xml +=          "<double>" + maxx + "</double>"
            xml +=          "<double>" + maxy + "</double>"
            xml +=      "</coords>"
            xml +=  "</bounds>"
        xml +=  "<gridSetId>" + grid_set + "</gridSetId>"
        xml +=  "<zoomStart>" + zoom_start + "</zoomStart>"
        xml +=  "<zoomStop>" + zoom_stop + "</zoomStop>"
        xml +=  "<format>" + format + "</format>"
        xml +=  "<type>" + op_type + "</type>"
        xml +=  "<threadCount>" + thread_count + "</threadCount>"
        xml += "</seedRequest>"
        
        api_url = url + "/gwc/rest/seed/" + layer_name + ".xml"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'text/xml'}
        response = self.session.post(api_url, data=xml, headers=headers, auth=auth)
        if response.status_code==200:
            return True
        
        raise FailedRequestError(response.status_code, response.content)
    
    def execute_group_cache_operation(self, group, server, url, minx, miny, maxx, maxy, grid_set, zoom_start, zoom_stop, format, op_type, thread_count):      
        xml = ""
        xml += "<seedRequest>"
        xml +=  "<name>" + group.name + "</name>"
        xml +=  "<bounds>"
        xml +=      "<coords>"
        xml +=          "<double>" + minx + "</double>"
        xml +=          "<double>" + miny + "</double>"
        xml +=          "<double>" + maxx + "</double>"
        xml +=          "<double>" + maxy + "</double>"
        xml +=      "</coords>"
        xml +=  "</bounds>"
        xml +=  "<gridSetId>" + grid_set + "</gridSetId>"
        xml +=  "<zoomStart>" + zoom_start + "</zoomStart>"
        xml +=  "<zoomStop>" + zoom_stop + "</zoomStop>"
        xml +=  "<format>" + format + "</format>"
        xml +=  "<type>" + op_type + "</type>"
        xml +=  "<threadCount>" + thread_count + "</threadCount>"
        xml += "</seedRequest>"
        
        api_url = url + "/gwc/rest/seed/" + group.name + ".xml"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'text/xml'}
        response = self.session.post(api_url, data=xml, headers=headers, auth=auth)
        if response.status_code==200:
            return True
        
        raise FailedRequestError(response.status_code, response.content)
    
    def get_pending_and_running_tasks(self, ws, layer, server, master_node_url):
        layer_name = None
        if ws is None:
            layer_name = layer.name
        else:
            layer_name = ws + ":" + layer.name
            
        api_url = master_node_url + "/gwc/rest/seed/" + layer_name + ".json"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.get(api_url, headers=headers, auth=auth, timeout=_gwc_rest_timeout())
        if response.status_code==200:
            return json.loads(response.content)
        
        raise FailedRequestError(response.status_code, response.content)
    
    def get_group_pending_and_running_tasks(self, group, server, master_node_url):
        api_url = master_node_url + "/gwc/rest/seed/" + group.name + ".json"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.get(api_url, headers=headers, auth=auth, timeout=_gwc_rest_timeout())
        if response.status_code==200:
            return json.loads(response.content)
        
        raise FailedRequestError(response.status_code, response.content)
    
    def kill_all_tasks(self, ws, layer, server, master_node_url):
        layer_name = None
        if ws is None:
            layer_name = layer.name
        else:
            layer_name = ws + ":" + layer.name
            
        api_url = master_node_url + "/gwc/rest/seed/" + layer_name
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.post(api_url, data="kill_all=all", headers=headers, auth=auth)
        if response.status_code==200:
            return True
        
        raise FailedRequestError(response.status_code, response.content)
    
    def kill_all_group_tasks(self, group, server, master_node_url):
        api_url = master_node_url + "/gwc/rest/seed/" + group.name
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.post(api_url, data="kill_all=all", headers=headers, auth=auth)
        if response.status_code==200:
            return True
        
        raise FailedRequestError(response.status_code, response.content)
    
    def clear_cache(self, ws, layer, user=None, password=None):
        url = self.gwc_url + "/masstruncate"
        headers = {'content-type': 'text/xml'}
        if getattr(layer, 'external', False):
            gwc_layer_name = layer.name
        else:
            gwc_layer_name = ws + ":" + layer.name
        xml = "<truncateLayer>"
        xml += "<layerName>" + gwc_layer_name + "</layerName>"
        xml += "</truncateLayer>"
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, data=xml, headers=headers, auth=auth)
        
        if r.status_code==200:
            return True
        
        raise FailedRequestError(r.status_code, r.content)
    
    def clear_layergroup_cache(self, name, user=None, password=None):
        url = self.gwc_url + "/masstruncate"
        headers = {'content-type': 'text/xml'}
        
        xml = "<truncateLayer>"
        xml +=  "<layerName>" + name + "</layerName>"
        xml += "</truncateLayer>"
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
            
        r = self.session.post(url, data=xml, headers=headers, auth=auth)
        if r.status_code==200:
            return True
        
        raise FailedRequestError(r.status_code, r.content)

__api_geowebcache = None

def get_instance():
    global __api_geowebcache
    if __api_geowebcache is None:
        __api_geowebcache = APIGeoWebCache()
    return __api_geowebcache