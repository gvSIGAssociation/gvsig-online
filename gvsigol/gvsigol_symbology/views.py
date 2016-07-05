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
from gvsigol_services.backend_mapservice import backend as mapservice_backend
from gvsigol_symbology.sld_utils import get_style_from_library_symbol
from gvsigol_services.models import Workspace, Datastore, Layer
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from models import Style, StyleLayer, StyleRule
from gvsigol_auth.utils import admin_required
from gvsigol_symbology import sld_utils
from gvsigol_symbology import services
import json

  
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
def get_sld_body(request):      
    if request.method == 'POST':  
        
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        sld_body = sld_utils.get_sld_body(json_data)
        
        response = {
            'sld_body': sld_body
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def sld_import(request, layer_id):
    if request.method == 'POST': 
        name = request.POST.get('sld-name')
        
        message = ''
        if name != '' and 'sld-file' in request.FILES: 
            rules = services.upload_sld(request.FILES['sld-file'])
            for rule in rules:               
                
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
                mapservice_backend.createStyle(style.name, sld_body, request.session)
                             
            return redirect('style_layer_list')
        
        elif name == '' and 'sld-file' in request.FILES:
            message = _('You must enter a name for the style')
            
        elif name != '' and not 'sld-file' in request.FILES:
            message = _('You must select a file')
            
        elif name == '' and not 'sld-file' in request.FILES:
            message = _('You must enter a name for the style and select a file')
            
        return render_to_response('sld_import.html', {'message': message}, context_instance=RequestContext(request))
    
    else:   
        layer = Layer.objects.get(id=int(layer_id))
        index = len(StyleLayer.objects.filter(layer=layer))
        
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        
        response = {
            'layer_id': layer_id,
            'style_name': workspace.name + '_' + layer.name + '_' + str(index)
        }
        
        return render_to_response('sld_import.html', response, context_instance=RequestContext(request))