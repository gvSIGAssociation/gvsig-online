# utils.py o donde creas conveniente

from gvsigol_plugin_geoetl.models import ETLPluginSettings

def get_ttl_hours():
    settings = ETLPluginSettings.objects.first()
    return settings.ttl_hours if settings else 24
