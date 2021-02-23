

from django.apps import AppConfig
import logging
logger = logging.getLogger("gvsigol")


class GvsigolServicesConfig(AppConfig):
    name = 'gvsigol_services'
    
    def _updateLayerInfo(self):
        from gvsigol_services import geographic_servers
        from gvsigol_services.models import Layer, Datastore, Workspace
        layer_list = Layer.objects.filter(external=False)
        for l in layer_list:
            datastore = Datastore.objects.get(id=l.datastore_id)
            workspace = Workspace.objects.get(id=datastore.workspace_id)
            server = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
            try:
                (ds_type, layer_info) = server.getResourceInfo(workspace.name, datastore, l.name, "json")
                if ds_type == 'imagemosaic':
                    ds_type = 'coverage'
                l.native_srs = layer_info[ds_type]['srs']
                l.native_extent = str(layer_info[ds_type]['nativeBoundingBox']['minx']) + ',' + str(layer_info[ds_type]['nativeBoundingBox']['miny']) + ',' + str(layer_info[ds_type]['nativeBoundingBox']['maxx']) + ',' + str(layer_info[ds_type]['nativeBoundingBox']['maxy'])
                l.latlong_extent = str(layer_info[ds_type]['latLonBoundingBox']['minx']) + ',' + str(layer_info[ds_type]['latLonBoundingBox']['miny']) + ',' + str(layer_info[ds_type]['latLonBoundingBox']['maxx']) + ',' + str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
                
            except Exception as e:
                l.default_srs = 'EPSG:4326'
                l.native_extent = '-180,-90,180,90'
                l.latlong_extent = '-180,-90,180,90'
            l.save()
            
    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Layer'))
        
        from gvsigol_core.utils import is_gvsigol_process
        if is_gvsigol_process():
            # don't run during migrations 
            try:
                self._updateLayerInfo()
            except:
                logger.exception("Error updating layer information")