

from django.apps import AppConfig

class GvsigolViewerApiConfig(AppConfig):
    name = 'gvsigol_plugin_projectapi'
    verbose_name = "API Rest de gvsig Online"

    
    def ready(self):
        AppConfig.ready(self)

