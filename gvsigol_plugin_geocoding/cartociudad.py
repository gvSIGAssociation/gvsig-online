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
from gvsigol_services.models import Datastore
from geopy.compat import urlencode
from geopy.util import logger
from gvsigol import settings as core_settings
import settings
import urllib2
import json, requests
import logging

class Cartociudad():

    def __init__(self, provider, type):
        self.urls = settings.GEOCODING_PROVIDER['cartociudad']
        self.providers=[]
        self.providers.append(provider)



    def get_type(self):
        return 'cartociudad'


    def is_unique_instance(self):
        return False


    def set_database_config(self,provider):
        params = json.loads(provider.params)

        datastore_id = params["datastore_id"]
        datastore = Datastore.objects.get(id=datastore_id)
        connection_params = json.loads(datastore.connection_params)

        response = requests.get(url=self.urls['configuration_url'], params=connection_params)
        return response.status_code == 200


    def append(self, provider):
        self.providers.append(provider)
        if provider.type == 'cartociudad':
            self.set_database_config(provider)


    def geocode(self, query, exactly_one):
        '''
        http://localhost:8090/geocodersolr/api/geocoder/candidatesJsonp?q=casas&autocancel=true&limit=20&countrycodes=es
        '''

        params = {
            'q': query,
            'autocancel': self.urls['autocancel'],
            'limit': self.urls['max_results'],
            'countrycodes':self.urls['country_codes'],
            'priority': json.dumps(self.get_provider_priority()),
            'filter_ine_mun': settings.CARTOCIUDAD_INE_MUN_FILTER
        }

        #url = "?".join((self.urls['candidates_url'], urlencode(params)))
        return self.get_json_from_url(self.urls['candidates_url'], params)

    def find(self, address_str, exactly_one):
        '''
        http://localhost:8090/geocodersolr/api/geocoder/candidatesJsonp?q=casas&autocancel=true&limit=20&countrycodes=es
        '''

        address = json.loads(address_str)
        if address['address[source]'] == 'user':
            params = {
                'id': address['address[id]'],
                'address': address['address[address]'],
                'source': address['address[source]'],
                'type': address['address[type]'],
                'lat': address['address[lat]'],
                'lng': address['address[lng]'],
                'srs' : 'EPSG:4258'
            }
            return params

        params = {
            'id': address['address[id]'],
            'address': address['address[address]'],
            'source': address['address[source]'],
            'type': address['address[type]'],
            'tip_via': address['address[tip_via]'],
            'portal': address['address[portalNumber]'],
            'filter_ine_mun': settings.CARTOCIUDAD_INE_MUN_FILTER
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
                json_result['srs'] = 'EPSG:4258'

        return json_result




    def reverse(self, coordinate, exactly_one, language):
        '''
        http://localhost:8090/geocodersolr/api/geocoder/candidatesJsonp?q=casas&autocancel=true&limit=20&countrycodes=es
        '''
        schema = 'cartociudad'
        for provider in self.providers:
            if provider.type == 'cartociudad':
                params = json.loads(provider.params)

                datastore_id = params["datastore_id"]
                datastore = Datastore.objects.get(id=datastore_id)
                connection_params = json.loads(datastore.connection_params)

                if 'schema' in connection_params:
                    schema = connection_params['schema']

        params = {
            'lat': coordinate[1],
            'lon': coordinate[0],
            'schema': schema,
            'srs' : 'EPSG:4258'
        }

        json_result =  self.get_json_from_url(self.urls['reverse_url'], params)
        if not json_result:
            updated_data = False
            for provider in self.providers:
                if provider.type == 'cartociudad':
                    updated_data = self.set_database_config(provider)
            if updated_data:
                json_result = self.get_json_from_url(self.urls['reverse_url'], params)

        return json_result


    def get_json_from_url(self, url, params):
        response = requests.get(url=url, params=params)
        if response.status_code == 200:
            respuesta = response.content
            if respuesta.startswith('callback('):
                respuesta = respuesta['callback('.__len__():-1]

            data = json.loads(respuesta)
            if isinstance(data, list):
                for datum in data:
                    if datum['source'] == 'user':
                        for provider in self.providers:
                            table_name = provider.type+'-'+str(provider.pk)
                            if datum['resource'] == table_name:
                                datum['image'] = str(provider.image)
                return data
            else:
                if data['source'] == 'user':
                    for provider in self.providers:
                        table_name = provider.type+'-'+str(provider.pk)
                        if data['resource'] == table_name:
                            data['image'] = str(provider.image)
                return data
        return []


    def get_provider_priority(self):
        num_total = self.providers.__len__()
        providers_order = {}
        if num_total != 0:
            step = 1/float(num_total)
            for provider in self.providers:
                table_name = provider.type+'-'+str(provider.pk)
                order = provider.order
                if(order == 0 or order >= num_total):
                    order = num_total-1
                providers_order[table_name] = ((num_total-order)*step)
        return providers_order
