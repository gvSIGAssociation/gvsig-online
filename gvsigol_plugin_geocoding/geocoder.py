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
from gvsigol_plugin_geocoding.googlemaps import GoogleMaps
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.core.exceptions import ImproperlyConfigured
from urlparse import urlparse
import settings
from cartociudad import Cartociudad
from nominatim import Nominatim 
import json, ast

class Geocoder():
    
    def __init__(self):
        self.geocoders=[]#
        
    def add_provider(self, provider):
        for geocoder in self.geocoders:
            type = provider.type
            if type == 'user':
                type = 'cartociudad'
            if geocoder.has_key(type):
                geocoder[type].append(provider)
                return
        
        geocoder = {}
        if provider.type == 'nominatim':
            geocoder[provider.type] = Nominatim(provider)
            self.geocoders.append(geocoder)
            
        if provider.type == 'googlemaps':
            geocoder[provider.type] = GoogleMaps(provider)
            self.geocoders.append(geocoder)
            
        if provider.type == 'cartociudad' or provider.type == 'user':
            geocoder['cartociudad'] = Cartociudad(provider, provider.type)
            self.geocoders.append(geocoder)
        
          
    def search_candidates(self, query):
        suggestions = []
        
        for geocoder_types in self.geocoders:
            for geocoder_type in geocoder_types:
                geocoder = geocoder_types[geocoder_type]
                if suggestions == []:
                    suggestions = geocoder.geocode(query, exactly_one=False)
                else:
                    aux = geocoder.geocode(query, exactly_one=False)
                    suggestions = suggestions + aux
                 
        response = {
            "query": query,
            "suggestions": suggestions
        }
        
        return response
    
    
    def find_candidate(self, address):
        location = {}
        address_json = json.loads(address)
        type = address_json["address[source]"]
        if type == 'user':
            type = 'cartociudad'
                
        for geocoder_types in self.geocoders:
            for geocoder_type in geocoder_types:
                geocoder = geocoder_types[geocoder_type]
                if geocoder.get_type() == type:
                    location = geocoder.find(address,exactly_one=True)
                 
        response = {
            "address": location
        }
   
        return response
            
    def get_location_address(self, query, type):
        point = query.split(',')
        coordinate = [point[0], point[1]]
        loc = {}
        
        for geocoder_types in self.geocoders:
            for geocoder_type in geocoder_types:
                geocoder = geocoder_types[geocoder_type]
                if geocoder.get_type() == type:
                    loc = geocoder.reverse(coordinate,exactly_one=True,language='es')

        return loc
    
    
    def get_reverse_location(self, lat, lon):
        coordinate = [lat, lon]
        loc = self.geolocator.reverse(coordinate,exactly_one=True,language='es')
        location = {
            'title': loc.address,
            'address': loc._raw['address'],
            'latitude': loc.latitude,
            'longitude': loc.longitude
        }
        
        return location
        

