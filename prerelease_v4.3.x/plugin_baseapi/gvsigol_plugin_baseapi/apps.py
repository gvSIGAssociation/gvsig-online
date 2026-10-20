

from django.apps import AppConfig

class GvsigolBaseApiConfig(AppConfig):
    name = 'gvsigol_plugin_baseapi'
    verbose_name = "API de gvsig Online"

    
    def ready(self):
        AppConfig.ready(self)

