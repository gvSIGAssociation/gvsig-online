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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from gvsigol.settings import GVSIGOL_SERVICES
from models import Layer, LayerGroup, Workspace, Datastore
import requests
import json
from datetime import datetime

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
        if srs is not None:
            ft['nativeBoundingBox'] = {"minx": 0, "maxx": 1, "miny": 0, "maxy":1 , "crs":srs}
            
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
        
    def create_wmslayer(self, workspace, store, name, nativeName=None, user=None, password=None):           
        url = self.service_url + "/workspaces/" + workspace.name + "/wmsstores/" + store.name + "/wmslayers"
        data = {"wmsLayer": {'enabled': True, "name": name, "nativeName": nativeName}}
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.post(url, json=data, auth=auth)
        if r.status_code==201:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def create_wmsstore(self, workspace, store, capabilitiesURL, wmsuser=None, wmspassword=None, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace.name + "/wmsstores"
        headers = {'content-type': "text/xml"}
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
            
        data = ""
        data += "<wmsStore>"
        data +=     "<name>" + store + "</name>"
        data +=     "<type>WMS</type>"
        data +=     "<enabled>true</enabled>"
        data +=     "<workspace>"
        data +=         "<name>" + workspace.name + "</name>"      
        data +=     "</workspace>"
        data +=     "<__default>false</__default>"
        data +=     "<capabilitiesURL>" + capabilitiesURL + "</capabilitiesURL>"
        if wmsuser and wmspassword:
            data +=     "<user>" + wmsuser + "</user>"
            data +=     "<password>" + wmspassword + "</password>"
        data += "</wmsStore>"
        
        r = self.session.post(url, data=data, headers=headers, auth=auth)
        if r.status_code==201:
            return True
        raise UploadError(r.status_code, r.content)
    
    def update_wmsstore(self, wsname, dsname, capabilitiesURL, wmsuser=None, wmspassword=None, user=None, password=None):
        url = self.service_url + "/workspaces/" + wsname + "/wmsstores/" + dsname + ".xml"
        headers = {
            "Content-type": "application/xml",
            "Accept": "application/xml"
        }
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        data = ''
        data += '<wmsStore>'
        data +=     '<name>' + dsname + '</name>'
        data +=     '<enabled>true</enabled>'
        data +=     '<capabilitiesURL>' + capabilitiesURL + '</capabilitiesURL>'
        if wmsuser and wmspassword:
            data +=     '<user>' + wmsuser + '</user>'
            data +=     '<password>' + wmspassword + '</password>'
        data +=     '<metadata />'
        data += '</wmsStore>'
        
        r = self.session.put(url, data=data, headers=headers, auth=auth)
        if r.status_code==200:
            return True
        raise UploadError(r.status_code, r.content)
    
    def create_coveragestore(self, workspace, store, filetype, file, user=None, password=None):
        url = self.service_url + "/workspaces/" + workspace + "/coveragestores.json"
        headers = {'content-type': "text/xml"}
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
            
        data = ""
        data += "<coverageStore>"
        data +=     "<name>" + store + "</name>"
        data +=     "<type>" + filetype + "</type>"
        data +=     "<enabled>true</enabled>"
        data +=     "<workspace>"
        data +=         "<name>" + workspace + "</name>"      
        data +=     "</workspace>"
        data +=     "<__default>false</__default>"
        data +=     "<url>" + file + "</url>"
        data += "</coverageStore>"
        
        r = self.session.post(url, data=data, headers=headers, auth=auth)
        if r.status_code==201:
            return True
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
    
    def set_queryable(self, workspace, ds_name, ds_type, name, queryable, user=None, password=None):
        url = self.service_url + '/layers/' + name + '.json'
        
        type = 'VECTOR'
        resource_class = 'featureType'
        href = self.service_url + '/rest/workspaces/' + workspace + '/datastores/' + ds_name + '/featuretypes/' + name + '.json' 
        if 'c_GeoTIFF' in ds_type:
            type = 'RASTER'
            resource_class = 'coverage'
            href = self.service_url + '/rest/workspaces/' + workspace + '/coveragestores/' + ds_name + '/coverages/' + name + '.json' 
            
        data = {
            'layer': {
                'name': name,
                'type': type,
                'resource':{
                    '@class': resource_class,
                    'name': name, 
                    "href": href 
                },
                'queryable': queryable,
                'opaque': False,
                "attribution":{
                    "logoWidth":0,
                    "logoHeight":0
                }
                
            }
            
        }
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
            
        r = self.session.put(url, json=data, auth=auth)
        if r.status_code==200:
            return True
        
        raise FailedRequestError(r.status_code, r.content)
    
    def set_time_dimension(self, workspace, ds_name, ds_type, name, time_enabled, time_field, time_endfield=None, presentation='CONTINUOUS_INTERVAL', resolution=0, default_value_mode='MAXIMUM', default_value=None, user=None, password=None):
        #from geoserver.support import DimensionInfo
        
        url =  self.service_url + '/workspaces/'+workspace+'/datastores/'+ds_name+'/featuretypes/'+name+'.xml'
        headers = {'Content-Type': 'text/xml'}
       
        data = ''
        data += '<featureType>'
        data += '    <name>'+name+'</name>'
        data += '    <metadata>'
        data += '        <entry key="time">'
        data += '            <dimensionInfo>'
        data += '                <enabled>'+str(time_enabled).lower()+'</enabled>'
        if time_enabled:
            data += '                <attribute>'+time_field+'</attribute>'
            if time_endfield != None and time_endfield != '':
                data += '                <endAttribute>'+time_endfield+'</endAttribute>'
            data += '                <presentation>'+presentation+'</presentation>'
            if resolution != 0 and presentation == 'DISCRETE_INTERVAL':
                data += '                <resolution>'+str(resolution*1000)+'</resolution>'
            data += '                <units>ISO8601</units>'
            data += '                <defaultValue>'
            data += '                    <strategy>'+default_value_mode+'</strategy>'
            if default_value != None and default_value_mode != 'MINIMUM' and default_value_mode != 'MAXIMUM':
                date_format = datetime.strptime(default_value, '%d-%m-%Y %H:%M:%S')
                # 2001-12-12T18:00:00.0Z
                final_value = date_format.strftime('%Y-%m-%dT%H:%M:%S.0Z')
                data += '                    <referenceValue>'+final_value+'</referenceValue>'
            data += '                </defaultValue>'
        data += '            </dimensionInfo>'
        data += '        </entry>'
        data += '    </metadata>'
        data += '</featureType>'
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
            
        r = self.session.put(url, headers=headers, auth=auth, data=data)
        if r.status_code==200:
            return True
        
        raise FailedRequestError(r.status_code, r.content)
            
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
    
    
    def get_resources(self, workspace, datastore, type, user=None, password=None):
        json = []
        if type == 'all':
            configurables = self.get_resources(workspace, datastore, "configurable", user, password)
            availables = self.get_resources(workspace, datastore, "available", user, password)
            json =  configurables + availables
            
        else:    
            url = self.service_url + "/workspaces/" + workspace + "/datastores/" + datastore + "/featuretypes.json?list="+type
            if user and password:
                auth = (user, password)
            else:
                auth = self.session.auth
            r = self.session.get(url, auth=auth)
            json = r.json()
            
            
            if type == 'available' or type == 'available_with_geom':
                if json['list'] and json['list']['string']:
                    resources = json['list']['string']
                    return [resource for resource in resources]
            else:
                if json['featureTypes'] and json['featureTypes']['featureType']:
                    resources = json['featureTypes']['featureType']
                    return [resource['name'] for resource in resources]
            return []
            
        return json
    
    def get_wmsresources(self, workspace, wmsstore, user=None, password=None):
        json = []
        url = self.service_url + "/workspaces/" + workspace + "/wmsstores/" + wmsstore + "/wmslayers.json?list=available"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.get(url, auth=auth)
        json = r.json()
        
        if json['list'] and json['list']['string']:
            resources = json['list']['string']
            return [resource for resource in resources]
            
        return json

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
        if r.status_code==404:
            return None
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
    
    def update_feature_type(self, workspace, datastore, feature_type, user=None, password=None):
        """
        Updates the native & lat/lon bounding box of the feature type using
        the bounding box computed from data
        """
        url = self.service_url + "/workspaces/" + workspace + "/datastores/" + datastore + "/featuretypes/" + feature_type + ".json?recalculate="
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        data = {"featureType": {"name": feature_type, "enabled": "true"}}
        r = self.session.put(url, json=data, auth=auth)
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
        layers_in_group = Layer.objects.filter(layer_group_id=group.id).order_by('-order')
        
        if len(layers_in_group) > 0:   
            layers = []
            for l in layers_in_group:
                datastore = Datastore.objects.get(id=l.datastore.id)
                workspace = Workspace.objects.get(id=datastore.workspace_id)
                layer = {}
                layer["@type"] = "layer"
                layer["name"] = workspace.name + ":"+ l.name
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
    
    def create_or_update_sorted_gs_layer_group(self, toc, content_type=None, user=None, password=None):  
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        # delete the layergroup if exists
        for toc_group in toc:
            response_get = self.session.get(self.service_url + "/layergroups/" + toc[toc_group].get('name') + ".json", auth=auth)
            if response_get.status_code==200:
                r = self.session.delete(self.service_url + "/layergroups/" + toc[toc_group].get('name') + ".json", params={}, auth=auth)
            
            group = LayerGroup.objects.get(name__exact=toc[toc_group].get('name'))
            layers_in_group = Layer.objects.filter(layer_group_id=group.id).order_by('order')
            #layers_in_toc = sorted(toc[toc_group].get('layers').iteritems(), key=lambda (x, y): y['order'], reverse=True)
        
            if len(layers_in_group) > 0:   
                layers = []
                #for tl in layers_in_toc:
                for l in layers_in_group:
                #       if l.name == tl[1]['name']:
                    datastore = Datastore.objects.get(id=l.datastore.id)
                    workspace = Workspace.objects.get(id=datastore.workspace_id)
                    layer = {}
                    layer["@type"] = "layer"
                    layer["name"] = workspace.name + ":"+ l.name
                    layer["href"] = GVSIGOL_SERVICES['URL'] + '/layers/' + l.name + '.json'
                    layers.append(layer)

                data = {
                    "layerGroup": {
                        "name": group.name,
                        "mode": "SINGLE",
                        "title": group.name,
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
        if r.status_code==200:
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
        if r.status_code==200:
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
        xml +=          "<defaultValue></defaultValue>"
        xml +=          "<availableStyles class=\"sorted-set\"/>"
        xml +=          "<defaultStyle>point</defaultStyle>"
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
    
    
    def add_style(self, layer, style_name, user=None, password=None):
        url = self.service_url + "/layers/" +  layer + "/styles/"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
            #auth = ('admin', 'geoserver')
        
        headers = {'content-type': 'text/xml'}
        data_xml = "<style><name>"+style_name+"</name></style>"
        
        r = self.session.post(url, data=data_xml, headers=headers, auth=auth)
        if r.status_code==201:
            return True
        raise UploadError(r.status_code, r.content)
    
    
    def get_layer_styles_configuration(self, layer, user=None, password=None):
        url = self.gwc_url + '/layers/'+layer.datastore.workspace.name +':'+layer.name+'.xml'
        print '########################### get_layer_styles_configuration: update_layer_styles_configuration' + url
        
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        r = self.session.get(url, json={}, auth=auth)
        if r.status_code==200:
            return r._content
        raise FailedRequestError(r.status_code, r.content)
    
    
    def update_layer_styles_configuration(self, layer, style_name, default_style, styles_list, user=None, password=None):
        xml = self.get_layer_styles_configuration(layer, user, password)
        
        
        url = self.gwc_url + '/layers/'+layer.datastore.workspace.name +':'+layer.name+'.xml'
        print '########################### update_layer_styles_configuration: ' + url
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
            #auth = ('admin', 'geoserver')
        
        headers = {'content-type': 'text/xml'}
        
        start_index = xml.find('<stringParameterFilter>')
        end_index = xml.find('</stringParameterFilter>')
        
        start_xml = xml[:start_index+'<stringParameterFilter>'.__len__()]
        end_xml = xml[end_index:]
        
        style_xml = ''
        style_xml += '      <key>STYLES</key>'
        style_xml += '      <defaultValue>'+default_style+'</defaultValue>'
        style_xml += '      <normalize/>'
        style_xml += '      <values>'
        for style_list in styles_list: 
            style_xml += '        <string>'+style_list+'</string>'
        style_xml += '      </values>'
        
        aux_xml = start_xml + style_xml + end_xml
        
        r = self.session.post(url, data=aux_xml, headers=headers, auth=auth)
        if r.status_code==200:
            return True
        raise UploadError(r.status_code, r.content)
        
    
    def update_style(self, style_name, sld_body, user=None, password=None):
        url = self.service_url + "/styles/" + style_name + ".sld"
        if user and password:
            auth = (user, password)
        else:
            auth = self.session.auth
        
        headers = { "content-type": "application/vnd.ogc.sld+xml" }
        r = self.session.put(url, data=sld_body.encode('utf-8'), headers=headers, auth=auth)
        if r.status_code==200:
            return True
        raise UploadError(r.status_code, r.content)
    
    def get_content_type(self, file_type):
        if file_type=="geotiff":
            return "image/tiff"
        elif file_type=="worldimage":
            return "image/tiff"
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
