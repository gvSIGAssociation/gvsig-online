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
@author: Javi Rodrigo <jrodrigo@scolab.es>
@author: Cesar Martinez Izquierdo <cmartinez@scolab.es>
'''
from builtins import str as text
from gvsigol_services import signals
from gvsigol_services import geographic_servers
from gvsigol_plugin_catalog import settings as plugin_settings, api_gn_0_1
from django.core.exceptions import ImproperlyConfigured
from gvsigol_plugin_catalog.models import LayerMetadata
import logging
from gvsigol_plugin_catalog.mdstandards import registry
import requests
from  django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger("gvsigol")

class UnsupportedRequestError(Exception):
    pass


ONLINE_RES_TYPE_WFS = 'WFS'
ONLINE_RES_TYPE_WMS = 'WMS'
ONLINE_RES_TYPE_WCS = 'WCS'
ONLINE_RES_TYPE_HTTP = 'HTTP'
ONLINE_RES_TYPE_OTHER = 'OTHER'

class OnlineResource():
    def __init__(self, res_type, url, protocol, name, desc, app_profile, function, transferSize=None):
        self.res_type = res_type,
        self.url = url
        self.protocol = protocol
        self.name = name
        self.desc = desc
        self.app_profile = app_profile
        self.function = function
        self.transferSize = transferSize


class Geonetwork():
    def __init__(self, version, service_url, user, password):
        self.xmlapi = api_gn_0_1.Geonetwork(service_url)
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

    def get_raw_metadata_url(self, uuid):
        return self.xmlapi.gn_get_raw_metadata_url(uuid)
    
    def get_metadata_raw(self, uuid):
        try:
            if self.xmlapi.gn_auth(self.user, self.password):
                content = self.xmlapi.gn_get_metadata_raw(uuid)
                self.xmlapi.gn_unauth()
                return content
            return None
        
        except Exception as e:
            logger.exception(e);
            print e
            
    def _get_first_dict_value(self, d):
        if len(d) > 0:
            key = next(iter(d))
            return d.get(key, '')
        return ''
        
    def get_online_resources(self, record_uuid, raiseRequestExceptions=False):
        """
        Returns a list of OnlineResource objects, describing the online resources
        encoded in the provided metadata_record
        """
        try:
            online_resources = []
            if self.xmlapi.gn_auth(self.user, self.password):
                onlinesJson = self.xmlapi.get_online_resources(record_uuid)
                for online in onlinesJson.get('onlines', []):
                    res_type = online.get('type', '')
                    url = self._get_first_dict_value(online.get('url', {}))
                    protocol = online.get('protocol')
                    title = self._get_first_dict_value(online.get('title', {}))
                    desc = self._get_first_dict_value(online.get('description', {}))
                    app_profile = online.get('applicationProfile', '')
                    function = online.get('function', '')
                    online_resource = OnlineResource(res_type, url, protocol, title, desc, app_profile, function)
                    online_resources.append(online_resource) 
                self.xmlapi.gn_unauth()
        except requests.exceptions.RequestException as e:
            raise
        except Exception as e:
            logger.exception(e);
            print e
        return online_resources
        
    def create_metadata(self, layer, layer_info, ds_type):
        ws = layer.datastore.workspace
        if ds_type == 'imagemosaic':
            ds_type = 'coverage'
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
            spatial_representation_type = 'vector'
        elif ds_type in ('coverage', 'imagemosaic') and ws.wcs_endpoint:
            wfs_endpoint = None
            wcs_endpoint = ws.wcs_endpoint
            spatial_representation_type = 'grid'
        else:
            wfs_endpoint = None
            wcs_endpoint = None
            spatial_representation_type = None

        mdfields = {
            'title': layer.title,
            'abstract': layer.abstract,
            'qualified_name': ws.name + ':' + layer.name,
            'extent_tuple': (minx, miny, maxx, maxy),
            'crs': crs,
            'spatial_representation_type': spatial_representation_type,
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
            logger.error("Error authenticating in catalog")
            return None
        
        except:
            logger.exception("Error inserting metadata")
            
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
        except ObjectDoesNotExist:
            pass
        except Exception as e:
            logger.exception("layer metadata update failed")
            pass
        
    def layer_deleted_handler(self, sender, **kwargs):
        try:
            layer = kwargs['layer']
            lm = LayerMetadata.objects.get(layer=layer)
            self.metadata_delete(lm)
            lm.delete()
        except LayerMetadata.DoesNotExist:
            pass
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
