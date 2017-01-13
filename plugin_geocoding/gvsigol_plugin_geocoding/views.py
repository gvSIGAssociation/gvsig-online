# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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

from django.shortcuts import HttpResponse
from geocoder import geocoder
import settings
import json

def get_conf(request):
    if request.method == 'POST': 
        response = {
            'candidates_url': settings.GEOCODING_PROVIDER['cartociudad']['candidates_url'],
            'find_url': settings.GEOCODING_PROVIDER['cartociudad']['find_url'],
            'reverse_url': settings.GEOCODING_PROVIDER['cartociudad']['reverse_url']
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')           

def search_candidates(request):
    if request.method == 'GET':
        query = request.GET.get('query')           
        suggestions = geocoder.search_candidates(query)
            
        return HttpResponse(json.dumps(suggestions, indent=4), content_type='application/json')

def get_location_address(request):
    if request.method == 'POST':
        query = request.POST.get('query')
        location = geocoder.get_location_address(query)
        
        return HttpResponse(json.dumps(location, indent=4), content_type='application/json')
