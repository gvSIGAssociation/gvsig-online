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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import render_to_response, RequestContext, redirect, HttpResponse
from django.core import serializers
from django.db.models import Max, Q
from django.contrib.auth.decorators import login_required
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_services.backend_mapservice import backend as mapservice_backend
from django.utils.translation import ugettext as _  
from django.views.decorators.csrf import csrf_exempt
import xml.etree.ElementTree as ET
import json, ast
from models import LayerStyle, RuleSymbol, Style, Rule, Symbol, Library, LibrarySymbol
from utils import get_distinct_query, get_minmax_query, sortFontsArray
from django_ajax.decorators import ajax
from sld_tools import get_sld_style, get_sld_filter_operations
from backend_symbology import get_layer_field_description, get_raster_layer_description, uploadLibrary, exportLibrary
import os.path
import gvsigol.settings
from django.views.decorators.http import require_http_methods
from gvsigol_auth.utils import admin_required
import utils

  
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def style_layer_list(request):
    ls = []
    layers = Layer.objects.all()
    
    for lyr in layers:
        layerStyles = LayerStyle.objects.filter(layer=lyr).order_by('order')
        styles = []
        for layerStyle in layerStyles:
            styles.append(layerStyle.style)
    
        ls.append({'layer': lyr, 'styles': styles})
    
    response = {
        'layerStyles': ls
    }
    return render_to_response('layer_symbology_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def select_legend_type(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    
    is_vectorial = False
    if layer.type == 'v_PostGIS':
        is_vectorial = True
        
    is_view = False
    if layer.type == 'v_PostGIS_View':
        is_view = True
        
    response = {
        'layer': layer,
        'is_vectorial': is_vectorial,
        'is_view': is_view
    }
        
    return render_to_response('select_legend_type.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def unique_symbol_add(request, layer_id):
    
    resource = get_layer_field_description(layer_id, request.session)
    if resource != None:
        fields = resource.get('featureType').get('attributes').get('attribute')
    
    featureType = "PointSymbolizer"
    for field in fields:
        if field.get('binding').startswith('com.vividsolutions.jts.geom'):
            auxType = field.get('binding').replace('com.vividsolutions.jts.geom.', '')
            if auxType == "Point" or auxType == "MultiPoint":
                featureType = "PointSymbolizer"
            if auxType == "Line" or auxType == "MultiLineString":
                featureType = "LineSymbolizer"
            if auxType == "Polygon" or auxType == "MultiPolygon":
                featureType = "PolygonSymbolizer"
    
    sldFilterValues = get_sld_filter_operations()
    for category in sldFilterValues:
        for oper in sldFilterValues[category]:
            sldFilterValues[category][oper]["genCodeFunc"] = ""
            
    supportedfontsStr = mapservice_backend.getSupportedFonts(request.session)
    supportedfonts = json.loads(supportedfontsStr)
    sorted_fonts = sortFontsArray(supportedfonts.get("fonts"))
    
    alphanumeric_fields = []
    for field in fields:
        if not field.get('binding').startswith('com.vividsolutions.jts.geom'):
            alphanumeric_fields.append(field)
                        
    response = {
        'featureType': featureType,
        'fields': json.dumps(fields), 
        'alphanumeric_fields': json.dumps(alphanumeric_fields),
        'sldFilterValues': json.dumps(sldFilterValues),
        'fonts': sorted_fonts,
        'layer_id': layer_id
    }
   
    return render_to_response('unique_symbol_add.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def save_style(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        layer = Layer.objects.get(id=int(layer_id))
        style = Style(
            title = utils.create_style_name(layer),
            name = utils.create_style_name(layer),
            description = "",
            type = json_data.get('type')
        )
        style.save()
        layerStyle = LayerStyle(
            layer = layer,
            style = style
        )
        layerStyle.save()
            
        json_rule = json_data.get('rule')
        rule = Rule(
            name = json_rule.get('name') if json_rule.get('name') != "" else utils.create_style_name(layer),
            order = json_rule.get('order'),
            style = style
        )
        rule.save();
        
        for symbols in json_data.get('symbols'):
            symbol = Symbol(
                name = symbols.get('name'),
                sld_code = symbols.get('sld_code')
            )
            symbol.save()
            RuleSymbol.objects.create(
                rule_id = rule.id, 
                symbol_id = symbol.id
            )
                
        sld_body = get_sld_style(layer_id, style.id, request.session)
        layer = Layer.objects.get(id=layer_id)
        datastore = Datastore.objects.get(id=layer.datastore_id) 
        workspace = Workspace.objects.get(id=datastore.workspace_id)

        if not mapservice_backend.createStyle(style.name, sld_body, request.session): 
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
        layerStyles = LayerStyle.objects.filter(layer=layer).order_by('order')
        if len(layerStyles) > 0 and str(layerStyles[0].style_id) == str(style.id):
            mapservice_backend.setLayerStyle(workspace.name+":"+layer.name, style.name, request.session)
            
        layer.style = style.name
        layer.save()
        
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
