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
from gvsigol_core.models import Project
from .models import SimpleDownloadConfig
from . import settings
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@login_required
def config_list(request):
    """Lista de configuraciones de Simple Download"""
    configs = SimpleDownloadConfig.objects.all().order_by('-created_at')
    
    paginator = Paginator(configs, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'simpledownload_config_list.html', {
        'page_obj': page_obj,
        'configs': page_obj
    })

@login_required
def config_add(request):
    """Añadir nueva configuración de Simple Download"""
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        file_configs = request.POST.getlist('file_configs[]')
        
        if not project_id:
            messages.error(request, 'Debe seleccionar un proyecto')
            return redirect('simpledownload_config_add')
        
        try:
            project = Project.objects.get(id=project_id)
            
            if SimpleDownloadConfig.objects.filter(project=project).exists():
                messages.warning(request, f'Ya existe configuración para el proyecto {project.name}')
                return redirect('simpledownload_config_list')
            
            file_configs_data = {}
            for file_config_json in file_configs:
                try:
                    file_config = json.loads(file_config_json)
                    file_configs_data[file_config['fileId']] = {
                        'title': file_config['title'],
                        'description': file_config['description'],
                        'file_url': file_config['file_url'],
                        'updated_at': file_config['updated_at']
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error procesando configuración de archivo: {e}")
                    continue
            
            config = SimpleDownloadConfig.objects.create(
                project=project,
                file_configs=file_configs_data
            )
            
            messages.success(request, f'Configuración creada para el proyecto {project.name}')
            return redirect('simpledownload_config_list') 
            
        except Project.DoesNotExist:
            messages.error(request, 'Proyecto no encontrado')
            return redirect('simpledownload_config_add')
    
    # GET - Mostrar formulario de selección de proyecto
    projects_with_config = SimpleDownloadConfig.objects.values_list('project_id', flat=True)
    projects = Project.objects.exclude(id__in=projects_with_config).order_by('name')
    return render(request, 'simpledownload_config_add.html', {
        'projects': projects
    })

@login_required
def config_edit(request, config_id):
    """Editar configuración de Simple Download"""
    config = get_object_or_404(SimpleDownloadConfig, id=config_id)
    
    if request.method == 'POST':
        file_configs = request.POST.getlist('file_configs[]')

        file_configs_data = {}
        for file_config_json in file_configs:
            try:
                file_config = json.loads(file_config_json)
                file_id = str(file_config.get('fileId'))
                if not file_id:
                    continue

                file_configs_data[file_id] = {
                    'title': file_config.get('title', ''),
                    'description': file_config.get('description', ''),
                    'file_url': file_config.get('file_url', ''),
                    'updated_at': file_config.get('updated_at')
                }
            except (json.JSONDecodeError, KeyError) as exc:
                print(f"Error procesando configuración de archivo: {exc}")
                continue

        config.file_configs = file_configs_data
        config.save()

        messages.success(request, 'Configuración actualizada correctamente')
        return redirect('simpledownload_config_list')
     
    file_configs_dict = config.file_configs or {}
    files = []

    try:
        sorted_items = sorted(
            file_configs_dict.items(),
            key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0])
        )
    except Exception:
        sorted_items = file_configs_dict.items()

    for file_id, file_config in sorted_items:
        files.append({
            'id': str(file_id),
            'title': file_config.get('title', ''),
            'description': file_config.get('description', ''),
            'file_url': file_config.get('file_url', ''),
            'updated_at': file_config.get('updated_at')
        })

    return render(request, 'simpledownload_config_edit.html', {
        'config': config,
        'files': files,
        'initial_file_configs_json': json.dumps(file_configs_dict)
    })

@login_required
def config_delete(request, config_id):
    """Eliminar configuración de Simple Download"""
    config = get_object_or_404(SimpleDownloadConfig, id=config_id)
    project_name = config.project.name
    
    if request.method == 'POST': 
        config.delete()
        messages.success(request, f'Configuración eliminada para el proyecto {project_name}')
        return redirect('simpledownload_config_list')
    
    return render(request, 'simpledownload_config_delete.html', {
        'config': config
    })

@csrf_exempt
@require_http_methods(['GET'])
def get_config(request):
    """Obtener configuración para el frontend"""

    try:
        project_id = request.GET.get('project_id')
        
        if not project_id:
            return JsonResponse({'error': 'project_id is required'}, status=400)
        
        try:
            project = Project.objects.get(id=project_id)
            
            try:
                config = SimpleDownloadConfig.objects.get(project=project)
                file_configs = config.file_configs
            except SimpleDownloadConfig.DoesNotExist:
                file_configs = {}
            
            return JsonResponse({
                'file_configs': file_configs
            })
            
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
