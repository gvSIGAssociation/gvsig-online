

from django.apps import AppConfig


class GvsigolSymbologyConfig(AppConfig):
    name = 'gvsigol_symbology'
    
    def ready(self):
        """Importar signals cuando la app esté lista."""
        import gvsigol_symbology.signals  # noqa