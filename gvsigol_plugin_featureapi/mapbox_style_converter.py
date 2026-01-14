# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2024 SCOLAB.

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

@author: Conversor SLD a Mapbox GL Style
'''

import json
import logging
import xml.etree.ElementTree as ET

from gvsigol_symbology.models import (
    Style, StyleLayer, Rule, 
    MarkSymbolizer, LineSymbolizer, PolygonSymbolizer, 
    TextSymbolizer, ExternalGraphicSymbolizer, RasterSymbolizer,
    ColorMap, ColorMapEntry
)
from gvsigol_services.models import Layer

logger = logging.getLogger(__name__)


def hex_to_rgba(hex_color, opacity=1.0):
    """Convierte color hexadecimal a formato rgba de Mapbox."""
    if not hex_color:
        return None
    
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        if opacity < 1.0:
            return f"rgba({r}, {g}, {b}, {opacity})"
        return f"#{hex_color}"
    return hex_color


def parse_dash_array(dash_array_str):
    """Convierte stroke-dasharray de SLD a formato Mapbox."""
    if not dash_array_str or dash_array_str.strip() == '':
        return None
    
    try:
        parts = dash_array_str.replace(',', ' ').split()
        return [float(p) for p in parts if p]
    except:
        return None


def convert_filter_to_mapbox(filter_json_str):
    """
    Convierte un filtro JSON de gvSIG Online a formato de filtro Mapbox GL.
    
    Formatos de entrada soportados (gvSIG Online):
    
    1. Formato UniqueValues/Intervals (el más común):
       {"operation": "is_equal_to", "field": "campo", "value": "valor"}
    
    2. Formato alternativo:
       {"type": "is_equal_to", "property_name": "campo", "value1": "valor"}
    
    3. Array de filtros:
       [{"operation": "is_equal_to", "field": "campo", "value": "valor"}]
    
    Formato de salida (Mapbox GL):
    ["==", ["get", "campo"], "valor"]
    """
    if not filter_json_str or filter_json_str.strip() == '':
        return None
    
    try:
        filter_data = json.loads(filter_json_str)
        
        # Si es un objeto único, convertirlo a lista
        if isinstance(filter_data, dict):
            filters = [filter_data]
        elif isinstance(filter_data, list):
            filters = filter_data
        else:
            return None
        
        if not filters or len(filters) == 0:
            return None
        
        mapbox_filters = []
        
        for f in filters:
            # Soportar múltiples formatos de nombres de campos
            # Formato 1: operation/field/value (UniqueValues, Intervals)
            # Formato 2: type/property_name/value1 (SLD import)
            filter_type = f.get('operation', f.get('type', ''))
            prop = f.get('field', f.get('property_name', f.get('property', '')))
            value = f.get('value', f.get('value1', ''))
            
            if not filter_type or not prop:
                logger.warning(f"Filter missing operation or field: {f}")
                continue
            
            # Normalizar el tipo de filtro (quitar guiones bajos y convertir a minúsculas)
            filter_type_lower = filter_type.lower().replace('_', '').replace(' ', '')
            
            if filter_type_lower in ['isequalto', 'propertyisequalto', 'equalto']:
                mapbox_filters.append(["==", ["get", prop], value])
            elif filter_type_lower in ['isnotequalto', 'propertyisnotequalto', 'notequalto']:
                mapbox_filters.append(["!=", ["get", prop], value])
            elif filter_type_lower in ['islessthan', 'propertyislessthan', 'lessthan']:
                try:
                    mapbox_filters.append(["<", ["get", prop], float(value)])
                except:
                    mapbox_filters.append(["<", ["get", prop], value])
            elif filter_type_lower in ['islessthanorequalto', 'propertyislessthanorequalto', 'lessthanorequalto']:
                try:
                    mapbox_filters.append(["<=", ["get", prop], float(value)])
                except:
                    mapbox_filters.append(["<=", ["get", prop], value])
            elif filter_type_lower in ['isgreaterthan', 'propertyisgreaterthan', 'greaterthan']:
                try:
                    mapbox_filters.append([">", ["get", prop], float(value)])
                except:
                    mapbox_filters.append([">", ["get", prop], value])
            elif filter_type_lower in ['isgreaterthanorequalto', 'propertyisgreaterthanorequalto', 'greaterthanorequalto']:
                try:
                    mapbox_filters.append([">=", ["get", prop], float(value)])
                except:
                    mapbox_filters.append([">=", ["get", prop], value])
            elif filter_type_lower in ['islike', 'propertyislike', 'like']:
                # Mapbox no soporta LIKE directamente
                clean_value = str(value).replace('%', '')
                mapbox_filters.append(["in", clean_value, ["get", prop]])
            elif filter_type_lower in ['isnull', 'propertyisnull', 'null']:
                mapbox_filters.append(["==", ["get", prop], None])
            elif filter_type_lower in ['isbetween', 'propertyisbetween', 'between']:
                lower = f.get('value', f.get('value1', f.get('lowerBoundary', '')))
                upper = f.get('value2', f.get('upperBoundary', ''))
                try:
                    mapbox_filters.append(["all", 
                        [">=", ["get", prop], float(lower)],
                        ["<=", ["get", prop], float(upper)]
                    ])
                except:
                    mapbox_filters.append(["all", 
                        [">=", ["get", prop], lower],
                        ["<=", ["get", prop], upper]
                    ])
            else:
                logger.warning(f"Unknown filter type: {filter_type} in filter: {f}")
        
        if len(mapbox_filters) == 0:
            return None
        elif len(mapbox_filters) == 1:
            return mapbox_filters[0]
        else:
            return ["all"] + mapbox_filters
            
    except Exception as e:
        logger.warning(f"Error parsing filter '{filter_json_str}': {e}")
        return None


def convert_mark_symbolizer(symbolizer, layer_id, rule_name, source_layer):
    """Convierte MarkSymbolizer a capa Mapbox GL (circle)."""
    layer = {
        "id": f"{layer_id}_{rule_name}_point",
        "type": "circle",
        "source": "gvsigol",
        "source-layer": source_layer,
        "paint": {}
    }
    
    # Circle radius (size / 2)
    if symbolizer.size:
        layer["paint"]["circle-radius"] = symbolizer.size / 2
    
    # Fill color
    if symbolizer.fill:
        fill_color = hex_to_rgba(symbolizer.fill, symbolizer.fill_opacity or 1.0)
        if fill_color:
            layer["paint"]["circle-color"] = fill_color
    
    # Fill opacity
    if symbolizer.fill_opacity is not None and symbolizer.fill_opacity < 1.0:
        layer["paint"]["circle-opacity"] = symbolizer.fill_opacity
    
    # Stroke color
    if symbolizer.stroke:
        stroke_color = hex_to_rgba(symbolizer.stroke, symbolizer.stroke_opacity or 1.0)
        if stroke_color:
            layer["paint"]["circle-stroke-color"] = stroke_color
    
    # Stroke width
    if symbolizer.stroke_width:
        layer["paint"]["circle-stroke-width"] = symbolizer.stroke_width
    
    # Stroke opacity
    if symbolizer.stroke_opacity is not None and symbolizer.stroke_opacity < 1.0:
        layer["paint"]["circle-stroke-opacity"] = symbolizer.stroke_opacity
    
    return layer


def convert_line_symbolizer(symbolizer, layer_id, rule_name, source_layer):
    """Convierte LineSymbolizer a capa Mapbox GL (line)."""
    layer = {
        "id": f"{layer_id}_{rule_name}_line",
        "type": "line",
        "source": "gvsigol",
        "source-layer": source_layer,
        "paint": {},
        "layout": {
            "line-join": "round",
            "line-cap": "round"
        }
    }
    
    # Stroke color
    if symbolizer.stroke:
        stroke_color = hex_to_rgba(symbolizer.stroke, symbolizer.stroke_opacity or 1.0)
        if stroke_color:
            layer["paint"]["line-color"] = stroke_color
    
    # Stroke width
    if symbolizer.stroke_width:
        layer["paint"]["line-width"] = symbolizer.stroke_width
    
    # Stroke opacity
    if symbolizer.stroke_opacity is not None and symbolizer.stroke_opacity < 1.0:
        layer["paint"]["line-opacity"] = symbolizer.stroke_opacity
    
    # Dash array
    dash = parse_dash_array(symbolizer.stroke_dash_array)
    if dash:
        layer["paint"]["line-dasharray"] = dash
    
    return layer


def convert_polygon_symbolizer(symbolizer, layer_id, rule_name, source_layer):
    """Convierte PolygonSymbolizer a capas Mapbox GL (fill + line para borde)."""
    layers = []
    
    # Capa de relleno
    fill_layer = {
        "id": f"{layer_id}_{rule_name}_fill",
        "type": "fill",
        "source": "gvsigol",
        "source-layer": source_layer,
        "paint": {}
    }
    
    # Fill color
    if symbolizer.fill:
        fill_color = hex_to_rgba(symbolizer.fill, symbolizer.fill_opacity or 1.0)
        if fill_color:
            fill_layer["paint"]["fill-color"] = fill_color
    
    # Fill opacity
    if symbolizer.fill_opacity is not None and symbolizer.fill_opacity < 1.0:
        fill_layer["paint"]["fill-opacity"] = symbolizer.fill_opacity
    
    layers.append(fill_layer)
    
    # Capa de borde (si hay stroke)
    if symbolizer.stroke and symbolizer.stroke_width and symbolizer.stroke_width > 0:
        stroke_layer = {
            "id": f"{layer_id}_{rule_name}_stroke",
            "type": "line",
            "source": "gvsigol",
            "source-layer": source_layer,
            "paint": {},
            "layout": {
                "line-join": "round",
                "line-cap": "round"
            }
        }
        
        stroke_color = hex_to_rgba(symbolizer.stroke, symbolizer.stroke_opacity or 1.0)
        if stroke_color:
            stroke_layer["paint"]["line-color"] = stroke_color
        
        stroke_layer["paint"]["line-width"] = symbolizer.stroke_width
        
        if symbolizer.stroke_opacity is not None and symbolizer.stroke_opacity < 1.0:
            stroke_layer["paint"]["line-opacity"] = symbolizer.stroke_opacity
        
        dash = parse_dash_array(symbolizer.stroke_dash_array)
        if dash:
            stroke_layer["paint"]["line-dasharray"] = dash
        
        layers.append(stroke_layer)
    
    return layers


def convert_text_symbolizer(symbolizer, layer_id, rule_name, source_layer):
    """Convierte TextSymbolizer a capa Mapbox GL (symbol)."""
    if not symbolizer.is_actived:
        return None
    
    layer = {
        "id": f"{layer_id}_{rule_name}_label",
        "type": "symbol",
        "source": "gvsigol",
        "source-layer": source_layer,
        "layout": {},
        "paint": {}
    }
    
    # Label field
    if symbolizer.label:
        layer["layout"]["text-field"] = ["get", symbolizer.label]
    
    # Font
    font_family = symbolizer.font_family or "Arial"
    font_weight = symbolizer.font_weight or "Regular"
    layer["layout"]["text-font"] = [f"{font_family} {font_weight}"]
    
    # Font size
    if symbolizer.font_size:
        layer["layout"]["text-size"] = symbolizer.font_size
    
    # Text color
    if symbolizer.fill:
        text_color = hex_to_rgba(symbolizer.fill, symbolizer.fill_opacity or 1.0)
        if text_color:
            layer["paint"]["text-color"] = text_color
    
    # Halo (outline)
    if symbolizer.halo_fill and symbolizer.halo_radius:
        halo_color = hex_to_rgba(symbolizer.halo_fill, symbolizer.halo_fill_opacity or 1.0)
        if halo_color:
            layer["paint"]["text-halo-color"] = halo_color
            layer["paint"]["text-halo-width"] = symbolizer.halo_radius
    
    # Anchor/offset
    if symbolizer.anchor_point_x is not None and symbolizer.anchor_point_y is not None:
        layer["layout"]["text-offset"] = [symbolizer.anchor_point_x, symbolizer.anchor_point_y]
    
    return layer


def convert_external_graphic_symbolizer(symbolizer, layer_id, rule_name, source_layer):
    """Convierte ExternalGraphicSymbolizer a capa Mapbox GL (symbol con icon)."""
    layer = {
        "id": f"{layer_id}_{rule_name}_icon",
        "type": "symbol",
        "source": "gvsigol",
        "source-layer": source_layer,
        "layout": {},
        "paint": {}
    }
    
    # Icon image (referencia al sprite)
    if symbolizer.online_resource:
        # Extraer nombre del icono de la URL
        icon_name = symbolizer.online_resource.split('/')[-1].split('.')[0]
        layer["layout"]["icon-image"] = icon_name
    
    # Icon size
    if symbolizer.size:
        layer["layout"]["icon-size"] = symbolizer.size / 32.0  # Normalizar
    
    # Rotation
    if symbolizer.rotation:
        layer["layout"]["icon-rotate"] = symbolizer.rotation
    
    # Opacity
    if symbolizer.opacity is not None and symbolizer.opacity < 1:
        layer["paint"]["icon-opacity"] = symbolizer.opacity
    
    return layer


def parse_ogc_filter_from_sld(filter_elem, namespaces):
    """
    Parsea un filtro OGC desde SLD XML y lo convierte a formato Mapbox GL.
    
    Soporta:
    - PropertyIsEqualTo
    - PropertyIsNotEqualTo
    - PropertyIsLessThan
    - PropertyIsLessThanOrEqualTo
    - PropertyIsGreaterThan
    - PropertyIsGreaterThanOrEqualTo
    - PropertyIsLike
    - PropertyIsNull
    - PropertyIsBetween
    - And, Or, Not (operadores lógicos)
    
    Args:
        filter_elem: Elemento XML del filtro (<ogc:Filter>)
        namespaces: Diccionario de namespaces XML
    
    Returns:
        list o None: Filtro en formato Mapbox GL o None si no se puede parsear
    """
    if filter_elem is None:
        return None
    
    try:
        # PropertyIsEqualTo
        prop_is_equal = filter_elem.find('ogc:PropertyIsEqualTo', namespaces)
        if prop_is_equal is not None:
            prop_name = prop_is_equal.find('ogc:PropertyName', namespaces)
            literal = prop_is_equal.find('ogc:Literal', namespaces)
            if prop_name is not None and literal is not None:
                value = literal.text
                # Intentar convertir a número si es posible
                try:
                    value = float(value) if '.' in value else int(value)
                except:
                    pass
                return ["==", ["get", prop_name.text], value]
        
        # PropertyIsNotEqualTo
        prop_is_not_equal = filter_elem.find('ogc:PropertyIsNotEqualTo', namespaces)
        if prop_is_not_equal is not None:
            prop_name = prop_is_not_equal.find('ogc:PropertyName', namespaces)
            literal = prop_is_not_equal.find('ogc:Literal', namespaces)
            if prop_name is not None and literal is not None:
                value = literal.text
                try:
                    value = float(value) if '.' in value else int(value)
                except:
                    pass
                return ["!=", ["get", prop_name.text], value]
        
        # PropertyIsLessThan
        prop_is_less = filter_elem.find('ogc:PropertyIsLessThan', namespaces)
        if prop_is_less is not None:
            prop_name = prop_is_less.find('ogc:PropertyName', namespaces)
            literal = prop_is_less.find('ogc:Literal', namespaces)
            if prop_name is not None and literal is not None:
                try:
                    value = float(literal.text)
                except:
                    value = literal.text
                return ["<", ["get", prop_name.text], value]
        
        # PropertyIsLessThanOrEqualTo
        prop_is_less_or_equal = filter_elem.find('ogc:PropertyIsLessThanOrEqualTo', namespaces)
        if prop_is_less_or_equal is not None:
            prop_name = prop_is_less_or_equal.find('ogc:PropertyName', namespaces)
            literal = prop_is_less_or_equal.find('ogc:Literal', namespaces)
            if prop_name is not None and literal is not None:
                try:
                    value = float(literal.text)
                except:
                    value = literal.text
                return ["<=", ["get", prop_name.text], value]
        
        # PropertyIsGreaterThan
        prop_is_greater = filter_elem.find('ogc:PropertyIsGreaterThan', namespaces)
        if prop_is_greater is not None:
            prop_name = prop_is_greater.find('ogc:PropertyName', namespaces)
            literal = prop_is_greater.find('ogc:Literal', namespaces)
            if prop_name is not None and literal is not None:
                try:
                    value = float(literal.text)
                except:
                    value = literal.text
                return [">", ["get", prop_name.text], value]
        
        # PropertyIsGreaterThanOrEqualTo
        prop_is_greater_or_equal = filter_elem.find('ogc:PropertyIsGreaterThanOrEqualTo', namespaces)
        if prop_is_greater_or_equal is not None:
            prop_name = prop_is_greater_or_equal.find('ogc:PropertyName', namespaces)
            literal = prop_is_greater_or_equal.find('ogc:Literal', namespaces)
            if prop_name is not None and literal is not None:
                try:
                    value = float(literal.text)
                except:
                    value = literal.text
                return [">=", ["get", prop_name.text], value]
        
        # PropertyIsLike
        prop_is_like = filter_elem.find('ogc:PropertyIsLike', namespaces)
        if prop_is_like is not None:
            prop_name = prop_is_like.find('ogc:PropertyName', namespaces)
            literal = prop_is_like.find('ogc:Literal', namespaces)
            if prop_name is not None and literal is not None:
                # Mapbox no soporta LIKE directamente, usar "in"
                clean_value = literal.text.replace('%', '').replace('*', '')
                return ["in", clean_value, ["get", prop_name.text]]
        
        # PropertyIsNull
        prop_is_null = filter_elem.find('ogc:PropertyIsNull', namespaces)
        if prop_is_null is not None:
            prop_name = prop_is_null.find('ogc:PropertyName', namespaces)
            if prop_name is not None:
                return ["==", ["get", prop_name.text], None]
        
        # PropertyIsBetween
        prop_is_between = filter_elem.find('ogc:PropertyIsBetween', namespaces)
        if prop_is_between is not None:
            prop_name = prop_is_between.find('ogc:PropertyName', namespaces)
            lower_boundary = prop_is_between.find('ogc:LowerBoundary/ogc:Literal', namespaces)
            upper_boundary = prop_is_between.find('ogc:UpperBoundary/ogc:Literal', namespaces)
            if prop_name is not None and lower_boundary is not None and upper_boundary is not None:
                try:
                    lower = float(lower_boundary.text)
                    upper = float(upper_boundary.text)
                except:
                    lower = lower_boundary.text
                    upper = upper_boundary.text
                return ["all",
                    [">=", ["get", prop_name.text], lower],
                    ["<=", ["get", prop_name.text], upper]
                ]
        
        # And (operador lógico)
        and_filter = filter_elem.find('ogc:And', namespaces)
        if and_filter is not None:
            sub_filters = []
            for child in and_filter:
                # Crear un elemento temporal para parsear cada hijo
                temp_filter = ET.Element('Filter')
                temp_filter.append(child)
                sub_filter = parse_ogc_filter_from_sld(temp_filter, namespaces)
                if sub_filter:
                    sub_filters.append(sub_filter)
            if len(sub_filters) > 0:
                return ["all"] + sub_filters
        
        # Or (operador lógico)
        or_filter = filter_elem.find('ogc:Or', namespaces)
        if or_filter is not None:
            sub_filters = []
            for child in or_filter:
                temp_filter = ET.Element('Filter')
                temp_filter.append(child)
                sub_filter = parse_ogc_filter_from_sld(temp_filter, namespaces)
                if sub_filter:
                    sub_filters.append(sub_filter)
            if len(sub_filters) > 0:
                return ["any"] + sub_filters
        
        # Not (operador lógico)
        not_filter = filter_elem.find('ogc:Not', namespaces)
        if not_filter is not None:
            for child in not_filter:
                temp_filter = ET.Element('Filter')
                temp_filter.append(child)
                sub_filter = parse_ogc_filter_from_sld(temp_filter, namespaces)
                if sub_filter:
                    return ["!", sub_filter]
        
        return None
        
    except Exception as e:
        logger.warning(f"Error parsing OGC filter: {e}")
        return None


def parse_sld_to_mapbox(style, layer_id, source_layer):
    """
    Parsea un SLD personalizado (tipo CS) y convierte a Mapbox GL Style.
    Soporta estilos básicos: Point, Line, Polygon, Text symbolizers.
    
    Args:
        style: Objeto Style con campo sld con el XML
        layer_id: ID de la capa
        source_layer: Nombre del source-layer
    
    Returns:
        list: Lista de capas Mapbox GL
    """
    if not style.sld:
        logger.warning(f"Style {style.id} has no SLD content")
        return []
    
    try:
        root = ET.fromstring(style.sld)
        
        # Namespaces comunes en SLD
        namespaces = {
            'sld': 'http://www.opengis.net/sld',
            'ogc': 'http://www.opengis.net/ogc',
            'se': 'http://www.opengis.net/se'
        }
        
        layers = []
        
        # Buscar todas las reglas (Rules)
        rules = root.findall('.//sld:Rule', namespaces)
        
        for idx, rule in enumerate(rules):
            rule_name = rule.find('sld:Name', namespaces)
            rule_name_str = rule_name.text if rule_name is not None and rule_name.text else f"rule_{idx}"
            rule_name_str = rule_name_str.replace(' ', '_').replace(':', '_')
            
            # Buscar filtros OGC
            filter_elem = rule.find('ogc:Filter', namespaces)
            mapbox_filter = parse_ogc_filter_from_sld(filter_elem, namespaces) if filter_elem is not None else None
            
            # Buscar escalas
            minscale_elem = rule.find('sld:MinScaleDenominator', namespaces)
            maxscale_elem = rule.find('sld:MaxScaleDenominator', namespaces)
            minscale = float(minscale_elem.text) if minscale_elem is not None and minscale_elem.text else None
            maxscale = float(maxscale_elem.text) if maxscale_elem is not None and maxscale_elem.text else None
            
            # Buscar PointSymbolizer
            point_symbolizers = rule.findall('.//sld:PointSymbolizer', namespaces)
            for ps in point_symbolizers:
                lyr = parse_point_symbolizer_from_sld(ps, namespaces, layer_id, rule_name_str, source_layer)
                if lyr:
                    if mapbox_filter:
                        lyr["filter"] = mapbox_filter
                    lyr = apply_scale_to_layer(lyr, minscale, maxscale)
                    layers.append(lyr)
            
            # Buscar LineSymbolizer
            line_symbolizers = rule.findall('.//sld:LineSymbolizer', namespaces)
            for ls in line_symbolizers:
                lyr = parse_line_symbolizer_from_sld(ls, namespaces, layer_id, rule_name_str, source_layer)
                if lyr:
                    if mapbox_filter:
                        lyr["filter"] = mapbox_filter
                    lyr = apply_scale_to_layer(lyr, minscale, maxscale)
                    layers.append(lyr)
            
            # Buscar PolygonSymbolizer
            polygon_symbolizers = rule.findall('.//sld:PolygonSymbolizer', namespaces)
            for pgs in polygon_symbolizers:
                lyrs = parse_polygon_symbolizer_from_sld(pgs, namespaces, layer_id, rule_name_str, source_layer)
                for lyr in lyrs:
                    if mapbox_filter:
                        lyr["filter"] = mapbox_filter
                    lyr = apply_scale_to_layer(lyr, minscale, maxscale)
                    layers.append(lyr)
            
            # Buscar TextSymbolizer
            text_symbolizers = rule.findall('.//sld:TextSymbolizer', namespaces)
            for ts in text_symbolizers:
                lyr = parse_text_symbolizer_from_sld(ts, namespaces, layer_id, rule_name_str, source_layer)
                if lyr:
                    if mapbox_filter:
                        lyr["filter"] = mapbox_filter
                    lyr = apply_scale_to_layer(lyr, minscale, maxscale)
                    layers.append(lyr)
        
        return layers
        
    except ET.ParseError as e:
        logger.error(f"Error parsing SLD XML for style {style.id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing SLD for style {style.id}: {e}")
        return []


def parse_point_symbolizer_from_sld(symbolizer, namespaces, layer_id, rule_name, source_layer):
    """Parsea PointSymbolizer desde SLD XML."""
    layer = {
        "id": f"{layer_id}_{rule_name}_point",
        "type": "circle",
        "source": "gvsigol",
        "source-layer": source_layer,
        "paint": {}
    }
    
    # Buscar Graphic/Mark
    mark = symbolizer.find('.//sld:Mark', namespaces)
    if mark is not None:
        # Fill
        fill = mark.find('.//sld:Fill/sld:CssParameter[@name="fill"]', namespaces)
        if fill is not None and fill.text:
            layer["paint"]["circle-color"] = fill.text
        
        fill_opacity = mark.find('.//sld:Fill/sld:CssParameter[@name="fill-opacity"]', namespaces)
        if fill_opacity is not None and fill_opacity.text:
            try:
                layer["paint"]["circle-opacity"] = float(fill_opacity.text)
            except:
                pass
        
        # Stroke
        stroke = mark.find('.//sld:Stroke/sld:CssParameter[@name="stroke"]', namespaces)
        if stroke is not None and stroke.text:
            layer["paint"]["circle-stroke-color"] = stroke.text
        
        stroke_width = mark.find('.//sld:Stroke/sld:CssParameter[@name="stroke-width"]', namespaces)
        if stroke_width is not None and stroke_width.text:
            try:
                layer["paint"]["circle-stroke-width"] = float(stroke_width.text)
            except:
                pass
    
    # Size
    size = symbolizer.find('.//sld:Size', namespaces)
    if size is not None and size.text:
        try:
            layer["paint"]["circle-radius"] = float(size.text) / 2
        except:
            layer["paint"]["circle-radius"] = 4
    else:
        layer["paint"]["circle-radius"] = 4
    
    return layer


def parse_line_symbolizer_from_sld(symbolizer, namespaces, layer_id, rule_name, source_layer):
    """Parsea LineSymbolizer desde SLD XML."""
    layer = {
        "id": f"{layer_id}_{rule_name}_line",
        "type": "line",
        "source": "gvsigol",
        "source-layer": source_layer,
        "paint": {},
        "layout": {
            "line-join": "round",
            "line-cap": "round"
        }
    }
    
    # Stroke color
    stroke = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke"]', namespaces)
    if stroke is not None and stroke.text:
        layer["paint"]["line-color"] = stroke.text
    
    # Stroke width
    stroke_width = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke-width"]', namespaces)
    if stroke_width is not None and stroke_width.text:
        try:
            layer["paint"]["line-width"] = float(stroke_width.text)
        except:
            pass
    
    # Stroke opacity
    stroke_opacity = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke-opacity"]', namespaces)
    if stroke_opacity is not None and stroke_opacity.text:
        try:
            layer["paint"]["line-opacity"] = float(stroke_opacity.text)
        except:
            pass
    
    # Stroke dasharray
    stroke_dasharray = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke-dasharray"]', namespaces)
    if stroke_dasharray is not None and stroke_dasharray.text:
        dash = parse_dash_array(stroke_dasharray.text)
        if dash:
            layer["paint"]["line-dasharray"] = dash
    
    return layer


def parse_polygon_symbolizer_from_sld(symbolizer, namespaces, layer_id, rule_name, source_layer):
    """Parsea PolygonSymbolizer desde SLD XML."""
    layers = []
    
    # Capa de relleno
    fill_layer = {
        "id": f"{layer_id}_{rule_name}_fill",
        "type": "fill",
        "source": "gvsigol",
        "source-layer": source_layer,
        "paint": {}
    }
    
    # Fill color
    fill = symbolizer.find('.//sld:Fill/sld:CssParameter[@name="fill"]', namespaces)
    if fill is not None and fill.text:
        fill_layer["paint"]["fill-color"] = fill.text
    
    # Fill opacity
    fill_opacity = symbolizer.find('.//sld:Fill/sld:CssParameter[@name="fill-opacity"]', namespaces)
    if fill_opacity is not None and fill_opacity.text:
        try:
            fill_layer["paint"]["fill-opacity"] = float(fill_opacity.text)
        except:
            pass
    
    layers.append(fill_layer)
    
    # Capa de borde (Stroke)
    stroke = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke"]', namespaces)
    stroke_width = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke-width"]', namespaces)
    
    if stroke is not None and stroke.text and stroke_width is not None and stroke_width.text:
        try:
            width = float(stroke_width.text)
            if width > 0:
                stroke_layer = {
                    "id": f"{layer_id}_{rule_name}_stroke",
                    "type": "line",
                    "source": "gvsigol",
                    "source-layer": source_layer,
                    "paint": {
                        "line-color": stroke.text,
                        "line-width": width
                    },
                    "layout": {
                        "line-join": "round",
                        "line-cap": "round"
                    }
                }
                
                # Stroke opacity
                stroke_opacity = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke-opacity"]', namespaces)
                if stroke_opacity is not None and stroke_opacity.text:
                    try:
                        stroke_layer["paint"]["line-opacity"] = float(stroke_opacity.text)
                    except:
                        pass
                
                # Stroke dasharray
                stroke_dasharray = symbolizer.find('.//sld:Stroke/sld:CssParameter[@name="stroke-dasharray"]', namespaces)
                if stroke_dasharray is not None and stroke_dasharray.text:
                    dash = parse_dash_array(stroke_dasharray.text)
                    if dash:
                        stroke_layer["paint"]["line-dasharray"] = dash
                
                layers.append(stroke_layer)
        except:
            pass
    
    return layers


def parse_text_symbolizer_from_sld(symbolizer, namespaces, layer_id, rule_name, source_layer):
    """Parsea TextSymbolizer desde SLD XML."""
    layer = {
        "id": f"{layer_id}_{rule_name}_label",
        "type": "symbol",
        "source": "gvsigol",
        "source-layer": source_layer,
        "layout": {},
        "paint": {}
    }
    
    # Label (PropertyName)
    label = symbolizer.find('.//sld:Label/ogc:PropertyName', namespaces)
    if label is not None and label.text:
        layer["layout"]["text-field"] = ["get", label.text]
    else:
        # Si no hay PropertyName, podría ser un literal
        label_literal = symbolizer.find('.//sld:Label', namespaces)
        if label_literal is not None and label_literal.text:
            layer["layout"]["text-field"] = label_literal.text
    
    # Font
    font_family = symbolizer.find('.//sld:Font/sld:CssParameter[@name="font-family"]', namespaces)
    font_size = symbolizer.find('.//sld:Font/sld:CssParameter[@name="font-size"]', namespaces)
    font_weight = symbolizer.find('.//sld:Font/sld:CssParameter[@name="font-weight"]', namespaces)
    
    if font_family is not None and font_family.text:
        weight = font_weight.text if font_weight is not None and font_weight.text else "Regular"
        layer["layout"]["text-font"] = [f"{font_family.text} {weight}"]
    
    if font_size is not None and font_size.text:
        try:
            layer["layout"]["text-size"] = float(font_size.text)
        except:
            pass
    
    # Fill color
    fill = symbolizer.find('.//sld:Fill/sld:CssParameter[@name="fill"]', namespaces)
    if fill is not None and fill.text:
        layer["paint"]["text-color"] = fill.text
    
    # Halo
    halo_fill = symbolizer.find('.//sld:Halo/sld:Fill/sld:CssParameter[@name="fill"]', namespaces)
    halo_radius = symbolizer.find('.//sld:Halo/sld:Radius', namespaces)
    
    if halo_fill is not None and halo_fill.text and halo_radius is not None and halo_radius.text:
        layer["paint"]["text-halo-color"] = halo_fill.text
        try:
            layer["paint"]["text-halo-width"] = float(halo_radius.text)
        except:
            pass
    
    return layer


def create_heatmap_from_sld(style, layer_id, source_layer):
    """
    Crea una capa heatmap de Mapbox GL desde el SLD almacenado en el estilo.
    Los estilos tipo "MC" guardan el SLD directamente sin crear Rule/RasterSymbolizer.
    
    Args:
        style: Objeto Style con type='MC' y campo sld con el XML
        layer_id: ID de la capa
        source_layer: Nombre del source-layer
    
    Returns:
        dict: Capa Mapbox GL de tipo heatmap
    """
    if not style.sld:
        logger.warning(f"Style {style.id} is type MC but has no SLD content")
        return None
    
    try:
        # Parsear el SLD XML
        root = ET.fromstring(style.sld)
        
        # Namespaces comunes en SLD
        namespaces = {
            'sld': 'http://www.opengis.net/sld',
            'ogc': 'http://www.opengis.net/ogc'
        }
        
        # Buscar RasterSymbolizer
        raster_symbolizer = root.find('.//sld:RasterSymbolizer', namespaces)
        if raster_symbolizer is None:
            logger.warning(f"Style {style.id} SLD does not contain RasterSymbolizer")
            return None
        
        # Obtener opacidad
        opacity_elem = raster_symbolizer.find('sld:Opacity', namespaces)
        opacity = 0.6  # default
        if opacity_elem is not None and opacity_elem.text:
            try:
                opacity = float(opacity_elem.text)
            except:
                pass
        
        # Buscar ColorMap
        color_map = raster_symbolizer.find('sld:ColorMap', namespaces)
        color_stops = []
        
        if color_map is not None:
            # Obtener todas las entradas del ColorMap
            entries = color_map.findall('sld:ColorMapEntry', namespaces)
            
            for entry in entries:
                color = entry.get('color', '')
                quantity = entry.get('quantity', '0')
                label = entry.get('label', '')
                entry_opacity = entry.get('opacity', '1.0')
                
                try:
                    quantity_float = float(quantity)
                    opacity_float = float(entry_opacity) if entry_opacity else 1.0
                    
                    # Si es nodata, usar transparencia
                    if label and 'nodata' in label.lower():
                        color_rgba = "rgba(0,0,0,0)"
                    else:
                        # Convertir color hex a rgba
                        if color:
                            hex_color = color.lstrip('#')
                            if len(hex_color) == 6:
                                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                                color_rgba = f"rgba({r}, {g}, {b}, {opacity_float})"
                            else:
                                color_rgba = color
                        else:
                            color_rgba = "rgba(0,0,0,0)"
                    
                    color_stops.append(quantity_float)
                    color_stops.append(color_rgba)
                except Exception as e:
                    logger.warning(f"Error parsing ColorMapEntry: {e}")
                    continue
        
        # Crear la capa heatmap
        layer = {
            "id": f"{layer_id}_{style.name}_heatmap",
            "type": "heatmap",
            "source": "gvsigol",
            "source-layer": source_layer,
            "paint": {
                "heatmap-opacity": opacity,
                "heatmap-radius": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    0, 20,
                    9, 100,
                    22, 200
                ],
                "heatmap-intensity": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],
                    0, 1,
                    9, 3
                ],
                "heatmap-weight": 1.0
            }
        }
        
        # Añadir color stops si se encontraron
        if len(color_stops) > 0:
            # Ordenar por quantity para asegurar orden correcto
            # Los color_stops están en formato: [quantity1, color1, quantity2, color2, ...]
            # Agrupar en pares y ordenar
            pairs = [(color_stops[i], color_stops[i+1]) for i in range(0, len(color_stops), 2)]
            pairs.sort(key=lambda x: x[0])  # Ordenar por quantity
            color_stops = [item for pair in pairs for item in pair]
            
            # Asegurar que el primer stop es 0 con transparencia si no existe
            if color_stops[0] > 0:
                color_stops.insert(0, "rgba(0,0,0,0)")  # color
                color_stops.insert(0, 0.0)  # quantity
            
            layer["paint"]["heatmap-color"] = [
                "interpolate",
                ["linear"],
                ["heatmap-density"]
            ] + color_stops
        else:
            # Colores por defecto si no se encontró ColorMap
            layer["paint"]["heatmap-color"] = [
                "interpolate",
                ["linear"],
                ["heatmap-density"],
                0, "rgba(0,0,255,0)",
                0.2, "rgba(239,192,192,1)",
                0.4, "rgba(223,146,146,1)",
                0.6, "rgba(208,101,101,1)",
                0.8, "rgba(192,55,55,1)",
                1.0, "rgba(176,10,10,1)"
            ]
        
        return layer
        
    except ET.ParseError as e:
        logger.error(f"Error parsing SLD XML for style {style.id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error creating heatmap from SLD for style {style.id}: {e}")
        return None


def apply_scale_to_layer(mapbox_layer, minscale, maxscale):
    """Aplica restricciones de escala a una capa Mapbox."""
    # Mapbox usa zoom levels (0-22), SLD usa denominadores de escala
    # Conversión aproximada: zoom = log2(559082264 / scale)
    
    if minscale and minscale > 0:
        try:
            max_zoom = int(round(19 - (minscale / 50000000 * 19)))
            max_zoom = max(0, min(22, max_zoom))
            mapbox_layer["maxzoom"] = max_zoom
        except:
            pass
    
    if maxscale and maxscale > 0:
        try:
            min_zoom = int(round(19 - (maxscale / 50000000 * 19)))
            min_zoom = max(0, min(22, min_zoom))
            mapbox_layer["minzoom"] = min_zoom
        except:
            pass
    
    return mapbox_layer


def convert_raster_symbolizer(symbolizer, layer_id, rule_name, source_layer):
    """
    Convierte RasterSymbolizer (usado para Mapas de Calor) a capa Mapbox GL (heatmap).
    
    Args:
        symbolizer: RasterSymbolizer con ColorMap
        layer_id: ID de la capa
        rule_name: Nombre de la regla
        source_layer: Nombre del source-layer
    
    Returns:
        dict: Capa Mapbox GL de tipo heatmap
    """
    layer = {
        "id": f"{layer_id}_{rule_name}_heatmap",
        "type": "heatmap",
        "source": "gvsigol",
        "source-layer": source_layer,
        "paint": {}
    }
    
    # Opacidad
    opacity = symbolizer.opacity if symbolizer.opacity is not None else 0.6
    layer["paint"]["heatmap-opacity"] = opacity
    
    # Radio del heatmap (por defecto, se puede ajustar según zoom)
    # En el SLD ejemplo, radiusPixels es 100 por defecto
    # Mapbox usa heatmap-radius que puede variar con el zoom
    layer["paint"]["heatmap-radius"] = [
        "interpolate",
        ["linear"],
        ["zoom"],
        0, 20,
        9, 100,
        22, 200
    ]
    
    # Intensidad del heatmap
    layer["paint"]["heatmap-intensity"] = [
        "interpolate",
        ["linear"],
        ["zoom"],
        0, 1,
        9, 3
    ]
    
    # Peso del heatmap (si hay un campo weight, se usa; si no, todos los puntos tienen peso 1)
    # En el SLD ejemplo, weightAttr es "ogc_fid", pero en Mapbox usamos un campo numérico
    layer["paint"]["heatmap-weight"] = 1.0
    
    # Color del heatmap basado en ColorMap
    if symbolizer.color_map:
        color_map_entries = ColorMapEntry.objects.filter(
            color_map=symbolizer.color_map
        ).order_by('order', 'quantity')
        
        if color_map_entries.exists():
            # Construir la expresión de interpolación de color
            color_stops = []
            
            for entry in color_map_entries:
                # Normalizar quantity a rango 0-1 (heatmap-density va de 0 a 1)
                # Si el quantity máximo es 1.0, usamos directamente
                # Si no, normalizamos
                quantity = float(entry.quantity)
                
                # Obtener opacidad (si la entrada tiene opacity específica, usarla; si no, usar 1.0)
                entry_opacity = entry.opacity if entry.opacity is not None else 1.0
                
                # Convertir color hex a rgba
                # Si entry.opacity es 0 o None y el label es "nodata", usar transparencia total
                if entry.label and "nodata" in entry.label.lower():
                    color = "rgba(0,0,0,0)"
                else:
                    color = hex_to_rgba(entry.color, entry_opacity)
                    
                    # Si el color es rgba, usarlo directamente; si es hex, convertirlo
                    if color and not color.startswith('rgba'):
                        # Convertir hex a rgba
                        hex_color = color.lstrip('#')
                        if len(hex_color) == 6:
                            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                            color = f"rgba({r}, {g}, {b}, {entry_opacity})"
                
                # Añadir quantity y color al array (formato: [q1, c1, q2, c2, ...])
                color_stops.append(quantity)
                color_stops.append(color)
            
            if len(color_stops) > 0:
                # Asegurar que el primer stop es 0 con transparencia si no existe
                # Los color_stops están en formato: [quantity1, color1, quantity2, color2, ...]
                # Si el primer quantity no es 0, añadir un stop transparente en 0
                if color_stops[0] > 0:
                    color_stops.insert(0, "rgba(0,0,0,0)")  # color
                    color_stops.insert(0, 0.0)  # quantity
                
                layer["paint"]["heatmap-color"] = [
                    "interpolate",
                    ["linear"],
                    ["heatmap-density"]
                ] + color_stops
            else:
                # Si no hay color_map, usar colores por defecto para heatmap
                layer["paint"]["heatmap-color"] = [
                    "interpolate",
                    ["linear"],
                    ["heatmap-density"],
                    0, "rgba(0,0,255,0)",
                    0.2, "rgba(239,192,192,1)",
                    0.4, "rgba(223,146,146,1)",
                    0.6, "rgba(208,101,101,1)",
                    0.8, "rgba(192,55,55,1)",
                    1.0, "rgba(176,10,10,1)"
                ]
    
    return layer


def convert_style_to_mapbox(layer_id, style_id=None, tms_base_url=None, style_obj=None, layer_obj=None):
    """
    Convierte el estilo de una capa de gvSIG Online a formato Mapbox GL Style JSON.
    
    Args:
        layer_id: ID de la capa
        style_id: ID del estilo específico (opcional, si no se pasa usa el default)
        tms_base_url: URL base del servicio TMS (opcional)
        style_obj: Objeto Style (opcional, para evitar consultas adicionales)
        layer_obj: Objeto Layer (opcional, para evitar consultas adicionales)
    
    Returns:
        dict: Estilo Mapbox GL completo
    """
    if layer_obj:
        layer = layer_obj
    else:
        try:
            layer = Layer.objects.get(id=layer_id)
        except Layer.DoesNotExist:
            raise ValueError(f"Layer with id {layer_id} not found")
    
    # Obtener el estilo
    if style_obj:
        style = style_obj
    elif style_id:
        style_layer = StyleLayer.objects.filter(layer=layer, style_id=style_id).first()
        if not style_layer:
            raise ValueError(f"Style {style_id} not found for layer {layer_id}")
        style = style_layer.style
    else:
        style_layer = StyleLayer.objects.filter(layer=layer, style__is_default=True).first()
        if not style_layer:
            style_layer = StyleLayer.objects.filter(layer=layer).first()
        if not style_layer:
            raise ValueError(f"No style found for layer {layer_id}")
        style = style_layer.style
    
    # Construir source-layer (workspace:layername)
    workspace_name = layer.datastore.workspace.name if layer.datastore and layer.datastore.workspace else ""
    source_layer = f"{workspace_name}:{layer.name}" if workspace_name else layer.name
    
    # Construir URL de tiles
    if tms_base_url:
        tiles_url = f"{tms_base_url}/{source_layer}@EPSG:900913@pbf/{{z}}/{{x}}/{{y}}.pbf"
    else:
        tiles_url = f"/geoserver/gwc/service/tms/1.0.0/{source_layer}@EPSG:900913@pbf/{{z}}/{{x}}/{{y}}.pbf"
    
    # Estructura base del estilo Mapbox
    mapbox_style = {
        "version": 8,
        "name": style.title or style.name,
        "sources": {
            "gvsigol": {
                "type": "vector",
                "tiles": [tiles_url],
                "minzoom": 0,
                "maxzoom": 22
            }
        },
        "layers": []
    }
    
    # Detectar si es un Mapa de Calor (HeatMap)
    # Los estilos tipo "MC" guardan el SLD directamente, no tienen Rule/RasterSymbolizer en BD
    if style.type == 'MC' or (style.sld and 'vec:Heatmap' in style.sld):
        # Es un Mapa de Calor, crear la capa heatmap
        heatmap_layer = create_heatmap_from_sld(style, layer_id, source_layer)
        if heatmap_layer:
            mapbox_style["layers"].append(heatmap_layer)
        return mapbox_style
    
    # Obtener reglas del estilo
    rules = Rule.objects.filter(style=style).order_by('order')
    
    # Si no hay reglas pero el estilo tiene SLD personalizado (tipo "CS" u otro),
    # intentar parsear el SLD directamente
    if not rules.exists():
        if style.sld:
            if style.type == 'CS':
                logger.info(f"Style {style.id} is type CS (Custom SLD) - attempting to parse SLD")
                # Intentar parsear el SLD personalizado
                parsed_layers = parse_sld_to_mapbox(style, layer_id, source_layer)
                if parsed_layers:
                    mapbox_style["layers"].extend(parsed_layers)
                    return mapbox_style
                else:
                    # Si falla el parsing, devolver con metadata
                    logger.warning(f"Failed to parse Custom SLD for style {style.id}")
                    mapbox_style["metadata"] = {
                        "gvsigol:warning": "Custom SLD style - parsing failed",
                        "gvsigol:style_type": style.type,
                        "gvsigol:has_sld": True
                    }
                    return mapbox_style
            else:
                # Otro tipo de estilo sin reglas
                logger.warning(f"Style {style.id} has no rules and type is {style.type}")
        return mapbox_style
    
    for rule in rules:
        rule_name = rule.name.replace(' ', '_').replace(':', '_')
        
        # Obtener filtro
        logger.debug(f"Rule '{rule.name}' filter value: '{rule.filter}'")
        mapbox_filter = convert_filter_to_mapbox(rule.filter)
        logger.debug(f"Rule '{rule.name}' mapbox_filter: {mapbox_filter}")
        
        # Obtener symbolizers
        mark_symbolizers = MarkSymbolizer.objects.filter(rule=rule)
        line_symbolizers = LineSymbolizer.objects.filter(rule=rule)
        polygon_symbolizers = PolygonSymbolizer.objects.filter(rule=rule)
        text_symbolizers = TextSymbolizer.objects.filter(rule=rule)
        external_graphic_symbolizers = ExternalGraphicSymbolizer.objects.filter(rule=rule)
        raster_symbolizers = RasterSymbolizer.objects.filter(rule=rule)
        
        # Si hay RasterSymbolizer, es un Mapa de Calor (HeatMap)
        # Los Mapas de Calor tienen prioridad sobre otros symbolizers
        if raster_symbolizers.exists():
            for sym in raster_symbolizers:
                lyr = convert_raster_symbolizer(sym, layer_id, rule_name, source_layer)
                if mapbox_filter:
                    lyr["filter"] = mapbox_filter
                lyr = apply_scale_to_layer(lyr, rule.minscale, rule.maxscale)
                mapbox_style["layers"].append(lyr)
            # Si es un heatmap, no procesamos los otros symbolizers
            continue
        
        # Convertir cada tipo de symbolizer (solo si no es heatmap)
        for sym in polygon_symbolizers:
            layers = convert_polygon_symbolizer(sym, layer_id, rule_name, source_layer)
            for lyr in layers:
                if mapbox_filter:
                    lyr["filter"] = mapbox_filter
                lyr = apply_scale_to_layer(lyr, rule.minscale, rule.maxscale)
                mapbox_style["layers"].append(lyr)
        
        for sym in line_symbolizers:
            lyr = convert_line_symbolizer(sym, layer_id, rule_name, source_layer)
            if mapbox_filter:
                lyr["filter"] = mapbox_filter
            lyr = apply_scale_to_layer(lyr, rule.minscale, rule.maxscale)
            mapbox_style["layers"].append(lyr)
        
        for sym in mark_symbolizers:
            lyr = convert_mark_symbolizer(sym, layer_id, rule_name, source_layer)
            if mapbox_filter:
                lyr["filter"] = mapbox_filter
            lyr = apply_scale_to_layer(lyr, rule.minscale, rule.maxscale)
            mapbox_style["layers"].append(lyr)
        
        for sym in external_graphic_symbolizers:
            lyr = convert_external_graphic_symbolizer(sym, layer_id, rule_name, source_layer)
            if lyr:
                if mapbox_filter:
                    lyr["filter"] = mapbox_filter
                lyr = apply_scale_to_layer(lyr, rule.minscale, rule.maxscale)
                mapbox_style["layers"].append(lyr)
        
        for sym in text_symbolizers:
            lyr = convert_text_symbolizer(sym, layer_id, rule_name, source_layer)
            if lyr:
                if mapbox_filter:
                    lyr["filter"] = mapbox_filter
                lyr = apply_scale_to_layer(lyr, rule.minscale, rule.maxscale)
                mapbox_style["layers"].append(lyr)
    
    return mapbox_style


def get_all_styles_for_layer(layer_id, tms_base_url=None):
    """
    Obtiene todos los estilos de una capa y los convierte a formato Mapbox GL.
    
    Args:
        layer_id: ID de la capa
        tms_base_url: URL base del servicio TMS (opcional)
    
    Returns:
        dict: {
            "layer_id": int,
            "layer_name": str,
            "workspace": str,
            "styles": [
                {
                    "style_id": int,
                    "style_name": str,
                    "style_title": str,
                    "is_default": bool,
                    "mapbox_style": dict
                },
                ...
            ]
        }
    """
    try:
        layer = Layer.objects.get(id=layer_id)
    except Layer.DoesNotExist:
        raise ValueError(f"Layer with id {layer_id} not found")
    
    # Obtener todos los StyleLayer asociados a esta capa
    # Ordenar para que el estilo por defecto (is_default=True) aparezca primero
    style_layers = StyleLayer.objects.filter(layer=layer).select_related('style').order_by('-style__is_default', 'style__name')
    
    if not style_layers.exists():
        raise ValueError(f"No styles found for layer {layer_id}")
    
    workspace_name = layer.datastore.workspace.name if layer.datastore and layer.datastore.workspace else ""
    
    result = {
        "layer_id": layer_id,
        "layer_name": layer.name,
        "workspace": workspace_name,
        "styles": []
    }
    
    for style_layer in style_layers:
        style = style_layer.style
        
        # Excluir estilos temporales
        if style.name.endswith('__tmp'):
            continue
        
        try:
            mapbox_style = convert_style_to_mapbox(
                layer_id=layer_id,
                style_obj=style,
                layer_obj=layer,
                tms_base_url=tms_base_url
            )
            
            result["styles"].append({
                "style_id": style.id,
                "style_name": style.name,
                "style_title": style.title or style.name,
                "is_default": style.is_default,
                "style_type": style.type,
                "mapbox_style": mapbox_style
            })
        except Exception as e:
            logger.warning(f"Error converting style {style.id} for layer {layer_id}: {e}")
            # Incluir el estilo aunque falle la conversión, con error
            result["styles"].append({
                "style_id": style.id,
                "style_name": style.name,
                "style_title": style.title or style.name,
                "is_default": style.is_default,
                "style_type": style.type,
                "mapbox_style": None,
                "error": str(e)
            })
    
    return result

