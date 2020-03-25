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
@author: Francisco José Peñarrubia <fjp@scolab.es>
'''
from gvsigol_services.models import Datastore
from geopy.util import logger
from gvsigol import settings as core_settings
import settings
import json, requests
import logging

class GeocoderPostgres():

    def __init__(self, provider, type):
        self.urls = settings.GEOCODING_PROVIDER['postgres']
        self.providers=[]
        self.providers.append(provider)



    def get_type(self):
        return 'postgres'


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
        if provider.type == 'postgres':
            self.set_database_config(provider)


    def geocode(self, query, exactly_one):
        params = {
            'q': query,
            'autocancel': self.urls['autocancel'],
            'limit': self.urls['max_results'],
        }

        # TODO: NO LLAMAR A UNA URL, BUSCAR EN POSTGRES Y DEVOLVER UN JSON
        test = {
            'address': 'Calle San Antonio',
            'Lat': 40.0,
            'Lng': 0.0,
            'srs': 'EPSG:4326'
        }
        return self.get_json_from_url(self.urls['candidates_url'], params)

    def find(self, address_str, exactly_one):

        address = json.loads(address_str)
        test = {
            'id': 1,
            'address': 'Calle San Antonio',
            'source': 'postgres',
            'type': 'poi',
            'lat': 40.0,
            'lng': 0.0
        }
        return test


    def reverse(self, coordinate, exactly_one, language):
        schema = 'cartociudad'
        for provider in self.providers:
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

#         for provider in self.providers:
#             table_name = provider.type+'-'+str(provider.pk)
#             if data['resource'] == table_name:
#                 data['image'] = str(provider.image)
#         return data

        test = {
            'address': 'calle San Antonio',            
        }
        return test;



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
