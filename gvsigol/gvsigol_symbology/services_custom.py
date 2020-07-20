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

from models import Library, Style, StyleLayer, Rule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, ExternalGraphicSymbolizer, TextSymbolizer
from gvsigol_services import geographic_servers
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_core import utils as core_utils
from gvsigol import settings
import utils, sld_builder
import json
import ast

def create_style(style_name, style_title, is_default, sld, layer_id, is_preview=False):
    
    layer = Layer.objects.get(id=int(layer_id))
    datastore = layer.datastore
    workspace = datastore.workspace
    gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)

    layer_styles = StyleLayer.objects.filter(layer=layer)
    if is_default:
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            s.is_default = False
            s.save()
    else:
        has_default_style = False
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            if s.is_default:
                has_default_style = True
        if not has_default_style:
            is_default = True

    if is_preview:
        style_name = style_name + '__tmp'
        is_default = False

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

    sld_body = sld

    if is_preview:
        if gs.createOverwrittenStyle(style.name, sld_body, True): 
            return True
        else:
            return False
    else:
        if gs.createStyle(style.name, sld_body): 
            if not is_preview:
                gs.setLayerStyle(layer, style.name, style.is_default)
            return True

        else:
            return False

def update_style(style_title, is_default, sld, layer_id, style_id, is_preview=False):
    style = Style.objects.get(id=int(style_id))
    layer = Layer.objects.get(id=int(layer_id))
    datastore = layer.datastore
    workspace = datastore.workspace
    gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)

    layer_styles = StyleLayer.objects.filter(layer=layer)

    if is_default:
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            s.is_default = False
            s.save()
        gs.setLayerStyle(layer, style.name, style.is_default)

    else:
        has_default_style = False
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            if s != style and s.is_default:
                has_default_style = True
        if not has_default_style:
            gs.setLayerStyle(layer, style.name, True)

    style.sld = sld
    style.title = style_title
    style.is_default = is_default
    style.save()

    sld_body = sld

    if is_preview:
        if gs.createOverwrittenStyle(style.name, sld_body, True): 
            return True
        else:
            return False
    else:
        if gs.updateStyle(layer, style.name, sld_body): 
            gs.setLayerStyle(layer, style.name, style.is_default)
            return True
        else:
            return False



def get_conf(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    
    index = len(StyleLayer.objects.filter(layer=layer))
    styleLayers = StyleLayer.objects.filter(layer=layer)
    for style_layer in styleLayers:
        aux_name = style_layer.style.name
        aux_name = aux_name.replace(workspace.name + '_' + layer.name + '_' , '')

        try:
            aux_index = int(aux_name)
            if index < aux_index+1:
                index = aux_index + 1
        except ValueError:
            print "Error getting index"
    
    layer_url = core_utils.get_wms_url(workspace)

    conf = {
        'layer_id': layer_id,
        'layer_url': layer_url,
        'layer_name': workspace.name + ':' + layer.name,
        'style_name': workspace.name + '_' + layer.name + '_' + str(index)
    }

    return conf
