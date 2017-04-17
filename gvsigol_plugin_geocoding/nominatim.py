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
@author: Jose Badia <jbadia@scolab.es>
'''
from geopy.compat import urlencode
from geopy.util import logger
from geopy.geocoders import Nominatim as Nominatim_geocoder
import settings
import urllib2
import json, requests, ast
from urlparse import urlparse

class Nominatim():
    
    def __init__(self, provider):
        self.geolocators = []
        self.append(provider)
        
        
    def is_unique_instance(self):
        return True  
    
        
    def get_type(self):
        return 'nominatim'
    
    
    def append(self, provider):
        params = json.loads(ast.literal_eval(provider.params))
        url = params['url']
        country_code = params['country_codes']
        url_params = urlparse(url)
        scheme = url_params.scheme
        domain = url_params.netloc + url_params.path
        self.geolocators.append({
            'geocoder': Nominatim_geocoder(country_bias=country_code, scheme=scheme, domain=domain), 
            'provider': provider
        })
        
        
    def geocode(self, query, exactly_one):
        suggestions = []
        
        i=1
        for geolocator in self.geolocators:
            locations = geolocator['geocoder'].geocode(query,exactly_one=False)
            if locations:
                for l in locations:
                    suggestion = {}
                    suggestion['source'] = 'nominatim'
                    suggestion['type'] = 'nominatim-'+ str(geolocator['provider'].id)
                    suggestion['address'] = l.address
                    suggestion['id'] = l.address
                    suggestion['lat'] = l._raw['lat']
                    suggestion['lng'] = l._raw['lon'] 
                    suggestion['image'] = str(geolocator['provider'].image)
                    suggestion['category'] = geolocator['provider'].category
                    suggestions.append(suggestion)
            i=i+1
                
        response = suggestions
        
        return response
    
    
    def find(self, address_str, exactly_one):
        locations = json.loads(address_str)
        suggestion = {}
        suggestion['source'] = locations['address[source]']
        suggestion['type'] = locations['address[type]']
        suggestion['address'] = locations['address[address]']
        suggestion['id'] = locations['address[address]']
        suggestion['lat'] = locations['address[lat]']
        suggestion['lng'] = locations['address[lng]']

        return suggestion
        
        
    def reverse(self, coordinate, exactly_one, language): 
        #point = query.split(',')
        coordinate2 = [coordinate[1], coordinate[0]]
        suggestion = {}
        for geolocator in self.geolocators:
            l = geolocator['geocoder'].reverse(coordinate2,exactly_one=True,language='es')
            suggestion = {}
            suggestion['source'] = 'nominatim'
            suggestion['type'] = 'nominatim'
            suggestion['address'] = l.address
            suggestion['id'] = l.address
            suggestion['lat'] = l._raw['lat']
            suggestion['lng'] = l._raw['lon'] 
        
            return suggestion
        return suggestion
        