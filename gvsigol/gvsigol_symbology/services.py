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

from models import Library, Style, StyleLayer, Rule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, ExternalGraphicSymbolizer, TextSymbolizer, RasterSymbolizer, ColorMap
from django.utils.translation import ugettext_lazy as _
from gvsigol_services.models import Layer
from django.http import HttpResponse
import utils, sld_builder
import tempfile
import json
import os

def create_default_style(session, layer_id, style_name, style_type, geom_type):
    layer = Layer.objects.get(id=int(layer_id))
    
    style = Style(
        name = style_name,
        title = _('Default style for: ') + layer.title,
        is_default = True,
        type = style_type
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
            
    symbol_type = None
    if geom_type == 'point':
        symbol_type = 'MarkSymbolizer'           
    elif geom_type == 'line':
        symbol_type = 'LineSymbolizer'
    elif geom_type == 'polygon':
        symbol_type = 'PolygonSymbolizer'
    elif geom_type == 'raster':
        symbol_type = 'RasterSymbolizer'
    
    rule = Rule(
        style = style,
        name = 'Default symbol',
        title = 'Default symbol',
        abstract = '',
        filter = str(""),
        minscale = -1,
        maxscale = -1,
        order = 0
    )
    rule.save()
        
    if symbol_type == 'PolygonSymbolizer':
        symbolizer = PolygonSymbolizer(
            rule = rule,
            order = 0,
            fill = '#383838',
            fill_opacity = 0.6,
            stroke = '#000000',
            stroke_width = 1,
            stroke_opacity = 1.0                   
        )
        symbolizer.save()
    
    elif symbol_type == 'LineSymbolizer':
        symbolizer = LineSymbolizer(
            rule = rule,
            order = 0,
            stroke = '#000000',
            stroke_width = 1,
            stroke_opacity = 1.0                  
        )
        symbolizer.save()      
        
    elif symbol_type == 'MarkSymbolizer':
        symbolizer = MarkSymbolizer(
            rule = rule,
            order = 0,
            opacity = 1.0,
            size= 8,
            rotation = 0,
            well_known_name = 'circle',
            fill = '#383838',
            fill_opacity = 0.6,
            stroke = '#000000',
            stroke_width = 1,
            stroke_opacity = 1.0                  
        )
        symbolizer.save()  
        
    elif symbol_type == 'RasterSymbolizer':
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
            
    sld_body = sld_builder.build_sld(layer, style)
    return sld_body

def sld_import(name, is_default, layer_id, file, session, mapservice):
    
    layer = Layer.objects.get(id=int(layer_id))
    datastore = layer.datastore
    workspace = datastore.workspace
    
    ### write the data to a temp file
    tup = tempfile.mkstemp() # make a tmp file
    f = os.fdopen(tup[0], 'w') # open the tmp file for writing
    f.write(file.read()) # write the tmp file
    f.close()
    
    filepath = tup[1]
    tmp_sld = open(filepath, 'r')

    sld = sld_builder.parse_sld(tmp_sld)
    
    style = Style(
        name = name,
        title = sld.NamedLayer[0].UserStyle[0].Title,
        is_default = is_default,
        type = "EX"
    )
    style.save()
    
    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()
    
    rules = sld.NamedLayer[0].UserStyle[0].FeatureTypeStyle[0].Rule
    for r in rules:
        filter = utils.filter_to_json(r.Filter)
        rule = Rule(
            style = style,
            name = r.Name,
            title = r.Title,
            abstract = '',
            filter = json.dumps(filter),
            minscale = -1 if r.MinScaleDenominator is None else r.MinScaleDenominator,
            maxscale = -1 if r.MaxScaleDenominator is None else r.MaxScaleDenominator,
            order = 0
        )
        rule.save()
    
        scount = 0
        for s in r.Symbolizer:
            if s.original_tagname_ == 'PointSymbolizer':
                opacity = s.Graphic.Opacity.valueOf_
                rotation = s.Graphic.Rotation.valueOf_
                size = s.Graphic.Size.valueOf_
                if len(s.Graphic.Mark) >= 1:
                    mark = s.Graphic.Mark[0]
                    
                    fill = '#383838'
                    fill_opacity = 0.5
                    if len(mark.Fill.CssParameter) > 0:
                        for css_parameter in mark.Fill.CssParameter:
                            if css_parameter.name == 'fill':
                                fill =  css_parameter.valueOf_
                            if css_parameter.name == 'fill-opacity':
                                fill_opacity =  css_parameter.valueOf_
                                
                    stroke = '#ffffff'
                    stroke_width = 1
                    stroke_opacity = 0.0
                    if len(mark.Stroke.CssParameter) > 0:
                        for css_parameter in mark.Stroke.CssParameter:
                            if css_parameter.name == 'stroke':
                                stroke =  css_parameter.valueOf_
                            if css_parameter.name == 'stroke-width':
                                stroke_width =  css_parameter.valueOf_
                            if css_parameter.name == 'stroke-opacity':
                                stroke_opacity =  css_parameter.valueOf_
                        
                    symbolizer = MarkSymbolizer(
                        rule = rule,
                        order = scount,
                        opacity = opacity,
                        size = size,
                        rotation = rotation,
                        well_known_name = mark.WellKnownName,
                        fill = fill,
                        fill_opacity = fill_opacity,
                        stroke = stroke,
                        stroke_width = stroke_width,
                        stroke_opacity = stroke_opacity                 
                    )
                    symbolizer.save()
                    
                if len(s.Graphic.ExternalGraphic) >= 1:
                    print 'ExternalGraphic'
                    
            elif s.original_tagname_ == 'LineSymbolizer':
                stroke = '#ffffff'
                stroke_width = 1
                stroke_opacity = 0.0
                if len(s.Stroke.CssParameter) > 0:
                    for css_parameter in s.Stroke.CssParameter:
                        if css_parameter.name == 'stroke':
                            stroke =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-width':
                            stroke_width =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-opacity':
                            stroke_opacity =  css_parameter.valueOf_
                                
                symbolizer = LineSymbolizer(
                    rule = rule,
                    order = scount,
                    stroke = stroke,
                    stroke_width = stroke_width,
                    stroke_opacity = stroke_opacity                 
                )
                symbolizer.save()
                    
            elif s.original_tagname_ == 'PolygonSymbolizer':
                
                fill = '#383838'
                fill_opacity = 0.5
                if len(s.Fill.CssParameter) > 0:
                    for css_parameter in s.Fill.CssParameter:
                        if css_parameter.name == 'fill':
                            fill =  css_parameter.valueOf_
                        if css_parameter.name == 'fill-opacity':
                            fill_opacity =  css_parameter.valueOf_
                
                stroke = '#ffffff'
                stroke_width = 1
                stroke_opacity = 0.0
                if len(s.Stroke.CssParameter) > 0:
                    for css_parameter in s.Stroke.CssParameter:
                        if css_parameter.name == 'stroke':
                            stroke =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-width':
                            stroke_width =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-opacity':
                            stroke_opacity =  css_parameter.valueOf_
                            
                symbolizer = PolygonSymbolizer(
                    rule = rule,
                    order = scount,
                    fill = fill,
                    fill_opacity = fill_opacity,
                    stroke = stroke,
                    stroke_width = stroke_width,
                    stroke_opacity = stroke_opacity                  
                )
                symbolizer.save()
                
            scount+= 1
        
    sld_body = sld_builder.build_sld(layer, style)
    if mapservice.createStyle(style.name, sld_body, session): 
        if style.is_default:
            mapservice.setLayerStyle(workspace.name+":"+layer.name, style.name, session)
            utils.__delete_temporaries(filepath)
        return True
        
    else:
        utils.__delete_temporaries(filepath)
        return False
    
def delete_style(session, style_id, mapservice):
    try:
        style = Style.objects.get(id=int(style_id))
        
        if mapservice.deleteStyle(style.name, session):  
            layer_styles = StyleLayer.objects.filter(style=style)   
            for layer_style in layer_styles:
                layer_style.delete()
                
            rules = Rule.objects.filter(style=style)
            for rule in rules:
                symbolizers = Symbolizer.objects.filter(rule=rule)
                for symbolizer in symbolizers:
                    if hasattr(symbolizer, 'rastersymbolizer'):
                        symbolizer.rastersymbolizer.color_map.delete()
                    symbolizer.delete()
                rule.delete()
        
            style.delete()
        
    except Exception as e:
        raise e