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
import os
from . import settings

from django.utils.translation import ugettext as _
from geopy.util import logger
from gvsigol import settings as core_settings
import urllib.request, urllib.error, urllib.parse
import json, requests, ast
from urllib.parse import urlparse
    
class UY_SuDIR():
    
    def __init__(self, provider):
        # self.urls = settings.GEOCODING_PROVIDER['ide_uy']
        params = json.loads(provider.params)
        self.urls = params
        
        self.postal_codes = self.urls['filter']  # not used
        self.providers=[]
        self.append(provider)
        self.category = provider.category
        
    
    def is_unique_instance(self):
        return True
    
    def get_type(self):
        return 'uy_sudir'
        
        
    def append(self, provider):
        self.providers.append(provider)
        
    # Search for candidates
    def geocode(self, query, exactly_one):
        params = {
            'q': query,
            'limit': self.urls['max_results']
        }

        json_results = []
        if self.providers.__len__() > 0 :
            provider = self.providers[0]
            json_results = self.get_json_from_url(self.urls['candidates_url'], params)
            for json_result in json_results:                    
                json_result['category'] = provider.category
                json_result['source'] = provider.type
                #If there is not a defined image, use provider's image
                #if 'image' not in json_result:                    
                #    json_result['image'] = str(provider.image)
            
        return json_results
    
    # Used when use selects one item in the combo box
    def find(self, address_str, exactly_one):
        address = json.loads(address_str)
        print((str(address)))
        typeSearch = address['address[type]']
        
        
        params = {}
        params = {
            'type': typeSearch,
            'id': address['address[id]'],
            'idcalle': address['address[via_circulacion_id]'],
            'idcalleEsq': address['address[idViaEsq]'],
            'nomvia': address['address[nomVia]'],
            'source': 'uy_sudir',
            'localidad': address['address[localidad]'],
            'departamento': address['address[departamento]']
        }
        if ('0' != address['address[portalNumber]']):
            params['portal'] = address['address[portalNumber]']
        if ('' != address['address[letra]']):
            params['letra'] = address['address[letra]']
            
        if ('0' != address['address[km]']):
            params['km'] = address['address[km]']


        #url = "?".join((self.urls['candidates_url'], urlencode(params)))
        # Podemos devolver varios resultados (para el caso en que hay portales repetidos, por ejemplo)
        json_result =  self.get_json_from_url(self.urls['find_url'], params)
        if isinstance(json_result, list):
            for r in json_result:
                r['source'] = self.get_type()
                r['srs'] = 'EPSG:4326'
            return json_result
        
        return []
        
        

    def reverse(self, coordinate, exactly_one, language): 
        params = {
            'latitud': coordinate[1],
            'longitud': coordinate[0]
        }
        
        json_result =  self.get_json_from_url(self.urls['reverse_url'], params)
        if isinstance(json_result, list):
            firstAddress = json_result[0]
            firstAddress['source'] = self.get_type()
                
            return firstAddress
        
        parse_result = {
                    'address': _('Not found'),
                    'lat': coordinate[1], 
                    'lng': coordinate[0],
                    'srs': 'EPSG:4326'
                }
        return parse_result
    
    
    @staticmethod   
    def get_json_from_url(url, params):
        print(url)
        response = requests.get(url=url, params=params)
        if response.status_code == 200:
            respuesta = response.content
            data = json.loads(respuesta)
            if data:
                if 'address' in params:
                    data['address'] = params['address']                               
                    
                return data
        return []
        
        