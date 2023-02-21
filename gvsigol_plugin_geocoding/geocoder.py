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
from sqlalchemy import null
from gvsigol_plugin_geocoding.googlemaps import GoogleMaps
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse
from . import settings
from .cartociudad2 import CartoCiudad2
from .cartociudad import Cartociudad
from .nominatim import Nominatim 
from .geocoder_postgres import GeocoderPostgres
from .ide_uy import IdeUY
from .generic import GenericAPI
import json, ast
from .models import Provider

class Geocoder():
    
    def __init__(self):
        self.geocoders=[]#
        
    def add_provider(self, provider):
        for geocoder in self.geocoders:
            type = provider.type
            if type == 'user':
                type = 'cartociudad'
            if type in geocoder:
                geocoder[type].append(provider)
                return
        
        geocoder = {}
        
        if provider.type == 'new_cartociudad':
            geocoder[provider.type] = CartoCiudad2(provider)
            self.geocoders.append(geocoder)
           
        if provider.type == 'nominatim':
            geocoder[provider.type] = Nominatim(provider)
            self.geocoders.append(geocoder)
            
        if provider.type == 'googlemaps':
            geocoder[provider.type] = GoogleMaps(provider)
            self.geocoders.append(geocoder)

        if provider.type == 'ide_uy':
            geocoder[provider.type] = IdeUY(provider)
            self.geocoders.append(geocoder)

        if provider.type == 'generic':
            geocoder[provider.type] = GenericAPI(provider)
            self.geocoders.append(geocoder)

        if provider.type == 'postgres':
            geocoder[provider.type] = GeocoderPostgres(provider)
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

    def damerau_levenshtein_distance(self, string1, string2):

        s1 = string1.lower()

        s2 = string2.lower()

        #Cálculo de la distancia
        d = {}
        lenstr1 = len(s1)
        lenstr2 = len(s2)
        for i in range(-1,lenstr1+1):
            d[(i,-1)] = i+1
        for j in range(-1,lenstr2+1):
            d[(-1,j)] = j+1

        for i in range(lenstr1):
            for j in range(lenstr2):
                if s1[i] == s2[j]:
                    cost = 0
                else:
                    cost = 1
                d[(i,j)] = min(
                    d[(i-1,j)] + 1,
                    d[(i,j-1)] + 1,
                    d[(i-1,j-1)] + cost,
                    )
                if i and j and s1[i]==s2[j-1] and s1[i-1] == s2[j]:
                    d[(i,j)] = min (d[(i,j)], d[i-2,j-2] + cost)

        dDL= d[lenstr1-1,lenstr2-1]

        return dDL

    def geocoding_direct_from_etl(self, query, geocoder_type):

        provider = Provider.objects.get(type = geocoder_type)

        self.add_provider(provider)

        for geocoder_t in self.geocoders:
            if  geocoder_type in geocoder_t:
                geocoder = geocoder_t[geocoder_type]
                break
        try:
            sugges= geocoder.geocode(query, exactly_one=False)
        except:
            response = {}
            
            return response

        if geocoder_type == 'generic':
            suggestions = []
            for s in sugges:
                sg = {"address[" + str(key)+"]": val for key, val in s.items()}
                for key, val in sg.items():
                    if val is None:
                        sg[key] = ''
                    if val == 0:
                        sg[key] = '0'
                suggestions.append(sg)
        else:
            suggestions = sugges
        
        distance = 99999999
        suggestion = suggestions[0]
        
        for sug in suggestions:

            dld = self.damerau_levenshtein_distance(query, sug['address[address]'])

            if dld < distance:
                distance = dld
                suggestion = sug
        
        response = self.find_candidate(json.dumps(suggestion))

        return response

    def geocoding_reverse_from_etl(self, x, y, geocoder_type):
        coordinate = [x, y]
        loc = {}

        provider = Provider.objects.get(type = geocoder_type)

        self.add_provider(provider)

        for geocoder_t in self.geocoders:
            if  geocoder_type in geocoder_t:
                geocoder = geocoder_t[geocoder_type]
                break
        
        loc = geocoder.reverse(coordinate,exactly_one=True,language='es')

        return loc

    
    def find_candidate(self, address):
        location = {}
        address_json = json.loads(address)
        type = 'new_cartociudad'
        if "address[source]" in address_json:
            type = address_json["address[source]"]
        if "source" in address_json:
            type = address_json["source"]
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
            geocoder = geocoder_types.get(type)
            if geocoder:
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
        

