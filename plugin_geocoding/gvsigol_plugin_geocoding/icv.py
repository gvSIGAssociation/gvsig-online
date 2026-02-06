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
from builtins import RuntimeError
'''
@author: Jose Badia <jbadia@scolab.es>
'''
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
            'consulta': query,
            'limite': 10,
            'inicio': 0
        }
        url = self.urls['candidates_url']
        try:
            response = requests.get(url=url, params=params)
            response.raise_for_status()
            json_data = response.json()
            resp = json_data.get('response', json_data)
            results = resp.get('results', [])
            api_fields = ('clasificacion', 'descripcion', 'fuente', 'tipo_geometria', 'municipio', 'cod_ine', 'cod_postal', 'score', 'enlace_visor')
            for result in results:
                bbox_str = result.get('bbox', '')
                if not bbox_str:
                    continue
                parts = bbox_str.split(',')
                if len(parts) < 4:
                    continue
                xmin, ymin, xmax, ymax = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
                coord_x = (xmin + xmax) / 2
                coord_y = (ymin + ymax) / 2
                in_proj = Proj(init='epsg:25830')
                out_proj = Proj(init='epsg:4326')
                lng, lat = transform(in_proj, out_proj, coord_x, coord_y)
                suggestion = {
                    'source': 'icv',
                    'category': self.category,
                    'type': 'icv',
                    'address': result.get('nombre', ''),
                    'nombre': result.get('nombre', ''),
                    'id': result.get('id', ''),
                    'lat': lat,
                    'lng': lng,
                    'y': str(coord_y),
                    'x': str(coord_x),
                    'srs': 'EPSG:4326'
                }
                for key in api_fields:
                    val = result.get(key)
                    if val is not None and val != '':
                        suggestion[key] = val
                suggestions.append(suggestion)
        except Exception as e:
            print('Error al obtener candidatos de geocodificación:', e)
        return suggestions
    
    
    def find(self, address_str, exactly_one):
        """Devuelve la sugerencia seleccionada con todos los campos (igual que los candidatos del buscador)."""
        data = json.loads(address_str)
        suggestion = {}
        for key, value in data.items():
            if key.startswith('address[') and key.endswith(']'):
                field = key[8:-1]  # quitar "address[" y "]"
                suggestion[field] = value if value is not None else ''
            elif not key.startswith('address['):
                suggestion[key] = value if value is not None else ''
        suggestion.setdefault('source', 'icv')
        suggestion.setdefault('type', 'icv')
        suggestion.setdefault('srs', 'EPSG:4326')
        if 'address' not in suggestion:
            suggestion['address'] = data.get('address[address]', data.get('address', ''))
        return suggestion
    
        
        
    def reverse(self, coordinate, exactly_one, language):

        in_proj = Proj(init='epsg:4326')
        out_proj = Proj(init='epsg:25830')
        lng, lat = transform(in_proj, out_proj, float(coordinate[0]), float(coordinate[1]))
        params = {'x': lng, 'y': lat}
        url = self.urls['reverse_url']
        try:
            json_res = requests.get(url=url, params=params)
            json_res.raise_for_status()
            json_results = json_res.json()
        except Exception as e:
            print('Error en geocodificación inversa ICV:', e)
            return self._empty_reverse_suggestion()

        cod_ine_val = json_results.get('cod_ine', '')
        suggestion = {
            'source': 'icv',
            'type': 'icv',
            'address': json_results.get('nombre', ''),
            'nombre': json_results.get('nombre', ''),
            'cod_ine': cod_ine_val,
            'codigo_ine': cod_ine_val,
            'municipio': json_results.get('municipio', ''),
            'cod_postal': json_results.get('cod_postal', ''),
            'lat': '',
            'lng': '',
            'y': '',
            'x': '',
            'srs': 'EPSG:4326'
        }
        x_25830 = json_results.get('x_25830')
        y_25830 = json_results.get('y_25830')
        if x_25830 is not None and y_25830 is not None:
            try:
                in_proj = Proj(init='epsg:25830')
                out_proj = Proj(init='epsg:4326')
                lng_wgs, lat_wgs = transform(in_proj, out_proj, float(x_25830), float(y_25830))
                suggestion['x'] = str(x_25830)
                suggestion['y'] = str(y_25830)
                suggestion['lat'] = str(lat_wgs)
                suggestion['lng'] = str(lng_wgs)
            except (TypeError, ValueError):
                pass
        # clasificacion al final, con el nombre que llega del API
        suggestion['clasificacion'] = json_results.get('clasificacion', '')
        return suggestion

    def _empty_reverse_suggestion(self):
        return {
            'source': 'icv',
            'type': 'icv',
            'address': '',
            'nombre': '',
            'cod_ine': '',
            'codigo_ine': '',
            'municipio': '',
            'cod_postal': '',
            'lat': '',
            'lng': '',
            'y': '',
            'x': '',
            'srs': 'EPSG:4326',
            'clasificacion': ''
        }
    
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


