# utils.py o donde creas conveniente

from gvsigol_plugin_geoetl.models import ETLPluginSettings
from gvsigol_services.views import _layer_refresh_extent
from gvsigol_services import geographic_servers
from gvsigol_services.models import Layer, Datastore
import json

def get_ttl_hours():
    settings = ETLPluginSettings.objects.first()
    return settings.ttl_hours if settings else 24


def layer_refresh_conf_internal(layer_id):
    try:
        layer = Layer.objects.get(pk=layer_id)
        _layer_refresh_extent(layer)
        if layer.type.startswith('v_'):
            server = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            expose_pks = server.datastore_check_exposed_pks(layer.datastore)
            layer.get_config_manager().refresh_field_conf(include_pks=expose_pks)
        layer.save()
        if layer.type.startswith('v_'):
            i, source_name, schema = layer.get_db_connection()
            with i as conn:
                conn.update_pk_sequences(source_name, schema=schema)
        return True
    except Exception as e:
        print("Error refreshing layer conf: "+str(e))
        return False

def refresh_layers_by_params(schema: str, layer: str, params: dict):

    field_map = {
        "host": "host",
        "port": "port",
        "database": "database",
        "user": "user",
        "password": "passwd",
    }

    layers = Layer.objects.select_related('datastore').filter(name=layer)

    for lyr in layers:
        try:
            conn = json.loads(lyr.datastore.connection_params)
        except (ValueError, TypeError):
            continue 

        if conn.get("schema") != schema:
            continue

        match = True

        for param_key, json_key in field_map.items():
            conn_value = conn.get(json_key)
            param_value = params.get(param_key)

            if str(conn_value) != str(param_value):
                match = False
                break 

        if match:
            layer_refresh_conf_internal(lyr.id)