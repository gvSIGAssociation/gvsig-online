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
            rule.save()
            
            for sym in json_rule.get('symbolizers'):
                symbolizer = Symbolizer(
                    rule = rule,
                    type = symbol_type,
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
        response = {
            'library_id': library_id,
            'symbol_type': symbol_type
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