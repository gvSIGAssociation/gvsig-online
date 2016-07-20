# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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
from django.http import HttpResponse
from gvsigol import settings
import utils, sld_utils, sld_builder
import tempfile, zipfile
import os, shutil
import StringIO
import utils
import json
import re

def create_style(session, json_data, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    datastore = layer.datastore
    workspace = datastore.workspace
    
    style = Style(
        name = json_data.get('name'),
        title = json_data.get('title'),
        is_default = json_data.get('is_default'),
        type = 'US'
    )
    style.save()
    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()
    
    if style.is_default:
        layer_styles = StyleLayer.objects.filter(layer=layer)
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            s.is_default = False
    
    json_rule = json_data.get('rule')
    rule = Rule(
        style = style,
        name = json_rule.get('name'),
        title = json_rule.get('title'),
        abstract = '',
        filter = '',
        minscale = json_rule.get('minscale'),
        maxscale = json_rule.get('maxscale'),
        order = json_rule.get('order')
    )
    rule.save()
        
    for sym in json_data.get('symbolizers'): 
        if sym.get('type') == 'PolygonSymbolizer':
            json_sym = json.loads(sym.get('json'))
            symbolizer = PolygonSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity')                   
            )
            symbolizer.save()
        
        elif sym.get('type') == 'LineSymbolizer':
            json_sym = json.loads(sym.get('json'))
            symbolizer = LineSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity')                   
            )
            symbolizer.save()      
            
        elif sym.get('type') == 'Mark':
            json_sym = json.loads(sym.get('json'))
            symbolizer = MarkSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
                well_known_name = json_sym.get('well_known_name'),
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity')                  
            )
            symbolizer.save()  
            
        elif sym.get('type') == 'ExternalGraphicSymbolizer':
            json_sym = json.loads(sym.get('json'))
            symbolizer = ExternalGraphicSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
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
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                halo_fill = json_sym.get('halo_fill'),
                halo_fill_opacity = json_sym.get('halo_fill_opacity'),     
                halo_radius = json_sym.get('halo_radius'),
            )
            symbolizer.save()
            
    sld_body = sld_builder.build_sld(layer, style)
    if mapservice.createStyle(style.name, sld_body, session): 
        if style.is_default:
            mapservice.setLayerStyle(workspace.name+":"+layer.name, style.name, session)
        return True
        
    else:
        return False
    
def update_style(session, json_data, layer_id, style_id):   
    style = Style.objects.get(id=int(style_id))
    layer = Layer.objects.get(id=int(layer_id))
    
    if json_data.get('is_default'):
        layer_styles = StyleLayer.objects.filter(layer=layer)
        for ls in layer_styles:
            s = Style.objects.get(id=ls.style.id)
            s.is_default = False
            s.save()
        datastore = layer.datastore
        workspace = datastore.workspace
        mapservice.setLayerStyle(workspace.name+":"+layer.name, style.name, session)
    
    style.title = json_data.get('title')
    style.is_default = json_data.get('is_default')
    style.save()
    
    json_rule = json_data.get('rule')
    rule = Rule.objects.get(style=style)
    minscale = json_rule.get('minscale')
    maxscale = json_rule.get('maxscale')
    rule.minscale = minscale
    rule.maxscale = maxscale
    rule.save()
    
    for s in Symbolizer.objects.filter(rule=rule):
        s.delete()
        
    for sym in json_data.get('symbolizers'): 
        if sym.get('type') == 'PolygonSymbolizer':
            json_sym = json.loads(sym.get('json'))
            symbolizer = PolygonSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity')                   
            )
            symbolizer.save()
        
        elif sym.get('type') == 'LineSymbolizer':
            json_sym = json.loads(sym.get('json'))
            symbolizer = LineSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity')                   
            )
            symbolizer.save()      
            
        elif sym.get('type') == 'Mark':
            json_sym = json.loads(sym.get('json'))
            symbolizer = MarkSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
                well_known_name = json_sym.get('well_known_name'),
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity')                  
            )
            symbolizer.save()  
            
        elif sym.get('type') == 'ExternalGraphic':
            json_sym = json.loads(sym.get('json'))
            symbolizer = ExternalGraphicSymbolizer(
                rule = rule,
                order = int(sym.get('order')),
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
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                halo_fill = json_sym.get('halo_fill'),
                halo_fill_opacity = json_sym.get('halo_fill_opacity'),     
                halo_radius = json_sym.get('halo_radius'),
            )
            symbolizer.save()
    
    sld_body = sld_builder.build_sld(layer, style)
    if mapservice.updateStyle(style.name, sld_body, session): 
        return True
    else:
        return False


def get_conf(session, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    index = len(StyleLayer.objects.filter(layer=layer))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    
    resource = mapservice.getResourceInfo(workspace.name, datastore.name, layer.name, "json", session)
    fields = utils.get_fields(resource)
    feature_type = utils.get_feature_type(fields)
    alphanumeric_fields = utils.get_alphanumeric_fields(fields)
       
    supported_fonts_str = mapservice.getSupportedFonts(session)
    supported_fonts = json.loads(supported_fonts_str)
    sorted_fonts = utils.sortFontsArray(supported_fonts.get("fonts"))
              
    split_wms_url = workspace.wms_endpoint.split('//')
    authenticated_wms_url = split_wms_url[0] + '//' + session['username'] + ':' + session['password'] + '@' + split_wms_url[1]
    layer_url = authenticated_wms_url
    
    split_wfs_url = workspace.wfs_endpoint.split('//')
    authenticated_wfs_url = split_wfs_url[0] + '//' + session['username'] + ':' + session['password'] + '@' + split_wfs_url[1]
    layer_wfs_url = authenticated_wfs_url
                      
    conf = {
        'featureType': feature_type,
        'fields': json.dumps(fields), 
        'alphanumeric_fields': json.dumps(alphanumeric_fields),
        'fonts': sorted_fonts,
        'layer_id': layer_id,
        'layer_url': layer_url,
        'layer_wfs_url': layer_wfs_url,
        'layer_name': workspace.name + ':' + layer.name,
        'style_name': workspace.name + '_' + layer.name + '_' + str(index),
        'libraries': Library.objects.all(),
        'supported_crs': settings.SUPPORTED_CRS,
        'preview_point_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point',
        'preview_line_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line',
        'preview_polygon_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
    }    
     
    return conf