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
from models import WorldwindProvider
from forms import DirectoryPath
import settings
import services

from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from gvsigol_auth.utils import superuser_required
from django.shortcuts import render_to_response, redirect
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
        provider['path'] = i.path
        provider['project'] = i.project
        providers.append(provider)
                      
    response = {
        'providers': providers
    }     
    return render_to_response('ww_providers_list.html', response, context_instance=RequestContext(request))

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
                if services.create_service_wms(project.id, dir_path) is False:
                    form.add_error(None, _("Error: Problem creating mapfile."))
                else:           
                    provider = WorldwindProvider(path = dir_path, project = project)             
                    provider.save()           
                    return redirect('list')          
        else:
            form = DirectoryPath();      
            return render_to_response('ww_provider_add.html',  {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form}, context_instance=RequestContext(request))  
    except IntegrityError as e:
        form.add_error(None, _("Error: Provider already defined for this project."))    
        return render_to_response('ww_provider_add.html',  {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form}, context_instance=RequestContext(request))
    except Exception as e:        
        form.add_error(None, _("Error: "))
        form.add_error(None, str(e))    
        return render_to_response('ww_provider_add.html',  {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form}, context_instance=RequestContext(request))


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
        print e

@login_required(login_url='/gvsigonline/auth/login_user/')
def conf(request, id):
    try:
        try:
            provider = WorldwindProvider.objects.get(project=id)
            url = settings.MAPSERVER_URL + "?map=" + provider.path + "/" + str(id) + ".map" 
            baseLayerType = settings.WORLDWIND_DEFAULT_PROVIDER.get('baseLayerType')                   
            response = {
                    'provider_url': url,
                    'provider_version': '1.3.0',
                    'provider_layers': 'elevation',
                    'baseLayer': baseLayerType
            }  
        except WorldwindProvider.DoesNotExist:
            response = settings.WORLDWIND_DEFAULT_PROVIDER           
   
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')           
        
    except Exception as e:
        print e
