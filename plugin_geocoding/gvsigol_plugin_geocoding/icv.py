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
    
        
        
    DEFAULT_REVERSE_TEMAS = 'callejero,municipios,catastro,forestal,espacios-protegidos'

    def reverse(self, coordinate, exactly_one, language):
        """
        Geocodificador inverso ICV (API actual):
        https://descargas.icv.gva.es/00/geoprocesos/geocodificador-inverso/
        Params: tema (varios), x, y, epsg
        """
        lon_wgs = float(coordinate[0])
        lat_wgs = float(coordinate[1])
        in_proj = Proj(init='epsg:4326')
        out_proj = Proj(init='epsg:25830')
        x_25830, y_25830 = transform(in_proj, out_proj, lon_wgs, lat_wgs)
        params = {
            'tema': self._reverse_temas_param(),
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

        return self.suggestion_from_reverse_json(
            json_results, lon_wgs=lon_wgs, lat_wgs=lat_wgs, x_25830=x_25830, y_25830=y_25830
        )

    def _reverse_temas_param(self):
        temas = self.urls.get('reverse_temas', self.DEFAULT_REVERSE_TEMAS)
        if isinstance(temas, (list, tuple)):
            return ','.join(str(t).strip() for t in temas if str(t).strip())
        return str(temas or self.DEFAULT_REVERSE_TEMAS).replace(' ', '')

    @classmethod
    def _hits_by_tema(cls, json_results):
        by_tema = {}
        for group in json_results.get('results') or []:
            if not group.get('success'):
                continue
            tema = group.get('tema')
            inner = group.get('results') or []
            if tema and inner:
                by_tema[tema] = inner
        return by_tema

    @staticmethod
    def _first_hit(hits_by_tema, tema):
        hits = hits_by_tema.get(tema) or []
        return hits[0] if hits else {}

    @staticmethod
    def _clean_str(value):
        if value is None:
            return ''
        return str(value).strip()

    @classmethod
    def _address_from_callejero(cls, hit):
        direccion = hit.get('direccion') or {}
        address = cls._clean_str(direccion.get('nombreCompleto'))
        if address:
            return address, direccion
        tipo = cls._clean_str(direccion.get('tipoVial'))
        via = cls._clean_str(direccion.get('nombreVia'))
        numero = cls._clean_str(direccion.get('numero'))
        parts = [p for p in (tipo, via) if p]
        address = ' '.join(parts)
        if numero:
            address = (address + ', ' + numero).strip(', ')
        return address, direccion

    @classmethod
    def _address_from_catastro(cls, hit):
        direccion = hit.get('direccion') or {}
        tipo = cls._clean_str(direccion.get('tipoVia'))
        via = cls._clean_str(direccion.get('nombreVia'))
        num = cls._clean_str(direccion.get('numeroPol1')).lstrip('0') or ''
        letra = cls._clean_str(direccion.get('letra1'))
        parts = [p for p in (tipo, via) if p]
        address = ' '.join(parts)
        if num:
            address = (address + ' ' + num + letra).strip()
        mun = (hit.get('municipio') or {}).get('nombre')
        if mun and address:
            address = '%s (%s)' % (address, mun)
        elif mun:
            address = cls._clean_str(mun)
        return address

    @classmethod
    def suggestion_from_reverse_json(cls, json_results, lon_wgs='', lat_wgs='', x_25830='', y_25830=''):
        hits_by_tema = cls._hits_by_tema(json_results)
        if not hits_by_tema:
            return cls._empty_reverse_suggestion()

        callejero = cls._first_hit(hits_by_tema, 'callejero')
        municipios = cls._first_hit(hits_by_tema, 'municipios')
        catastro = cls._first_hit(hits_by_tema, 'catastro')
        forestal = cls._first_hit(hits_by_tema, 'forestal')
        eepp_hits = hits_by_tema.get('espacios-protegidos') or []

        address, direccion = cls._address_from_callejero(callejero)
        if not address:
            address = cls._address_from_catastro(catastro)

        mun_callejero = callejero.get('municipio') or {}
        mun_muni = municipios.get('municipio') or {}
        mun_catastro = catastro.get('municipio') or {}

        municipio_nombre = (
            cls._clean_str(mun_callejero.get('nombre'))
            or cls._clean_str(mun_muni.get('nombre'))
            or cls._clean_str(mun_catastro.get('nombre'))
        )
        if not address:
            address = municipio_nombre

        cod_ine_val = (
            cls._clean_str(mun_callejero.get('codigoIne'))
            or cls._clean_str(mun_muni.get('codigoIne'))
            or cls._clean_str(mun_catastro.get('codigoIne'))
        )
        cod_postal = (
            cls._clean_str(mun_callejero.get('codigoPostal'))
            or cls._clean_str((catastro.get('direccion') or {}).get('codigoPostal'))
        )

        suggestion = {
            'source': 'icv',
            'type': 'icv',
            'address': address,
            'nombre': address,
            'cod_ine': cod_ine_val,
            'codigo_ine': cod_ine_val,
            'municipio': municipio_nombre,
            'cod_postal': cod_postal,
            'lat': '',
            'lng': '',
            'y': '',
            'x': '',
            'srs': 'EPSG:4326',
            'clasificacion': cls._clean_str(direccion.get('clasificacion')),
        }

        comarca = cls._clean_str(municipios.get('comarca'))
        provincia = cls._clean_str(municipios.get('provincia'))
        if comarca:
            suggestion['comarca'] = comarca
        if provincia:
            suggestion['provincia'] = provincia

        linea = municipios.get('lineaLimiteMasCercana') or {}
        linea_nombre = cls._clean_str(linea.get('nombre'))
        if linea_nombre:
            suggestion['linea_limite'] = linea_nombre
            distancia_limite = linea.get('distanciaMetros')
            if distancia_limite is not None and distancia_limite != '':
                suggestion['distancia_limite_m'] = str(distancia_limite)

        refcat = cls._clean_str(catastro.get('referenciaCatastral'))
        if refcat:
            suggestion['ref_catastral'] = refcat
        tipo_parcela = cls._clean_str(catastro.get('tipo'))
        if tipo_parcela:
            suggestion['tipo_parcela'] = tipo_parcela
        cod_catastro = cls._clean_str(mun_catastro.get('codigoCatastro')) or cls._clean_str(mun_muni.get('codigoCatastro'))
        if cod_catastro:
            suggestion['codigo_catastro'] = cod_catastro

        if forestal:
            dem = cls._clean_str(forestal.get('nombre'))
            if dem:
                suggestion['demarcacion_forestal'] = dem
            tipo_for = cls._clean_str(forestal.get('tipo'))
            if tipo_for:
                suggestion['tipo_forestal'] = tipo_for

        if eepp_hits:
            labels = []
            for hit in eepp_hits:
                figura = cls._clean_str(hit.get('figuraProteccion'))
                nombre = cls._clean_str(hit.get('nombre'))
                if figura and nombre:
                    labels.append('%s: %s' % (figura, nombre))
                elif nombre:
                    labels.append(nombre)
            if labels:
                suggestion['espacios_protegidos'] = '; '.join(labels)

        distancia = callejero.get('distanciaMetros')
        if distancia is not None and distancia != '':
            suggestion['distancia_m'] = str(distancia)

        coords_pk = callejero.get('coordenadasPortalPk') or {}
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
            if x_25830 != '' and y_25830 != '':
                suggestion['x'] = str(x_25830)
                suggestion['y'] = str(y_25830)
            if lat_wgs != '' and lon_wgs != '':
                suggestion['lat'] = str(lat_wgs)
                suggestion['lng'] = str(lon_wgs)
        return suggestion

    @classmethod
    def _empty_reverse_suggestion(cls):
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
    def format_etl_address(suggestion):
        """Dirección enriquecida para nodos ETL (una sola columna _ADDRESS)."""
        if not suggestion:
            return ''
        address = suggestion.get('address') or suggestion.get('nombre') or ''
        extras = []
        if suggestion.get('ref_catastral'):
            extras.append('RC %s' % suggestion['ref_catastral'])
        if suggestion.get('comarca'):
            extras.append(suggestion['comarca'])
        if suggestion.get('demarcacion_forestal'):
            extras.append('Forestal: %s' % suggestion['demarcacion_forestal'])
        if suggestion.get('espacios_protegidos'):
            # En ETL acortar EEPP para no hinchar la celda
            eepp = suggestion['espacios_protegidos']
            if len(eepp) > 180:
                eepp = eepp[:177] + '...'
            extras.append('EEPP: %s' % eepp)
        if extras:
            return ('%s | %s' % (address, ' | '.join(extras))).strip(' |')
        return address
    
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


