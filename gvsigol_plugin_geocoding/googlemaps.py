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
@author: Jose Badia <jbadia@scolab.es>
'''
from geopy.compat import urlencode
from geopy.util import logger
from geopy.geocoders import Nominatim as Nominatim_geocoder
import settings
import urllib2
import json, requests, ast
from urlparse import urlparse
    
class GoogleMaps():
    
    def __init__(self, provider):
        self.urls = settings.GEOCODING_PROVIDER['googlemaps']
        self.key = self.urls['key']
        self.providers=[]
        self.append(provider)
        self.category = provider.category
        
    
    def is_unique_instance(self):
        return True
    
    def get_type(self):
        return 'googlemaps'
        
        
    def append(self, provider):
        self.providers.append(provider)
        
    
    def geocode(self, query, exactly_one):
        '''
        https://maps.googleapis.com/maps/api/place/autocomplete/xml?input=blasco&key=AIzaSyDRJwLAQS6t8LP-rnv0IBhkp6fT4lHjV1w
        '''
        params = {
            'input': query,
            'key': self.key
        }

        parse_results = []
        
        if self.providers.__len__() > 0 :
            provider = self.providers[0]
        
            json_results = self.get_json_from_url(self.urls['candidates_url'], params)
            
            if 'predictions' in json_results:
                for result in json_results['predictions']:
                    parse_result = {
                        'address': result['description'],
                        'type': 'googlemaps', 
                        'source': 'googlemaps', 
                        'category': self.category,
                        'data': result, 
                        'image': str(provider.image)
                    }
                parse_results.append(parse_result)
        return parse_results
    
    
    def find(self, address_str, exactly_one):
        '''
        https://maps.googleapis.com/maps/api/geocode/xml?address=Blasco Ibáñez, Valencia, Spain
        '''
        address_json = json.loads(address_str)
        query = address_json['address[data][description]']
        
        params = {
            'address': query
        }

        json_results = self.get_json_from_url(self.urls['find_url'], params)
        if 'results' in json_results:
            for result in json_results['results']:
                parse_result = {
                    'address': result['formatted_address'],
                    'lat': result['geometry']['location']['lat'], 
                    'lng': result['geometry']['location']['lng']
                }
                return parse_result
        return {}
        
        

    def reverse(self, coordinate, exactly_one, language): 
        '''
        https://maps.googleapis.com/maps/api/geocode/xml?latlng=39.4747822,-0.3492295
        '''
        params = {
            'latlng': str(coordinate[1])+','+str(coordinate[0])
        }
        
        json_results = self.get_json_from_url(self.urls['reverse_url'], params)
        if 'results' in json_results:
            for result in json_results['results']:
                parse_result = {
                    'address': result['formatted_address'],
                    'lat': result['geometry']['location']['lat'], 
                    'lng': result['geometry']['location']['lng']
                }
                return parse_result
        return {}
      
    
    
    @staticmethod   
    def get_json_from_url(url, params):
        response = requests.get(url=url, params=params)
        if response.status_code == 200:
            respuesta = response.content
            if respuesta.startswith('callback('):
                respuesta = respuesta['callback('.__len__():-1]
    
            data = json.loads(respuesta)
            if data:
                return data
        return []
    
        