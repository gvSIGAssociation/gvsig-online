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

from models import Rule as ModelRule, Symbolizer as ModelSymbolizer, ColorMapEntry as ModelColorMapEntry
from gvsigol_symbology.sld import StyledLayerDescriptor, PointSymbolizer, LineSymbolizer, PolygonSymbolizer, TextSymbolizer, \
    Graphic, Mark, Fill, Stroke, Label, Font, Halo, RasterSymbolizer, ColorMap, ExternalGraphic, Filter, PropertyCriterion, \
    Geometry, Function, LabelPlacement, LinePlacement, PointPlacement, AnchorPoint
import utils
import json
import sys
import re

CDATA_pattern_ = re.compile(r"<!\[CDATA\[.*?\]\]>", re.DOTALL)

Validate_simpletypes_ = True
if sys.version_info.major == 2:
    BaseStrType_ = basestring
else:
    BaseStrType_ = str
    
def parse_sld(file):
    sld_object = StyledLayerDescriptor(file)
    return sld_object

def build_sld(layer, style, single_symbol = False):
    field_geom = 'wkb_geometry' #get_layer_geom_field(layer)
    style_layer_descriptor = StyledLayerDescriptor()
    named_layer = style_layer_descriptor.create_namedlayer(layer.name)
    user_style = named_layer.create_userstyle(style.name, style.title)
    feature_type_style = user_style.create_featuretypestyle()
    #if style.type == 'CP':
    #    tr = feature_type_style.create_transformation()
    
    rules = ModelRule.objects.filter(style=style)
    for r in rules:
        symbolizers = ModelSymbolizer.objects.filter(rule=r).order_by('-order')
        field_geom = utils.get_geometry_field(layer)
        create_rule(r, symbolizers, feature_type_style, field_geom)
    
    sld_body = style_layer_descriptor.as_sld(True)
    if style.type == 'CP' and not single_symbol:
        transform = ''\
        '                <sld:Transformation>'\
        '                    <ogc:Function name="gs:PointStacker">'\
        '                        <ogc:Function name="parameter">'\
        '                            <ogc:Literal>data</ogc:Literal>'\
        '                        </ogc:Function>'\
        '                        <ogc:Function name="parameter">'\
        '                            <ogc:Literal>cellSize</ogc:Literal>'\
        '                            <ogc:Literal>30</ogc:Literal>'\
        '                        </ogc:Function>'\
        '                        <ogc:Function name="parameter">'\
        '                            <ogc:Literal>outputBBOX</ogc:Literal>'\
        '                            <ogc:Function name="env">'\
        '                                <ogc:Literal>wms_bbox</ogc:Literal>'\
        '                            </ogc:Function>'\
        '                        </ogc:Function>'\
        '                        <ogc:Function name="parameter">'\
        '                            <ogc:Literal>outputWidth</ogc:Literal>'\
        '                            <ogc:Function name="env">'\
        '                                <ogc:Literal>wms_width</ogc:Literal>'\
        '                            </ogc:Function>'\
        '                        </ogc:Function>'\
        '                        <ogc:Function name="parameter">'\
        '                            <ogc:Literal>outputHeight</ogc:Literal>'\
        '                            <ogc:Function name="env">'\
        '                               <ogc:Literal>wms_height</ogc:Literal>'\
        '                            </ogc:Function>'\
        '                        </ogc:Function>'\
        '                       <ogc:Function name="parameter">'\
        '                           <ogc:Literal>preserveLocation</ogc:Literal>'\
        '                           <ogc:Literal>Superimposed</ogc:Literal>'\
        '                        </ogc:Function>'\
        '                    </ogc:Function>'\
        '               </sld:Transformation>'
        sld_body = sld_body.replace('<sld:FeatureTypeStyle>', '@@@'+transform, 1)
        sld_body = sld_body.replace('@@@', '<sld:FeatureTypeStyle>', 1)

    return sld_body

def build_library_symbol(rule):
    style_layer_descriptor = StyledLayerDescriptor()
    named_layer = style_layer_descriptor.create_namedlayer(rule.name)
    user_style = named_layer.create_userstyle(rule.name, rule.name)
    feature_type_style = user_style.create_featuretypestyle()

    symbolizers = ModelSymbolizer.objects.filter(rule=rule).order_by('-order')
    create_rule(rule, symbolizers, feature_type_style)
    
    sld_body = style_layer_descriptor.as_sld(True)
    
    return sld_body

def get_operation_symbol(op):
    operation = None
    if op == 'is_equal_to':
        operation = '=='
    elif op == 'is_less_than_or_equal_to':
        operation = '<='
    elif op == 'is_less_than':
        operation = '>'
    elif op == 'is_greater_than_or_equal_to':
        operation = '>='
    elif op == 'is_greater_than':
        operation = '>'
    elif op == 'is_not_equal':
        operation = '!='
    elif op == 'is_like':
        operation = '%'
    elif op == 'is_null':
        operation = 'IS NULL'
    
    return operation

def get_operation_name(op):
    operation = None
    if op == 'is_equal_to':
        operation = 'PropertyIsEqualTo'
    elif op == 'is_less_than_or_equal_to':
        operation = 'PropertyIsLessThanOrEqualTo'
    elif op == 'is_less_than':
        operation = 'PropertyIsLessThan'
    elif op == 'is_greater_than_or_equal_to':
        operation = 'PropertyIsGreaterThanOrEqualTo'
    elif op == 'is_greater_than':
        operation = 'PropertyIsGreaterThan'
    elif op == 'is_not_equal':
        operation = 'PropertyIsNotEqualTo'
    elif op == 'is_like':
        operation = 'PropertyIsLike'
    elif op == 'is_null':
        operation = 'PropertyIsNull'
    
    return operation

def get_filter_section(f, op):
    if op == 'is_equal_to':
        return f.PropertyIsEqualTo
    elif op == 'is_less_than_or_equal_to':
        return f.PropertyIsLessThanOrEqualTo
    elif op == 'is_less_than':
        return f.PropertyIsLessThan
    elif op == 'is_greater_than_or_equal_to':
        return f.PropertyIsGreaterThanOrEqualTo
    elif op == 'is_greater_than':
        return f.PropertyIsGreaterThan
    elif op == 'is_not_equal':
        return f.PropertyIsNotEqualTo
    elif op == 'is_like':
        return f.PropertyIsLike
    elif op == 'is_null':
        return f.PropertyIsNull
    
    return f

def build_complex_filter(filters, rule):
    complex_filter = None
    operator = None
    for item in filters:
        if item.get('type') == 'expression':
            f = Filter(rule)
            filter_op = get_filter_section(f, item.get('operation'))
            filter_op = PropertyCriterion(f, get_operation_name(item.get('operation')))
            filter_op.PropertyName = item.get('field')
            filter_op.Literal = item.get('value')
            
            if complex_filter == None:
                complex_filter = f
            else:
                if operator == 'and':
                    complex_filter = complex_filter + f
                elif operator == 'or':
                    complex_filter = complex_filter | f
        
        elif item.get('type') == 'and':
            operator = 'and'
        elif item.get('type') == 'or':
            operator = 'or'
                
    return complex_filter
        

def create_rule(r, symbolizers, feature_type_style, geom_field=None):
    min_scale_denominator = None
    max_scale_denominator = None
    if r.minscale >= 0:
        min_scale_denominator = r.minscale
    if r.maxscale >= 0:
        max_scale_denominator = r.maxscale
        
    rule = feature_type_style.create_rule(
        r.title,
        MinScaleDenominator=min_scale_denominator, 
        MaxScaleDenominator=max_scale_denominator
    )
    
    if r.filter != '':
        f = json.loads(r.filter)
        if isinstance(f, list):
            if len(f) == 1:
                if f[0].get('operation') == 'is_null':
                    f2 = Filter(rule)
                    f2.PropertyIsNull = PropertyCriterion(f2, 'PropertyIsNull')
                    f2.PropertyIsNull.PropertyName = f[0].get('field')
                    
                    rule.Filter = f2 
                
                else:
                    rule.create_filter(f[0].get('field'), get_operation_symbol(f[0].get('operation')), f[0].get('value'))
                
            elif len(f) >= 3:
                rule.Filter = build_complex_filter(f, rule)
        else:
            if f.get('operation') == 'is_between':
                f1 = Filter(rule)
                f1.PropertyIsGreaterThanOrEqualTo = PropertyCriterion(f1, 'PropertyIsGreaterThanOrEqualTo')
                f1.PropertyIsGreaterThanOrEqualTo.PropertyName = f.get('field')
                f1.PropertyIsGreaterThanOrEqualTo.Literal = str(f.get('value1'))
                
                f2 = Filter(rule)
                f2.PropertyIsLessThanOrEqualTo = PropertyCriterion(f2, 'PropertyIsLessThanOrEqualTo')
                f2.PropertyIsLessThanOrEqualTo.PropertyName = f.get('field')
                f2.PropertyIsLessThanOrEqualTo.Literal = str(f.get('value2'))
                
                rule.Filter = f1 + f2 
                
            else:
                if f.get('operation') == 'is_null':
                    f2 = Filter(rule)
                    f2.PropertyIsNull = PropertyCriterion(f2, 'PropertyIsNull')
                    f2.PropertyIsNull.PropertyName = f.get('field')
                    
                    rule.Filter = f2 
                
                else:
                    rule.create_filter(f.get('field'), get_operation_symbol(f.get('operation')), f.get('value'))
    
    for s in symbolizers:
        if hasattr(s, 'marksymbolizer'):
            symbolizer = PointSymbolizer(rule)
            gph = Graphic(symbolizer)
            mrk = Mark(gph)
            mrk.WellKnownName = s.marksymbolizer.well_known_name
            fill = Fill(mrk)
            fill.create_cssparameter('fill', s.marksymbolizer.fill)
            fill.create_cssparameter('fill-opacity', str(s.marksymbolizer.fill_opacity))
            stroke = Stroke(mrk)
            stroke.create_cssparameter('stroke', s.marksymbolizer.stroke)
            stroke.create_cssparameter('stroke-width', str(s.marksymbolizer.stroke_width))
            stroke.create_cssparameter('stroke-opacity', str(s.marksymbolizer.stroke_opacity))
            if str(s.marksymbolizer.stroke_dash_array) != 'none':
                stroke.create_cssparameter('stroke-dasharray', s.marksymbolizer.stroke_dash_array)
            gph.Opacity = str(s.marksymbolizer.opacity)
            gph.Size = str(s.marksymbolizer.size)
            gph.Rotation = str(s.marksymbolizer.rotation)
        
        elif hasattr(s, 'linesymbolizer'):
            symbolizer = LineSymbolizer(rule)
            stroke = Stroke(symbolizer)
            stroke.create_cssparameter('stroke', s.linesymbolizer.stroke)
            stroke.create_cssparameter('stroke-width', str(s.linesymbolizer.stroke_width))
            stroke.create_cssparameter('stroke-opacity', str(s.linesymbolizer.stroke_opacity))
            if str(s.linesymbolizer.stroke_dash_array) != 'none':
                stroke.create_cssparameter('stroke-dasharray', s.linesymbolizer.stroke_dash_array)
            
        elif hasattr(s, 'polygonsymbolizer'):
            symbolizer = PolygonSymbolizer(rule)
            fill = Fill(symbolizer)
            fill.create_cssparameter('fill', s.polygonsymbolizer.fill)
            fill.create_cssparameter('fill-opacity', str(s.polygonsymbolizer.fill_opacity))
            stroke = Stroke(symbolizer)
            stroke.create_cssparameter('stroke', s.polygonsymbolizer.stroke)
            stroke.create_cssparameter('stroke-width', str(s.polygonsymbolizer.stroke_width))
            stroke.create_cssparameter('stroke-opacity', str(s.polygonsymbolizer.stroke_opacity))
            if str(s.polygonsymbolizer.stroke_dash_array) != 'none':
                stroke.create_cssparameter('stroke-dasharray', s.polygonsymbolizer.stroke_dash_array)
            
        elif hasattr(s, 'externalgraphicsymbolizer'):
            symbolizer = PointSymbolizer(rule)
            gph = Graphic(symbolizer)
            gph.Size = str(s.externalgraphicsymbolizer.size)
            gph.Rotation = str(s.externalgraphicsymbolizer.rotation)
            gph.Opacity = str(s.externalgraphicsymbolizer.opacity)
            egph = ExternalGraphic(gph)
            egph.Format = s.externalgraphicsymbolizer.format
            egph.create_onlineresource(s.externalgraphicsymbolizer.online_resource)
            
        elif hasattr(s, 'textsymbolizer'):
            symbolizer = TextSymbolizer(rule)
            if geom_field:
                if geom_field['field_type'] != 'MULTILINESTRING' and geom_field['field_type'] != 'LINESTRING' and geom_field['field_type'] != 'MULTIPOINT' and geom_field['field_type'] != 'POINT' and geom_field['field_name'] != '':
                    geometry = Geometry(symbolizer)
                    function = Function(geometry)
                    function.set_name('centroid')
                    function.PropertyName = geom_field['field_name']
            label = Label(symbolizer)
            label.PropertyName = s.textsymbolizer.label
            font = Font(symbolizer)
            font.create_cssparameter('font-family', s.textsymbolizer.font_family)
            font.create_cssparameter('font-size', str(s.textsymbolizer.font_size))
            font.create_cssparameter('font-style', s.textsymbolizer.font_style)
            font.create_cssparameter('font-weight', str(s.textsymbolizer.font_weight))

            if geom_field['field_type'] == 'MULTILINESTRING' or geom_field['field_type'] == 'LINESTRING':
                labelplacement = LabelPlacement(symbolizer)
                lineplacement = LinePlacement(labelplacement)
                lineplacement.PerpendicularOffset = str(15)
            else:
                labelplacement = LabelPlacement(symbolizer)
                pointplacement = PointPlacement(labelplacement)
                anchorpoint = AnchorPoint(pointplacement)
                anchorpoint.AnchorPointX = str(s.textsymbolizer.anchor_point_x)
                anchorpoint.AnchorPointY = str(s.textsymbolizer.anchor_point_y)
            halo = Halo(symbolizer)
            halo.Radius = str(s.textsymbolizer.halo_radius)
            halo_fill = Fill(halo)
            halo_fill.create_cssparameter('fill', s.textsymbolizer.halo_fill)
            halo_fill.create_cssparameter('fill-opacity', str(s.textsymbolizer.halo_fill_opacity))
            fill = Fill(symbolizer)
            fill.create_cssparameter('fill', s.textsymbolizer.fill)
            fill.create_cssparameter('fill-opacity', str(s.textsymbolizer.fill_opacity))

            symbolizer.create_vendoroption('conflictResolution', 'true')
            symbolizer.create_vendoroption('autoWrap', '120')
            symbolizer.create_vendoroption('spaceAround', '0')
            symbolizer.create_vendoroption('polygonAlign', 'mbr')
            
            if geom_field['field_type'] == 'MULTILINESTRING' or geom_field['field_type'] == 'LINESTRING':
                symbolizer.create_vendoroption('group', 'yes')
                symbolizer.create_vendoroption('partials', 'true')
                symbolizer.create_vendoroption('forceLeftToRight', 'true')
                
        elif hasattr(s, 'rastersymbolizer'):
            symbolizer = RasterSymbolizer(rule)
            color_map = ColorMap(symbolizer)
            
            entries = ModelColorMapEntry.objects.filter(color_map=s.rastersymbolizer.color_map).order_by('order')
            if entries is not None:
                for e in entries:
                    color_map.create_colormapentry(e.color, str(e.quantity), e.label, str(e.opacity))