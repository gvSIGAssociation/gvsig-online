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

from .models import Style, StyleLayer, Rule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, ExternalGraphicSymbolizer, RasterSymbolizer, ColorMap
from django.db.models import Max
from django.utils.translation import ugettext_lazy as _
from gvsigol_core import geom
from gvsigol_services.models import Layer
from . import utils, sld_builder
import tempfile
import json
import os
from django.utils.crypto import get_random_string


def create_default_style(layer_id, style_name, style_type, geom_type, count):
    layer = Layer.objects.get(id=int(layer_id))

    minscaledenominator = -1
    maxscaledenominator = -1
    if count and count > 200000:
        minscaledenominator = 0
        maxscaledenominator = 50000
 
    style = Style(
        name = style_name,
        title = _('Default style for: ') + layer.title,
        is_default = True,
        type = style_type,
        minscale = minscaledenominator,
        maxscale = maxscaledenominator
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
    if geom.isPoint(geom_type):
        symbol_type = 'MarkSymbolizer'           
    elif geom.isLine(geom_type):
        symbol_type = 'LineSymbolizer'
    elif geom.isPolygon(geom_type):
        symbol_type = 'PolygonSymbolizer'
    elif geom.isRaster(geom_type):
        symbol_type = 'RasterSymbolizer'
    
    rule = Rule(
        style = style,
        name = 'Default symbol',
        title = _('Default symbol'),
        abstract = '',
        filter = str(""),
        minscale = minscaledenominator,
        maxscale = maxscaledenominator,
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
            stroke_opacity = 1.0 ,
            stroke_dash_array = 'none'                  
        )
        symbolizer.save()
    
    elif symbol_type == 'LineSymbolizer':
        symbolizer = LineSymbolizer(
            rule = rule,
            order = 0,
            stroke = '#000000',
            stroke_width = 1,
            stroke_opacity = 1.0,
            stroke_dash_array = 'none'                 
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
            stroke_opacity = 1.0,
            stroke_dash_array = 'none'                 
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

def sld_import(name, is_default, layer_id, file, mapservice):
    
    layer = Layer.objects.get(id=int(layer_id))
    
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
                    stroke_dash_array = 'none'
                    if len(mark.Stroke.CssParameter) > 0:
                        for css_parameter in mark.Stroke.CssParameter:
                            if css_parameter.name == 'stroke':
                                stroke =  css_parameter.valueOf_
                            if css_parameter.name == 'stroke-width':
                                stroke_width =  css_parameter.valueOf_
                            if css_parameter.name == 'stroke-opacity':
                                stroke_opacity =  css_parameter.valueOf_
                            if css_parameter.name == 'stroke-dasharray':
                                stroke_dash_array =  css_parameter.valueOf_
                        
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
                        stroke_opacity = stroke_opacity,
                        stroke_dash_array = stroke_dash_array                
                    )
                    symbolizer.save()
                    
                if len(s.Graphic.ExternalGraphic) >= 1:
                    print('ExternalGraphic')
                    
            elif s.original_tagname_ == 'LineSymbolizer':
                stroke = '#ffffff'
                stroke_width = 1
                stroke_opacity = 0.0
                stroke_dash_array = 'none'
                if len(s.Stroke.CssParameter) > 0:
                    for css_parameter in s.Stroke.CssParameter:
                        if css_parameter.name == 'stroke':
                            stroke =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-width':
                            stroke_width =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-opacity':
                            stroke_opacity =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-dasharray':
                            stroke_dash_array =  css_parameter.valueOf_
                                
                symbolizer = LineSymbolizer(
                    rule = rule,
                    order = scount,
                    stroke = stroke,
                    stroke_width = stroke_width,
                    stroke_opacity = stroke_opacity,
                    stroke_dash_array = stroke_dash_array              
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
                stroke_dash_array = 'none'
                if len(s.Stroke.CssParameter) > 0:
                    for css_parameter in s.Stroke.CssParameter:
                        if css_parameter.name == 'stroke':
                            stroke =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-width':
                            stroke_width =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-opacity':
                            stroke_opacity =  css_parameter.valueOf_
                        if css_parameter.name == 'stroke-dasharray':
                            stroke_dash_array =  css_parameter.valueOf_
                            
                symbolizer = PolygonSymbolizer(
                    rule = rule,
                    order = scount,
                    fill = fill,
                    fill_opacity = fill_opacity,
                    stroke = stroke,
                    stroke_width = stroke_width,
                    stroke_opacity = stroke_opacity,
                    stroke_dash_array = stroke_dash_array                 
                )
                symbolizer.save()
                
            scount+= 1
        
    sld_body = sld_builder.build_sld(layer, style)
    if mapservice.createStyle(style.name, sld_body): 
        mapservice.setLayerStyle(layer, style.name, style.is_default)
        utils.__delete_temporaries(filepath)
        return True
        
    else:
        utils.__delete_temporaries(filepath)
        return False

def clone_layer_style(style, target_layer, new_style_name=None):
    if not new_style_name:
        # TODO: decide the new style name
        new_style_name = target_layer.datastore.workspace.name + "_" + style.name
    old_id = style.pk
    style.pk = None
    style.name = new_style_name
    style.save()
    
    original_style = Style.objects.get(id=old_id)
    
    for rule in Rule.objects.filter(style=original_style).order_by('order'):
        old_id = rule.pk
        rule.pk = None # cloning
        rule.style = style
        rule.save()
        
        new_rule_instance = Rule.objects.get(id=rule.pk)
        old_rule_instance = Rule.objects.get(id=old_id)
        original_symbolizers = Symbolizer.objects.filter(rule=old_rule_instance)
        for original_symbolizer in original_symbolizers:
            if hasattr(original_symbolizer, 'externalgraphicsymbolizer'):
                symbolizer = ExternalGraphicSymbolizer(
                    rule = new_rule_instance,
                    order = original_symbolizer.externalgraphicsymbolizer.order,
                    opacity = original_symbolizer.externalgraphicsymbolizer.opacity,
                    size = original_symbolizer.externalgraphicsymbolizer.size,
                    rotation = original_symbolizer.externalgraphicsymbolizer.rotation,
                    online_resource = original_symbolizer.externalgraphicsymbolizer.online_resource,
                    format = original_symbolizer.externalgraphicsymbolizer.format,
                )
                symbolizer.save()
                    
            elif hasattr(original_symbolizer, 'polygonsymbolizer'):
                symbolizer = PolygonSymbolizer(
                    rule = new_rule_instance,
                    order = original_symbolizer.polygonsymbolizer.order,
                    fill = original_symbolizer.polygonsymbolizer.fill,
                    fill_opacity = original_symbolizer.polygonsymbolizer.fill_opacity,
                    stroke = original_symbolizer.polygonsymbolizer.stroke,
                    stroke_width = original_symbolizer.polygonsymbolizer.stroke_width,
                    stroke_opacity = original_symbolizer.polygonsymbolizer.stroke_opacity,
                    stroke_dash_array = original_symbolizer.polygonsymbolizer.stroke_dash_array
                )
                symbolizer.save()
            
            elif hasattr(original_symbolizer, 'linesymbolizer'):
                symbolizer = LineSymbolizer(
                    rule = new_rule_instance,
                    order = original_symbolizer.linesymbolizer.order,
                    stroke = original_symbolizer.linesymbolizer.stroke,
                    stroke_width = original_symbolizer.linesymbolizer.stroke_width,
                    stroke_opacity = original_symbolizer.linesymbolizer.stroke_opacity,
                    stroke_dash_array = original_symbolizer.linesymbolizer.stroke_dash_array
                )
                symbolizer.save()      
                
            elif hasattr(original_symbolizer, 'marksymbolizer'):
                symbolizer = MarkSymbolizer(
                    rule = new_rule_instance,
                    order = original_symbolizer.marksymbolizer.order,
                    opacity = original_symbolizer.marksymbolizer.opacity,
                    size = original_symbolizer.marksymbolizer.size,
                    rotation = original_symbolizer.marksymbolizer.rotation,
                    well_known_name = original_symbolizer.marksymbolizer.well_known_name,
                    fill = original_symbolizer.marksymbolizer.fill,
                    fill_opacity = original_symbolizer.marksymbolizer.fill_opacity,
                    stroke = original_symbolizer.marksymbolizer.stroke,
                    stroke_width = original_symbolizer.marksymbolizer.stroke_width,
                    stroke_opacity = original_symbolizer.marksymbolizer.stroke_opacity,
                    stroke_dash_array = original_symbolizer.marksymbolizer.stroke_dash_array
                )
                symbolizer.save() 
    return Style.objects.get(id=style.pk)


def clone_layer_styles(mapservice, source_layer, target_layer):
    for style_layer in StyleLayer.objects.filter(layer=source_layer).order_by("-style__is_default"):
        style = style_layer.style
        # TODO: decide the new style name
        source_layer.datastore.workspace.name
        ws_base_name = target_layer.datastore.workspace.name
        base_name = style.name.replace(source_layer.datastore.workspace.name + "_", "")
        new_style_name = target_layer.datastore.workspace.name + "_" + base_name
        salt = ''
        i = 0
        while mapservice.getStyle(new_style_name) is not None:
            suffix = "_" + str(i) + salt
            new_style_name = ws_base_name[:100] + "_" + base_name[:(210 - min(len(ws_base_name), 100) - len(suffix)) - 1] + suffix
            i = i + 1
            if (i%1000) == 0:
                salt = '_' + get_random_string(3)
        new_style = clone_layer_style(style, target_layer, new_style_name=new_style_name)
        new_style_layer = StyleLayer()
        new_style_layer.layer = target_layer
        new_style_layer.style = new_style
        new_style_layer.save()
        sld_body = sld_builder.build_sld(target_layer, new_style)
        if mapservice.createStyle(new_style.name, sld_body):
            mapservice.setLayerStyle(target_layer, new_style.name, new_style.is_default)
        else:
            # TODO: manage errors
            print("DEBUG: Problem cloning style .." + new_style.name)


def clone_style(mapservice, layer, original_style_name, cloned_style_name):
    exists_cloned_style = False
    try:
        original_style = Style.objects.filter(name__exact=original_style_name)[0]
    except Exception as e:
        print(str(e))
        return False
        
    try:
        style = Style.objects.filter(name__exact=cloned_style_name)[0] 
        exists_cloned_style = True   
    except Exception as e:
        print("DEBUG: Problem getting style .." + cloned_style_name)
        print(str(e))
        
    if exists_cloned_style:
        print("DEBUG: Exists cloned style .." + cloned_style_name)
        rule = Rule.objects.filter(style=style)[0]
        symbolizers_to_delete = Symbolizer.objects.filter(rule=rule)
        for i in symbolizers_to_delete:
            i.delete()
    else:           
        print("DEBUG: Not existe cloned style .." + cloned_style_name)         
        style = Style(
            name = cloned_style_name,
            title = original_style_name,
            is_default = True,
            type = 'US'
        )
        style.save()
        
        style_layer = StyleLayer(
            style = style,
            layer = layer
        )
        style_layer.save()
    
        rule = Rule(
            style = style,
            name = 'Default symbol',
            title = original_style_name,
            abstract = '',
            filter = str(""),
            minscale = -1,
            maxscale = -1,
            order = 0
        )
        rule.save()
        

    original_rules = Rule.objects.filter(style=original_style).order_by('order')
    for original_rule in original_rules:
        original_symbolizers = Symbolizer.objects.filter(rule=original_rule)
        for original_symbolizer in original_symbolizers:
            if hasattr(original_symbolizer, 'externalgraphicsymbolizer'):
                symbolizer = ExternalGraphicSymbolizer(
                    rule = rule,
                    order = original_symbolizer.externalgraphicsymbolizer.order,
                    opacity = original_symbolizer.externalgraphicsymbolizer.opacity,
                    size = original_symbolizer.externalgraphicsymbolizer.size,
                    rotation = original_symbolizer.externalgraphicsymbolizer.rotation,
                    online_resource = original_symbolizer.externalgraphicsymbolizer.online_resource,
                    format = original_symbolizer.externalgraphicsymbolizer.format,
                )
                symbolizer.save()
                    
            elif hasattr(original_symbolizer, 'polygonsymbolizer'):
                symbolizer = PolygonSymbolizer(
                    rule = rule,
                    order = original_symbolizer.polygonsymbolizer.order,
                    fill = original_symbolizer.polygonsymbolizer.fill,
                    fill_opacity = original_symbolizer.polygonsymbolizer.fill_opacity,
                    stroke = original_symbolizer.polygonsymbolizer.stroke,
                    stroke_width = original_symbolizer.polygonsymbolizer.stroke_width,
                    stroke_opacity = original_symbolizer.polygonsymbolizer.stroke_opacity,
                    stroke_dash_array = original_symbolizer.polygonsymbolizer.stroke_dash_array                  
                )
                symbolizer.save()
            
            elif hasattr(original_symbolizer, 'linesymbolizer'):
                symbolizer = LineSymbolizer(
                    rule = rule,
                    order = original_symbolizer.linesymbolizer.order,
                    stroke = original_symbolizer.linesymbolizer.stroke,
                    stroke_width = original_symbolizer.linesymbolizer.stroke_width,
                    stroke_opacity = original_symbolizer.linesymbolizer.stroke_opacity,
                    stroke_dash_array = original_symbolizer.linesymbolizer.stroke_dash_array                
                )
                symbolizer.save()      
                
            elif hasattr(original_symbolizer, 'marksymbolizer'):
                symbolizer = MarkSymbolizer(
                    rule = rule,
                    order = original_symbolizer.marksymbolizer.order,
                    opacity = original_symbolizer.marksymbolizer.opacity,
                    size = original_symbolizer.marksymbolizer.size,
                    rotation = original_symbolizer.marksymbolizer.rotation,
                    well_known_name = original_symbolizer.marksymbolizer.well_known_name,
                    fill = original_symbolizer.marksymbolizer.fill,
                    fill_opacity = original_symbolizer.marksymbolizer.fill_opacity,
                    stroke = original_symbolizer.marksymbolizer.stroke,
                    stroke_width = original_symbolizer.marksymbolizer.stroke_width,
                    stroke_opacity = original_symbolizer.marksymbolizer.stroke_opacity,
                    stroke_dash_array = original_symbolizer.marksymbolizer.stroke_dash_array               
                )
                symbolizer.save() 
                
    sld_body = sld_builder.build_library_symbol(rule)
    s = mapservice.getStyle(style.name)
    if s is None:        
        print("DEBUG: style not exists in Geoserver .. " + style.name)
        if mapservice.createStyle(style.name, sld_body):
            mapservice.setLayerStyle(layer, cloned_style_name, style.is_default)
        else:
            "DEBUG: problem creating style !!!!!" + style.name
    else:
        print("DEBUG: Style exists in Geoserver .. " +style.name)
        if not mapservice.createStyle(cloned_style_name, sld_body):
            mapservice.updateStyle(layer, cloned_style_name, sld_body)
        mapservice.setLayerStyle(layer, cloned_style_name, style.is_default)
        
        
    return True

     
#eliminar estilo solo de gvsigonline, no llego a guardarlo en geoserver    
def delete_style_name(name):
    try:
        last_inserted_id = Style.objects.filter(name=name).aggregate(Max('id'))['id__max']

        if last_inserted_id is not None:
           style = Style.objects.get(id=int(last_inserted_id))
        
           if style:
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
    
def delete_style(style_id, mapservice):
    try:
        style = Style.objects.get(id=int(style_id))
        
        mapservice.deleteStyle(style.name)
       
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