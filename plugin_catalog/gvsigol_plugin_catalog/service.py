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
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''
from gvsigol_services import signals
from gvsigol_services.backend_mapservice import backend as mapservice
from gvsigol_plugin_catalog import settings as plugin_settings
from django.core.exceptions import ImproperlyConfigured
from gvsigol_plugin_catalog.models import LayerMetadata
import api as xmlapi

class UnsupportedRequestError(Exception):
    pass

class Geonetwork():
    def __init__(self, service_url, user, password):
        self.xmlapi = xmlapi.Geonetwork(service_url)
        self.user = user
        self.password = password
        
    def metadata_insert(self, layer, abstract, ws, layer_info, ds_type):
        self.xmlapi.gn_auth(self.user, self.password)
        uuid = self.xmlapi.gn_insert_metadata(layer, abstract, ws, layer_info, ds_type)
        self.xmlapi.add_thumbnail(uuid, layer.thumbnail.url)
        self.xmlapi.set_metadata_privileges(uuid)
        self.xmlapi.gn_unauth()
        return uuid
        
    def metadata_delete(self, lm):
        try:
            self.xmlapi.gn_auth(self.user, self.password)
            self.xmlapi.gn_delete_metadata(lm)
            self.xmlapi.gn_unauth()
            return True
        
        except Exception as e:
            print e
            return False
        
    def layer_created_handler(self, sender, **kwargs):
        layer = kwargs['layer']
        try:
            (ds_type, layer_info) = mapservice.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, "json")
            muuid = self.metadata_insert(layer, layer.abstract, layer.datastore.workspace, layer_info, ds_type)
            lm = LayerMetadata(layer=layer, metadata_uuid=muuid)
            lm.save()
            
        except Exception as e:
            print e
            pass
        
    def layer_updated_handler(self, sender, **kwargs):
        layer = kwargs['layer']
        try:
            lm = LayerMetadata.objects.get(layer=layer)            
            self.metadata_delete(lm)
            (ds_type, layer_info) = mapservice.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, "json")
            muuid = self.metadata_insert(layer, layer.abstract, layer.datastore.workspace, layer_info, ds_type)
            lm.metadata_uuid=muuid
            lm.save()
            
        except Exception as e:
            print e
            pass
        
    def layer_deleted_handler(self, sender, **kwargs):
        layer = kwargs['layer']
        try:
            lm = LayerMetadata.objects.get(layer=layer)            
            self.metadata_delete(lm)
            lm.delete()
            
        except Exception as e:
            print e
            pass

def initialize():
    try:
        service_url = plugin_settings.CATALOG_URL
        user = plugin_settings.CATALOG_USER
        password = plugin_settings.CATALOG_PASSWORD
        geonetwork_service = Geonetwork(service_url, user, password) 
        return geonetwork_service
    
    except:
        raise ImproperlyConfigured

geonetwork_service = initialize()
signals.layer_created.connect(geonetwork_service.layer_created_handler)
signals.layer_updated.connect(geonetwork_service.layer_updated_handler)
signals.layer_deleted.connect(geonetwork_service.layer_deleted_handler)