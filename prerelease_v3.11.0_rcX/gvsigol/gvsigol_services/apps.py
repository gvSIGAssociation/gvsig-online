

from django.apps import AppConfig

class GvsigolServicesConfig(AppConfig):
    name = 'gvsigol_services'
            
    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Layer'))
