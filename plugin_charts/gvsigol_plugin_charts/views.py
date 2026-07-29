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
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def get_browser_wfs_url(layer):
    """
    Return a WFS URL usable from the browser (prefer relative path through the
    public reverse proxy instead of an internal docker hostname).
    """
    workspace = layer.datastore.workspace
    server = getattr(workspace, 'server', None)
    if server is not None:
        endpoint = server.getWfsEndpoint(workspace.name, relative=True)
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            path = urlparse(endpoint).path
            if path:
                return path
        return endpoint
    if workspace.wfs_endpoint:
        endpoint = workspace.wfs_endpoint
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            path = urlparse(endpoint).path
            if path:
                return path
        return endpoint
    return '/geoserver/%s/wfs' % workspace.name


def load_layer_field_context(layer):
    """
    Load GeoServer field metadata for chart forms.
    Never raises: returns empty field lists if GeoServer/resource is unavailable.
    """
    empty = {
        'fields': [],
        'numeric_fields': [],
        'alpha_numeric_fields': [],
        'geom_fields': [],
    }
    try:
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        _ds_type, resource = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
        fields = utils.get_fields(resource)
        return {
            'fields': fields,
            'numeric_fields': utils.get_numeric_fields(fields),
            'alpha_numeric_fields': utils.get_alphanumeric_fields(fields),
            'geom_fields': utils.get_geometry_fields(fields),
        }
    except Exception:
        logger.exception('plugin_charts: unable to load fields for layer_id=%s', getattr(layer, 'id', None))
        return empty


def chart_form_field_context(layer):
    ctx = load_layer_field_context(layer)
    return {
        'fields': json.dumps(ctx['fields']),
        'numeric_fields': json.dumps(ctx['numeric_fields']),
        'alpha_numeric_fields': json.dumps(ctx['alpha_numeric_fields']),
        'geom_fields': json.dumps(ctx['geom_fields']),
    }


def chart_update_template_context(layer_id, chart_id, chart, include_axes=True):
    """Build safe template context for chart update forms."""
    conf = utils.parse_chart_conf(chart.conf)
    columns = conf.get('columns')
    if not isinstance(columns, list):
        columns = []
    ctx = {
        'layer_id': layer_id,
        'chart_id': chart_id,
        'title': chart.title,
        'description': chart.description,
        'dataset_type': conf.get('dataset_type') or 'single_selection',
        'geographic_names_column': conf.get('geographic_names_column') or '',
        'geometries_column': conf.get('geometries_column') or '',
        'selected_columns': json.dumps(columns),
    }
    ctx.update(chart_form_field_context(chart.layer))
    if include_axes:
        ctx['x_axis_title'] = conf.get('x_axis_title') or ''
        ctx['y_axis_title'] = conf.get('y_axis_title') or ''
        ctx['y_axis_begin_at_zero'] = bool(conf.get('y_axis_begin_at_zero'))
    return ctx


def save_chart_conf_from_post(request):
    """
    Validate chart_conf from POST. Returns (normalized_json_str, None) or (None, error_response).
    """
    raw = request.POST.get('chart_conf')
    conf = utils.parse_chart_conf(raw)
    if not conf:
        return None, HttpResponse(
            json.dumps({'success': False, 'error': 'invalid_chart_conf'}, indent=4),
            content_type='application/json',
            status=400,
        )
    if not isinstance(conf.get('columns'), list):
        conf['columns'] = []
    conf.setdefault('dataset_type', 'single_selection')
    conf.setdefault('geographic_names_column', '')
    conf.setdefault('geometries_column', '')
    return json.dumps(conf), None


def get_conf(request):
    if request.method == 'POST': 
        chart_layers = Chart.objects.values('layer').distinct()
        layers = []
        for cl in chart_layers:
            try:
                l = Layer.objects.get(id=(cl['layer']))
            except Layer.DoesNotExist:
                logger.warning('plugin_charts: skipping charts for missing layer_id=%s', cl.get('layer'))
                continue
            try:
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
            except Exception:
                logger.exception('plugin_charts: error building get_conf for layer_id=%s', getattr(l, 'id', None))
            
        response = {
            'layers': layers
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
    
@login_required()
@staff_required
def chart_list(request):
    
    response = {
        'layers': Layer.objects.exclude(external=True),
        'charts': Chart.objects.all()
    }
    return render(request, 'chart_list.html', response)     

@login_required()
@staff_required
def select_chart_type(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    
    response = {
        'layer': layer
    }
    
    return render(request, 'select_chart_type.html', response)  

@login_required()
@staff_required
def chart_update(request, layer_id, chart_id):
    chart = Chart.objects.get(id=int(chart_id))
    
    if (chart.type == 'barchart'):
        return redirect('barchart_update', layer_id=layer_id, chart_id=chart_id)
    
    elif (chart.type == 'linechart'):
        return redirect('linechart_update', layer_id=layer_id, chart_id=chart_id)
    
    elif (chart.type == 'piechart'):
        return redirect('piechart_update', layer_id=layer_id, chart_id=chart_id)

    logger.warning('plugin_charts: unknown chart type %r for chart_id=%s', chart.type, chart_id)
    return redirect('chart_list')

@login_required()
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def barchart_add(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf, error = save_chart_conf_from_post(request)
        if error:
            return error
        
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
        conf = {'layer_id': layer_id}
        conf.update(chart_form_field_context(layer))
        return render(request, 'barchart_add.html', conf)


@login_required()
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def barchart_update(request, layer_id, chart_id):
    if request.method == 'POST':
        chart = Chart.objects.get(id=int(chart_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf, error = save_chart_conf_from_post(request)
        if error:
            return error
        
        chart.title = title
        chart.description = description
        chart.conf = chart_conf

        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
    else:
        chart = Chart.objects.get(id=int(chart_id))
        return render(request, 'barchart_update.html', chart_update_template_context(layer_id, chart_id, chart, include_axes=True))
    

@login_required()
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def linechart_add(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf, error = save_chart_conf_from_post(request)
        if error:
            return error
        
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
        conf = {'layer_id': layer_id}
        conf.update(chart_form_field_context(layer))
        return render(request, 'linechart_add.html', conf)

@login_required()
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def linechart_update(request, layer_id, chart_id):
    if request.method == 'POST':
        chart = Chart.objects.get(id=int(chart_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf, error = save_chart_conf_from_post(request)
        if error:
            return error
        
        chart.title = title
        chart.description = description
        chart.conf = chart_conf

        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
    else:
        chart = Chart.objects.get(id=int(chart_id))
        return render(request, 'linechart_update.html', chart_update_template_context(layer_id, chart_id, chart, include_axes=True))

@login_required()
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def piechart_add(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf, error = save_chart_conf_from_post(request)
        if error:
            return error
        
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
        conf = {'layer_id': layer_id}
        conf.update(chart_form_field_context(layer))
        return render(request, 'piechart_add.html', conf)


@login_required()
@staff_required
@require_http_methods(["GET", "POST", "HEAD"])
def piechart_update(request, layer_id, chart_id):
    if request.method == 'POST':
        chart = Chart.objects.get(id=int(chart_id))
        
        title = request.POST.get('title')
        description = request.POST.get('description')
        chart_conf, error = save_chart_conf_from_post(request)
        if error:
            return error
        
        chart.title = title
        chart.description = description
        chart.conf = chart_conf

        chart.save()
                
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
        
    else:
        chart = Chart.objects.get(id=int(chart_id))
        return render(request, 'piechart_update.html', chart_update_template_context(layer_id, chart_id, chart, include_axes=False))
    
    
@login_required()
@staff_required
def chart_delete(request):
    try:
        chart_id = request.POST.get('chart_id')
        chart = Chart.objects.get(id=int(chart_id))
        chart.delete()
        
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
    
    except Exception:
        return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json') 


#@login_required(login_url='/gvsigonline/auth/login_user/')   
def view(request):
    if request.method == 'POST':
        try:
            layer = Layer.objects.get(id=int(request.POST.get('layer_id')))
        except (Layer.DoesNotExist, TypeError, ValueError):
            return HttpResponse(json.dumps({'error': 'layer_not_found'}, indent=4), content_type='application/json', status=404)

        chart_objects = Chart.objects.filter(layer=layer)
        
        charts = []
        for c in chart_objects:
            charts.append({
                'chart_id': c.id,
                'chart_type': c.type,
                'chart_title': c.title,
                'chart_description': c.description,
                'chart_conf': utils.parse_chart_conf(c.conf)
            })
            
        response = {
            'layer_id': layer.id,
            'layer_name': layer.name,
            'layer_title': layer.title,
            'layer_workspace': layer.datastore.workspace.name,
            'layer_wfs_url': get_browser_wfs_url(layer),
            'layer_native_srs': layer.native_srs,
            'charts': charts
        }
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

#@login_required(login_url='/gvsigonline/auth/login_user/')   
def single_chart(request):
    if request.method == 'POST':
        try:
            layer = Layer.objects.get(id=int(request.POST.get('layer_id')))
            chart_id = int(request.POST.get('chart_id'))
            chart = Chart.objects.get(id=chart_id)
        except (Layer.DoesNotExist, Chart.DoesNotExist, TypeError, ValueError):
            return HttpResponse(json.dumps({'error': 'not_found'}, indent=4), content_type='application/json', status=404)
            
        response = {
            'layer_id': layer.id,
            'layer_name': layer.name,
            'layer_title': layer.title,
            'layer_workspace': layer.datastore.workspace.name,
            'layer_wfs_url': get_browser_wfs_url(layer),
            'layer_native_srs': layer.native_srs,
            'chart': {
                'chart_id': chart.id,
                'chart_type': chart.type,
                'chart_title': chart.title,
                'chart_description': chart.description,
                'chart_conf': utils.parse_chart_conf(chart.conf)
            }
        }
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
