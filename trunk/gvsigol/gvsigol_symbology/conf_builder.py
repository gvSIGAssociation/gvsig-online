# -*- coding: utf-8 -*-
'''
Contexto común de los editores de leyendas vectoriales (get_conf de cada tipo).

Antes cada services_<tipo>.get_conf tenía su propia copia de esta lógica; las
diferencias entre tipos se expresan ahora con parámetros. La salida está fijada
por GetConfCharacterizationTest.
'''
import ast
import json

from gvsigol import settings
from gvsigol_core import utils as core_utils
from gvsigol_services import geographic_servers
from gvsigol_services.models import Layer, Datastore, Workspace

from .models import Library, ColorRampLibrary
from . import utils


def _apply_field_titles(fields, layer_conf):
    '''Añade title-<idioma> a los campos configurados en layer.conf (formato de dict Python).'''
    conf = ast.literal_eval(layer_conf) if layer_conf else None
    new_fields = []
    for field in fields:
        if conf:
            for f in conf['fields']:
                if f['name'] == field['name']:
                    for lang_id, language in settings.LANGUAGES:
                        field['title-' + lang_id] = f.get('title-' + lang_id, field['name'])
        else:
            for lang_id, language in settings.LANGUAGES:
                field['title-' + lang_id] = field['name']
        new_fields.append(field)
    return new_fields


def build_vector_conf(request, layer_id, alphanumeric_list=True, numeric_list=False,
                      json_numeric=False, ramp_libraries=False, tolerate_empty_fields=False):
    '''
    alphanumeric_list: incluye 'fields' (campos alfanuméricos).
    numeric_list: incluye 'numeric_fields'.
    json_numeric: incluye 'json_numeric_fields'.
    ramp_libraries: incluye 'ramp_libraries'.
    tolerate_empty_fields: si la capa no tiene campos, usa PointSymbolizer y lista vacía
        (comportamiento de símbolo único; el resto de tipos fallaban en ese caso).
    '''
    layer = Layer.objects.get(id=int(layer_id))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    index = utils.get_next_index(layer)

    (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
    fields = utils.get_fields(resource)
    if layer.conf and (fields or not tolerate_empty_fields):
        fields = _apply_field_titles(fields, layer.conf)

    if tolerate_empty_fields:
        feature_type = utils.get_feature_type(fields) or 'PointSymbolizer'
        alphanumeric_fields = utils.get_alphanumeric_fields(fields) if fields else []
    else:
        feature_type = utils.get_feature_type(fields)
        alphanumeric_fields = utils.get_alphanumeric_fields(fields)

    supported_fonts = json.loads(gs.getSupportedFonts())
    sorted_fonts = utils.sortFontsArray(supported_fonts.get("fonts"))

    conf = {
        'featureType': feature_type,
        'json_alphanumeric_fields': utils.json_for_script(alphanumeric_fields),
        'fonts': sorted_fonts,
        'layer_id': layer_id,
        'layer_url': core_utils.get_wms_url(workspace),
        'layer_wfs_url': core_utils.get_wfs_url(workspace),
        'layer_name': workspace.name + ':' + layer.name,
        'style_name': workspace.name + '_' + layer.name + '_' + str(index),
        'libraries': Library.objects.all(),
        'supported_crs': utils.json_for_script(core_utils.get_supported_crs()),
        'preview_url': utils.get_preview_url(workspace, feature_type)
    }
    if alphanumeric_list:
        conf['fields'] = alphanumeric_fields
    if numeric_list or json_numeric:
        numeric_fields = utils.get_numeric_fields(fields)
        if numeric_list:
            conf['numeric_fields'] = numeric_fields
        if json_numeric:
            conf['json_numeric_fields'] = utils.json_for_script(numeric_fields)
    utils.set_auth_settings(request, conf)
    if ramp_libraries:
        conf['ramp_libraries'] = ColorRampLibrary.objects.all()
    return conf
