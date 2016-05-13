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
from sld_tools import get_sld_style, get_style_from_library_symbol
import backend_symbology
import os.path
import gvsigol.settings
from django.views.decorators.http import require_http_methods
from gvsigol_auth.utils import admin_required
import utils

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
    backend_symbology.delete_library_dir(lib)
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
                title = json_rule.get('title'),
                type = symbol_type
            )
            rule.save()
            if json_rule.get('filter') != "":
                rule.filter = json_rule.get('filter')
            rule.save()
            
            library = Library.objects.get(id=int(library_id))
            
            for sym in json_rule.get('symbolizers'):
                sld = sym.get('sld')
                json_sym = sym.get('json')
                if symbol_type == 'ExternalGraphicSymbolizer':
                    library_path = backend_symbology.check_library_path(library)
                    file_name = json_rule.get('name') + '.png'
                    if backend_symbology.save_external_graphic(library_path, request.FILES['eg-file'], file_name):
                        online_resource = backend_symbology.get_online_resource(library, file_name)
                        sld = sld.replace("online_resource_replace", online_resource)
                        json_sym = json_sym.replace("online_resource_replace", online_resource)
                        
                symbolizer = Symbolizer(
                    rule = rule,
                    type = symbol_type,
                    sld = sld,
                    json = json_sym,
                    order = int(sym.get('order'))
                )
                symbolizer.save()
            
            library_rule = LibraryRule(
                library = library,
                rule = rule
            )
            library_rule.save()
            
            style = Style(
                name = rule.name,
                title = rule.name,
                is_default = False,
                type = "US"
            )
            style.save()
            
            style_rule = StyleRule(
                style = style,
                rule = rule
            )
            style_rule.save()
            
            sld_body = get_style_from_library_symbol(style.id, request.session)
            if not mapservice_backend.createStyle(style.name, sld_body, request.session): 
                return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')

            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
 
    else:          
        response = {
            'library_id': library_id,
            'symbol_type': symbol_type
        }
        if symbol_type == 'ExternalGraphicSymbolizer':
            return render_to_response('external_graphic_add.html', response, context_instance=RequestContext(request))
        
        else:
            return render_to_response('symbol_add.html', response, context_instance=RequestContext(request))
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def symbol_update(request, symbol_id):
    if request.method == 'POST':
        data = request.POST['rule']
        json_rule = json.loads(data)     
                
        try:
            rule = Rule.objects.get(id=int(symbol_id))
            #rule.name = json_rule.get('name')
            rule.title = json_rule.get('title')
            rule.save()
            if json_rule.get('filter') != "":
                rule.filter = json_rule.get('filter')
            rule.save()
            library_rule = LibraryRule.objects.get(rule=rule)
            
            for s in Symbolizer.objects.filter(rule=rule):
                if s.type == 'ExternalGraphicSymbolizer':
                    file_name = rule.name + '.png'
                    backend_symbology.delete_external_graphic_img(library_rule.library, file_name)
                s.delete()
                
            for sym in json_rule.get('symbolizers'):
                
                sld = sym.get('sld')
                json_sym = sym.get('json')
                if rule.type == 'ExternalGraphicSymbolizer':
                    library_path = backend_symbology.check_library_path(library_rule.library)
                    file_name = json_rule.get('name') + '.png'
                    if backend_symbology.save_external_graphic(library_path, request.FILES['eg-file'], file_name):
                        online_resource = backend_symbology.get_online_resource(library_rule.library, file_name)
                        sld = sld.replace('online_resource_replace', online_resource)
                        sld = json_sym.replace('online_resource_replace', online_resource)
                        
                symbolizer = Symbolizer(
                    rule = rule,
                    type = sym.get('type'),
                    sld = sld,
                    json = json_sym,
                    order = int(sym.get('order'))
                )
                symbolizer.save()
            
            style_rule = StyleRule.objects.get(rule=rule)
            style = Style.objects.get(id=style_rule.style.id)
            if mapservice_backend.deleteStyle(style.name, request.session): 
                sld_body = get_style_from_library_symbol(style.id, request.session)
                if not mapservice_backend.createStyle(style.name, sld_body, request.session): 
                    return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')

            return HttpResponse(json.dumps({'library_id': library_rule.library.id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
        
    else:
        r = Rule.objects.get(id=int(symbol_id))
        if r.type == 'ExternalGraphicSymbolizer':       
            symbolizer = Symbolizer.objects.filter(rule=r)[0]
            rule = {
                'id': r.id,
                'name': r.name,
                'title': r.title,
                'minscale': r.minscale,
                'maxscale': r.maxscale,
                'type': r.type,
                'symbolizer_format': json.loads(symbolizer.json).get('format'),
                'symbolizer_online_resource': json.loads(symbolizer.json).get('online_resource'),
            }
            response = {
                'rule': rule
            }
            return render_to_response('external_graphic_update.html', response, context_instance=RequestContext(request))
        else:
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
                if symbolizer.type == 'ExternalGraphicSymbolizer':
                    file_name = rule.name + '.png'
                    backend_symbology.delete_external_graphic_img(library_rule.library, file_name)
                symbolizer.delete()
            library_rule.delete()
            
            style_rule = StyleRule.objects.get(rule=rule)
            style = Style.objects.get(id=style_rule.style.id)
            if mapservice_backend.deleteStyle(style.name, request.session):            
                style.delete()
                style_rule.delete()
                
            rule.delete()


            return HttpResponse(json.dumps({'library_id': library_id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')