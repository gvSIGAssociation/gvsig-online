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
from gvsigol_services.backend_mapservice import backend as mapservice
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_core import utils as core_utils
from django.http import HttpResponse
from gvsigol import settings
import utils, sld_utils, sld_builder
import tempfile, zipfile
import os, shutil
import StringIO
import utils
import json
import re
import ast

def create_style(request, json_data, layer_id, is_preview=False):

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
        type = 'EX'
    )
    if json_data.get('minscale') != '':
        style.minscale = json_data.get('minscale')
    else:
        style.minscale = -1
    if json_data.get('maxscale') != '':
        style.maxscale = json_data.get('maxscale')
    else:
        style.maxscale = -1
    style.save()
    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()
            
    for r in json_data.get('rules'):
        json_rule = r.get('rule')
        
        filter_text = ""
        if json_rule.get('filter').__len__() != 0:
            filter_text = str(json.dumps(json_rule.get('filter')))
            
        rule = Rule(
            style = style,
            name = json_rule.get('name'),
            title = json_rule.get('title'),
            abstract = '',
            filter = filter_text,
            minscale = json_rule.get('minscale'),
            maxscale = json_rule.get('maxscale'),
            order = json_rule.get('order')
        )
        rule.save()
        
        for sym in r.get('symbolizers'): 
            if sym.get('type') == 'PolygonSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = PolygonSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()
            
            elif sym.get('type') == 'LineSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = LineSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()      
                
            elif sym.get('type') == 'MarkSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = MarkSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    well_known_name = json_sym.get('well_known_name'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()  
                
            elif sym.get('type') == 'ExternalGraphicSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = ExternalGraphicSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    online_resource = json_sym.get('online_resource'),
                    format = json_sym.get('format')                 
                )
                symbolizer.save()    
                
            elif sym.get('type') == 'TextSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = TextSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    label = json_sym.get('label'),
                    font_family = json_sym.get('font_family'),
                    font_size = json_sym.get('font_size'),
                    font_weight = json_sym.get('font_weight'),
                    font_style = json_sym.get('font_style'),
                    halo_fill = json_sym.get('halo_fill'),
                    halo_fill_opacity = json_sym.get('halo_fill_opacity'),     
                    halo_radius = json_sym.get('halo_radius'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    
                )
                symbolizer.save()
            
    sld_body = sld_builder.build_sld(layer, style)
    if is_preview:
        if mapservice.createOverwrittenStyle(style.name, sld_body, True): 
            return True
        else:
            return False
    else:
        if mapservice.createStyle(style.name, sld_body): 
            if not is_preview:
                mapservice.setLayerStyle(layer, style.name, style.is_default)
            return True
            
        else:
            return False
    
def update_style(request, json_data, layer_id, style_id):   
    style = Style.objects.get(id=int(style_id))
    layer = Layer.objects.get(id=int(layer_id))
    
    layer_styles = StyleLayer.objects.filter(layer=layer)
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
    
    rules = Rule.objects.filter(style=style)
    for ru in rules:
        symbolizers = Symbolizer.objects.filter(rule=ru)
        for symbolizer in symbolizers:
            symbolizer.delete()
        ru.delete()
    
    for r in json_data.get('rules'):           
        json_rule = r.get('rule')
        
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
            
        for sym in r.get('symbolizers'): 
            if sym.get('type') == 'PolygonSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = PolygonSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()
            
            elif sym.get('type') == 'LineSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = LineSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()      
                
            elif sym.get('type') == 'MarkSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = MarkSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    well_known_name = json_sym.get('well_known_name'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()  
                
            elif sym.get('type') == 'ExternalGraphicSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = ExternalGraphicSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    online_resource = json_sym.get('online_resource'),
                    format = json_sym.get('format')                 
                )
                symbolizer.save()    
                
            elif sym.get('type') == 'TextSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = TextSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    label = json_sym.get('label'),
                    font_family = json_sym.get('font_family'),
                    font_size = json_sym.get('font_size'),
                    font_weight = json_sym.get('font_weight'),
                    font_style = json_sym.get('font_style'),
                    halo_fill = json_sym.get('halo_fill'),
                    halo_fill_opacity = json_sym.get('halo_fill_opacity'),     
                    halo_radius = json_sym.get('halo_radius'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    
                )
                symbolizer.save()
    
    sld_body = sld_builder.build_sld(layer, style)
    if mapservice.updateStyle(layer, style.name, sld_body): 
        mapservice.setLayerStyle(layer, style.name, style.is_default)
        return True
    else:
        return False


def get_conf(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    index = len(StyleLayer.objects.filter(layer=layer))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    
    (ds_type, resource) = mapservice.getResourceInfo(workspace.name, datastore, layer.name, "json")
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
                            field['title-'+id] = f['title-'+id]
            else:
                for id, language in settings.LANGUAGES:
                    field['title-'+id] = field['name']
            new_fields.append(field)
        fields = new_fields
        
    feature_type = utils.get_feature_type(fields)
    alphanumeric_fields = utils.get_alphanumeric_fields(fields)
       
    supported_fonts_str = mapservice.getSupportedFonts()
    supported_fonts = json.loads(supported_fonts_str)
    sorted_fonts = utils.sortFontsArray(supported_fonts.get("fonts"))
              
    layer_url = core_utils.get_wms_url(request, workspace)
    layer_wfs_url = core_utils.get_wfs_url(request, workspace)
    
    preview_url = ''
    if feature_type == 'PointSymbolizer':
        preview_url = settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point'    
    elif feature_type == 'LineSymbolizer':      
        preview_url = settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line'     
    elif feature_type == 'PolygonSymbolizer': 
        preview_url = settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
                  
    conf = {
        'featureType': feature_type,
        'fields': alphanumeric_fields,
        'json_alphanumeric_fields': json.dumps(alphanumeric_fields),
        'fonts': sorted_fonts,
        'layer_id': layer_id,
        'layer_url': layer_url,
        'layer_wfs_url': layer_wfs_url,
        'layer_name': workspace.name + ':' + layer.name,
        'style_name': workspace.name + '_' + layer.name + '_' + str(index),
        'libraries': Library.objects.all(),
        'supported_crs': json.dumps(core_utils.get_supported_crs()),
        'preview_url': preview_url
    }    
     
    return conf