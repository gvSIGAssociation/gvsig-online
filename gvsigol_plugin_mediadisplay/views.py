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
@author: lsanjaime <lsanjaime@scolab.es>
'''

from django.shortcuts import render, HttpResponse, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from gvsigol_core.models import Project, Layer
from .models import MediaDisplayConfig
from . import settings
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@login_required
def config_list(request):
    """Lista de configuraciones de Media Display"""
    configs = MediaDisplayConfig.objects.all().order_by('-created_at')
    
    paginator = Paginator(configs, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'mediadisplay_config_list.html', {
        'page_obj': page_obj,
        'configs': page_obj
    })

@login_required
def config_add(request):
    """Añadir nueva configuración de Media Display"""
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        layer_configs = request.POST.getlist('layer_configs[]')
        
        if not project_id:
            messages.error(request, 'Debe seleccionar un proyecto')
            return redirect('mediadisplay_config_add')
        
        try:
            project = Project.objects.get(id=project_id)
            
            if MediaDisplayConfig.objects.filter(project=project).exists():
                messages.warning(request, f'Ya existe configuración para el proyecto {project.name}')
                return redirect('mediadisplay_config_list')
            
            layer_configs_data = {}
            for layer_config_json in layer_configs:
                try:
                    layer_config = json.loads(layer_config_json)
                    layer_configs_data[layer_config['layerId']] = {
                        'order_field': layer_config['orderField'],
                        'media_fields': layer_config['mediaFields']
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error procesando configuración de capa: {e}")
                    continue
            
            config = MediaDisplayConfig.objects.create(
                project=project,
                layer_configs=layer_configs_data
            )
            
            messages.success(request, f'Configuración creada para el proyecto {project.name}')
            return redirect('mediadisplay_config_list') 
            
        except Project.DoesNotExist:
            messages.error(request, 'Proyecto no encontrado')
            return redirect('mediadisplay_config_add')
    
    # GET - Mostrar formulario de selección de proyecto
    projects_with_config = MediaDisplayConfig.objects.values_list('project_id', flat=True)
    projects = Project.objects.exclude(id__in=projects_with_config).order_by('name')
    return render(request, 'mediadisplay_config_add.html', {
        'projects': projects
    })

@login_required
def config_edit(request, config_id):
    """Editar configuración de Media Display"""
    config = get_object_or_404(MediaDisplayConfig, id=config_id)
    
    if request.method == 'POST':
        layer_configs = request.POST.getlist('layer_configs[]')
        
        layer_configs_data = {}
        for layer_config_json in layer_configs:
            try:
                layer_config = json.loads(layer_config_json)
                layer_configs_data[layer_config['layerId']] = {
                    'order_field': layer_config['orderField'],
                    'media_fields': layer_config['mediaFields']
                }
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error procesando configuración de capa: {e}")
                continue
        
        config.layer_configs = layer_configs_data
        config.save()
        
        messages.success(request, 'Configuración actualizada correctamente')
        return redirect('mediadisplay_config_list')
    
    # Obtener capas del proyecto para mostrar en el formulario
    try:
        from django.test import RequestFactory
        from gvsigol_plugin_projectapi.api import ProjectLayersView
        
        factory = RequestFactory()
        internal_request = factory.get(f'/api/v1/projects/{config.project.id}/layers/')
        internal_request.user = request.user
        
        view = ProjectLayersView()
        response = view.get(internal_request, project_id=config.project.id)
        
        if response.status_code == 200:
            if hasattr(response, 'data'):
                layers_data = response.data
            else:
                layers_data = json.loads(response.content)
            
            
            configured_layer_ids = list(config.layer_configs.keys())
            
            layers = []
            
            if isinstance(layers_data, dict):
                layers_list = layers_data.get('content', [])
            elif isinstance(layers_data, list):
                layers_list = layers_data
            else:
                layers_list = []
            
            for i, layer in enumerate(layers_list):
                
                if isinstance(layer, dict):
                    layer_type = layer.get('type', '')
                    if layer_type == 'WMS' or layer_type == 'OSM':
                        continue
                        
                    layer_id = str(layer.get('layer_id', layer.get('id')))
                    layer_config = config.layer_configs.get(layer_id, {})
                    
                    layers.append({
                        'id': layer_id,
                        'name': layer.get('name', ''),
                        'title': layer.get('title', layer.get('name', '')),
                        'enabled': layer_id in configured_layer_ids,
                        'config': layer_config
                    })
                else:
                    pass
            
        else:
            layers = []
            messages.error(request, 'Error obteniendo capas del proyecto')
            
    except Exception as e:
        import traceback
        layers = []
        messages.error(request, f'Error obteniendo capas: {str(e)}')
    
    return render(request, 'mediadisplay_config_edit.html', {
        'config': config,
        'layers': layers
    })

@login_required
def config_delete(request, config_id):
    """Eliminar configuración de Media Display"""
    config = get_object_or_404(MediaDisplayConfig, id=config_id)
    project_name = config.project.name
    
    if request.method == 'POST': 
        config.delete()
        messages.success(request, f'Configuración eliminada para el proyecto {project_name}')
        return redirect('mediadisplay_config_list')
    
    return render(request, 'mediadisplay_config_delete.html', {
        'config': config
    })

@login_required
def get_project_layers(request):
    """Obtener capas de un proyecto específico usando el endpoint de projectapi"""
    try:
        project_id = request.GET.get('project_id')
        
        if not project_id:
            return JsonResponse({'error': 'project_id is required'}, status=400)
        
        project = Project.objects.get(id=project_id)
        
        # Usar el endpoint existente de projectapi internamente
        try:
            from django.test import RequestFactory
            from gvsigol_plugin_projectapi.api import ProjectLayersView
            
            # Crear una petición simulada
            factory = RequestFactory()
            internal_request = factory.get(f'/api/v1/projects/{project_id}/layers/')
            internal_request.user = request.user
            
            view = ProjectLayersView()
            response = view.get(internal_request, project_id=project_id)
            
            if response.status_code == 200:
                try:
                    if hasattr(response, 'data'):
                        layers_data = response.data
                    else:
                        layers_data = json.loads(response.content)
                except json.JSONDecodeError as e:
                    return JsonResponse({'error': f'Error parsing JSON: {str(e)}'}, status=500)            

                if isinstance(layers_data, dict):
                    layers_list = layers_data.get('content', [])
                elif isinstance(layers_data, list):
                    layers_list = layers_data
                else:
                    return JsonResponse({'error': f'Expected dict or list, got {type(layers_data)}'}, status=500)
                
                if not isinstance(layers_list, list):
                    return JsonResponse({'error': f'Expected list in content, got {type(layers_list)}'}, status=500)
                
                layers = []
                for layer in layers_list:
                    if isinstance(layer, dict):
                        # Filtrar capas que no tienen campos configurables
                        layer_type = layer.get('type', '')
                        if layer_type == 'WMS' or layer_type == 'OSM':
                            continue
                        
                        layers.append({
                            'id': layer.get('id'),
                            'name': layer.get('name', ''),
                            'title': layer.get('title', layer.get('name', ''))
                        })
                    else:
                        pass 
              
                return JsonResponse({
                    'project_name': project.name,
                    'layers': layers
                })
            else:
                return JsonResponse({'error': f'Error obteniendo capas del proyecto: {response.status_code}'}, status=response.status_code)
                
        except Exception as e:
            import traceback
            return JsonResponse({'error': f'Error interno: {str(e)}\n{traceback.format_exc()}'}, status=500)
        
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['GET'])
def get_config(request):
    """Obtener configuración para el frontend"""

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    try:
        project_id = request.GET.get('project_id')
        
        if not project_id:
            return JsonResponse({'error': 'project_id is required'}, status=400)
        
        try:
            project = Project.objects.get(id=project_id)
            
            try:
                config = MediaDisplayConfig.objects.get(project=project)
                layer_configs = config.layer_configs
            except MediaDisplayConfig.DoesNotExist:
                layer_configs = {}
            
            return JsonResponse({
                'layer_configs': layer_configs
            })
            
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_layer_fields(request):
    """Obtener campos de una capa específica"""
    try:
        layer_id = request.GET.get('layer_id')
        
        if not layer_id:
            return JsonResponse({'error': 'layer_id is required'}, status=400)
        
        layer = Layer.objects.get(id=layer_id)
        
        fields = []
        
        layer_config = layer.get_config_manager()
        field_configs = layer_config.get_field_viewconf(include_pks=False)

        for field in field_configs:
            if field.get('editable', True):
                fields.append({
                    'id': field.get('name', ''),
                    'name': field.get('name', ''),
                    'type': field.get('type', ''),
                    'title': field.get('title', field.get('name', '')),
                    'visible': field.get('visible', True),
                    'editable': field.get('editable', True)
                })
        
        return JsonResponse({
            'success': True,
            'fields': fields,
            'layer_name': layer.name
        })
        
    except Layer.DoesNotExist:
        return JsonResponse({'error': 'Layer not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 