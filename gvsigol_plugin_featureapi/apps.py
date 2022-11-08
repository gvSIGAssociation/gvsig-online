

from django.apps import AppConfig

class GvsigolFeatureApiConfig(AppConfig):
    name = 'gvsigol_plugin_featureapi'
    verbose_name = "API de Feature Layer de gvsig Online"

    
    def ready(self):
        AppConfig.ready(self)

