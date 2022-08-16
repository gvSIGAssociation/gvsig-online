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
@author: Javi Rodrigo <jrodrigo@scolab.es>
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
        type = 'CS',
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
    index = utils.get_next_index(layer)
    layer_url = core_utils.get_wms_url(workspace)

    conf = {
        'layer_id': layer_id,
        'layer_url': layer_url,
        'layer_name': workspace.name + ':' + layer.name,
        'style_name': workspace.name + '_' + layer.name + '_' + str(index)
    }
    utils.set_auth_settings(request, conf)
    return conf
