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

from builtins import RuntimeError
from django.utils.translation import ugettext as _
from geopy.util import logger
from geopy.geocoders import Nominatim as Nominatim_geocoder
import json, requests, ast
import urllib.request, urllib.error, urllib.parse
from urllib.parse import urlparse
from gvsigol import settings
from . import settings
from pyproj import Proj, transform

class icv():
    
    def __init__(self, provider):
        self.urls = settings.GEOCODING_PROVIDER['icv']
        self.providers=[]
        self.append(provider)
        self.category = provider.category
        
        
    def is_unique_instance(self):
        return True  
    
        
    def get_type(self):
        return 'icv'
    
    
    def append(self, provider):
        self.providers.append(provider)
        
        
    def geocode(self, query, exactly_one):
        suggestions = []
        
        params = {
            'query': query,
            'limit': 10
        }

        url = self.urls['candidates_url']
        try:
            json_results = self.get_json_from_url(url=url, params=params)

            if 'results' in json_results:
                for result in json_results['results']:
                    boundingbox_coords = result.get('boundingbox', '').split(',')
                    coord_x = boundingbox_coords[0] if boundingbox_coords else ''
                    coord_y = boundingbox_coords[1] if len(boundingbox_coords) > 1 else ''
                    
                    in_proj = Proj(init='epsg:25830')
                    out_proj = Proj(init='epsg:4326')
                    lng, lat = transform(in_proj, out_proj, float(coord_x), float(coord_y))

                    suggestion = {
                        'source': 'icv',
                        'category': self.category,
                        'type': 'icv',
                        'address': result.get('titulo', ''),
                        'id': result.get('id', ''),
                        'lat': lat,
                        'lng': lng,
                        'y': coord_y,
                        'x': coord_x,
                        'srs': 'EPSG:4326'
                    }
                    suggestions.append(suggestion)
        except Exception as e:
            print('Error al obtener candidatos de geocodificación:', e)

        #response = suggestions
        return suggestions
    
    
    def find(self, address_str, exactly_one):
        '''
        https://descargas.icv.gva.es/server_api/buscador/solrclient.php?start=0&limit=10
        '''
        
        json_results = json.loads(address_str)
        
        suggestion = {}
        
        suggestion['source'] = json_results['address[source]']
        suggestion['type'] = json_results['address[type]']
        suggestion['address'] = json_results['address[address]']
        suggestion['id'] = json_results['address[address]']
        suggestion['lat'] = json_results['address[lat]']
        suggestion['y'] = json_results['address[y]']
        suggestion['lng'] = json_results['address[lng]']
        suggestion['x'] = json_results['address[x]']
        suggestion['srs'] = 'EPSG:4326'
        
        return suggestion
    
        
        
    def reverse(self, coordinate, exactly_one, language):
        '''
        https://descargas.icv.gva.es/server_api/geocodificador/geocoder.php?x=7valorx&y=valory
        '''

        coordenadas = {
            'y': coordinate[1],
            'x': coordinate[0]
        }
        
        in_proj = Proj(init='epsg:4326')
        out_proj = Proj(init='epsg:25830')
        coord_x = coordinate[0]
        coord_y= coordinate[1]
        
        lng, lat = transform(in_proj, out_proj, float(coord_x), float(coord_y))
        params= {
            'x': lng,
            'y': lat
        }
        url=self.urls['reverse_url']
        json_res = requests.get(url=url, params=params)
        content2 = json_res.content.decode('utf-8')
        json_results = json.loads(content2)
        


        suggestion = {
            'source': 'icv',
            'type': 'icv',
            'address': '',
            'calle': '',
            'nombre': '',
            'numero': '',
            'codigo_ine': '',
            'municipio': '',
            'lat': '',
            'lng': '',
            'y': '',
            'x': '',
            'srs': 'EPSG:4326'
        }

        if 'dtipo_vial' in json_results:
            suggestion['dtipo_vial'] = json_results['dtipo_vial']
            
        if 'nombre' in json_results:
            suggestion['address'] = json_results['nombre'] + ' ' + json_results['numero']
        
        if 'calle' in json_results:
            suggestion['calle'] = json_results['calle']
            
        if 'nombre' in json_results:
            suggestion['nombre'] = json_results['nombre']
        
        if 'numero' in json_results:
            suggestion['numero'] = json_results['numero']
        
        if 'codigo_ine' in json_results:
            suggestion['codigo_ine'] = json_results['codigo_ine']
            
        if 'municipio' in json_results:
            suggestion['municipio'] = json_results['municipio']

        if 'y' in json_results and 'x' in json_results:
            suggestion['y'] = json_results['y']
            suggestion['x'] = json_results['x']
            in_proj = Proj(init='epsg:25830')
            out_proj = Proj(init='epsg:4326')
            coord_x = json_results['x']
            coord_y = json_results['y']
            lng, lat = transform(in_proj, out_proj, float(coord_x), float(coord_y))
            suggestion['lat'] = str(lat)
            suggestion['lng'] = str(lng)
        
        

        return suggestion
    
    @staticmethod
    def get_json_from_url(url, params):
        try:
            response = requests.get(url=url, params=params)
            response.raise_for_status()

            content = response.content.decode('utf-8')[1:-1]

            json_data = json.loads(content)
            return json_data
        except requests.exceptions.RequestException as e:
            print('Error en la solicitud HTTP:', e)
            return {}
        except json.JSONDecodeError as je:
            print('Error al decodificar JSON:', je)
            print('Contenido de la respuesta:', content)
            return {}   


