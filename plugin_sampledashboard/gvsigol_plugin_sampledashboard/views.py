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
@author: nbrodin <nbrodin@scolab.es>
'''

from django.shortcuts import HttpResponse, render, redirect
from .models import SampleDashboard
from django.contrib.auth.decorators import login_required
from . import settings
import json

def get_conf(request):
    if request.method == 'POST': 
        response = {
            'sample_url': settings.SAMPLE_URL
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')           

@login_required(login_url='/gvsigonline/auth/login_user/')
def sampledashboard_list(request):
    response = {
        'samples': get_list()
    }
    return render(request, 'dashboard_list.html', response)

def get_list():
    sample_list = SampleDashboard.objects.all()
    
    samples = []
    for lg in sample_list:
        sample = {}
        sample['id'] = lg.id
        sample['name'] = lg.name
        sample['title'] = lg.title
        sample['description'] = lg.description
        samples.append(sample)
    return samples

@login_required(login_url='/gvsigonline/auth/login_user/')
def sampledashboard_add(request):
    if request.method == 'POST':
        sample = SampleDashboard(
            name = request.POST.get('sample_name'),
            title = request.POST.get('sample_title'),
            description = request.POST.get('sample_description')
        )
        sample.save()
   
        return redirect('sampledashboard_list')
    else:
        response = {
        }
        return render(request, 'dashboard_add.html', response)
    
@login_required(login_url='/gvsigonline/auth/login_user/')
def sampledashboard_update(request):
    if request.method == 'GET':
        lgid = request.GET['lgid']
        instance  = SampleDashboard.objects.get(id=int(lgid))
        response = {
            'id':lgid,
            'name':instance.name,
            'title':instance.title,
            'description':instance.description
        }
        return render(request, 'dashboard_update.html', response)
    else:
        sample = SampleDashboard(
            id = int(request.POST.get('sample_id')),
            name = request.POST.get('sample_name'),
            title = request.POST.get('sample_title'),
            description = request.POST.get('sample_description')
        )
        sample.save()
        return redirect('sampledashboard_list')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
def sampledashboard_delete(request):
    lgid = request.POST['lgid']
    if request.method == 'POST':
        instance  = SampleDashboard.objects.get(id=int(lgid))
        #instance = SampleDashboard().objects.filter(id=int(lgid))
        instance.delete()
    response = {}
    return render(request, 'dashboard_add.html', response)
            
    
    