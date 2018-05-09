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

from models import ColorMap, ColorMapEntry, Library, Style, StyleLayer, Rule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, ExternalGraphicSymbolizer, TextSymbolizer, RasterSymbolizer
from gvsigol_services.backend_mapservice import backend as mapservice
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_core import utils as core_utils
from django.http import HttpResponse
from gvsigol import settings
import utils, sld_utils, sld_builder
import tempfile, zipfile
import os, shutil
import StringIO
import string
import random
import utils
import json
import re

def create_style(request, json_data, layer_id, is_preview=False, has_custom_legend=None):

    layer = Layer.objects.get(id=int(layer_id))
    datastore = layer.datastore
    workspace = datastore.workspace
    
    layer_styles = StyleLayer.objects.filter(layer=layer)
    is_default = False
    if not is_preview:
        is_default = json_data.get('is_default')
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
        
    name = json_data.get('name')
    if is_preview:
        name = name + '__tmp'
        is_default = False        
        
    style = Style(
        name = name,
        title = json_data.get('title'),
        is_default = is_default,
        type = 'CT'
    )
    
    if has_custom_legend == 'true':
        style.has_custom_legend = True
        legend_name = 'legend_' + ''.join(random.choice(string.ascii_uppercase) for i in range(6)) + '.png'
        legend_path = utils.check_custom_legend_path()
        style.custom_legend_url = utils.save_custom_legend(legend_path, request.FILES['file'], legend_name)
        
    else:
        style.has_custom_legend = False
        
    style.save()
    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()
    
    json_rule = json_data.get('rule')
    
    filter_text = ""
    if json_rule.get('filter').__len__() != 0:
        filter_text = str(json.dumps(json_rule.get('filter')))
        
    rule = Rule(
        style = style,
        name = json_rule.get('name'),
        title = json_rule.get('title'),
        abstract = "",
        filter = filter_text,
        minscale = json_rule.get('minscale'),
        maxscale = json_rule.get('maxscale'),
        order = json_rule.get('order')
    )
    rule.save()
    
    color_map = ColorMap(
        type = 'ramp',
        extended = False
    )
    color_map.save()
    
    symbolizer = RasterSymbolizer(
        rule = rule,
        color_map = color_map,
        order = 0,
        opacity = 1.0           
    )
    symbolizer.save()
    
    color_map_entry_list = []
    for entry in json_data.get('entries'): 
        json_entry = json.loads(entry.get('json'))
        color_map_entry = ColorMapEntry(
            color_map = color_map,
            order = int(json_entry.get('order')),
            color = json_entry.get('color'),
            quantity = json_entry.get('quantity'),
            label = json_entry.get('label'),
            opacity = json_entry.get('opacity')                
        )
        color_map_entry_list.append(color_map_entry)
    
    order = 0
    color_map_entry_list = sorted(color_map_entry_list, key=lambda color_map_entry: float(color_map_entry.quantity))
    for cme in color_map_entry_list:
        cme.order = order
        cme.save()
        order = order + 1
         
    sld_body = sld_builder.build_sld(layer, style)
    if is_preview:
        if mapservice.createOverwrittenStyle(style.name, sld_body, True): 
            return True
        else:
            return False
    else:
        if mapservice.createOverwrittenStyle(style.name, sld_body, True): 
            if not is_preview:
                mapservice.setLayerStyle(layer, style.name, style.is_default)
            return True
            
        else:
            return False
    
def update_style(request, json_data, layer_id, style_id, is_preview=False, has_custom_legend=None):   
    style = Style.objects.get(id=int(style_id))
    layer = Layer.objects.get(id=int(layer_id))
    
    layer_styles = StyleLayer.objects.filter(layer=layer)
    style_is_default = False
    if not is_preview:
        style_is_default = json_data.get('is_default')
        
    if style_is_default:
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            s.is_default = False
            s.save()
        datastore = layer.datastore
        workspace = datastore.workspace
        mapservice.setLayerStyle(layer, style.name, style.is_default)
    else:
        has_default_style = False
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            if s != style and s.is_default:
                has_default_style = True
        if not has_default_style:
            datastore = layer.datastore
            workspace = datastore.workspace
            style_is_default = True
            mapservice.setLayerStyle(layer, style.name, True)
        
    
    if has_custom_legend == 'true':
        style.has_custom_legend = True
        legend_name = 'legend_' + ''.join(random.choice(string.ascii_uppercase) for i in range(6)) + '.png'
        legend_path = utils.check_custom_legend_path()
        style.custom_legend_url = utils.save_custom_legend(legend_path, request.FILES['file'], legend_name)
        
    else:
        style.has_custom_legend = False
        
    style.title = json_data.get('title')
    if json_data.get('minscale') != '':
        style.minscale = json_data.get('minscale')
    else:
        style.minscale = -1
    if json_data.get('maxscale') != '':
        style.maxscale = json_data.get('maxscale')
    else:
        style.maxscale = -1
    style.is_default = style_is_default
    style.save()
    
    json_rule = json_data.get('rule')
        
    filter_text = ""
    if json_rule.get('filter').__len__() != 0:
        filter_text = str(json.dumps(json_rule.get('filter')))
        
    if json_data.get('minscale') != '':
        minscale = json_rule.get('minscale')
    else:
        minscale = -1
    if json_data.get('maxscale') != '':
        maxscale = json_rule.get('maxscale')
    else:
        maxscale = -1
    
    rule_old = Rule.objects.get(style=style)
    rule_old.delete()
    
    rule = Rule(
        style = style,
        name = json_rule.get('name'),
        title = json_rule.get('title'),
        abstract = '',
        filter = filter_text,
        minscale = minscale,
        maxscale = maxscale,
        order = json_rule.get('order')
    )
    rule.save()
    
    for s in Symbolizer.objects.filter(rule=rule):
        s.rastersymbolizer.color_map.delete()
        s.delete()
        
    color_map = ColorMap(
        type = 'ramp',
        extended = False
    )
    color_map.save()
    
    symbolizer = RasterSymbolizer(
        rule = rule,
        color_map = color_map,
        order = 0,
        opacity = 1.0           
    )
    symbolizer.save()
    
    color_map_entry_list = []
    for entry in json_data.get('entries'): 
        json_entry = json.loads(entry.get('json'))
        color_map_entry = ColorMapEntry(
            color_map = color_map,
            order = int(json_entry.get('order')),
            color = json_entry.get('color'),
            quantity = json_entry.get('quantity'),
            label = json_entry.get('label'),
            opacity = json_entry.get('opacity')                
        )
        
        color_map_entry_list.append(color_map_entry)
    
    order = 0
    color_map_entry_list = sorted(color_map_entry_list, key=lambda color_map_entry: float(color_map_entry.quantity))
    for cme in color_map_entry_list:
        cme.order = order
        cme.save()
        order = order + 1
    
    sld_body = sld_builder.build_sld(layer, style)
    if is_preview:
        if mapservice.createOverwrittenStyle(style.name, sld_body, True): 
            return True
        else:
            return False
    else:
        if mapservice.updateStyle(layer, style.name, sld_body): 
            mapservice.setLayerStyle(layer, style.name, style.is_default)
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
    
    (ds_type, resource) = mapservice.getResourceInfo(workspace.name, datastore, layer.name, "json")

    layer_url = core_utils.get_wms_url(request, workspace)
    layer_wfs_url = core_utils.get_wfs_url(request, workspace)
    
    preview_url = settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
                      
    conf = {
        'layer_id': layer_id,
        'layer_url': layer_url,
        'layer_wfs_url': layer_wfs_url,
        'layer_name': workspace.name + ':' + layer.name,
        'style_name': workspace.name + '_' + layer.name + '_' + str(index),
        'libraries': Library.objects.all(),
        'supported_crs': json.dumps(core_utils.get_supported_crs()),
        'extent': json.dumps(resource.get('coverage').get('nativeBoundingBox')),
        'extent_epsg': resource.get('coverage').get('grid').get('crs'),
        'preview_url': preview_url
    }    
     
    return conf