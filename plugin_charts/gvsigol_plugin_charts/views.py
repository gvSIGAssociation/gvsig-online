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
@author: jrodrigo <jrodrigo@scolab.es>
'''
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.views.decorators.http import require_http_methods, require_safe, require_POST, require_GET
from gvsigol_auth.utils import superuser_required, staff_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import HttpResponse
from gvsigol_core.models import Project
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_services import geographic_servers
from .forms import ChartForm

from .models import Chart
from . import settings
from . import utils
import json

def get_conf(request):
    if request.method == 'POST': 
        chart_layers = Chart.objects.values('layer').distinct()
        layers = []
        for cl in chart_layers:
            l = Layer.objects.get(id=(cl['layer']))
            chart_objects = Chart.objects.filter(layer=l)
            charts = []
            for c in chart_objects:
                charts.append({
                    'id': c.id,
                    'title': c.title,
                    'type': c.type
                })
                
            layer = {
                'id': l.id,
                'name': l.name,
                'workspace': l.datastore.workspace.name,
                'charts': charts
            }
            layers.append(layer)
            
        response = {
            'layers': layers
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')   
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def chart_list(request):
    
    response = {
        'layers': Layer.objects.exclude(external=True),
        'charts': Chart.objects.all()
    }
    return render(request, 'chart_list.html', response)     

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def select_chart_type(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    
    response = {
        'layer': layer
    }
    
    return render(request, 'select_chart_type.html', response)  

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def chart_update(request, layer_id, chart_id):
    chart = Chart.objects.get(id=int(chart_id))
    
    if (chart.type == 'barchart'):
        return redirect('barchart_update', layer_id=layer_id, chart_id=chart_id)
    
    elif (chart.type == 'linechart'):
        return redirect('linechart_update', layer_id=layer_id, chart_id=chart_id)
    
    elif (chart.type == 'piechart'):
        return redirect('piechart_update', layer_id=layer_id, chart_id=chart_id)

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def barchart_add(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf = request.POST.get('chart_conf')
        
        chart = Chart(
            layer = layer,
            type = 'barchart',
            title = title,
            description = description,
            conf = chart_conf
        )
        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')

    else:
        layer = Layer.objects.get(id=int(layer_id))
        
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
        fields = utils.get_fields(resource)
        numeric_fields = utils.get_numeric_fields(fields)
        alpha_numeric_fields = utils.get_alphanumeric_fields(fields)
        geom_fields = utils.get_geometry_fields(fields)
        
        conf = {
            'layer_id': layer_id,
            'fields': json.dumps(fields),
            'numeric_fields': json.dumps(numeric_fields),
            'alpha_numeric_fields': json.dumps(alpha_numeric_fields),
            'geom_fields': json.dumps(geom_fields)
        }
    
        return render(request, 'barchart_add.html', conf)


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def barchart_update(request, layer_id, chart_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        chart = Chart.objects.get(id=int(chart_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf = request.POST.get('chart_conf')
        
        chart.title = title
        chart.description = description
        chart.conf = chart_conf

        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
    else:
        layer = Layer.objects.get(id=int(layer_id))
        chart = Chart.objects.get(id=int(chart_id))
               
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
        fields = utils.get_fields(resource)
        numeric_fields = utils.get_numeric_fields(fields)
        alpha_numeric_fields = utils.get_alphanumeric_fields(fields)
        geom_fields = utils.get_geometry_fields(fields)
        
        conf = json.loads(chart.conf)
        
        y_axis_begin_at_zero = False
        if 'y_axis_begin_at_zero' in conf:
            y_axis_begin_at_zero = conf['y_axis_begin_at_zero']

        return render(request, 'barchart_update.html', {
            'layer_id': layer_id,
            'chart_id': chart_id,
            'fields': json.dumps(fields),
            'numeric_fields': json.dumps(numeric_fields),
            'alpha_numeric_fields': json.dumps(alpha_numeric_fields),
            'geom_fields': json.dumps(geom_fields),
            'title': chart.title,
            'description': chart.description,
            'dataset_type': conf['dataset_type'],
            'x_axis_title': conf['x_axis_title'],
            'y_axis_title': conf['y_axis_title'],
            'y_axis_begin_at_zero': y_axis_begin_at_zero,
            'geographic_names_column': conf['geographic_names_column'],
            'geometries_column': conf['geometries_column'],
            'selected_columns': json.dumps(conf['columns'])
        })
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def linechart_add(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf = request.POST.get('chart_conf')
        
        chart = Chart(
            layer = layer,
            type = 'linechart',
            title = title,
            description = description,
            conf = chart_conf
        )
        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')

    else:
        layer = Layer.objects.get(id=int(layer_id))
        
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
        fields = utils.get_fields(resource)
        numeric_fields = utils.get_numeric_fields(fields)
        alpha_numeric_fields = utils.get_alphanumeric_fields(fields)
        geom_fields = utils.get_geometry_fields(fields)
        
        conf = {
            'layer_id': layer_id,
            'fields': json.dumps(fields),
            'numeric_fields': json.dumps(numeric_fields),
            'alpha_numeric_fields': json.dumps(alpha_numeric_fields),
            'geom_fields': json.dumps(geom_fields)
        }
    
        return render(request, 'linechart_add.html', conf)

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def linechart_update(request, layer_id, chart_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        chart = Chart.objects.get(id=int(chart_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf = request.POST.get('chart_conf')
        
        chart.title = title
        chart.description = description
        chart.conf = chart_conf

        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
    else:
        layer = Layer.objects.get(id=int(layer_id))
        chart = Chart.objects.get(id=int(chart_id))
               
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
        fields = utils.get_fields(resource)
        numeric_fields = utils.get_numeric_fields(fields)
        alpha_numeric_fields = utils.get_alphanumeric_fields(fields)
        geom_fields = utils.get_geometry_fields(fields)
        
        conf = json.loads(chart.conf)
        
        y_axis_begin_at_zero = False
        if 'y_axis_begin_at_zero' in conf:
            y_axis_begin_at_zero = conf['y_axis_begin_at_zero']

        return render(request, 'linechart_update.html', {
            'layer_id': layer_id,
            'chart_id': chart_id,
            'fields': json.dumps(fields),
            'numeric_fields': json.dumps(numeric_fields),
            'alpha_numeric_fields': json.dumps(alpha_numeric_fields),
            'geom_fields': json.dumps(geom_fields),
            'title': chart.title,
            'description': chart.description,
            'dataset_type': conf['dataset_type'],
            'x_axis_title': conf['x_axis_title'],
            'y_axis_title': conf['y_axis_title'],
            'y_axis_begin_at_zero': y_axis_begin_at_zero,
            'geographic_names_column': conf['geographic_names_column'],
            'geometries_column': conf['geometries_column'],
            'selected_columns': json.dumps(conf['columns'])
        })

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def piechart_add(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf = request.POST.get('chart_conf')
        
        chart = Chart(
            layer = layer,
            type = 'piechart',
            title = title,
            description = description,
            conf = chart_conf
        )
        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')

    else:
        layer = Layer.objects.get(id=int(layer_id))
        
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
        fields = utils.get_fields(resource)
        numeric_fields = utils.get_numeric_fields(fields)
        alpha_numeric_fields = utils.get_alphanumeric_fields(fields)
        geom_fields = utils.get_geometry_fields(fields)
        
        conf = {
            'layer_id': layer_id,
            'fields': json.dumps(fields),
            'numeric_fields': json.dumps(numeric_fields),
            'alpha_numeric_fields': json.dumps(alpha_numeric_fields),
            'geom_fields': json.dumps(geom_fields)
        }
    
        return render(request, 'piechart_add.html', conf)


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def piechart_update(request, layer_id, chart_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        chart = Chart.objects.get(id=int(chart_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf = request.POST.get('chart_conf')
        
        chart.title = title
        chart.description = description
        chart.conf = chart_conf

        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
    else:
        layer = Layer.objects.get(id=int(layer_id))
        chart = Chart.objects.get(id=int(chart_id))
               
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
        fields = utils.get_fields(resource)
        numeric_fields = utils.get_numeric_fields(fields)
        alpha_numeric_fields = utils.get_alphanumeric_fields(fields)
        geom_fields = utils.get_geometry_fields(fields)
        
        conf = json.loads(chart.conf)
        
        return render(request, 'piechart_update.html', {
            'layer_id': layer_id,
            'chart_id': chart_id,
            'fields': json.dumps(fields),
            'numeric_fields': json.dumps(numeric_fields),
            'alpha_numeric_fields': json.dumps(alpha_numeric_fields),
            'geom_fields': json.dumps(geom_fields),
            'title': chart.title,
            'description': chart.description,
            'dataset_type': conf['dataset_type'],
            'geographic_names_column': conf['geographic_names_column'],
            'geometries_column': conf['geometries_column'],
            'selected_columns': json.dumps(conf['columns'])
        })
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def chart_delete(request):
    try:
        chart_id = request.POST.get('chart_id')
        chart = Chart.objects.get(id=int(chart_id))
        chart.delete()
        
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
    
    except:
        return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json') 


#@login_required(login_url='/gvsigonline/auth/login_user/')   
def view(request):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(request.POST.get('layer_id')))
        chart_objects = Chart.objects.filter(layer=layer)
        
        charts = []
        for c in chart_objects:
            charts.append({
                'chart_id': c.id,
                'chart_type': c.type,
                'chart_title': c.title,
                'chart_description': c.description,
                'chart_conf': json.loads(c.conf)
            })
            
        response = {
            'layer_id': layer.id,
            'layer_name': layer.name,
            'layer_title': layer.title,
            'layer_workspace': layer.datastore.workspace.name,
            'layer_wfs_url': layer.datastore.workspace.wfs_endpoint,
            'layer_native_srs': layer.native_srs,
            'charts': charts
        }
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

#@login_required(login_url='/gvsigonline/auth/login_user/')   
def single_chart(request):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(request.POST.get('layer_id')))
        chart_id = int(request.POST.get('chart_id'))
        chart = Chart.objects.get(id=chart_id)
            
        response = {
            'layer_id': layer.id,
            'layer_name': layer.name,
            'layer_title': layer.title,
            'layer_workspace': layer.datastore.workspace.name,
            'layer_wfs_url': layer.datastore.workspace.wfs_endpoint,
            'layer_native_srs': layer.native_srs,
            'chart': {
                'chart_id': chart.id,
                'chart_type': chart.type,
                'chart_title': chart.title,
                'chart_description': chart.description,
                'chart_conf': json.loads(chart.conf)
            }
        }
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')