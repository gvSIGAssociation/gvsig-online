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
from django.utils.translation import gettext as _
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
        """
        Geocodificador inverso ICV (API actual):
        https://descargas.icv.gva.es/00/geoprocesos/geocodificador-inverso/
        Params: tema, x, y, epsg
        """
        lon_wgs = float(coordinate[0])
        lat_wgs = float(coordinate[1])
        in_proj = Proj(init='epsg:4326')
        out_proj = Proj(init='epsg:25830')
        x_25830, y_25830 = transform(in_proj, out_proj, lon_wgs, lat_wgs)
        params = {
            'tema': 'callejero',
            'x': x_25830,
            'y': y_25830,
            'epsg': 25830,
        }
        url = self.urls['reverse_url']
        try:
            json_res = requests.get(url=url, params=params)
            json_res.raise_for_status()
            json_results = json_res.json()
        except Exception as e:
            print('Error en geocodificación inversa ICV:', e)
            return self._empty_reverse_suggestion()

        if not json_results.get('success'):
            return self._empty_reverse_suggestion()

        hit = self._first_reverse_hit(json_results, preferred_tema='callejero')
        if not hit:
            return self._empty_reverse_suggestion()

        direccion = hit.get('direccion') or {}
        municipio = hit.get('municipio') or {}
        coords_pk = hit.get('coordenadasPortalPk') or {}

        address = direccion.get('nombreCompleto') or ''
        if not address:
            tipo = (direccion.get('tipoVial') or '').strip()
            via = (direccion.get('nombreVia') or '').strip()
            numero = (direccion.get('numero') or '').strip()
            parts = [p for p in (tipo, via) if p]
            address = ' '.join(parts)
            if numero:
                address = (address + ', ' + numero).strip(', ')
            if not address:
                address = municipio.get('nombre', '') or ''

        cod_ine_val = municipio.get('codigoIne', '') or ''
        suggestion = {
            'source': 'icv',
            'type': 'icv',
            'address': address,
            'nombre': address,
            'cod_ine': cod_ine_val,
            'codigo_ine': cod_ine_val,
            'municipio': municipio.get('nombre', '') or '',
            'cod_postal': municipio.get('codigoPostal', '') or '',
            'lat': '',
            'lng': '',
            'y': '',
            'x': '',
            'srs': 'EPSG:4326',
            'clasificacion': direccion.get('clasificacion', '') or '',
        }

        x_out = coords_pk.get('x')
        y_out = coords_pk.get('y')
        if x_out is not None and y_out is not None:
            try:
                in_proj = Proj(init='epsg:25830')
                out_proj = Proj(init='epsg:4326')
                lng_out, lat_out = transform(in_proj, out_proj, float(x_out), float(y_out))
                suggestion['x'] = str(x_out)
                suggestion['y'] = str(y_out)
                suggestion['lat'] = str(lat_out)
                suggestion['lng'] = str(lng_out)
            except (TypeError, ValueError):
                pass
        if not suggestion['lat'] or not suggestion['lng']:
            # Fallback: coordenadas de la consulta transformadas
            suggestion['x'] = str(x_25830)
            suggestion['y'] = str(y_25830)
            suggestion['lat'] = str(lat_wgs)
            suggestion['lng'] = str(lon_wgs)
        return suggestion

    @staticmethod
    def _first_reverse_hit(json_results, preferred_tema='callejero'):
        """Extrae el primer resultado del tema preferido (o el primero disponible)."""
        groups = json_results.get('results') or []
        fallback = None
        for group in groups:
            if not group.get('success'):
                continue
            inner = group.get('results') or []
            if not inner:
                continue
            if group.get('tema') == preferred_tema:
                return inner[0]
            if fallback is None:
                fallback = inner[0]
        return fallback

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


