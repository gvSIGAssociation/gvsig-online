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
'''
from gvsigol_services import signals
from gvsigol_services.backend_mapservice import backend as mapservice
from gvsigol_plugin_catalog import settings as plugin_settings
from django.core.exceptions import ImproperlyConfigured
from gvsigol_plugin_catalog.models import LayerMetadata
from gvsigol_plugin_catalog import api_old as xmlapi_old
from gvsigol_plugin_catalog import api_new as xmlapi_new
import logging
from gvsigol_plugin_catalog.mdstandards import registry

logger = logging.getLogger("gvsigol")

class UnsupportedRequestError(Exception):
    pass

class Geonetwork():
    def __init__(self, version, service_url, user, password):
        if version == 'api0.1':
            self.xmlapi = xmlapi_new.Geonetwork(service_url)
        else:
            self.xmlapi = xmlapi_old.Geonetwork(service_url + '/srv/eng/')
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
            
    def create_metadata(self, layer, layer_info, ds_type):
        ws = layer.datastore.workspace
        minx, miny, maxx, maxy = self.get_extent(layer_info, ds_type)
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
        (ds_type, layer_info) = mapservice.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, "json")
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
        layer = kwargs['layer']
        try:
            muuid = self.metadata_insert(layer)
            if muuid:
                lm = LayerMetadata(layer=layer, metadata_uuid=muuid[0], metadata_id=muuid[1])
                lm.save()
            
        except Exception as e:
            logger.exception("layer metadata create failed")
            pass
        
    def layer_updated_handler(self, sender, **kwargs):
        layer = kwargs['layer']
        try:
            lm = LayerMetadata.objects.get(layer=layer)
            (ds_type, layer_info) = mapservice.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, "json")
            if self.xmlapi.gn_auth(self.user, self.password):
                self.xmlapi.gn_update_metadata(lm.metadata_uuid, layer, layer.abstract, layer_info, ds_type)
                self.xmlapi.gn_unauth()
        except Exception as e:
            logger.exception("layer metadata update failed")
            pass
        
    def layer_deleted_handler(self, sender, **kwargs):
        layer = kwargs['layer']
        try:
            lm = LayerMetadata.objects.get(layer=layer)            
            self.metadata_delete(lm)
            lm.delete()
            
        except Exception as e:
            logger.exception("layer metadata delete failed")
            pass

    def get_extent(self, layer_info, ds_type):
        minx = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['minx'])
        miny = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['miny'])
        maxx = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['maxx'])
        if layer_info[ds_type]['latLonBoundingBox']['minx'] > layer_info[ds_type]['latLonBoundingBox']['maxx']:
            maxx = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['minx'] + 1)
        maxy = str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
        if layer_info[ds_type]['latLonBoundingBox']['miny'] > layer_info[ds_type]['latLonBoundingBox']['maxy']:
            maxy = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['miny'] + 1)
        return (minx, miny, maxx, maxy)

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
signals.layer_created.connect(geonetwork_service.layer_created_handler)
signals.layer_updated.connect(geonetwork_service.layer_updated_handler)
signals.layer_deleted.connect(geonetwork_service.layer_deleted_handler)
