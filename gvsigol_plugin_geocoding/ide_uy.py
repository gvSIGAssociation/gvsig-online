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
import settings
'''
@author: Francisco J. Peñarrubia <fjp@scolab.es>
'''
from django.utils.translation import ugettext as _
from geopy.compat import urlencode
from geopy.util import logger
from gvsigol import settings as core_settings
import urllib2
import json, requests, ast
from urlparse import urlparse
    
class IdeUY():
    
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
        return 'ide_uy'
        
        
    def append(self, provider):
        self.providers.append(provider)
        
    # Search for candidates
    def geocode(self, query, exactly_one):
        '''
        www.cartociudad.es/geocoder/api/geocoder/candidatesJsonp?q=blasco ibañez&limit=10     
        http://127.0.0.1:8080/api/v1/geocode/candidates?q=ordo%C3%B1ez canelones&limit=10   
        '''
        params = {
            'q': query,
            'limit': self.urls['max_results']
        }

        json_results = []
        if self.providers.__len__() > 0 :
            provider = self.providers[0]
            json_results = self.get_json_from_url(self.urls['candidates_url'], params)
            for json_result in json_results:
                if (json_result['address'] == None):
                    json_result['address'] = ''
                json_result['category'] = provider.category
                #If there is not a defined image, use provider's image
                #if 'image' not in json_result:                    
                #    json_result['image'] = str(provider.image)
            
        return json_results
    
    # Used when use selects one item in the combo box
    def find(self, address_str, exactly_one):
        '''
        http://www.cartociudad.es/geocoder/api/geocoder/findJsonp?q=blasco ibañez   
        http://127.0.0.1:8080/api/v1/geocode/find?type=calle&nomvia=YAGUARON&departamento=MONTEVIDEO&localidad=MONTEVIDEO
        '''
        address = json.loads(address_str)
        print(str(address))
        typeSearch = address['address[type]']
        inmueble = address['address[inmueble]'] 
        if (inmueble != ''):
            typeSearch = "inmueble"
        
        
        
        params = {}
        params = {
            'type': typeSearch,
            'id': address['address[id]'],
            'idcalle': address['address[idCalle]'],
            'idcalleEsq': address['address[idCalleEsq]'],
            'nomvia': address['address[nomVia]'],
            'source': 'ide_uy',
            'localidad': address['address[localidad]'],
            'departamento': address['address[departamento]'],
            'inmueble': inmueble
        }
        if ('0' != address['address[portalNumber]']):
            params['portal'] = address['address[portalNumber]']
        if ('' != address['address[letra]']):
            params['letra'] = address['address[letra]']
            

        if ('' != address['address[manzana]']):
            params['manzana'] = address['address[manzana]']
            params['solar'] = address['address[solar]']

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
            # if (json_result.__len__() > 0):
#                 first = json_result[0]
#                 first['source'] = self.get_type()
#                 first['srs'] = 'EPSG:4326'
#                 return first
        
        return []
        
        

    def reverse(self, coordinate, exactly_one, language): 
        '''
        http://www.cartociudad.es/geocoder/api/geocoder/reverseGeocode?lon=-4.702148&lat=39.727469
        http://127.0.0.1:8080/api/v1/geocode/reverse?longitud=-56.1881599&latitud=-34.9032784&limit=10
        '''
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
                # auxStaticUrl = os.path.join(core_settings.BASE_URL, core_settings.STATIC_URL)
                # Parche: Jose hizo un apaño para usar image o type como parámetro para las imágenes.
                # El problema es que si usas image, las busca en MEDIA, y si usas type, busca en static.
                # Para que busque en static, hay que usar la clave "type", que ya la estamos usando, así que le doy el cambiazo aquí
                # No cambio ese funcionamiento por si rompo algo en otro sitio, pero estaría bien buscar otra forma de hacerlo.
                # Mirar en el javascript jquery.autocomplete.js, que es ahí donde metió el parche Jose.
                # Cambio de táctica. Metemos unas imagenes con los nombres de los iconos que nos interesan en nuestro type
                
#                 for d in data:                        
#                     if 'type' in d:
#                         myType = d['type']
#                         if myType == 'LOCALIDAD':
#                             d['type'] = 'country';    
#                         if myType == 'POI':
#                             d['image'] = os.path.join(auxStaticUrl, 'img/geocoding/municipio.png');                                
                    
                return data
        return []
        
        