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
from gvsigol_plugin_catalog.xmlutils import getLocalizedText
'''
@author: Javi Rodrigo <jrodrigo@scolab.es>
@author: Cesar Martinez Izquierdo <cmartinez@scolab.es>
'''
from gvsigol_services import signals
from gvsigol_services import geographic_servers
from gvsigol_plugin_catalog import settings as plugin_settings
from django.core.exceptions import ImproperlyConfigured
from gvsigol_plugin_catalog.models import LayerMetadata
from gvsigol_plugin_catalog import api_old as xmlapi_old
from gvsigol_plugin_catalog import api_new as xmlapi_new
import logging
from gvsigol_plugin_catalog.mdstandards import registry
import xml.etree.ElementTree as ET
from xmlutils import getTextFromXMLNode
from django.utils.translation import get_language

logger = logging.getLogger("gvsigol")

class UnsupportedRequestError(Exception):
    pass


ONLINE_RES_TYPE_WFS = 'WFS'
ONLINE_RES_TYPE_WMS = 'WMS'
ONLINE_RES_TYPE_WCS = 'WCS'
ONLINE_RES_TYPE_HTTP = 'HTTP'
ONLINE_RES_TYPE_OTHER = 'OTHER'

class OnlineResource():
    def __init__(self, res_type, url, protocol, name, desc, app_profile, function):
        self.res_type = res_type,
        self.url = url
        self.protocol = protocol
        self.name = name
        self.desc = desc
        self.app_profile = app_profile
        self.function = function


class Geonetwork():
    def __init__(self, version, service_url, user, password):
        if version == 'legacy3.2':
            self.xmlapi = xmlapi_old.Geonetwork(service_url + '/srv/eng/')
        else: # version == 'api0.1':
            self.xmlapi = xmlapi_new.Geonetwork(service_url)
        self.user = user
        self.password = password
    
    def get_metadata(self, uuid):
        try:
            if self.xmlapi.gn_auth(self.user, self.password):
                content = self.xmlapi.gn_get_metadata(uuid)
                self.xmlapi.gn_unauth()
                return content
            return None
        
        except Exception as e:
            logger.exception(e);
            print e
            
            
    def get_online_resources(self, record_uuid):
        """
        Returns a list of OnlineResource objects, describing the online resources
        encoded in the provided metadata_record
        """
        try:
            online_resources = []
            if self.xmlapi.gn_auth(self.user, self.password):
                content = self.xmlapi.get_online_resources(record_uuid)
                self.xmlapi.gn_unauth()
                tree = ET.fromstring(content.encode('utf8'))
                online_resource = OnlineResource()
                for onlines_node in tree.findall('./related/onlines/item/'):
                    urlNode = getTextFromXMLNode(onlines_node, './url/')
                    online_resource.url = getLocalizedText(urlNode)
                    titleNode = getTextFromXMLNode(onlines_node, './title/')
                    online_resource.title = getLocalizedText(titleNode)
                    online_resource.res_type = getTextFromXMLNode(onlines_node, './type/')
                    online_resource.protocol = getTextFromXMLNode(onlines_node, './protocol/')
                    descriptionNode = getTextFromXMLNode(onlines_node, './description/')
                    online_resource.desc = getLocalizedText(descriptionNode)
                    online_resource.function = getTextFromXMLNode(onlines_node, './function/')
                    online_resource.app_profile = getTextFromXMLNode(onlines_node, './applicationProfile/')
                online_resources.append(online_resource)
        
        except Exception as e:
            logger.exception(e);
            print e
        return online_resources
        
    def create_metadata(self, layer, layer_info, ds_type):
        ws = layer.datastore.workspace
        minx, miny, maxx, maxy = self.xmlapi.get_extent(layer_info, ds_type)
        crs_object = layer_info[ds_type]['nativeBoundingBox']['crs']
        if isinstance(crs_object,dict):
            crs = str(crs_object['$'])
        else:
            crs = str(crs_object)
        
        wms_endpoint = ws.wms_endpoint
        if ds_type == 'featureType':
            wfs_endpoint = ws.wfs_endpoint
            wcs_endpoint = None
        elif ds_type in ('coverage', 'imagemosaic') and ws.wcs_endpoint:
            wfs_endpoint = None
            wcs_endpoint = ws.wcs_endpoint
        else:
            wfs_endpoint = None
            wcs_endpoint = None

        mdfields = {
            'title': layer.title,
            'abstract': layer.abstract,
            'qualified_name': ws.name + ':' + layer.name,
            'extent_tuple': (minx, miny, maxx, maxy),
            'crs': crs,
            'thumbnail_url': layer.thumbnail.url,
            'wms_endpoint': wms_endpoint,
            'wfs_endpoint': wfs_endpoint,
            'wcs_endpoint': wcs_endpoint
            }
        
        return registry.create('dataset', mdfields)
    
    def metadata_insert(self, layer):
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        (ds_type, layer_info) = gs.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, "json")
        md_record = self.create_metadata(layer, layer_info, ds_type)
        try:
            if self.xmlapi.gn_auth(self.user, self.password):
                uuid = self.xmlapi.gn_insert_metadata(md_record)
                self.xmlapi.add_thumbnail(uuid[0], layer.thumbnail.url)
                self.xmlapi.set_metadata_privileges(uuid[0])
                self.xmlapi.gn_unauth()
                return uuid
            return None
        
        except Exception as e:
            logger.exception("Error inserting metadata", e)
            
    def get_query(self, query):
        try:
            if self.xmlapi.gn_auth(self.user, self.password):
                content = self.xmlapi.get_query(query)
                self.xmlapi.gn_unauth()
                return content
            return None
        
        except Exception as e:
            print e        

    def metadata_delete(self, lm):
        try:
            if self.xmlapi.gn_auth(self.user, self.password):
                self.xmlapi.gn_delete_metadata(lm)
                self.xmlapi.gn_unauth()
                return True
            return False
        
        except Exception as e:
            print e
            return False
        
    def layer_created_handler(self, sender, **kwargs):
        try:
            layer = kwargs['layer']
            muuid = self.metadata_insert(layer)
            if muuid:
                lm = LayerMetadata(layer=layer, metadata_uuid=muuid[0], metadata_id=muuid[1])
                lm.save()
            
        except Exception as e:
            logger.exception("layer metadata create failed")
            pass
        
    def layer_updated_handler(self, sender, **kwargs):
        try:
            layer = kwargs['layer']
            lm = LayerMetadata.objects.get(layer=layer)
            
            gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            (ds_type, layer_info) = gs.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, "json")
            if self.xmlapi.gn_auth(self.user, self.password) and lm.metadata_uuid:
                self.xmlapi.gn_update_metadata(lm.metadata_uuid, layer, layer.abstract, layer_info, ds_type)
                self.xmlapi.gn_unauth()
        except Exception as e:
            logger.exception("layer metadata update failed")
            pass
        
    def layer_deleted_handler(self, sender, **kwargs):
        try:
            layer = kwargs['layer']
            lm = LayerMetadata.objects.get(layer=layer)
            self.metadata_delete(lm)
            lm.delete()
        except Exception as e:
            logger.exception("layer metadata delete failed")
            pass

def connect_signals(geonetwork_service):
    signals.layer_created.connect(geonetwork_service.layer_created_handler)
    signals.layer_updated.connect(geonetwork_service.layer_updated_handler)
    signals.layer_deleted.connect(geonetwork_service.layer_deleted_handler)


def initialize():
    try:
        version = plugin_settings.CATALOG_API_VERSION
        service_url = plugin_settings.CATALOG_BASE_URL
        user = plugin_settings.CATALOG_USER
        password = plugin_settings.CATALOG_PASSWORD
        geonetwork_service = Geonetwork(version, service_url, user, password) 
        return geonetwork_service
    
    except:
        #logging.basicConfig()
        logger.exception("initialization error")
        raise ImproperlyConfigured

geonetwork_service = initialize()
connect_signals(geonetwork_service)


#__geonetwork_service = None
def get_instance():
    return geonetwork_service
    """
    if __geonetwork_service is None:
        __geonetwork_service = initialize()
        connect_signals(__geonetwork_service)
    return __geonetwork_service
    """
