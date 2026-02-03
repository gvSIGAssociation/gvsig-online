# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
@author: Mehdi Jelassia <mjelassia@scolab.es>
'''

from .models import Library, Style, StyleLayer, Rule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, ExternalGraphicSymbolizer, TextSymbolizer
from gvsigol_services import geographic_servers
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_core import utils as core_utils
from gvsigol import settings
from . import utils, sld_builder
import json
import ast

def create_style(style_name, style_title, is_default, sld, layer, gs, is_preview=False):
    if is_preview:
        style_name = style_name + '__tmp'
    is_default = utils.set_default_style(layer, gs, is_preview=is_preview, is_default=is_default)

    style = Style(
        name = style_name,
        title = style_title,
        is_default = is_default,
        minscale = -1,
        maxscale = -1,
        type = 'MC',
        sld = sld
    )
    style.save()
    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()

    sld_body = utils.encode_xml(sld)

    if is_preview:
        if gs.createOverwrittenStyle(style.name, sld_body, True): 
            return style
    else:
        if gs.createStyle(style.name, sld_body): 
            if not is_preview:
                gs.setLayerStyle(layer, style.name, style.is_default)
            return style

def update_style(style_title, is_default, sld, layer, gs, style, is_preview=False):
    is_default = utils.set_default_style(layer, gs, style=style, is_preview=is_preview, is_default=is_default)

    style.sld = sld
    style.title = style_title
    style.is_default = is_default
    style.save()

    sld_body = utils.encode_xml(sld)

    if is_preview:
        if gs.createOverwrittenStyle(style.name, sld_body, True): 
            return style
    else:
        if gs.updateStyle(layer, style.name, sld_body): 
            gs.setLayerStyle(layer, style.name, style.is_default)
            return style
        else:
            # try to recover from inconsistent gvsigol - geoserver status
            if utils.reset_geoserver_style(gs, layer, style):
                gs.setLayerStyle(layer, style.name, style.is_default)
                return style


def get_conf(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    index = utils.get_next_index(layer)
    (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
    fields = utils.get_fields(resource)
    if layer.conf:
        new_fields = []
        conf = None
        if layer and layer.conf:
            conf = ast.literal_eval(layer.conf)
        for field in fields:
            if conf:
                for f in conf['fields']:
                    if f['name'] == field['name']:
                        for id, language in settings.LANGUAGES:
                            if 'title-'+id in f:
                                field['title-'+id] = f.get('title-'+id, field['name'])
                            else:
                                field['title-'+id] = f['name']
            else:
                for id, language in settings.LANGUAGES:
                    field['title-'+id] = field['name']
            new_fields.append(field)
        fields = new_fields

    feature_type = utils.get_feature_type(fields)
    alphanumeric_fields = utils.get_alphanumeric_fields(fields)

    supported_fonts_str = gs.getSupportedFonts()
    supported_fonts = json.loads(supported_fonts_str)
    sorted_fonts = utils.sortFontsArray(supported_fonts.get("fonts"))
    
    layer_url = core_utils.get_wms_url(workspace)
    layer_wfs_url = core_utils.get_wfs_url(workspace)
    numeric_fields = utils.get_numeric_fields(fields)


    conf = {
        'featureType': feature_type,
        'json_alphanumeric_fields': json.dumps(alphanumeric_fields),
        'json_numeric_fields': json.dumps(numeric_fields),
        'fonts': sorted_fonts,
        'layer_id': layer_id,
        'layer_url': layer_url,
        'layer_wfs_url': layer_wfs_url,
        'layer_name': workspace.name + ':' + layer.name,
        'style_name': workspace.name + '_' + layer.name + '_' + str(index),
        'libraries': Library.objects.all(),
        'supported_crs': json.dumps(core_utils.get_supported_crs()),
        'preview_url': utils.get_preview_url(workspace, feature_type)
    }
    utils.set_auth_settings(request, conf)
    return conf
