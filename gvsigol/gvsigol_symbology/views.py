# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

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

from django.shortcuts import render, redirect, HttpResponse
from django.http import HttpResponseForbidden
from gvsigol_services import geographic_servers
from gvsigol_services.models import Workspace, Datastore, Layer
from gvsigol_services import utils as service_utils
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from .models import Style, StyleLayer, Rule, Library, LibraryRule, Symbolizer, ColorMap, ColorMapEntry, RasterSymbolizer, ColorRamp, ColorRampFolder, ColorRampLibrary
from gvsigol_auth.utils import staff_required
from gvsigol_symbology import services, services_library, services_unique_symbol,\
    services_unique_values, services_intervals, services_expressions, services_color_table, services_clustered_points, services_custom
from django.views.decorators.csrf import csrf_exempt
from . import utils
import json
import ast
from gvsigol_services.backend_postgis import Introspect
import re
import logging
logger = logging.getLogger("gvsigol")

@login_required()
@staff_required
def get_raster_statistics(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    params = json.loads(datastore.connection_params)
    result = None
    if 'url' in params:
        result = utils.get_raster_stats(params['url'])
    if result:
        response = {
            'result': result
            }
    else:
        response = {}
        
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


def delete_preview_style(request, name, gs):
    styles = Style.objects.filter(name=name+'__tmp')
    success = True
    for style in styles:
        try:
            services.delete_style(style.id, gs)
            style.delete()
        except Exception:
            success = False
            pass
        
    return success
  
@login_required()
@staff_required
def style_layer_list(request):
    ls = []
    
    layers = None
    if request.user.is_superuser:
        layers = Layer.objects.filter(external=False)
    else:
        layers = Layer.objects.filter(created_by__exact=request.user.username).filter(external=False)
    
    for lyr in layers:
        layerStyles = StyleLayer.objects.filter(layer=lyr)
        styles = []
        for layerStyle in layerStyles:
            if not layerStyle.style.name.endswith('__tmp'):
                styles.append(layerStyle.style)
        ls.append({'layer': lyr, 'styles': styles})
    
    response = {
        'layerStyles': ls
    }
    return render(request, 'style_layer_list.html', response)

@login_required()
@staff_required
def style_layer_update(request, layer_id, style_id):
    style = Style.objects.get(id=int(style_id))
    
    if (style.type == 'US'):
        return redirect('unique_symbol_update', layer_id=layer_id, style_id=style_id)
    
    elif (style.type == 'UV'):
        return redirect('unique_values_update', layer_id=layer_id, style_id=style_id)
    
    elif (style.type == 'IN'):
        return redirect('intervals_update', layer_id=layer_id, style_id=style_id)
    
    elif (style.type == 'EX'):
        return redirect('expressions_update', layer_id=layer_id, style_id=style_id)
    
    elif (style.type == 'CP'):
        return redirect('clustered_points_update', layer_id=layer_id, style_id=style_id)
    
    elif (style.type == 'CT'):
        return redirect('color_table_update', layer_id=layer_id, style_id=style_id)
    
    elif (style.type == 'CS'):
        return redirect('custom_update', layer_id=layer_id, style_id=style_id)
    
@login_required()
@staff_required
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
                    gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
                    services.delete_style(style_id, gs)
                    success = True
                    gs.reload_nodes()
                except Exception as e:
                    message = str(e)
                    pass
                
            
        return HttpResponse(json.dumps({'success': success, 'message': message}, indent=4), content_type='application/json')

@login_required()
@staff_required
def select_legend_type(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    
    is_vectorial = False
    is_points = False
    if layer.type == 'v_PostGIS':
        is_vectorial = True
        try:
            params = json.loads(layer.datastore.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            rows = i.get_geometry_columns_info(layer.name, schema)
            i.close()
            for r in rows:
                if r[5] == 'MULTIPOINT' or r[5] == 'POINT':
                    is_points = True
        except Exception as e:
            print(str(e))
            raise
        
    is_view = False
    if layer.type == 'v_PostGIS_View':
        is_view = True
        
    response = {
        'layer': layer,
        'is_vectorial': is_vectorial,
        'is_view': is_view,
        'is_points': is_points
    }
        
    return render(request, 'select_legend_type.html', response)

@login_required()
@staff_required
def custom_add(request, layer_id):
    if request.method == 'POST':
        style_name = request.POST.get('style_name')
        style_title = request.POST.get('style_title')
        sld = request.POST.get('sld')
        
        is_default = request.POST.get('is_default') == 'true'
        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        server = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_custom.create_style(style_name, style_title, is_default, sld, layer, server)
        if style:
            delete_preview_style(request, style_name, server)
            server.reload_nodes()
            if style.is_default:
                server.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                 
        response = services_custom.get_conf(request, layer_id)     
        return render(request, 'custom_add.html', response)
    
@login_required()
@staff_required
def custom_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_name = request.POST.get('style_name')
        style_title = request.POST.get('style_title')
        sld = request.POST.get('sld')
            
        is_default = request.POST.get('is_default') == 'true'
        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_custom.update_style(style_title, is_default, sld, layer, gs, style)
        if style:
            delete_preview_style(request, style_name, gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:
        style = Style.objects.get(id=int(style_id))
                         
        response = services_custom.get_conf(request, layer_id)
        response['style'] = style  
         
        return render(request, 'custom_update.html', response)

@login_required()
@staff_required
def unique_symbol_add(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_unique_symbol.create_style(request, json_data, layer, gs)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                 
        response = services_unique_symbol.get_conf(request, layer_id)     
        return render(request, 'unique_symbol_add.html', response)
    
@login_required()
@staff_required
def unique_symbol_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)

        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        style = services_unique_symbol.update_style(request, json_data, layer, gs, style)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:
        style = Style.objects.get(id=int(style_id))
        
        style_rules = Rule.objects.filter(style=style)
        rules = []
        rule = None
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
                         
        response = services_unique_symbol.get_conf(request, layer_id)
        
        response['style'] = style
        if style.minscale and int(style.minscale) >=0:
            response['minscale'] = int(style.minscale)
        if style.maxscale and int(style.maxscale) >=0:
            response['maxscale'] = int(style.maxscale)
        response['rules'] = json.dumps(rules)   
        for r in rules:
            if r and r['filter']:
                if r['filter'] != '':
                    rule_filter = json.loads(r['filter'])
                    if 'field' in rule_filter:
                        response['property_name'] = rule_filter.get('field')    
                        
                    # Adaptación para garantizar compatibilidad con versiones anteriores
                    if 'property_name' in rule_filter:
                        response['property_name'] = rule_filter.get('property_name')   
         
        
        return render(request, 'unique_symbol_update.html', response)
    
    
@login_required()
@staff_required
def unique_values_add(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_unique_values.create_style(request, json_data, layer, gs)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:             
        response = services_unique_values.get_conf(request, layer_id) 
        color_ramps = ColorRampLibrary.objects.all()        
        response["ramp_libraries"] = color_ramps
        
        return render(request, 'unique_values_add.html', response)
    
@login_required()
@staff_required
def unique_values_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_unique_values.update_style(request, json_data, layer, gs, style)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
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
                         
        response = services_unique_values.get_conf(request, layer_id)
        
        response['style'] = style
        if style.minscale and int(style.minscale) >=0:
            response['minscale'] = int(style.minscale)
        if style.maxscale and int(style.maxscale) >=0:
            response['maxscale'] = int(style.maxscale)
        response['rules'] = json.dumps(rules)   
        for r in rules:
            if r and r['filter']:
                if r['filter'] != '':
                    rule_filter = json.loads(r['filter'])
                    if 'field' in rule_filter:
                        response['property_name'] = rule_filter.get('field')    
                        
                    # Adaptación para garantizar compatibilidad con versiones anteriores
                    if 'property_name' in rule_filter:
                        response['property_name'] = rule_filter.get('property_name')    
        
        color_ramps = ColorRampLibrary.objects.all()        
        response["ramp_libraries"] = color_ramps
        
        return render(request, 'unique_values_update.html', response)
    
@login_required()
@staff_required
def get_unique_values(request):
    if request.method == 'POST':
        layer_id = request.POST.get('layer_id')
        field = request.POST.get('field')
        
        layer = Layer.objects.get(id=layer_id)
        if not (layer.created_by == request.user.username or service_utils.can_read_layer(request, layer)):
            return HttpResponseForbidden(json.dumps({'values': []}), content_type='application/json')
        i, source_name, schema = layer.get_db_connection()
        with i as c:
            unique_fields = c.get_unique_values(schema, source_name, field)
            return HttpResponse(json.dumps({'values': unique_fields}, indent=4), content_type='application/json')

@login_required()
@staff_required
def remove_temporal_preview(request):
    if request.method == 'POST':
        name = request.POST['name']
        layer_id = request.POST['layer_id']
        layer = Layer.objects.get(id=int(layer_id))
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        delete_preview_style(request, name, gs)
        gs.reload_nodes()
        
    return HttpResponse(json.dumps({'success': 'OK'}, indent=4), content_type='application/json')
    
@login_required()
@staff_required
def intervals_add(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)

        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_intervals.create_style(request, json_data, layer, gs)
        if style: 
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:         
        response = services_intervals.get_conf(request, layer_id) 
        color_ramps = ColorRampLibrary.objects.all()        
        response["ramp_libraries"] = color_ramps
        
        return render(request, 'intervals_add.html', response)


@login_required()
@staff_required
def update_preview(request, layer_id):
    if request.method == 'POST':
        style_type = request.POST['style']
        if style_type == 'CS':
            style_name = request.POST.get('style_name')
            style_title = request.POST.get('style_title')
            sld = request.POST.get('sld')
            
            is_default = request.POST.get('is_default') == 'true'
            layer = Layer.objects.get(id=layer_id)
            layer_styles = StyleLayer.objects.filter(layer_id=layer.id)
            style = None
            for layer_style in layer_styles:
                stl = Style.objects.get(id=layer_style.style_id)
                if stl.name == style_name + '__tmp':
                    style = stl
            
            gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            if not style:
                style = services_custom.create_style(style_name, style_title, is_default, sld, layer, gs, True)
                if style:
                    gs.reload_nodes()
                    return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            else:    
                style = services_custom.update_style(style_title, is_default, sld, layer, gs, style, True)
                if style:
                    gs.reload_nodes()
                    return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            style_data = request.POST['style_data']
            json_data = json.loads(style_data)
            name = json_data.get('name')
            services = None
            
            if style_type == 'UV':
                services = services_unique_values
            elif style_type == 'US':
                services = services_unique_symbol
            elif style_type == 'IN':
                services = services_intervals
            elif style_type == 'EX':
                services = services_expressions
            elif style_type == 'CT':
                services = services_color_table
            elif style_type == 'CP':
                services = services_clustered_points
            
            if services:
                layer = Layer.objects.get(id=layer_id)
                layer_styles = StyleLayer.objects.filter(layer_id=layer.id)
                style = None
                for layer_style in layer_styles:
                    stl = Style.objects.get(id=layer_style.style_id)
                    if stl.name == name + '__tmp':
                        style = stl
                
                gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
                if not style:
                    style = services.create_style(request, json_data, layer, gs, True)
                    if style:
                        gs.reload_nodes()
                        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
                else:    
                    style = services.update_style(request, json_data, layer, gs, style, True)
                    if style:
                        gs.reload_nodes()
                        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
    return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
 
   
@login_required()
@staff_required
def intervals_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_intervals.update_style(request, json_data, layer, gs, style)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                
        style = Style.objects.get(id=int(style_id))
        
        style_rules = Rule.objects.filter(style=style)
        rules = []
        num_rules = 0
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
            if not r.name.endswith('_text'):
                num_rules = num_rules + 1 
                         
        response = services_intervals.get_conf(request, layer_id)
        
        response['style'] = style
        if style.minscale and int(style.minscale) >=0:
            response['minscale'] = int(style.minscale)
        if style.maxscale and int(style.maxscale) >=0:
            response['maxscale'] = int(style.maxscale)
        response['rules'] = json.dumps(rules)
        if rule and rule['filter']:
            filter_json = json.loads(rule['filter'])
            response['property_name'] = filter_json.get('field') 
            
        for r in rules:
            if r and r['filter']:
                if r['filter'] != '':
                    filter_json = json.loads(r['filter'])
                    if isinstance(filter_json, list):
                        response['property_name'] = filter_json[0].get('field')
                    else:
                        response['property_name'] = filter_json.get('field')   
            
        response['intervals'] = num_rules
        
        color_ramps = ColorRampLibrary.objects.all()        
        response["ramp_libraries"] = color_ramps
        
        return render(request, 'intervals_update.html', response)
    
@login_required()
@staff_required
def get_minmax_values(request):
    layer_id = request.POST.get('layer_id')
    field = request.POST.get('field')
    
    lyr = Layer.objects.get(id=layer_id)
    connection = ast.literal_eval(lyr.datastore.connection_params)
    
    host = connection.get('host')
    port = connection.get('port')
    schema = connection.get('schema')
    database = connection.get('database')
    user = connection.get('user')
    password = connection.get('passwd')
    
    response = service_utils.get_minmax_query(host, port, schema, database, user, password, lyr.name, field)
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
    
@login_required()
@staff_required
def clustered_points_add(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        

        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_clustered_points.create_style(request, json_data, layer, gs)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                 
        response = services_expressions.get_conf(request, layer_id) 
        return render(request, 'clustered_points_add.html', response)

@login_required()
@staff_required
def clustered_points_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
    
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        style = services_clustered_points.update_style(request, json_data, layer, gs, style)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
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
                         
        response = services_expressions.get_conf(request, layer_id)
        
        response['style'] = style
        if style.minscale and int(style.minscale) >=0:
            response['minscale'] = int(style.minscale)
        if style.maxscale and int(style.maxscale) >=0:
            response['maxscale'] = int(style.maxscale)
        response['rules'] = json.dumps(rules)        
        
        return render(request, 'clustered_points_update.html', response)
    

@login_required()
@staff_required
def expressions_add(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)

        layer = Layer.objects.get(id=int(layer_id))
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        style =services_expressions.create_style(request, json_data, layer, gs)
        if style: 
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                 
        response = services_expressions.get_conf(request, layer_id) 
        return render(request, 'expressions_add.html', response)
    
@login_required()
@staff_required
def create_sld(request):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        layer_id = request.POST['layer_id']
        json_data = json.loads(style_data)
        
        single_symbol=False
        if 'single_symbol' in request.POST:
            single_symbol = request.POST['single_symbol']
        
        sld = services_library.get_sld(request, type, json_data, layer_id, single_symbol=='true')           
        return HttpResponse(json.dumps({'success': True, 'sld': sld}, indent=4), content_type='application/json')
            
    return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
  
@login_required()
@staff_required
def expressions_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        json_data = json.loads(style_data)
        
        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        style = services_expressions.update_style(request, json_data, layer, gs, style)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
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
                         
        response = services_expressions.get_conf(request, layer_id)
        
        response['style'] = style
        if style.minscale and int(style.minscale) >=0:
            response['minscale'] = int(style.minscale)
        if style.maxscale and int(style.maxscale) >=0:
            response['maxscale'] = int(style.maxscale)
        response['rules'] = json.dumps(rules)        
        
        return render(request, 'expressions_update.html', response)
    
    
@login_required()
@staff_required
def color_table_add(request, layer_id):
    if request.method == 'POST':
        style_data = request.POST['style_data']
        has_custom_legend = request.POST['has_custom_legend']
        json_data = json.loads(style_data)
        

        layer = Layer.objects.get(id=int(layer_id))
        datastore = layer.datastore
        workspace = datastore.workspace
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        style = services_color_table.create_style(request, json_data, layer, gs, False, has_custom_legend)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:                 
        response = services_color_table.get_conf(request, layer_id)    
        color_ramps = ColorRampLibrary.objects.all()        
        response["ramp_libraries"] = color_ramps 
        return render(request, 'color_table_add.html', response)
    
@login_required()
@staff_required
def color_table_update(request, layer_id, style_id):  
    if request.method == 'POST':
        style_data = request.POST['style_data']
        has_custom_legend = request.POST['has_custom_legend']
        json_data = json.loads(style_data)
        
        style = Style.objects.get(id=int(style_id))
        layer = Layer.objects.get(id=int(layer_id))
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        style = services_color_table.update_style(request, json_data, layer, gs, style, False, has_custom_legend)
        if style:
            delete_preview_style(request, json_data.get('name'), gs)
            gs.reload_nodes()
            if style.is_default:
                gs.updateThumbnail(layer)
            return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            
        else:
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
    else:
        style = Style.objects.get(id=int(style_id))
        
        r = Rule.objects.get(style=style)
        rs = RasterSymbolizer.objects.get(rule=r)
        cm = ColorMap.objects.get(id=rs.color_map.id)
        entries = []
        for e in ColorMapEntry.objects.filter(color_map=cm).order_by('order'):
            entries.append(utils.entry_to_json(e))
            
        rule = {
            'id': r.id,
            'name': r.name,
            'title': r.title,
            'abstract': '',
            'filter': '',
            'minscale': r.minscale,
            'maxscale': r.maxscale,
            'order': r.order,
            'entries': entries
        }
                         
        response = services_color_table.get_conf(request, layer_id)
        
        response['style'] = style
        if style.minscale and int(style.minscale) >=0:
            response['minscale'] = int(style.minscale)
        if style.maxscale and int(style.maxscale) >=0:
            response['maxscale'] = int(style.maxscale)
        response['rule'] = json.dumps(rule)        
        
        color_ramps = ColorRampLibrary.objects.all()        
        response["ramp_libraries"] = color_ramps
        
        return render(request, 'color_table_update.html', response)
    
    
@login_required()
@staff_required
def sld_import(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    index = len(StyleLayer.objects.filter(layer=layer))
        
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    if request.method == 'POST':
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        style_name = request.POST.get('sld-name')
        
        is_default = False
        if 'style-is-default' in request.POST:
            is_default = True
        
        if 'sld-file' in request.FILES: 
            if services.sld_import(style_name, is_default, layer_id, request.FILES['sld-file'], request, gs):
                gs.reload_nodes()
                return redirect('style_layer_list')
            else:
                response = {
                    'message': _('Error importing SLD'),
                    'layer_id': layer_id,
                    'style_name': workspace.name + '_' + layer.name + '_' + str(index)
                }
            
        
        else:
            response = {
                'message': _('You must select a file'),
                'layer_id': layer_id,
                'style_name': workspace.name + '_' + layer.name + '_' + str(index)
            }
            
            
        return render(request, 'sld_import.html', response)
    
    else:   
        response = {
            'layer_id': layer_id,
            'style_name': workspace.name + '_' + layer.name + '_' + str(index)
        }
        
        return render(request, 'sld_import.html', response)


@staff_required
def color_ramp_list(request):
    response = {
        'color_ramps': ColorRamp.objects.all()
    }
    return render(request, 'color_ramp_list.html', response)


@login_required()
@staff_required
def color_ramp_add(request, color_ramp_folder_id):
    folder = ColorRampFolder.objects.get(id=int(color_ramp_folder_id))
    if request.method == 'POST': 
        name = request.POST.get('colorramp-name')
        definition = request.POST.get('colorramp-definition')  
        colorrampfolder = ColorRampFolder.objects.get(id=int(color_ramp_folder_id))      

        if name != '' and re.match("^[a-z0-9_]*$", name):
            colorramp = ColorRamp(
                name = name,
                definition = definition,
                color_ramp_folder_id = colorrampfolder.id
            )
            colorramp.save()         
            response = {
                'library': folder.color_ramp_library,
                'folder': folder,
                'color_ramps': ColorRamp.objects.filter(color_ramp_folder_id=folder.id)
            }
            return redirect('/gvsigonline/symbology/color_ramp_folder_update/'+str(colorrampfolder.id)+'/')
        
        else:
            
            response = {
                'folder': folder,
                'message': _('You must enter a correct name for the color ramp (without uppercases, whitespaces or other special characters)')
            
            }
            return render(request, 'color_ramp_add.html', response)
    
    else:   
        response = {
            'folder': folder
        }
        return render(request, 'color_ramp_add.html', response)
  
    
@login_required()
@staff_required
def color_ramp_update(request, color_ramp_id):      
    cramp = ColorRamp.objects.get(id=int(color_ramp_id))
    if request.method == 'POST': 
        name = request.POST.get('colorramp-name')
        lib_description = request.POST.get('colorramp-definition')

        if name != '' and re.match("^[a-z0-9_]*$", name):
            cramp.name = name
            cramp.definition = lib_description
            cramp.save()
        else:
            message = _('You must enter a correct name for the color ramp (without uppercases, whitespaces or other special characters)')
            response = {
                'message': message,
                'color_ramp': cramp,
            }
            
            return render(request, 'color_ramp_update.html', response)
     
        return redirect('/gvsigonline/symbology/color_ramp_folder_update/'+str(cramp.color_ramp_folder_id)+'/')
    
    else:   
        response = {
            'color_ramp': cramp,
        }
        return render(request, 'color_ramp_update.html', response)

@login_required()
@staff_required
def color_ramp_library_export(request, color_ramp_library_id):
    library = ColorRampLibrary.objects.get(id=int(color_ramp_library_id))
    folders = ColorRampFolder.objects.filter(color_ramp_library_id=library.id)
    
    folders_json = {}
    for folder in folders:
        folders_json[folder.name] = ColorRamp.objects.filter(color_ramp_folder_id=folder.id)
    
    try:
        response = services_library.export_ramp_color_library(library, folders_json)
        return response
        
    except Exception as e:
        message = str(e)
        return HttpResponse(json.dumps({'message':message}, indent=4), content_type='application/json')


@login_required()
@staff_required
def color_ramp_delete(request, color_ramp_id):
    colorramp = ColorRamp.objects.get(id=int(color_ramp_id))
    folder_id = colorramp.color_ramp_folder.id
    folder = ColorRampFolder.objects.get(id=int(folder_id))
    colorramp.delete()
    
    return redirect('/gvsigonline/symbology/color_ramp_folder_update/'+str(folder.id)+'/')


@staff_required
def color_ramp_library_list(request):
    response = {
        'libraries': ColorRampLibrary.objects.all()
    }
    return render(request, 'color_ramp_library_list.html', response)


@login_required()
@staff_required
def color_ramp_library_add(request):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')        

        if name != '' and re.match("^[a-z0-9_]*$", name):
            library = ColorRampLibrary(
                name = name,
                description = description
            )
            library.save()         
            return redirect('color_ramp_library_list')
        
        else:
            message = _('You must enter a correct name for the library (without uppercases, whitespaces or other special characters)')
            return render(request, 'color_ramp_library_add.html', {'message': message})
    
    else:   
        return render(request, 'color_ramp_library_add.html', {})


@login_required()
@staff_required
def color_ramp_library_update(request, color_ramp_library_id):      
    if request.method == 'POST': 
        lib_description = request.POST.get('library-description')

        library = ColorRampLibrary.objects.get(id=int(color_ramp_library_id))
        library.description = lib_description
        library.save()
        
        return redirect('color_ramp_library_list')
    
    else:   
        library = ColorRampLibrary.objects.get(id=int(color_ramp_library_id))
            
        response = {
            'library': library,
            'folders': ColorRampFolder.objects.filter(color_ramp_library_id=library.id)
        }
        return render(request, 'color_ramp_library_update.html', response)


@login_required()
@staff_required
def color_ramp_library_delete(request, color_ramp_library_id):
    lib = ColorRampLibrary.objects.get(id=int(color_ramp_library_id))
    lib.delete()
    return redirect('color_ramp_library_list')

 
@login_required()
@staff_required
def color_ramp_library_import(request):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')
        message = ''
        
        try:            
            if name != '' and not re.match("^[a-z0-9_]*$", name):
                message = _('You must enter a correct name for the library (without uppercases, whitespaces or other special characters)')
            
            elif name != '' and 'library-file' in request.FILES: 
                services_library.upload_color_ramp_library(name, description, request.FILES['library-file'])                
                return redirect('color_ramp_library_list')
            
            elif name == '' and 'library-file' in request.FILES:
                message = _('You must enter a name for the library')
                
            elif name != '' and not 'library-file' in request.FILES:
                message = _('You must select a file')
                
            elif name == '' and not 'library-file' in request.FILES:
                message = _('You must enter a name for the library and select a file')
                
            return render(request, 'color_ramp_library_import.html', {'message': message})
        
        except Exception as e:
            message = str(e)
            return render(request, 'color_ramp_library_import.html', {'message': message})
    
    else:   
        return render(request, 'color_ramp_library_import.html', {})
    

@login_required()
@staff_required
def color_ramp_folder_add(request, color_ramp_library_id):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')        
        library = ColorRampLibrary.objects.get(id=int(color_ramp_library_id))
        
        if name != '' and re.match("^[a-z0-9_]*$", name):
            folder = ColorRampFolder(
                name = name,
                description = description,
                color_ramp_library_id = library.id
            )
            folder.save()         
            response = {
                'folder': folder
            }
            return redirect('/gvsigonline/symbology/color_ramp_folder_update/'+str(folder.id)+'/')
        
        else:
            response = {
                'library': library,
                'message': _('You must enter a correct name for the library (without uppercases, whitespaces or other special characters)')
            }
            return render(request, 'color_ramp_folder_add.html', response)
    
    else:   
        library = ColorRampLibrary.objects.get(id=int(color_ramp_library_id))
        response = {
            'library': library
        }
        return render(request, 'color_ramp_folder_add.html', response)


@login_required()
@staff_required
def color_ramp_folder_update(request, color_ramp_folder_id):      
    if request.method == 'POST': 
        lib_description = request.POST.get('folder-description')

        folder = ColorRampFolder.objects.get(id=int(color_ramp_folder_id))
        folder.description = lib_description
        folder.save()
        
        response = {
            'library': folder.color_ramp_library,
            'folders': ColorRampFolder.objects.filter(color_ramp_library_id=folder.color_ramp_library.id)
        }
        return render(request, 'color_ramp_library_update.html', response)

    
    else:   
        folder = ColorRampFolder.objects.get(id=int(color_ramp_folder_id))
        color_ramps = ColorRamp.objects.filter(color_ramp_folder_id=folder.id).order_by('id')
            
        response = {
            'library': folder.color_ramp_library,
            'folder': folder,
            'color_ramps': color_ramps
        }
        return render(request, 'color_ramp_folder_update.html', response)

@login_required()
@staff_required
def color_ramp_folder_delete(request, color_ramp_folder_id):
    folder = ColorRampFolder.objects.get(id=int(color_ramp_folder_id))
    library_id = folder.color_ramp_library.id
    library = ColorRampLibrary.objects.get(id=int(library_id))
    folder.delete()
    response = {
        'library': library
    }
    return render(request, 'color_ramp_library_update.html', response)


  
@staff_required
def library_list(request):
    response = {
        'libraries': Library.objects.all()
    }
    return render(request, 'library_list.html', response)

@login_required()
@staff_required
def library_add(request):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')        

        if name != '' and re.match("^[a-z0-9_]*$", name):
            library = Library(
                name = name,
                description = description
            )
            library.save()         
            return redirect('library_list')
        
        else:
            message = _('You must enter a correct name for the library (without uppercases, whitespaces or other special characters)')
            return render(request, 'library_add.html', {'message': message})
    
    else:   
        return render(request, 'library_add.html', {})

    
@login_required()
@staff_required
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
        
        gs = geographic_servers.get_instance().get_default_server()
        master = geographic_servers.get_instance().get_master_node(gs.id)
        response = {
            'library': library,
            'rules': rules,
            'preview_point_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point',
            'preview_line_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line',
            'preview_polygon_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
        }
        return render(request, 'library_update.html', response)
    
@login_required()
@staff_required
def library_import(request):
    if request.method == 'POST': 
        name = request.POST.get('library-name')
        description = request.POST.get('library-description')
        message = ''
        
        try:            
            if name != '' and not re.match("^[a-z0-9_]*$", name):
                message = _('You must enter a correct name for the library (without uppercases, whitespaces or other special characters)')
            
            elif name != '' and 'library-file' in request.FILES: 
                services_library.upload_library(name, description, request.FILES['library-file'])                
                return redirect('library_list')
            
            elif name == '' and 'library-file' in request.FILES:
                message = _('You must enter a name for the library')
                
            elif name != '' and not 'library-file' in request.FILES:
                message = _('You must select a file')
                
            elif name == '' and not 'library-file' in request.FILES:
                message = _('You must enter a name for the library and select a file')
                
            return render(request, 'library_import.html', {'message': message})
        
        except Exception as e:
            message = str(e)
            return render(request, 'library_import.html', {'message': message})
    
    else:   
        return render(request, 'library_import.html', {})
    

@login_required()
@staff_required
def library_export(request, library_id):
    library = Library.objects.get(id=library_id)
    library_rules = LibraryRule.objects.filter(library_id=library.id)
    
    try:
        response = services_library.export_library(library, library_rules)
        return response
        
    except Exception as e:
        logger.exception(str(e))
        return HttpResponse(json.dumps({'message':str(e)}, indent=4), content_type='application/json')
    
    

@login_required()
@staff_required
def get_ramps_from_folder(request):      
    if request.method == 'POST':  
        folder_id = request.POST.get('folder_id')
        colorramps = ColorRamp.objects.filter(color_ramp_folder_id=int(folder_id))
        
        lib_folds = []
        for colorramp in colorramps:
            lib_folds.append({
                "id": colorramp.id, 
                "name": colorramp.name, 
                'definition': json.loads(colorramp.definition)
            })
        
        response = {
            'color_ramps': lib_folds
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@login_required()
@staff_required
def get_folders_from_library(request):      
    if request.method == 'POST':  
        library_id = request.POST.get('library_id')
        library_folders = ColorRampFolder.objects.filter(color_ramp_library_id=int(library_id))
        
        lib_folds = []
        for library_folder in library_folders:
            lib_folds.append({"id": library_folder.id, "name": library_folder.name})
        
        response = {
            'library_folders': lib_folds
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@login_required()
@staff_required
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

    
@login_required()
@staff_required
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


@login_required()
@staff_required
def symbol_add(request, library_id, symbol_type):
    if request.method == 'POST':
        data = request.POST['rule']
        json_rule = json.loads(data)     
    
        try:    
            if not 'name' in json_rule or json_rule['name'] == '' or not re.match("^[a-z0-9_]*$", json_rule['name']):
                message = _('You must enter a correct name for the library (without uppercases, whitespaces or other special characters)')
                return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
            gs = geographic_servers.get_instance().get_default_server()
            if services_library.add_symbol(request, json_rule, library_id, symbol_type, gs):
                gs.reload_nodes()
                return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
            else:
                return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = str(e)
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
 
    else: 
        gs = geographic_servers.get_instance().get_default_server()
        master = geographic_servers.get_instance().get_master_node(gs.id)         
        response = {
            'library_id': library_id,
            'symbol_type': symbol_type,
            'preview_point_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point',
            'preview_line_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line',
            'preview_polygon_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
        }
        if symbol_type == 'ExternalGraphicSymbolizer':
            return render(request, 'external_graphic_add.html', response)
        
        else:
            return render(request, 'symbol_add.html', response)
    

@login_required()
@staff_required
def symbol_update(request, symbol_id):
    if request.method == 'POST':
        data = request.POST['rule']
        json_rule = json.loads(data)   
        
        rule = Rule.objects.get(id=int(symbol_id))
        library_rule = LibraryRule.objects.get(rule=rule)
        
        try:
            gs = geographic_servers.get_instance().get_default_server()
            if services_library.update_symbol(request, json_rule, rule, library_rule, gs):
                gs.reload_nodes()
                return HttpResponse(json.dumps({'library_id': library_rule.library.id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = str(e)
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
        
    else:
        r = Rule.objects.get(id=int(symbol_id))
        s = Symbolizer.objects.filter(rule=r)[0]
        ftype = services_library.get_ftype(s)
            
        if ftype == 'ExternalGraphicSymbolizer':       
            response = {
                'rule': services_library.get_symbol(r, ftype)
            }
            return render(request, 'external_graphic_update.html', response)
        
        else:
            gs = geographic_servers.get_instance().get_default_server()
            master = geographic_servers.get_instance().get_master_node(gs.id)
            response = {
                'rule': services_library.get_symbol(r, ftype),
                'preview_point_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_point',
                'preview_line_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_line',
                'preview_polygon_url': master.url + '/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_polygon'
            }
            return render(request, 'symbol_update.html', response)
    
@login_required()
@staff_required
def symbol_delete(request):
    if request.method == 'POST':
        symbol_id = request.POST.get('symbol_id')
             
        try:
            rule = Rule.objects.get(id=int(symbol_id))
            library_rule = LibraryRule.objects.get(rule=rule)
            library_id = library_rule.library.id
            gs = geographic_servers.get_instance().get_default_server()
            services_library.delete_symbol(rule, library_rule, gs)
            gs.reload_nodes()
            return HttpResponse(json.dumps({'library_id': library_id, 'success': True}, indent=4), content_type='application/json')
        
        except Exception as e:
            message = str(e)
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')
        
@csrf_exempt
def get_wfs_style(request):
    if request.method == 'POST':
        layer_name = request.POST['layer_name']
        layer_query_set = Layer.objects.filter(name=layer_name)
        layer = layer_query_set[0]
             
        try:
            layerStyles = StyleLayer.objects.filter(layer=layer)
            for layerStyle in layerStyles:
                if layerStyle.style.is_default:
                    style_rules = Rule.objects.filter(style=layerStyle.style)
                    rule = style_rules[0]
                    symbolizers = Symbolizer.objects.filter(rule=rule).order_by('order')
                    sym = utils.symbolizer_to_json(symbolizers[0])
                    return HttpResponse(json.dumps({'style':sym, 'success': True}, indent=4), content_type='application/json')
                    
        except Exception as e:
            message = str(e)
            return HttpResponse(json.dumps({'message':message, 'success': False}, indent=4), content_type='application/json')


def get_ol_style(layer):
    try:
        layerStyles = StyleLayer.objects.filter(layer=layer)
        for layerStyle in layerStyles:
            if layerStyle.style.is_default:
                style_rules = Rule.objects.filter(style=layerStyle.style)
                rule = style_rules[0]
                symbolizers = Symbolizer.objects.filter(rule=rule).order_by('order')
                sym = utils.symbolizer_to_json(symbolizers[0])
                default_style = sym
                return default_style
                
    except Exception as e:
        return None
        
