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

from models import Library, Style, StyleLayer, Rule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, ExternalGraphicSymbolizer, TextSymbolizer, RasterSymbolizer
from django.utils.translation import ugettext_lazy as _
from gvsigol_services.models import Layer
from django.http import HttpResponse
import utils, sld_utils, sld_builder
import tempfile, zipfile
import StringIO
import json
import re
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
        symbolizer = RasterSymbolizer(
            rule = rule,
            order = 0,
            opacity = 1.0           
        )
        symbolizer.save()
            
    sld_body = sld_builder.build_sld(layer, style)
    return sld_body