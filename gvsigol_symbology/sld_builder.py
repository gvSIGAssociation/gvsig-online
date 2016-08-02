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

from models import Rule, Symbolizer
from gvsigol_symbology import sld
from lxml import etree
import StringIO
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
    sld_object = sld.parse(file)
    return sld_object

def build_sld(layer, style):
    style_layer_descriptor = sld.StyledLayerDescriptor()
    style_layer_descriptor.set_version('1.0.0')
    
    feature_type_style = get_feature_type_style()
    rules = Rule.objects.filter(style=style)
    for r in rules:
        symbolizers = Symbolizer.objects.filter(rule=r)
        rule = get_rule(r, symbolizers)
        feature_type_style.add_Rule(rule)
    user_style = get_user_style(style.name, style.title, style.is_default, feature_type_style) 
    named_layer = get_named_layer(layer.name, user_style)
    
    sld_body = get_sld_body(style_layer_descriptor, named_layer)
    
    return sld_body

def build_library_symbol(rule):
    style_layer_descriptor = sld.StyledLayerDescriptor()
    style_layer_descriptor.set_version('1.0.0')
    
    feature_type_style = get_feature_type_style()

    symbolizers = Symbolizer.objects.filter(rule=rule)
    r = get_rule(rule, symbolizers)
    feature_type_style.add_Rule(r)
        
    user_style = get_user_style(rule.name, rule.title, True, feature_type_style) 
    named_layer = get_named_layer(rule.name, user_style)
    
    sld_body = get_sld_body(style_layer_descriptor, named_layer)
    
    return sld_body

def get_named_layer(layer_name, user_style):
    named_layer = sld.NamedLayer(Name=layer_name)
    named_layer.add_UserStyle(user_style)
    
    return named_layer

def get_user_style(name, title, is_default, feature_type_style):
    user_style = sld.UserStyle()
    user_style.set_Name(name)
    user_style.set_Title(name)
    user_style.set_IsDefault(is_default)
    user_style.add_FeatureTypeStyle(feature_type_style)

    return user_style

def get_feature_type_style():
    feature_type_style = sld.FeatureTypeStyle()
    return feature_type_style

def get_rule(r, symbolizers):
    rule = sld.Rule()
    rule.set_Name(r.name)
    rule.set_Title(r.title.encode('ascii', 'ignore'))
    rule.set_Abstract(r.abstract)
    if r.filter == "":
        rule.set_Filter(None)
    else:
        filter = getFilter(r.filter)
        rule.set_Filter(filter)
        
    if r.minscale >= 0:
        rule.set_MinScaleDenominator(r.minscale)
    if r.maxscale >= 0:
        rule.set_MaxScaleDenominator(r.maxscale)
    for s in symbolizers:
        rule.add_Symbolizer(get_symbolizer(s))
    return rule

def get_sld_body(style_layer_descriptor, named_layer):
    style_layer_descriptor.add_NamedLayer(named_layer)
    output = StringIO.StringIO()
    style_layer_descriptor.export(output, 0)
    style_layer_descriptor.export(sys.stdout, 0)
    sld_body = output.getvalue()
    output.close()
    
    return sld_body               

def get_symbolizer(s):
    symbolizer = None
    if hasattr(s, 'polygonsymbolizer'):
        symbolizer = sld.PolygonSymbolizer()
        symbolizer.set_Fill(get_fill(s.polygonsymbolizer))
        symbolizer.set_Stroke(get_stroke(s.polygonsymbolizer))
        
    elif hasattr(s, 'linesymbolizer'):
        symbolizer = sld.LineSymbolizer()
        symbolizer.set_Stroke(get_stroke(s.linesymbolizer))
        
    elif hasattr(s, 'marksymbolizer'):
        symbolizer = sld.PointSymbolizer()
        graphic = sld.Graphic()
        mark = sld.Mark()
        mark.set_WellKnownName(s.marksymbolizer.well_known_name)
        mark.set_Fill(get_fill(s.marksymbolizer))
        mark.set_Stroke(get_stroke(s.marksymbolizer))
        graphic.add_Mark(mark)
        graphic.set_Opacity(str(s.marksymbolizer.opacity))
        graphic.set_Size(str(s.marksymbolizer.size))
        graphic.set_Rotation(str(s.marksymbolizer.rotation))
        symbolizer.set_Graphic(graphic)
        
    elif hasattr(s, 'externalgraphicsymbolizer'):
        symbolizer = sld.PointSymbolizer()
        graphic = sld.Graphic()
        externalgraphic = sld.ExternalGraphic()
        o_resource = sld.OnlineResource()
        o_resource.set_href(s.externalgraphicsymbolizer.online_resource)
        externalgraphic.set_OnlineResource(o_resource)
        externalgraphic.set_Format(s.externalgraphicsymbolizer.format)
        graphic.add_ExternalGraphic(externalgraphic)
        graphic.set_Opacity(str(s.externalgraphicsymbolizer.opacity))
        graphic.set_Size(str(s.externalgraphicsymbolizer.size))
        graphic.set_Rotation(str(s.externalgraphicsymbolizer.rotation))
        symbolizer.set_Graphic(graphic)
        
    elif hasattr(s, 'textsymbolizer'):
        symbolizer = sld.TextSymbolizer()
        symbolizer.set_Label(get_label(s.textsymbolizer))
        symbolizer.set_Font(get_font(s.textsymbolizer))
        symbolizer.set_Fill(get_fill(s.textsymbolizer))
        symbolizer.set_Halo(get_halo(s.textsymbolizer))
        
    elif hasattr(s, 'rastersymbolizer'):
        symbolizer = sld.RasterSymbolizer()
        
    return symbolizer
        
def get_fill(s):
    fill = sld.Fill()
    
    fill_color = sld.CssParameter() 
    fill_color.set_name('fill')
    fill_color.set_valueOf_(s.fill)
    fill.add_CssParameter(fill_color)
    
    fill_opacity = sld.CssParameter()
    fill_opacity.set_name('fill-opacity')
    fill_opacity.set_valueOf_(str(s.fill_opacity))
    fill.add_CssParameter(fill_opacity)
    
    return fill
    
def get_stroke(s):
    stroke = sld.Stroke()
    
    stroke_color = sld.CssParameter()
    stroke_color.set_name('stroke')
    stroke_color.set_valueOf_(str(s.stroke))
    stroke.add_CssParameter(stroke_color)
    
    stroke_width = sld.CssParameter()
    stroke_width.set_name('stroke-width')
    stroke_width.set_valueOf_(str(s.stroke_width))
    stroke.add_CssParameter(stroke_width)
    
    stroke_opacity = sld.CssParameter()
    stroke_opacity.set_name('stroke-opacity')
    stroke_opacity.set_valueOf_(str(s.stroke_opacity))
    stroke.add_CssParameter(stroke_opacity)
    
    return stroke

def get_label(s):
    label = sld.ParameterValueType()
    node = etree.Element('root')
    node.text = ('<%s%s>%s</%s%s>%s' % ('ogc:', 'PropertyName', label.gds_encode(label.gds_format_string(quote_xml(s.label), input_name='PropertyName')),'ogc:', 'PropertyName', '\n'))
    
    return label.build(node)

def getFilter(f):
    filt = sld.FilterType()
    
    json_filter = json.loads(f)
    
    if json_filter.get('type') == 'is_equal_to':
        operation = sld.PropertyIsEqualTo()
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_Literal(json_filter.get('value1'))
        filt.set_comparisonOps(operation)
        
    elif json_filter.get('type') == 'is_null':
        operation = sld.PropertyIsNullType()
        operation.set_PropertyName(json_filter.get('property_name'))
        filt.set_comparisonOps(operation)
        
        
    elif json_filter.get('type') == 'is_like':
        operation = sld.PropertyIsLikeType()
        operation.set_wildCard('*')
        operation.set_singleChar('.')
        operation.set_escape('!')
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_Literal(json_filter.get('value1'))
        filt.set_comparisonOps(operation)
        
    elif json_filter.get('type') == 'is_not_equal_to':
        operation = sld.PropertyIsNotEqualTo()
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_Literal(json_filter.get('value1'))
        filt.set_comparisonOps(operation)
        
    elif json_filter.get('type') == 'is_greater_than':
        operation = sld.PropertyIsGreaterThan()
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_Literal(json_filter.get('value1'))
        filt.set_comparisonOps(operation)
        
    elif json_filter.get('type') == 'is_greater_than_or_equal_to':
        operation = sld.PropertyIsGreaterThanOrEqualTo()
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_Literal(json_filter.get('value1'))
        filt.set_comparisonOps(operation)
        
    elif json_filter.get('type') == 'is_less_than':
        operation = sld.PropertyIsLessThan()
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_Literal(json_filter.get('value1'))
        filt.set_comparisonOps(operation)
        
    elif json_filter.get('type') == 'is_less_than_or_equal_to':
        operation = sld.PropertyIsLessThanOrEqualTo()
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_Literal(json_filter.get('value1'))
        filt.set_comparisonOps(operation)
        
    elif json_filter.get('type') == 'is_between':
        operation = sld.PropertyIsBetweenType()
        operation.set_PropertyName(json_filter.get('property_name'))
        operation.set_LowerBoundary(json_filter.get('value1'))
        operation.set_UpperBoundary(json_filter.get('value2'))
        filt.set_comparisonOps(operation)
    
    return filt

def get_font(s):
    font = sld.Font()
    
    font_family = sld.CssParameter()
    font_family.set_name('font-family')
    font_family.set_valueOf_(str(s.font_family))
    font.add_CssParameter(font_family)
    
    font_size = sld.CssParameter()
    font_size.set_name('font-size')
    font_size.set_valueOf_(str(s.font_size))
    font.add_CssParameter(font_size)
    
    font_style = sld.CssParameter()
    font_style.set_name('font-style')
    font_style.set_valueOf_(str(s.font_style))
    font.add_CssParameter(font_style)
    
    font_weight = sld.CssParameter()
    font_weight.set_name('font-weight')
    font_weight.set_valueOf_(str(s.font_weight))
    font.add_CssParameter(font_weight)
    
    return font

def get_halo(s):
    halo = sld.Halo()
    
    halo.set_Radius(str(s.halo_radius))
    
    halo_fill = sld.Fill()
    
    halo_fill_color = sld.CssParameter() 
    halo_fill_color.set_name('fill')
    halo_fill_color.set_valueOf_(s.halo_fill)
    halo_fill.add_CssParameter(halo_fill_color)
    
    halo_fill_opacity = sld.CssParameter()
    halo_fill_opacity.set_name('fill-opacity')
    halo_fill_opacity.set_valueOf_(str(s.halo_fill_opacity))
    halo_fill.add_CssParameter(halo_fill_opacity)
    
    halo.set_Fill(halo_fill)
    return halo

def quote_xml(inStr):
    "Escape markup chars, but do not modify CDATA sections."
    if not inStr:
        return ''
    s1 = (isinstance(inStr, BaseStrType_) and inStr or '%s' % inStr)
    s2 = ''
    pos = 0
    matchobjects = CDATA_pattern_.finditer(s1)
    for mo in matchobjects:
        s3 = s1[pos:mo.start()]
        s2 += quote_xml_aux(s3)
        s2 += s1[mo.start():mo.end()]
        pos = mo.end()
    s3 = s1[pos:]
    s2 += quote_xml_aux(s3)
    return s2

def quote_xml_aux(inStr):
    s1 = inStr.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    return s1