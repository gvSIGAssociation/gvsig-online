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

from gvsigol_symbology.models import (
    Style, StyleLayer, Rule, 
    MarkSymbolizer, LineSymbolizer, PolygonSymbolizer, 
    TextSymbolizer, ExternalGraphicSymbolizer, RasterSymbolizer
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
    
    # Obtener reglas del estilo
    rules = Rule.objects.filter(style=style).order_by('order')
    
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
        
        # Convertir cada tipo de symbolizer
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

