from django.apps import AppConfig
from django.db.models.signals import post_migrate

class GvsigolCatastroConfig(AppConfig):
    name = 'gvsigol_plugin_catastro'
    verbose_name = "Catastro"
    label = "gvsigol_plugin_catastro"

    def ready(self):
        AppConfig.ready(self)
        post_migrate.connect(self._ensure_catastro_layer_exists, sender=self)
    
    def _ensure_catastro_layer_exists(self, sender, **kwargs):
        """
        Asegura que existe un LayerGroup y Layer de catastro.
        Si no existen, los crea automáticamente.
        """
        try:            
            from gvsigol_services.models import LayerGroup, Layer, Server
            from . import settings
            from django.db import transaction
            
            with transaction.atomic():
                default_server = Server.objects.filter(default=True).first()
                if not default_server:
                    default_server = Server.objects.first()
                    if not default_server:
                        print("ERROR: No hay ningún servidor configurado en el sistema")
                        return
                    print(f"WARNING: No hay servidor por defecto, usando: {default_server.name}")
                    
                layer_group_name = "group_plugin_catastro"
                layer_group, created = LayerGroup.objects.get_or_create(
                    name=layer_group_name,
                    defaults={
                        'server_id': default_server.id,
                        'title': 'Catastro',
                        'visible': False,
                        'cached': False,
                        'created_by': 'system'
                    }
                )
                
                if created:
                    print(f"INFO: Creado LayerGroup '{layer_group_name}' para catastro")
                else:
                    print(f"INFO: LayerGroup '{layer_group_name}' ya existe")
                
                layer_name = "plugin_catastro"
                layer, created = Layer.objects.get_or_create(
                    name=layer_name,
                    defaults={
                        'external': True,
                        'external_params': f'{{"url": "{settings.URL_CATASTRO}", "layers": "Catastro", "format": "image/png", "version": "1.1.1", "srs": "EPSG:3857"}}',
                        'layer_group': layer_group,
                        'title': 'Catastro',
                        'abstract': 'Servicio WMS de catastro del Ministerio de Hacienda. Información catastral de parcelas y edificios.',
                        'type': 'WMS',
                        'public': True,
                        'visible': False,
                        'queryable': False,
                        'cached': False,
                        'single_image': False,
                        'vector_tile': False,
                        'allow_download': False,
                        'time_enabled': False,
                        'order': 100,
                        'created_by': 'system',
                        'detailed_info_enabled': True,
                        'detailed_info_button_title': 'Información Catastral',
                        'timeout': 30000,
                        'native_srs': 'EPSG:3857',
                        'native_extent': '-20037508.34,-20037508.34,20037508.34,20037508.34',
                        'latlong_extent': '-180,-90,180,90',
                        'real_time': False,
                        'update_interval': 1000,
                        'featureapi_endpoint': '/api/v1'
                    }
                )
                
                if created:
                    print(f"INFO: Creado Layer WMS externo '{layer_name}' para catastro")
                else:
                    print(f"INFO: Layer WMS externo '{layer_name}' ya existe")
                    
        except Exception as e:
            print(f"ERROR: No se pudo crear el layer de catastro: {str(e)}")
            import traceback
            traceback.print_exc()

