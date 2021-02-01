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
@author: jvhigon <jvhigon@scolab.es>
'''
from .models import WorldwindProvider
from .forms import DirectoryPath
from . import settings
from . import services

from django.contrib.auth.decorators import login_required
from gvsigol_auth.utils import superuser_required
from django.shortcuts import render, redirect
from gvsigol.settings import FILEMANAGER_DIRECTORY
from django.http import  HttpResponse
import json
from django.utils.translation import ugettext as _
from django.db import IntegrityError




def index(request):
    return redirect('home')

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def list(request):
    
    provider_list = WorldwindProvider.objects.all()
    
    providers = []
    for i in provider_list:
        provider = {}
        provider['id'] = i.id
        #provider['name'] = i.name
        provider['type'] = i.type
        provider['path'] = i.path
        provider['project'] = i.project
        provider['heightUrl'] = i.heightUrl
        provider['layers'] = i.layers
        providers.append(provider)
                      
    response = {
        'providers': providers
    }     
    return render(request, 'ww_providers_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def add(request):
    try:
        if request.method == 'POST':   
            form = DirectoryPath(request.POST);
            #name = form.cleaned_data['name'];     
            if form.is_valid():
                dir_path =  form.cleaned_data['directory_path'];     
                project = form.cleaned_data['projects'];
                type = form.cleaned_data['type'];
                heightUrl = form.cleaned_data['heightUrl'];
                layers = form.cleaned_data['layers'];
                if type == 'url':
                    provider = WorldwindProvider(
                        type = type, path = dir_path,
                         project = project, heightUrl = heightUrl,
                         layers = layers
                        )             
                    provider.save()           
                    return redirect('list')
                else:                    
                    if services.create_service_wms(project.id, dir_path) is False:
                        form.add_error(None, _("Error: Problem creating mapfile."))
                    else:           
                        provider = WorldwindProvider(
                            type = 'mapserver', path = dir_path, project = project, 
                            heightUrl = '', layers = layers)             
                        provider.save()           
                        return redirect('list')          
        else:
            form = DirectoryPath();      
            return render(request, 'ww_provider_add.html',  {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form})  
    except IntegrityError as e:
        form.add_error(None, _("Error: Provider already defined for this project."))    
        return render(request, 'ww_provider_add.html',  {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form})
    except Exception as e:        
        form.add_error(None, _("Error: "))
        form.add_error(None, str(e))    
        return render(request, 'ww_provider_add.html',  {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form})


@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def delete(request,id):
    try:
        if request.method == 'POST':        
            provider = WorldwindProvider.objects.get(id=id)
            provider.delete()            
            response = {
                'deleted': True
            }     
            return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')                         
        else:
            return redirect('list')
    except Exception as e:
        print(e)


def conf(request, id):
    try:
        try:
            provider = WorldwindProvider.objects.get(project=id)
            if (provider.type == 'url'):
                url = provider.heightUrl
            else:
                url = settings.MAPSERVER_URL + "?map=" + provider.path + "/" + str(id) + ".map" 
            baseLayerType = settings.WORLDWIND_DEFAULT_PROVIDER.get('baseLayerType')                   
            response = {
                    'provider_url': url,
                    'provider_version': '1.3.0',
                    'provider_layers': provider.layers,
                    'baseLayer': baseLayerType
            }  
        except WorldwindProvider.DoesNotExist:
            response = settings.WORLDWIND_DEFAULT_PROVIDER           
   
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')           
        
    except Exception as e:
        print(e)
