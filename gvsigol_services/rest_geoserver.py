# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from gvsigol.settings import GVSIGOL_SERVICES
from models import Layer, LayerGroup
import requests
import json

PURGE_NONE="none"
PURGE_METADATA="metadata"
PURGE_ALL="all"

class Geoserver():
    """
    geoserver-py is a Python interface to Geoserver REST API
    
    Compared to the alternative gsconfig library, geoserver-py aims to
    offer a simple python interface to Geoserver REST API
    (there is no catalog caching nor synchronization).
    
    Warning: The input parameters are directly provided to the server, no
    validation is performed by the library.
    
    Dependences: This library depends on requests and json libraries.
    It must be kept free from any django and gvSIG Online dependency.
    Use backend module to include your gvSIG Online-dependent code.
    """
    
    def __init__(self, service_url, gwc_url, user=None, password=None):
        self.session = requests.Session()
        self.session.verify = False
        self.service_url = service_url
        self.gwc_url =  gwc_url
        self.session.auth = (user, password)
        
    def get_session(self):
        return self.session

    def get_service_url(self):
        return self.service_url
    
    def reload(self, node_url, user=None, password=None):
        url = node_url + "/rest/reload"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, auth=auth)
        if r.status_code==200:
            return True
        raise FailedRequestError(r.status_code, r.content)
        
    def create_feature_type(self, name, title, store, workspace, srs=None, fields=None, maxFeatures=0, content_type=None, user=None, password=None, extraParams=None):
        url = self.service_url + "/workspaces/" + workspace + "/datastores/" + store + "/featuretypes"
        qualified_store = workspace + ":" + store
        
        # Geoserver is producing an error if no native bounding box is provided. 
        # As the new layer will be empty, we can't calculate the bounding box from data.
        # Moreover, we can't provide a universally sensible bounding box, as it depends on
        #the CRS. Therefore, we provide a fake one (0,0,1,1) which makes Geoser
        # Note that it may be outside the boundaries of the projection (depending on the CRS
        # in use, but it seems to work correctly).
        ft = {
                'name': name, 'title': title, 'enabled': True,
                "store": {"@class": "dataStore", "name": qualified_store},
                "maxFeatures": maxFeatures
              }
        try:
            ft.update(extraParams)
        except:
            pass
            
        if srs:
            ft["srs"] = srs
        if fields:
            attr_array = {"attribute": fields}
            ft["attributes"] = attr_array
            
        data = {"featureType": ft}
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, json=data, auth=auth)
        if r.status_code==201:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def create_coverage(self, name, title, store, workspace, srs="EPSG:4326", content_type=None, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/coveragestores/" + store + "/coverages"
        data = {"coverage": {'enabled': True, "name": name, "title": title}}
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, json=data, auth=auth)
        if r.status_code==201:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def upload_coverage(self, workspace, store, filetype, file, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/coveragestores/" + store + "/file."+filetype
        # don't use Accept header as it is not honored by Geoserver. See https://osgeo-org.atlassian.net/browse/GEOS-7401
        #headers = {'content-type': content_type, 'Accept': 'application/json'}
        headers = {'content-type': self.get_content_type(filetype)}
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        if isinstance(file, basestring):
            with open(file, 'rb') as f:
                r = self.session.put(url, data=f, headers=headers, auth=auth)
        else:
            r = self.session.put(url, data=file, headers=headers, auth=auth)
        if r.status_code==201:
            return r.text
        raise UploadError(r.status_code, r.content)

    def upload_feature_type(self, workspace, store, name, filetype, file, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/datastores/" + store + "/file."+filetype
        headers = {'content-type': self.get_content_type(filetype)}
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        if isinstance(file, basestring):
            with open(file, 'rb') as f:
                r = self.session.put(url, data=f, headers=headers, auth=auth)
        else:
            r = self.session.put(url, data=file, headers=headers, auth=auth)
        if r.status_code==201:
            return True
        raise UploadError(r.status_code, r.content)
            
    def raw_request(self, url, params, user=None, password=None):
        try:
            if user and password:
                auth = (user, password)
            else:
                auth = self.session.auth
            response = self.session.post(url, data=params, auth=auth)
            return response 
        
        except Exception as e:
            print str(e)
    
        
    def get_datastore(self, workspace, datastore, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/datastores/" + datastore + ".json"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.get(url, auth=auth)
        return r.json()

    def get_coveragestore(self, workspace, coveragestore, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/coveragestores/" + coveragestore + ".json"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.get(url, auth)
        return r.json()
    
    def delete_coveragestore(self, workspace, coveragestore, purge=None, recurse=False, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/coveragestores/" + coveragestore + ".json"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        params = {}
        if purge == "metadata" or purge == "all":
            params['purge'] = purge
        if recurse:
            params['recurse'] = "true" 
        r = self.session.delete(url, params=params, auth=auth)

    def get_coverage(self, workspace, coveragestore, coverage, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/coveragestores/" + coveragestore + "/coverages/" + coverage + ".json"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth        
        r = self.session.get(url, auth=auth)
        if r.status_code==200:
            return r.json()
        raise FailedRequestError(r.status_code, r.content)

    def get_feature_type(self, workspace, datastore, feature_type, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/datastores/" + datastore + "/featuretypes/" + feature_type + ".json"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.get(url, auth=auth)
        return r.json()
    
    def update_coverage(self, workspace, coveragestore, coverage, json_data, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/coveragestores/" + coveragestore + "/coverages/" + coverage + ".json"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        data_str = json.dumps(json_data)
        print "json:"
        print data_str
        r = self.session.put(url, json=json_data, auth=auth)
        if r.status_code==200:
            return
        raise UploadError(r.status_code, r.content)
    
    def update_ft_bounding_box(self, workspace, datastore, feature_type, user=None, password=None):
        """
        Updates the native & lat/lon bounding box of the feature type using
        the bounding box computed from data
        """
        url = self.service_url + "/workspaces/" + workspace + "/datastores/" + datastore + "/featuretypes/" + feature_type + ".json?recalculate=nativebbox,latlonbbox"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        data = {"featureType": {"name": feature_type, "enabled": "true"}}
        r = self.session.put(url, json=data, auth=auth)
        if r.status_code==200:
            return
        raise UploadError(r.status_code, r.content)
    
    def create_sql_view(self, workspace, datastore, name, sql_statement, key_column, geom_column, geom_type, srid, id_column=None, title=None, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/datastores/" + datastore + "/featuretypes.json"
        qualified_store = workspace + ":" + datastore
        if "," in key_column:
            key = key_column.replace(" ", "").split(",")
        else:
            key = key_column
        the_title = title if title else name
        ft = {
                'name': name, 'title': the_title, "enabled": True,
                "metadata": {
                    "entry": {
                        "@key": "JDBC_VIRTUAL_TABLE",
                        "virtualTable": {
                            "name": name,
                            "sql": sql_statement,
                            "escapeSql": False,
                            "keyColumn": key,
                            "geometry": {
                                "name": geom_column,
                                "type": geom_type,
                                "srid": srid
                            }
                        }
                    }
                },
                "store": {"@class": "dataStore", "name": qualified_store},
                "maxFeatures":0
              }
        data = {"featureType": ft}
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, json=data, auth=auth)
        if r.status_code==201:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def create_or_update_gs_layer_group(self, lg_name, lg_title, content_type=None, user=None, password=None):  
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        # delete the layergroup if exists
        response_get = self.session.get(self.service_url + "/layergroups/"+lg_name+".json", auth=auth)
        if response_get.status_code==200:
            r = self.session.delete(self.service_url + "/layergroups/" + lg_name + ".json", params={}, auth=auth)
            
        group = LayerGroup.objects.get(name__exact=lg_name)
        layers_in_group = Layer.objects.filter(layer_group_id=group.id).order_by('order')
        
        if len(layers_in_group) > 0:   
            layers = []
            for l in layers_in_group:
                layer = {}
                layer["@type"] = "layer"
                layer["name"] = l.name
                layer["href"] = GVSIGOL_SERVICES['URL'] + '/layers/' + l.name + '.json'
                layers.append(layer)

            data = {
                "layerGroup": {
                    "name": lg_name,
                    "mode": "SINGLE",
                    "title": lg_title,
                    "publishables": {
                        "published": layers
                    }
                }
            }
            r = self.session.post(self.service_url + "/layergroups/", json=data, auth=auth)
            if r.status_code==201:
                return True
            
        else:
            return True
                
        raise FailedRequestError(r.status_code, r.content)
    
    def delete_gs_layer_group(self, layer_group, content_type=None, user=None, password=None):  
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        r = self.session.delete(self.service_url + "/layergroups/" + layer_group.name + ".json", params={}, auth=auth)
        if r.status_code==200:
            return True
        
        elif r.status_code==404:
            return False
        
        raise FailedRequestError(r.status_code, r.content)
    
    def get_fonts(self, user=None, password=None):
        url = self.service_url + "/fonts.json"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.get(url, json={}, auth=auth)
        if r.status_code==200:
            return r._content
        raise FailedRequestError(r.status_code, r.content)
    
    def clear_cache(self, ws, layer, user=None, password=None):
        url = self.gwc_url + "/masstruncate"
        headers = {'content-type': 'text/xml'}
        xml = "<truncateLayer><layerName>" + ws + ":" + layer.name + "</layerName></truncateLayer>"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, data=xml, headers=headers, auth=auth)
        if r.status_code==201:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def clear_layergroup_cache(self, name, user=None, password=None):
        url = self.gwc_url + "/masstruncate"
        headers = {'content-type': 'text/xml'}
        xml = "<truncateLayer><layerName>" + name + "</layerName></truncateLayer>"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, data=xml, headers=headers, auth=auth)
        if r.status_code==201:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def add_grid_subset(self, ws, layer, user=None, password=None):
        url = self.gwc_url + "/layers/" + ws.name + ":" + layer.name + ".xml"
        headers = {'content-type': 'text/xml'}
        xml = "<GeoServerLayer>"
        xml +=  "<enabled>true</enabled>"
        xml +=  "<inMemoryCached>false</inMemoryCached>"
        xml +=  "<name>" + ws.name + ":" + layer.name + "</name>"
        xml +=  "<mimeFormats>"
        xml +=      "<string>image/png</string>"
        xml +=      "<string>image/jpeg</string>"
        xml +=  "</mimeFormats>"
        xml +=  "<gridSubsets>"
        xml +=      "<gridSubset>"
        xml +=          "<gridSetName>EPSG:900913</gridSetName>"
        xml +=      "</gridSubset>"
        xml +=      "<gridSubset>"
        xml +=          "<gridSetName>EPSG:4326</gridSetName>"
        xml +=      "</gridSubset>"
        xml +=      "<gridSubset>"
        xml +=          "<gridSetName>EPSG:3857</gridSetName>"
        xml +=      "</gridSubset>"
        xml +=  "</gridSubsets>"
        xml +=  "<metaWidthHeight>"
        xml +=      "<int>4</int>"
        xml +=      "<int>4</int>"
        xml +=  "</metaWidthHeight>"
        xml +=  "<expireCache>0</expireCache>"
        xml +=  "<expireClients>0</expireClients>"
        xml +=  "<parameterFilters>"
        xml +=      "<styleParameterFilter>"
        xml +=          "<key>STYLES</key>"
        xml +=          "<defaultValue/>"
        xml +=      "</styleParameterFilter>"
        xml +=  "</parameterFilters>"
        xml +=  "<gutter>0</gutter>"
        xml += "</GeoServerLayer>"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, data=xml, headers=headers, auth=auth)
        if r.status_code==201:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def update_style(self, style_name, sld_body, user=None, password=None):
        url = self.service_url + "/styles/" + style_name + ".sld"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        headers = { "content-type": "application/vnd.ogc.sld+xml" }
        r = self.session.put(url, data=sld_body, headers=headers, auth=auth)
        if r.status_code==200:
            return True
        raise UploadError(r.status_code, r.content)
    
    def get_content_type(self, file_type):
        if file_type=="geotiff":
            return "image/tiff"
        elif file_type=="":
            return ""
        else:
            return "application/zip"
        
    
    def __update_dict(self, d, u):
        for k, v in u.iteritems():
            if isinstance(v, dict):
                r = self.__update_dict(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        return d

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

class UploadError(RequestError):
    pass

class ConflictingDataError(RequestError):
    pass

class AmbiguousRequestError(RequestError):
    pass

class FailedRequestError(RequestError):
    pass
