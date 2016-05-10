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
from models import Style, StyleLayer, Rule, Symbolizer, StyleRule, Library, LibraryRule
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
        layerStyles = StyleLayer.objects.filter(layer=lyr)
        styles = []
        for layerStyle in layerStyles:
            styles.append(layerStyle.style)
        ls.append({'layer': lyr, 'styles': styles})
    
    response = {
        'layerStyles': ls
    }
    return render_to_response('style_layer_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def style_layer_update(request, layer_id, style_id):
    style = Style.objects.get(id=int(style_id))
    if (style.type == 'US'):
        return redirect('unique_symbol_update', layer_id=layer_id, style_id=style_id)

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
        'symbolizers': json.dumps(symbolizers)
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
        'rule': rule
        
    }
    return render_to_response('unique_symbol_update.html', response, context_instance=RequestContext(request))


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
        layerStyle = StyleLayer(
            layer = layer,
            style = style
        )
        layerStyle.save()
        
        '''    
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
         '''       
        sld_body = get_sld_style(layer_id, style.id, request.session)
        layer = Layer.objects.get(id=layer_id)
        datastore = Datastore.objects.get(id=layer.datastore_id) 
        workspace = Workspace.objects.get(id=datastore.workspace_id)

        if not mapservice_backend.createStyle(style.name, sld_body, request.session): 
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
        layerStyles = StyleLayer.objects.filter(layer=layer).order_by('order')
        if len(layerStyles) > 0 and str(layerStyles[0].style_id) == str(style.id):
            mapservice_backend.setLayerStyle(workspace.name+":"+layer.name, style.name, request.session)
            
        layer.style = style.name
        layer.save()
        
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_list(request):
    libraries = Library.objects.all()
    response = {
        'libraries': libraries
    }
    return render_to_response('library_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_add(request, library_id):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')
        
        is_public = False
        if 'library-is-public' in request.POST:
            is_public = True

        library = Library(
            name = name,
            description = description,
            is_public = is_public
        )
        library.save()
        
        return redirect('library_list')
    
    else:   
        return render_to_response('library_add.html', {}, context_instance=RequestContext(request))

    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_update(request, library_id):      
    if request.method == 'POST': 
        lib_description = request.POST.get('library-description')
        
        is_public = False
        if 'library-is-public' in request.POST:
            is_public = True

        library = Library.objects.get(id=int(library_id))
        library.description = lib_description
        library.is_public = is_public
        library.save()
        
        return redirect('library_list')
    
    else:   
        library = Library.objects.get(id=int(library_id))
        library_rules = LibraryRule.objects.filter(library_id=library_id)
        rules = []
        for lr in library_rules:
            r = Rule.objects.get(id=lr.rule.id)
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
                'symbolizers': json.dumps(symbolizers)
            }
            rules.append(rule)
        response = {
            'library': library,
            'rules': rules
        }
        return render_to_response('library_update.html', response, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def get_symbols_from_library(request):      
    if request.method == 'POST':  
        library_id = request.POST.get('library_id')
        library_rules = LibraryRule.objects.filter(library_id=int(library_id))
        rules = []
        for lr in library_rules:
            r = Rule.objects.get(id=lr.rule.id)
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
            rules.append(rule)
            
        response = {
            'rules': rules
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_delete(request, library_id):
    library_rules = LibraryRule.objects.filter(library_id=library_id)
    for lib_rule in library_rules:
        rule = Rule.objects.get(id=lib_rule.rule.id)
        symbolizers = Symbolizer.objects.filter(rule_id=rule.id)
        for symbolizer in symbolizers:
            symbolizer.delete()
        rule.delete()
        lib_rule.delete()
    
    lib = Library.objects.get(id=library_id)
    lib.delete()
    return redirect('library_list')


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def symbol_add(request, library_id, symbol_type):
    if request.method == 'POST':
        data = request.POST['rule']
        json_rule = json.loads(data)     
                
        try:
            rule = Rule(
                name = json_rule.get('name'),
                title = json_rule.get('title')
            )
            rule.save()
            if json_rule.get('filter') != "":
                rule.filter = json_rule.get('filter')
            if json_rule.get('minscale') != "":
                rule.minscale = float(json_rule.get('minscale'))
            if json_rule.get('maxscale') != "":
                rule.maxscale = float(json_rule.get('maxscale'))
            rule.save()
            
            for sym in json_rule.get('symbolizers'):
                symbolizer = Symbolizer(
                    rule = rule,
                    type = sym.get('type'),
                    sld = sym.get('sld'),
                    json = sym.get('json'),
                    order = int(sym.get('order'))
                )
                symbolizer.save()
            
            library = Library.objects.get(id=int(library_id))
            library_rule = LibraryRule(
                library = library,
                rule = rule
            )
            library_rule.save()

            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
 
    else:
        stype = 'PointSymbolizer'
        if symbol_type == 'line':
            stype = 'LineSymbolizer'
        elif symbol_type == 'polygon':
            stype = 'PolygonSymbolizer'
            
        response = {
            'library_id': library_id,
            'symbol_type': stype
        }
        return render_to_response('symbol_add.html', response, context_instance=RequestContext(request))
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def symbol_update(request, symbol_id):
    if request.method == 'POST':
        data = request.POST['rule']
        json_rule = json.loads(data)     
                
        try:
            rule = Rule.objects.get(id=int(symbol_id))
            rule.name = json_rule.get('name')
            rule.title = json_rule.get('title')
            rule.save()
            if json_rule.get('filter') != "":
                rule.filter = json_rule.get('filter')
            if json_rule.get('minscale') != "":
                rule.minscale = float(json_rule.get('minscale'))
            if json_rule.get('maxscale') != "":
                rule.maxscale = float(json_rule.get('maxscale'))
            rule.save()
            library_rule = LibraryRule.objects.get(rule=rule)
            
            for s in Symbolizer.objects.filter(rule=rule):
                s.delete()
                
            for sym in json_rule.get('symbolizers'):
                symbolizer = Symbolizer(
                    rule = rule,
                    type = sym.get('type'),
                    sld = sym.get('sld'),
                    json = sym.get('json'),
                    order = int(sym.get('order'))
                )
                symbolizer.save()

            return HttpResponse(json.dumps({'library_id': library_rule.library.id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
        
    else:
        r = Rule.objects.get(id=int(symbol_id))
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
            'symbolizers': json.dumps(symbolizers)
        }
        response = {
            'rule': rule
        }
        return render_to_response('symbol_update.html', response, context_instance=RequestContext(request))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def symbol_delete(request):
    if request.method == 'POST':
        symbol_id = request.POST.get('symbol_id')
                
        try:
            rule = Rule.objects.get(id=int(symbol_id))
            library_rule = LibraryRule.objects.get(rule=rule)
            library_id = library_rule.library.id
            symbolizers = Symbolizer.objects.filter(rule_id=rule.id)
            for symbolizer in symbolizers:
                symbolizer.delete()
            library_rule.delete()
            rule.delete()


            return HttpResponse(json.dumps({'library_id': library_id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')