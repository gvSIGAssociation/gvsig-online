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
from gvsigol_services.backend_mapservice import backend as mapservice
from gvsigol_services.models import Workspace, Datastore, Layer
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from models import Style, StyleLayer, Rule, Library, LibraryRule, Symbolizer
from gvsigol_auth.utils import admin_required
from gvsigol import settings
from gvsigol_symbology import services, services_library, services_unique_symbol,\
    services_unique_values
import utils
import json
import ast
  
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
    
    elif (style.type == 'UV'):
        return redirect('unique_values_update', layer_id=layer_id, style_id=style_id)
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def style_layer_delete(request):
    if request.method == 'POST':
        style_id = request.POST.get('style_id')
        layer_id = request.POST.get('layer_id')
        
        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
        layer_styles = StyleLayer.objects.filter(layer=layer)
        
        message = ''
        success = False
        if len(layer_styles) <= 1:
            message = _('The layer must contain at least one style')
        else:
            if (style.is_default):
                message = _('Can not delete a default style')
            else:
                try:
                    services_unique_symbol.delete_style(request.session, style_id)
                    success = True
                    
                except Exception as e:
                    message = e.message
                    pass
                
            
        return HttpResponse(json.dumps({'success': success, 'message': message}, indent=4), content_type='application/json')

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
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        if services_unique_symbol.create_style(request.session, json_data, layer_id):            
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                 
        response = services_unique_symbol.get_conf(request.session, layer_id)     
        return render_to_response('unique_symbol_add.html', response, context_instance=RequestContext(request))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def unique_symbol_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        if services_unique_symbol.update_style(request.session, json_data, layer_id, style_id):            
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:
        style = Style.objects.get(id=int(style_id))
        
        r = Rule.objects.get(style=style)
        symbolizers = []
        for s in Symbolizer.objects.filter(rule=r).order_by('order'):
            symbolizers.append(utils.symbolizer_to_json(s))
            
        rule = {
            'id': r.id,
            'name': r.name,
            'title': r.title,
            'abstract': '',
            'filter': '',
            'minscale': r.minscale,
            'maxscale': r.maxscale,
            'order': r.order,
            'symbolizers': symbolizers
        }
                         
        response = services_unique_symbol.get_conf(request.session, layer_id)
        
        response['style'] = style
        response['minscale'] = int(r.minscale)
        response['maxscale'] = int(r.maxscale)
        response['rule'] = json.dumps(rule)        
        
        return render_to_response('unique_symbol_update.html', response, context_instance=RequestContext(request))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def unique_values_add(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        if services_unique_values.create_style(request.session, json_data, layer_id):            
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                 
        response = services_unique_values.get_conf(request.session, layer_id) 
        return render_to_response('unique_values_add.html', response, context_instance=RequestContext(request))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def unique_values_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        if services_unique_values.update_style(request.session, json_data, layer_id, style_id):            
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                
        style = Style.objects.get(id=int(style_id))
        
        style_rules = Rule.objects.filter(style=style)
        rules = []
        for r in style_rules:
            symbolizers = []
            for s in Symbolizer.objects.filter(rule=r).order_by('order'):
                symbolizers.append(utils.symbolizer_to_json(s))
                
            rule = {
                'id': r.id,
                'name': r.name,
                'title': r.title,
                'abstract': '',
                'filter': r.filter,
                'minscale': r.minscale,
                'maxscale': r.maxscale,
                'order': r.order,
                'symbolizers': symbolizers
            }
            rules.append(rule)
                         
        response = services_unique_values.get_conf(request.session, layer_id)
        
        response['style'] = style
        response['minscale'] = int(r.minscale)
        response['maxscale'] = int(r.maxscale)
        response['rules'] = json.dumps(rules)        
        
        return render_to_response('unique_values_update.html', response, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def get_unique_values(request):
    if request.method == 'POST':
        layer_id = request.POST.get('layer_id')
        field = request.POST.get('field')
        
        layer = Layer.objects.get(id=layer_id)
        connection = ast.literal_eval(layer.datastore.connection_params)
        
        unique_fields = utils.get_distinct_query(connection, layer.name, field)
    
        return HttpResponse(json.dumps({'values': unique_fields}, indent=4), content_type='application/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def sld_import(request, layer_id):
    if request.method == 'POST': 
        name = request.POST.get('sld-name')
        
        message = ''
        if name != '' and 'sld-file' in request.FILES: 
            #TODO
                             
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
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_list(request):
    response = {
        'libraries': Library.objects.all()
    }
    return render_to_response('library_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_add(request, library_id):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')        

        if name != '':
            library = Library(
                name = name,
                description = description
            )
            library.save()         
            return redirect('library_list')
        
        else:
            message = _('You must enter a name for the library')
            return render_to_response('library_add.html', {'message': message}, context_instance=RequestContext(request))
    
    else:   
        return render_to_response('library_add.html', {}, context_instance=RequestContext(request))

    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_update(request, library_id):      
    if request.method == 'POST': 
        lib_description = request.POST.get('library-description')

        library = Library.objects.get(id=int(library_id))
        library.description = lib_description
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
                symbolizers.append(utils.symbolizer_to_json(s))
                
            rule = {
                'id': r.id,
                'name': r.name,
                'title': r.title,
                'minscale': -1,
                'maxscale': -1,
                'order': r.order,
                'symbolizers': json.dumps(symbolizers)
            }
            rules.append(rule)
            
        response = {
            'library': library,
            'rules': rules,
            'preview_point_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point',
            'preview_line_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line',
            'preview_polygon_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
        }
        return render_to_response('library_update.html', response, context_instance=RequestContext(request))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_import(request):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')
        message = ''
        
        try:            
            if name != '' and 'library-file' in request.FILES: 
                services_library.upload_library(name, description, request.FILES['library-file'], request.session)                
                return redirect('library_list')
            
            elif name == '' and 'library-file' in request.FILES:
                message = _('You must enter a name for the library')
                
            elif name != '' and not 'library-file' in request.FILES:
                message = _('You must select a file')
                
            elif name == '' and not 'library-file' in request.FILES:
                message = _('You must enter a name for the library and select a file')
                
            return render_to_response('library_import.html', {'message': message}, context_instance=RequestContext(request))
        
        except Exception as e:
            message = e.message
            return render_to_response('library_import.html', {'message': message}, context_instance=RequestContext(request))
    
    else:   
        return render_to_response('library_import.html', {}, context_instance=RequestContext(request))
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_export(request, library_id):
    library = Library.objects.get(id=library_id)
    library_rules = LibraryRule.objects.filter(library_id=library.id)
    
    try:
        response = services_library.export_library(library, library_rules)
        return response
        
    except Exception as e:
        message = e.message
        return HttpResponse(json.dumps({'message':message}, indent=4), content_type='application/json')
    
    
    
    
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
                symbolizers.append(utils.symbolizer_to_json(s))
                
            rule = {
                'id': r.id,
                'name': r.name,
                'title': r.title,
                'abstract': '',
                'filter': '',
                'minscale': -1,
                'maxscale': -1,
                'order': 0,
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
        
        rule.style.delete()
        rule.delete()
        lib_rule.delete()

    lib = Library.objects.get(id=library_id)
    utils.delete_library_dir(lib)
    lib.delete()
    return redirect('library_list')


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def symbol_add(request, library_id, symbol_type):
    if request.method == 'POST':
        data = request.POST['rule']
        json_rule = json.loads(data)     
    
        try:            
            if services_library.add_symbol(request, json_rule, library_id, symbol_type):
                return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            else:
                return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
 
    else:          
        response = {
            'library_id': library_id,
            'symbol_type': symbol_type,
            'preview_point_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point',
            'preview_line_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line',
            'preview_polygon_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
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
        
        rule = Rule.objects.get(id=int(symbol_id))
        library_rule = LibraryRule.objects.get(rule=rule)
        
        try:
            if services_library.update_symbol(request, json_rule, rule, library_rule):
                return HttpResponse(json.dumps({'library_id': library_rule.library.id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
        
    else:
        r = Rule.objects.get(id=int(symbol_id))
        s = Symbolizer.objects.filter(rule=r)[0]
        ftype = services_library.get_ftype(s)
            
        if ftype == 'ExternalGraphicSymbolizer':       
            response = {
                'rule': services_library.get_symbol(r, ftype)
            }
            return render_to_response('external_graphic_update.html', response, context_instance=RequestContext(request))
        
        else:
            response = {
                'rule': services_library.get_symbol(r, ftype),
                'preview_point_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point',
                'preview_line_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line',
                'preview_polygon_url': settings.GVSIGOL_SERVICES['URL'] + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
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
            services_library.delete_symbol(request.session, rule, library_rule)
            return HttpResponse(json.dumps({'library_id': library_id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = e.message
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')