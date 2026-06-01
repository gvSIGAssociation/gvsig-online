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

from .models import Style, StyleLayer, Rule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, ExternalGraphicSymbolizer, RasterSymbolizer, ColorMap, ColorMapEntry, TextSymbolizer as TextSymbolizerModel
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from gvsigol_core import geom
from gvsigol_services.models import Layer
from . import utils, sld_builder
import tempfile
import json
import os
import re
from lxml import etree
from django.utils.crypto import get_random_string

# Styles that store the full SLD document in style.sld (not built from Rule/Symbolizer rows).
SLD_STORED_TYPES = ('CS', 'MC')
# Rule-based styles that need full SLD build (e.g. gs:PointStacker transformation for clustered points).
SLD_BUILD_FULL_TYPES = ('CP',)

_SLD_NS = {
    'sld': 'http://www.opengis.net/sld',
    'ogc': 'http://www.opengis.net/ogc',
    'xlink': 'http://www.w3.org/1999/xlink',
}


def _sld_first_text(elem, xpath):
    if elem is None:
        return None
    hit = elem.xpath(xpath, namespaces=_SLD_NS)
    if not hit:
        return None
    t = hit[0].text
    if t is None:
        return None
    t = t.strip()
    return t if t else None


def _sld_css_map(elem):
    m = {}
    if elem is None:
        return m
    for p in elem.xpath('sld:CssParameter', namespaces=_SLD_NS):
        k = p.get('name')
        if k:
            m[k] = (p.text or '').strip()
    return m


def _sld_float(val, default):
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _sld_import_symbolizers(rule_node, model_rule):
    """
    Persist symbolizers from a Rule element using lxml (parse_sld uses sld.Rule
    wrappers, not generateDS).
    """
    scount = 0
    sym_tags = (
        'PointSymbolizer',
        'LineSymbolizer',
        'PolygonSymbolizer',
        'TextSymbolizer',
        'RasterSymbolizer',
    )
    for child in rule_node:
        if not isinstance(child.tag, str):
            continue
        if etree.QName(child).localname not in sym_tags:
            continue
        tag = etree.QName(child).localname

        if tag == 'PointSymbolizer':
            g = child.xpath('sld:Graphic', namespaces=_SLD_NS)
            graphic = g[0] if g else None
            if graphic is not None:
                opacity = _sld_float(_sld_first_text(graphic, 'sld:Opacity'), 1.0)
                rotation = _sld_float(_sld_first_text(graphic, 'sld:Rotation'), 0.0)
                size = _sld_float(_sld_first_text(graphic, 'sld:Size'), 8.0)
                marks = graphic.xpath('sld:Mark', namespaces=_SLD_NS)
                if marks:
                    mark = marks[0]
                    fill = '#383838'
                    fill_opacity = 0.5
                    fills = mark.xpath('sld:Fill', namespaces=_SLD_NS)
                    if fills:
                        for k, v in _sld_css_map(fills[0]).items():
                            if k == 'fill':
                                fill = v
                            elif k == 'fill-opacity':
                                fill_opacity = _sld_float(v, fill_opacity)
                    stroke = '#ffffff'
                    stroke_width = 1
                    stroke_opacity = 0.0
                    stroke_dash_array = 'none'
                    strokes = mark.xpath('sld:Stroke', namespaces=_SLD_NS)
                    if strokes:
                        for k, v in _sld_css_map(strokes[0]).items():
                            if k == 'stroke':
                                stroke = v
                            elif k == 'stroke-width':
                                stroke_width = _sld_float(v, stroke_width)
                            elif k == 'stroke-opacity':
                                stroke_opacity = _sld_float(v, stroke_opacity)
                            elif k == 'stroke-dasharray':
                                stroke_dash_array = v
                    wkn = _sld_first_text(mark, 'sld:WellKnownName') or 'circle'
                    MarkSymbolizer(
                        rule=model_rule,
                        order=scount,
                        opacity=opacity,
                        size=size,
                        rotation=rotation,
                        well_known_name=wkn,
                        fill=fill,
                        fill_opacity=fill_opacity,
                        stroke=stroke,
                        stroke_width=stroke_width,
                        stroke_opacity=stroke_opacity,
                        stroke_dash_array=stroke_dash_array,
                    ).save()
                elif graphic.xpath('sld:ExternalGraphic', namespaces=_SLD_NS):
                    eg_node = graphic.xpath('sld:ExternalGraphic', namespaces=_SLD_NS)[0]
                    or_nodes = eg_node.xpath('sld:OnlineResource', namespaces=_SLD_NS)
                    online_resource = ''
                    if or_nodes:
                        # Some serializers write xlink:href, others plain href.
                        online_resource = (
                            or_nodes[0].get('{http://www.w3.org/1999/xlink}href')
                            or or_nodes[0].get('href')
                            or ''
                        )
                    fmt = _sld_first_text(eg_node, 'sld:Format') or 'image/svg+xml'
                    if online_resource:
                        ExternalGraphicSymbolizer(
                            rule=model_rule,
                            order=scount,
                            opacity=max(1, int(round(opacity))),
                            size=max(1, int(round(size))),
                            rotation=int(round(rotation)),
                            online_resource=online_resource,
                            format=fmt,
                        ).save()

        elif tag == 'LineSymbolizer':
            stroke = '#ffffff'
            stroke_width = 1
            stroke_opacity = 0.0
            stroke_dash_array = 'none'
            strokes = child.xpath('sld:Stroke', namespaces=_SLD_NS)
            if strokes:
                for k, v in _sld_css_map(strokes[0]).items():
                    if k == 'stroke':
                        stroke = v
                    elif k == 'stroke-width':
                        stroke_width = _sld_float(v, stroke_width)
                    elif k == 'stroke-opacity':
                        stroke_opacity = _sld_float(v, stroke_opacity)
                    elif k == 'stroke-dasharray':
                        stroke_dash_array = v
            LineSymbolizer(
                rule=model_rule,
                order=scount,
                stroke=stroke,
                stroke_width=stroke_width,
                stroke_opacity=stroke_opacity,
                stroke_dash_array=stroke_dash_array,
            ).save()

        elif tag == 'PolygonSymbolizer':
            fill = '#383838'
            fill_opacity = 0.5
            fills = child.xpath('sld:Fill', namespaces=_SLD_NS)
            if fills:
                for k, v in _sld_css_map(fills[0]).items():
                    if k == 'fill':
                        fill = v
                    elif k == 'fill-opacity':
                        fill_opacity = _sld_float(v, fill_opacity)
            stroke = '#ffffff'
            stroke_width = 1
            stroke_opacity = 0.0
            stroke_dash_array = 'none'
            strokes = child.xpath('sld:Stroke', namespaces=_SLD_NS)
            if strokes:
                for k, v in _sld_css_map(strokes[0]).items():
                    if k == 'stroke':
                        stroke = v
                    elif k == 'stroke-width':
                        stroke_width = _sld_float(v, stroke_width)
                    elif k == 'stroke-opacity':
                        stroke_opacity = _sld_float(v, stroke_opacity)
                    elif k == 'stroke-dasharray':
                        stroke_dash_array = v
            PolygonSymbolizer(
                rule=model_rule,
                order=scount,
                fill=fill,
                fill_opacity=fill_opacity,
                stroke=stroke,
                stroke_width=stroke_width,
                stroke_opacity=stroke_opacity,
                stroke_dash_array=stroke_dash_array,
            ).save()

        elif tag == 'TextSymbolizer':
            # Label field (PropertyName inside Label element)
            label_pn = _sld_first_text(child, 'sld:Label/sld:PropertyName') or \
                       _sld_first_text(child, 'sld:Label/ogc:PropertyName') or ''

            # Font CSS parameters
            font_family = 'Arial'
            font_size = 12
            font_style = 'normal'
            font_weight = 'normal'
            fonts = child.xpath('sld:Font', namespaces=_SLD_NS)
            if fonts:
                for k, v in _sld_css_map(fonts[0]).items():
                    if k == 'font-family':
                        font_family = v
                    elif k == 'font-size':
                        font_size = int(_sld_float(v, font_size))
                    elif k == 'font-style':
                        font_style = v
                    elif k == 'font-weight':
                        font_weight = v

            # LabelPlacement — AnchorPoint
            anchor_x = 0.5
            anchor_y = -1.5
            ap = child.xpath(
                'sld:LabelPlacement/sld:PointPlacement/sld:AnchorPoint',
                namespaces=_SLD_NS,
            )
            if ap:
                anchor_x = _sld_float(_sld_first_text(ap[0], 'sld:AnchorPointX'), anchor_x)
                anchor_y = _sld_float(_sld_first_text(ap[0], 'sld:AnchorPointY'), anchor_y)

            # Halo
            halo_radius = 1
            halo_fill = '#ffffff'
            halo_fill_opacity = 1.0
            halos = child.xpath('sld:Halo', namespaces=_SLD_NS)
            if halos:
                halo_radius = int(_sld_float(
                    _sld_first_text(halos[0], 'sld:Radius'), halo_radius,
                ))
                halo_fills = halos[0].xpath('sld:Fill', namespaces=_SLD_NS)
                if halo_fills:
                    for k, v in _sld_css_map(halo_fills[0]).items():
                        if k == 'fill':
                            halo_fill = v
                        elif k == 'fill-opacity':
                            halo_fill_opacity = _sld_float(v, halo_fill_opacity)

            # Fill (text colour)
            text_fill = '#000000'
            text_fill_opacity = 1.0
            fills = child.xpath('sld:Fill', namespaces=_SLD_NS)
            if fills:
                for k, v in _sld_css_map(fills[0]).items():
                    if k == 'fill':
                        text_fill = v
                    elif k == 'fill-opacity':
                        text_fill_opacity = _sld_float(v, text_fill_opacity)

            TextSymbolizerModel(
                rule=model_rule,
                order=scount,
                is_actived=bool(label_pn),
                label=label_pn,
                font_family=font_family,
                font_size=font_size,
                font_style=font_style,
                font_weight=font_weight,
                fill=text_fill,
                fill_opacity=text_fill_opacity,
                halo_radius=halo_radius,
                halo_fill=halo_fill,
                halo_fill_opacity=halo_fill_opacity,
                anchor_point_x=anchor_x,
                anchor_point_y=anchor_y,
            ).save()

        elif tag == 'RasterSymbolizer':
            opacity = _sld_float(_sld_first_text(child, 'sld:Opacity'), 1.0)
            # ColorMap
            cm_type = 'ramp'
            cm_extended = False
            color_map_entries = []
            cms = child.xpath('sld:ColorMap', namespaces=_SLD_NS)
            if cms:
                cm_node = cms[0]
                cm_type = cm_node.get('type') or 'ramp'
                cm_extended = cm_node.get('extended', '').lower() in ('true', '1')
                for idx, entry in enumerate(cm_node.xpath('sld:ColorMapEntry', namespaces=_SLD_NS)):
                    color_map_entries.append({
                        'color': entry.get('color') or '#000000',
                        'quantity': float(entry.get('quantity') or 0),
                        'label': entry.get('label') or '',
                        'opacity': float(entry.get('opacity') or 1.0),
                        'order': idx,
                    })
            color_map = ColorMap(type=cm_type, extended=cm_extended)
            color_map.save()
            for e in color_map_entries:
                ColorMapEntry(
                    color_map=color_map,
                    color=e['color'],
                    quantity=e['quantity'],
                    label=e['label'],
                    opacity=e['opacity'],
                    order=e['order'],
                ).save()
            RasterSymbolizer(
                rule=model_rule,
                order=scount,
                opacity=opacity,
                color_map=color_map,
            ).save()

        scount += 1



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

def sld_import(name, is_default, layer_id, file, mapservice, style_type=None):

    layer = Layer.objects.get(id=int(layer_id))
    raw_sld_text = file.read()

    # SLD_STORED_TYPES (MC heatmap, CS custom): the SLD is kept verbatim in
    # style.sld and sent directly to GeoServer — do NOT try to parse rules
    # because these styles use rendering transformations (ras:Heatmap etc.)
    # that are not representable in the Rule/Symbolizer model.
    if style_type in SLD_STORED_TYPES:
        style = Style(
            name=name,
            title=name,
            is_default=is_default,
            type=style_type,
            sld=raw_sld_text,
        )
        style.save()
        StyleLayer(style=style, layer=layer).save()
        sld_body = utils.encode_xml(raw_sld_text)
        if mapservice.createStyle(style.name, sld_body):
            mapservice.setLayerStyle(layer, style.name, style.is_default)
            return True
        return False

    ### write the data to a temp file
    tup = tempfile.mkstemp() # make a tmp file
    f = os.fdopen(tup[0], 'w') # open the tmp file for writing
    f.write(raw_sld_text) # write the tmp file
    f.close()
    
    filepath = tup[1]
    tmp_sld = open(filepath, 'r')

    try:
        sld = sld_builder.parse_sld(tmp_sld)
    finally:
        tmp_sld.close()

    nl = sld.NamedLayer
    if nl is None:
        utils.__delete_temporaries(filepath)
        return False
    us = nl.UserStyle
    if us is None:
        utils.__delete_temporaries(filepath)
        return False
    fts = us.FeatureTypeStyle
    if fts is None:
        utils.__delete_temporaries(filepath)
        return False

    style_title = us.Title if us.Title else name

    style = Style(
        name=name,
        title=style_title,
        is_default=is_default,
        type=style_type or 'EX',
    )
    style.save()
    
    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()
    
    rules_col = fts.Rules
    for r in rules_col:
        filt = utils.sld_filter_to_json(r.Filter)
        rn = _sld_first_text(r._node, 'sld:Name')
        rt = _sld_first_text(r._node, 'sld:Title')
        rule_name = rn or rt or ''
        rule_title = rt or rn or ''
        rule = Rule(
            style = style,
            name = rule_name,
            title = rule_title,
            abstract = '',
            filter = json.dumps(filt) if filt is not None else '',
            minscale = -1 if r.MinScaleDenominator is None else r.MinScaleDenominator,
            maxscale = -1 if r.MaxScaleDenominator is None else r.MaxScaleDenominator,
            order = 0
        )
        rule.save()
        _sld_import_symbolizers(r._node, rule)

    # CP (clustered points) must keep the PointStacker transformation.
    single_symbol = style_type not in SLD_BUILD_FULL_TYPES
    sld_body = sld_builder.build_sld(layer, style, single_symbol=single_symbol)
    if mapservice.createStyle(style.name, sld_body): 
        mapservice.setLayerStyle(layer, style.name, style.is_default)
        utils.__delete_temporaries(filepath)
        return True
        
    else:
        utils.__delete_temporaries(filepath)
        return False


def clone_sld_style(style, target_layer, new_style_name, source_layer=None, original_style_name=None):
    """
    Update layer/style names inside a stored SLD document.
    Uses local-name() XPath so it works with both prefixed (sld:) and default-namespace elements.
    """
    target_layer_name = target_layer.name
    try:
        sld = etree.fromstring(style.sld)
    except Exception:
        xml_str = re.sub(r'^<\?xml[^>]*encoding=[\'"].*?[\'"][^>]*\?>', '', style.sld.strip())
        sld = etree.fromstring(xml_str)

    layer_name_els = sld.xpath(
        '/*[local-name()="StyledLayerDescriptor"]/*[local-name()="NamedLayer"]/*[local-name()="Name"]'
    )
    if layer_name_els:
        layer_name_els[0].text = target_layer_name

    user_style_names = sld.xpath(
        '/*[local-name()="StyledLayerDescriptor"]/*[local-name()="NamedLayer"]'
        '/*[local-name()="UserStyle"]/*[local-name()="Name"]'
    )
    if user_style_names:
        user_style_names[0].text = new_style_name

    user_style_titles = sld.xpath(
        '/*[local-name()="StyledLayerDescriptor"]/*[local-name()="NamedLayer"]'
        '/*[local-name()="UserStyle"]/*[local-name()="Title"]'
    )
    if user_style_titles:
        user_style_titles[0].text = style.title or new_style_name

    style.sld = etree.tostring(sld, encoding="utf-8", xml_declaration=True).decode('utf-8')

    if source_layer:
        old_ws = source_layer.datastore.workspace.name
        new_ws = target_layer.datastore.workspace.name
        old_layer = source_layer.name
        replacements = [
            (f'{old_ws}:{old_layer}', f'{new_ws}:{target_layer_name}'),
            (old_layer, target_layer_name),
        ]
        if original_style_name and original_style_name != new_style_name:
            replacements.append((original_style_name, new_style_name))
        for old, new in replacements:
            if old and old != new:
                style.sld = style.sld.replace(old, new)

    style.save()
    return style

def clone_with_subclass(obj):
    obj.pk = None
    obj.save()

    for related in obj._meta.related_objects:
        if related.one_to_one and issubclass(related.related_model, obj.__class__):
            child = getattr(obj, related.get_accessor_name(), None)
            if child:
                child.pk = None
                setattr(child, related.field.name, obj)
                child.save()

    return obj

def _clone_layer_style(style, original_style):
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

            elif hasattr(original_symbolizer, 'textsymbolizer'):
                symbolizer = clone_with_subclass(original_symbolizer)
                symbolizer.rule = new_rule_instance
                symbolizer.save()

    return Style.objects.get(id=style.pk)


def clone_layer_style(style, target_layer, new_style_name=None, source_layer=None):
    if not new_style_name:
        new_style_name = target_layer.datastore.workspace.name + "_" + style.name
    old_id = style.pk
    original_style_name = style.name
    style_type = style.type
    style.pk = None
    style.name = new_style_name
    style.save()
    if style_type in SLD_STORED_TYPES:
        return clone_sld_style(
            style,
            target_layer,
            new_style_name,
            source_layer=source_layer,
            original_style_name=original_style_name,
        )
    original_style = Style.objects.get(id=old_id)
    return _clone_layer_style(style, original_style)


def clone_layer_styles(mapservice, source_layer, target_layer):
    for style_layer in StyleLayer.objects.filter(layer=source_layer).order_by("-style__is_default"):
        style = style_layer.style
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
        new_style = clone_layer_style(
            style, target_layer, new_style_name=new_style_name, source_layer=source_layer
        )
        new_style_layer = StyleLayer()
        new_style_layer.layer = target_layer
        new_style_layer.style = new_style
        new_style_layer.save()
        if style.type in SLD_STORED_TYPES:
            sld_body = utils.encode_xml(new_style.sld)
        else:
            # CP clustered points require PointStacker (single_symbol=True strips it).
            single_symbol = style.type not in SLD_BUILD_FULL_TYPES
            sld_body = sld_builder.build_sld(target_layer, new_style, single_symbol=single_symbol)
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