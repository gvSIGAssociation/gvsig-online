from django.apps import AppConfig

class GvsigolCatalogConfig(AppConfig):
    name = 'gvsigol_plugin_catalog'

    def ready(self):
        from gvsigol_plugin_catalog.service import geonetwork_service