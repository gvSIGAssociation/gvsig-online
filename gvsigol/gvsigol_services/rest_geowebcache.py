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
        response = self.session.get(api_url, headers=headers, auth=auth)
        if response.status_code==200:
            return json.loads(response.content)
        
        raise FailedRequestError(response.status_code, response.content)
    
    def get_group(self, group, server, master_node_url):
            
        api_url = master_node_url + "/gwc/rest/layers/" + group.name + ".json"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.get(api_url, headers=headers, auth=auth)
        if response.status_code==200:
            return json.loads(response.content)
        
        raise FailedRequestError(response.status_code, response.content)
    
    def add_layer(self, ws, layer, server, master_node_url, crs_list):
        layer_name = None
        wms_layers = None
        url = None
        if layer.external:
            layer_name = layer.name
            external_params = json.loads(layer.external_params)
            wms_layers = external_params.get('layers')
            if external_params.get('get_map_url'):
                url = external_params.get('get_map_url')
            else:
                url = external_params
        else:
            layer_name = ws + ":" + layer.name
            wms_layers = layer_name
            url = server.getWmsEndpoint()

        xml = ""
        xml += "<wmsLayer>"
        xml +=  "<name>" + layer_name + "</name>"
        xml +=  "<mimeFormats>"
        xml +=      "<string>image/png</string>"
        xml +=  "</mimeFormats>"
        xml +=  "<gridSubsets>"
        for gs in settings.CACHE_OPTIONS['GRID_SUBSETS']:
            xml +=  "<gridSubset>"
            xml +=      "<gridSetName>" + gs + "</gridSetName>"
            xml +=      "<zoomStart>0</zoomStart>"
            xml +=      "<zoomStop>" + str(settings.MAX_ZOOM_LEVEL) + "</zoomStop>"
            for crs in crs_list:
                if crs['key'] == gs:
                    bounds = crs['value'].split(';')
                    xml +=  "<extent>"
                    xml +=      "<coords>"
                    xml +=          "<double>" + bounds[0] + "</double>"
                    xml +=          "<double>" + bounds[1] + "</double>"
                    xml +=          "<double>" + bounds[2] + "</double>"
                    xml +=          "<double>" + bounds[3] + "</double>"
                    xml +=      "</coords>"
                    xml +=  "</extent>"
            xml +=  "</gridSubset>"
        xml +=  "</gridSubsets>"
        xml +=  "<wmsUrl>"
        xml +=      "<string>" + url + "</string>"
        xml +=  "</wmsUrl>"
        xml +=  "<wmsLayers>" + wms_layers + "</wmsLayers>"
        xml += "</wmsLayer>"

        # xml-encode any & appearance which causes Geoserver to complain.
        # FIXME: we should instead generate the XML using lxml to ensure the encoding reliability
        xml = xml.replace('&', '&amp;')
        api_url = master_node_url + "/gwc/rest/layers/" + layer_name + ".xml"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'text/xml'}
        response = self.session.put(api_url, data=xml.encode('utf-8'), headers=headers, auth=auth)
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
        response = self.session.post(api_url, data=xml.encode(), headers=headers, auth=auth)
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
        response = self.session.delete(api_url, headers=headers, auth=auth)
        if response.status_code==200:
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
        response = self.session.get(api_url, headers=headers, auth=auth)
        if response.status_code==200:
            return json.loads(response.content)
        
        raise FailedRequestError(response.status_code, response.content)
    
    def get_group_pending_and_running_tasks(self, group, server, master_node_url):
        api_url = master_node_url + "/gwc/rest/seed/" + group.name + ".json"
        
        auth = (server.user, server.password)
        headers = {'content-type': 'application/json'}
        response = self.session.get(api_url, headers=headers, auth=auth)
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
        
        xml = "<truncateLayer>" 
        xml +=  "<layerName>" + ws + ":" + layer.name + "</layerName>"
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