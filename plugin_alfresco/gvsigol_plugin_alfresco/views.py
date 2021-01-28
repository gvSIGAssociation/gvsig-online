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
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''

from gvsigol_services.models import Layer, LayerResource
from gvsigol_plugin_alfresco.services import resource_manager
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

import logging
import json

logger = logging.getLogger(__name__)

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def get_sites(request):    
    try:
        default_repo = resource_manager.get_default_repository() 
        sites =  resource_manager.get_sites(default_repo)
                         
        response = {
            'sites': sites
        }
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
                    
    except Exception as e:
        return HttpResponseBadRequest(e.message)
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def get_folder_content(request):
    if request.method == 'POST':      
        object_id = request.POST.get('object_id')    
        
        try:
            default_repo = resource_manager.get_default_repository()
            folder_content = resource_manager.get_folder_content(default_repo, object_id)
                        
            response = {
                'folder_content': folder_content
            }
            
            return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
                        
        except:
            return HttpResponseBadRequest('<h1>Failed to get folder content</h1>')

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def save_resource(request):
    if request.method == 'POST':      
        path = request.POST.get('path')  
        ws_name = request.POST.get('workspace')
        layer_name = request.POST.get('layer_name')
        fid = request.POST.get('fid')
 
        try:
            if ":" in layer_name:
                layer_name = layer_name.split(":")[1]
            layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name) 
        
            res = LayerResource()
            res.feature = int(fid)
            res.layer = layer
            res.path = resource_manager.get_repository_url() + '#filter=path|' + path
            res.title = ''
            res.type = LayerResource.EXTERNAL_ALFRESCO_DIR
            res.created = timezone.now()
            res.save()
                        
            response = {'success': True}
            
            return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
                        
        except:
            return HttpResponseBadRequest('<h1>Failed to get folder content</h1>')
        
@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def update_resource(request):
    if request.method == 'POST':      
        path = request.POST.get('path')  
        ws_name = request.POST.get('workspace')
        layer_name = request.POST.get('layer_name')
        fid = request.POST.get('fid')
          
        try:
            if ":" in layer_name:
                layer_name = layer_name.split(":")[1]
            layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=int(fid))
            
            for resource in layer_resources:
                resource.path = resource_manager.get_repository_url() + '#filter=path|' + path
                resource.save()
                
            if len(layer_resources) <= 0:
                resource = LayerResource()
                resource.feature = int(fid)
                resource.layer = layer
                resource.path = resource_manager.get_repository_url() + '#filter=path|' + path
                resource.title = ''
                resource.type = LayerResource.EXTERNAL_ALFRESCO_DIR
                resource.created = timezone.now()
                resource.save()
                        
            response = {'success': True}
            
            return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
                        
        except:
            return HttpResponseBadRequest('<h1>Failed to get folder content</h1>')
        
@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def delete_resource(request):
    if request.method == 'POST':
        rid = request.POST.get('rid')
        try:
            resource = LayerResource.objects.get(id=int(rid)) 
            resource.delete()
            resource_manager.delete_resource(resource)
            response = {'deleted': True}
            
        except Exception as e:
            response = {'deleted': False}
            pass
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')