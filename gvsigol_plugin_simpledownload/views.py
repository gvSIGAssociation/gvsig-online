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
from django.core.files.storage import default_storage
from django.conf import settings as django_settings
from gvsigol_core.models import Project
from .models import SimpleDownloadConfig
from . import settings
import json
import os
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
            
            file_configs_data = []
            for idx, file_config_json in enumerate(file_configs):
                try:
                    file_config = json.loads(file_config_json)
                    file_id = file_config['fileId']
                    
                    file_url = file_config.get('file_url', '').strip()
                    uploaded_file_key = f'uploaded_file_{file_id}'
                    
                    if uploaded_file_key in request.FILES:
                        uploaded_file = request.FILES[uploaded_file_key]
                        upload_dir = os.path.join('simpledownload_files', str(project.id))
                        os.makedirs(os.path.join(django_settings.MEDIA_ROOT, upload_dir), exist_ok=True)
                        
                        file_path = os.path.join(upload_dir, uploaded_file.name)
                        full_path = os.path.join(django_settings.MEDIA_ROOT, file_path)
                        
                        if os.path.exists(full_path):
                            os.remove(full_path)
                        
                        saved_path = default_storage.save(file_path, uploaded_file)
                        file_url = django_settings.MEDIA_URL + saved_path
                    
                    file_configs_data.append({
                        'id': int(file_id),
                        'title': file_config['title'],
                        'description': file_config['description'],
                        'file_url': file_url,
                        'updated_at': file_config['updated_at']
                    })
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
        old_file_urls = set()
        old_configs = config.file_configs or []
        if isinstance(old_configs, list):
            for file_config in old_configs:
                file_url = file_config.get('file_url', '')
                if file_url and file_url.startswith(django_settings.MEDIA_URL):
                    old_file_urls.add(file_url)
        elif isinstance(old_configs, dict):
            for file_config in old_configs.values():
                file_url = file_config.get('file_url', '')
                if file_url and file_url.startswith(django_settings.MEDIA_URL):
                    old_file_urls.add(file_url)

        file_configs = request.POST.getlist('file_configs[]')
        file_configs_data = []
        new_file_urls = set()
        
        for file_config_json in file_configs:
            try:
                file_config = json.loads(file_config_json)
                file_id = file_config.get('fileId')
                if not file_id:
                    continue

                file_url = file_config.get('file_url', '').strip()
                uploaded_file_key = f'uploaded_file_{file_id}'
                
                if uploaded_file_key in request.FILES:
                    uploaded_file = request.FILES[uploaded_file_key]
                    upload_dir = os.path.join('simpledownload_files', str(config.project.id))
                    os.makedirs(os.path.join(django_settings.MEDIA_ROOT, upload_dir), exist_ok=True)
                    
                    file_path = os.path.join(upload_dir, uploaded_file.name)
                    full_path = os.path.join(django_settings.MEDIA_ROOT, file_path)
                    
                    if os.path.exists(full_path):
                        os.remove(full_path)
                    
                    saved_path = default_storage.save(file_path, uploaded_file)
                    file_url = django_settings.MEDIA_URL + saved_path

                file_configs_data.append({
                    'id': int(file_id),
                    'title': file_config.get('title', ''),
                    'description': file_config.get('description', ''),
                    'file_url': file_url,
                    'updated_at': file_config.get('updated_at')
                })
                
                if file_url and file_url.startswith(django_settings.MEDIA_URL):
                    new_file_urls.add(file_url)
                    
            except (json.JSONDecodeError, KeyError) as exc:
                print(f"Error procesando configuración de archivo: {exc}")
                continue

        files_to_delete = old_file_urls - new_file_urls
        for file_url in files_to_delete:
            try:
                file_path = file_url.replace(django_settings.MEDIA_URL, '', 1)
                full_path = os.path.join(django_settings.MEDIA_ROOT, file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"Archivo eliminado: {full_path}")
            except Exception as e:
                print(f"Error al eliminar archivo {file_url}: {e}")

        config.file_configs = file_configs_data
        config.save()

        messages.success(request, 'Configuración actualizada correctamente')
        return redirect('simpledownload_config_list')
     
    file_configs_list = config.file_configs or []
    
    if isinstance(file_configs_list, dict):
        files = []
        for file_id, file_config in sorted(file_configs_list.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0):
            files.append({
                'id': int(file_id),
                'title': file_config.get('title', ''),
                'description': file_config.get('description', ''),
                'file_url': file_config.get('file_url', ''),
                'updated_at': file_config.get('updated_at')
            })
    else:
        files = sorted(file_configs_list, key=lambda x: x.get('id', 0))

    # Convertir lista a objeto para el JavaScript (usando id como key)
    file_configs_obj = {}
    for file in files:
        file_configs_obj[str(file['id'])] = file

    return render(request, 'simpledownload_config_edit.html', {
        'config': config,
        'files': files,
        'initial_file_configs_json': json.dumps(file_configs_obj)
    })

@login_required
def config_delete(request, config_id):
    """Eliminar configuración de Simple Download"""
    config = get_object_or_404(SimpleDownloadConfig, id=config_id)
    project_name = config.project.name
    project_id = config.project.id
    
    if request.method == 'POST':
        project_dir = os.path.join(django_settings.MEDIA_ROOT, 'simpledownload_files', str(project_id))
        if os.path.exists(project_dir):
            try:
                import shutil
                shutil.rmtree(project_dir)
            except Exception as e:
                print(f"Error al eliminar carpeta {project_dir}: {e}")
        
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
                file_configs = config.file_configs or []
                
                if isinstance(file_configs, dict):
                    file_list = []
                    for file_id, file_data in sorted(file_configs.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0):
                        file_item = file_data.copy()
                        file_item['id'] = int(file_id)
                        file_list.append(file_item)
                    file_configs = file_list
                else:
                    file_configs = sorted(file_configs, key=lambda x: x.get('id', 0))
                    
            except SimpleDownloadConfig.DoesNotExist:
                file_configs = []
            
            return JsonResponse({
                'files': file_configs
            })
            
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
