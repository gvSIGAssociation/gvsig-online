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
from django.utils.translation import ugettext as _
from geopy.compat import urlencode
from geopy.util import logger
import settings
import urllib2
import json, requests, ast
from urlparse import urlparse
    
class CartoCiudad2():
    
    def __init__(self, provider):
        self.urls = settings.GEOCODING_PROVIDER['new_cartociudad']
        self.postal_codes = self.urls['cod_postal_filter']
        self.providers=[]
        self.append(provider)
        self.category = provider.category
        
    
    def is_unique_instance(self):
        return True
    
    def get_type(self):
        return 'new_cartociudad'
        
        
    def append(self, provider):
        self.providers.append(provider)
        
    
    def geocode(self, query, exactly_one):
        '''
        www.cartociudad.es/geocoder/api/geocoder/candidatesJsonp?q=blasco ibañez&limit=10        
        '''
        params = {
            'q': query,
            'autocancel': True,
            'limit': self.urls['max_results'],
            'cod_postal_filter': self.postal_codes
        }

        json_results = []
        if self.providers.__len__() > 0 :
            provider = self.providers[0]
            json_results = self.get_json_from_url(self.urls['candidates_url'], params)
            for json_result in json_results:
                json_result['category'] = provider.category
                json_result['image'] = str(provider.image)
            
        return json_results
    
    
    def find(self, address_str, exactly_one):
        '''
        http://www.cartociudad.es/geocoder/api/geocoder/findJsonp?q=blasco ibañez   
        '''
        address = json.loads(address_str)
        
        params = {}
        if 'address[id]' in address:
           params = {
                'id': address['address[id]'],
                'address': address['address[address]'],
                'source': 'new_cartociudad',
                'type': address['address[type]'],
                'tip_via': address['address[tip_via]'],
                'portal': address['address[portalNumber]'],
                'cod_postal_filter': settings.CARTOCIUDAD_INE_MUN_FILTER
            } 
        else:
            params = {
                'id': address['id'],
                'address': address['address'],
                'source': 'new_cartociudad',
                'type': address['type'],
                'tip_via': address['tip_via'],
                'portal': address['portalNumber'],
                'cod_postal_filter': settings.CARTOCIUDAD_INE_MUN_FILTER
            }

        #url = "?".join((self.urls['candidates_url'], urlencode(params)))
        json_result =  self.get_json_from_url(self.urls['find_url'], params)
        if not json_result:
            updated_data = False
            for provider in self.providers:
                if provider.type == 'cartociudad':
                    updated_data = self.set_database_config(provider)    
            if updated_data:
                json_result = self.get_json_from_url(self.urls['find_url'], params)
                
        return json_result
        
        

    def reverse(self, coordinate, exactly_one, language): 
        '''
        http://www.cartociudad.es/geocoder/api/geocoder/reverseGeocode?lon=-4.702148&lat=39.727469
        '''
        params = {
            'lat': coordinate[1],
            'lon': coordinate[0]
        }
        
        json_result =  self.get_json_from_url(self.urls['reverse_url'], params)
        if isinstance(json_result, dict):
            json_result['source'] = self.get_type()
                
            return json_result
        
        parse_result = {
                    'address': _('Not founded'),
                    'lat': coordinate[1], 
                    'lng': coordinate[0]
                }
        return parse_result
    
    
    @staticmethod   
    def get_json_from_url(url, params):
        response = requests.get(url=url, params=params)
        if response.status_code == 200:
            respuesta = response.content
            if respuesta.startswith('callback('):
                respuesta = respuesta['callback('.__len__():-1]
    
            data = json.loads(respuesta)
            if data:
                if 'address' in params:
                    data['address'] = params['address']
                return data
        return []
        
        