# -*- coding: utf-8 -*-
'''
    gvSIG Online.
    Copyright (C) SCOLAB.

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

from django.utils.translation import ugettext as _
from . import settings
from gvsigol import settings as core_settings
import json, requests
from .models import Provider
    
class CartoCiudad2():
    
    def __init__(self, provider):
        self.urls = settings.GEOCODING_PROVIDER['new_cartociudad']
        provider_params = json.loads(provider.params)
        self.postal_codes = provider_params.get('cod_postal_filter', '')
        self.poblacion_filter = provider_params.get('poblacion_filter')
        self.municipio_filter = provider_params.get('municipio_filter')
        self.provincia_filter = provider_params.get('provincia_filter')
        self.comunidad_autonoma_filter = provider_params.get('comunidad_autonoma_filter')
        
        self.limit = provider_params.get('max_results')
        self.providers=[
            provider
        ]
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
            'limit': self.limit,
            'cod_postal_filter': self.postal_codes
        }
        if self.poblacion_filter:
            params['poblacion_filter'] = self.poblacion_filter
        if self.municipio_filter:
            params['municipio_filter'] = self.municipio_filter
        if self.provincia_filter:
            params['provincia_filter'] = self.provincia_filter
        if self.comunidad_autonoma_filter:
            params['provincia_filter'] = self.comunidad_autonoma_filter

        if self.providers.__len__() > 0 :
            provider = self.providers[0]
            json_results = self.get_json_from_url(self.urls['candidates_url'], params)
            for json_result in json_results:
                json_result['category'] = provider.category
                json_result['image'] = str(provider.image)
                json_result['srs'] = 'EPSG:4258'

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
            json_result['srs'] = 'EPSG:4258'            
            return json_result
        
        parse_result = {
                    'address': _('Not founded'),
                    'lat': coordinate[1], 
                    'lng': coordinate[0],
                    'srs': 'EPSG:4258'
                }
        return parse_result
    
    
    @staticmethod   
    def get_json_from_url(url, params):
        response = requests.get(url=url, params=params)
        if response.status_code == 200:
            respuesta = response.text
            if respuesta.startswith('callback('):
                respuesta = respuesta['callback('.__len__():-1]
    
            data = json.loads(respuesta)
            if data:
                if 'address' in params:
                    data['address'] = params['address']
                return data
        return []
        
        