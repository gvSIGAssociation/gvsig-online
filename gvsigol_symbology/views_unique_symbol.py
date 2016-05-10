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

from django.shortcuts import render_to_response, RequestContext, HttpResponse
from django.contrib.auth.decorators import login_required
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_services.backend_mapservice import backend as mapservice_backend
from models import Style, StyleLayer, Rule, Symbolizer, StyleRule, Library
from sld_tools import get_sld_style, get_sld_filter_operations
from backend_symbology import get_layer_field_description
from django.utils.translation import ugettext as _
from gvsigol_auth.utils import admin_required
from utils import sortFontsArray
import utils
import json

  
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
    
    layer = Layer.objects.get(id=int(layer_id))
    index = len(StyleLayer.objects.filter(layer=layer))
                      
    response = {
        'featureType': featureType,
        'fields': json.dumps(fields), 
        'alphanumeric_fields': json.dumps(alphanumeric_fields),
        'sldFilterValues': json.dumps(sldFilterValues),
        'fonts': sorted_fonts,
        'layer_id': layer_id,
        'style_name': layer.name + '_' + str(index),
        'libraries': Library.objects.all()
    }
   
    return render_to_response('unique_symbol_add.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def unique_symbol_update(request, layer_id, style_id):  
    style = Style.objects.get(id=int(style_id))
    
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
            
    style_rule = StyleRule.objects.get(style=style)
    r = Rule.objects.get(id=int(style_rule.rule.id))
    symbolizers = []
    for s in Symbolizer.objects.filter(rule=r).order_by('order'):
        symbolizers.append({
            'type': s.type,
            'json': s.json
        })
    rule = {
        'id': r.id,
        'name': r.name,
        'title': r.title,
        'minscale': r.minscale,
        'maxscale': r.maxscale,
        'order': r.order,
        'type': r.type,
        'symbolizers': symbolizers
    }
                        
    response = {
        'featureType': featureType,
        'fields': json.dumps(fields), 
        'alphanumeric_fields': json.dumps(alphanumeric_fields),
        'sldFilterValues': json.dumps(sldFilterValues),
        'fonts': sorted_fonts,
        'layer_id': layer_id,
        'libraries': Library.objects.all(),
        'style': style,
        'minscale': r.minscale,
        'maxscale': r.maxscale,
        'rule': json.dumps(rule)
        
    }
    return render_to_response('unique_symbol_update.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def unique_symbol_save(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)

        layer = Layer.objects.get(id=int(layer_id))
        style = Style(
            name = json_data.get('name'),
            title = json_data.get('title'),
            is_default = json_data.get('is_default'),
            type = "US"
        )
        style.save()
        styleLayer = StyleLayer(
            layer = layer,
            style = style
        )
        styleLayer.save()
          
        json_rule = json_data.get('rule')
        rule = Rule(
            name = json_rule.get('name'),
            title = json_rule.get('title'),
            type = json_rule.get('type'),
            filter = '',
            minscale = float(json_rule.get('minscale')),
            maxscale = float(json_rule.get('maxscale')),
            order = json_rule.get('order')
        )
        rule.save();
        
        styleRule = StyleRule(
            rule = rule,
            style = style
        )
        styleRule.save()
        
        for sym in json_data.get('symbolizers'):
            symbolizer = Symbolizer(
                rule = rule,
                type = sym.get('type'),
                sld = sym.get('sld'),
                json = sym.get('json'),
                order = sym.get('order'),
            )
            symbolizer.save()
     
        sld_body = get_sld_style(layer_id, style.id, request.session)
        datastore = Datastore.objects.get(id=layer.datastore_id) 
        workspace = Workspace.objects.get(id=datastore.workspace_id)

        if not mapservice_backend.createStyle(style.name, sld_body, request.session): 
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
        if style.is_default:
            layer_styles = StyleLayer.objects.filter(layer=layer)
            for ls in layer_styles:
                s = Style.objects.get(id=ls.style.id)
                s.is_default = False
            mapservice_backend.setLayerStyle(workspace.name+":"+layer.name, style.name, request.session)

        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')