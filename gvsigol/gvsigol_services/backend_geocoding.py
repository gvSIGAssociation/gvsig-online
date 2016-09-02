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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.core.exceptions import ImproperlyConfigured
from gvsigol.settings import GVSIGOL_SEARCH
from geopy.geocoders import Nominatim
from urlparse import urlparse

class Geocoder():
    
    def __init__(self, url, country_codes):
        url_params = urlparse(url)
        scheme = url_params.scheme
        domain = url_params.netloc + url_params.path
        self.geolocator = Nominatim(country_bias=country_codes, scheme=scheme, domain=domain)
        
          
    def search_candidates(self, query):
        locations = self.geolocator.geocode(query,exactly_one=False)
        suggestions = []
        for l in locations:
            suggestion = {}
            suggestion['value'] = l.address
            suggestion['data'] = l._raw['lat'] + ',' + l._raw['lon'] 
            suggestions.append(suggestion)
                
        response = {
            "query": "Unit",
            "suggestions": suggestions
        }
        
        return response
    
        
    def get_location_address(self, query):
        point = query.split(',')
        coordinate = [point[0], point[1]]
        loc = self.geolocator.reverse(coordinate,exactly_one=True,language='es')
        location = {
            'title': loc.address,
            'address': loc._raw['address'],
            'latitude': loc.latitude,
            'longitude': loc.longitude
        }
        
        return location
    
    
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
        

def get_geocoder():
    try:
        url = GVSIGOL_SEARCH['nominatim']['url']
        country_codes = GVSIGOL_SEARCH['nominatim']['country_codes']
        
    except:
        raise ImproperlyConfigured
    
    gvsigOnline = Geocoder(url, country_codes)
    return gvsigOnline

geocoder = get_geocoder()