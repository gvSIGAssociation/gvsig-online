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
def new_style_options(request, layer_id):
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
        
    return render_to_response('new_style_options.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def unique_symbol(request, layer_id):
        
    response = {}
        
    return render_to_response('unique_symbol.html', response, context_instance=RequestContext(request))


