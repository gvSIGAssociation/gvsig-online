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

from openpyxl.utils.cell import rows_from_range
from lxml.etree import tounicode
from gvsigol_services.models import Datastore, Layer

from geopy.util import logger
from gvsigol import settings as core_settings
from gvsigol_services.backend_postgis import Introspect
from . import settings
import json, requests
import logging

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import quote_ident
from time import time

class GeocoderUserData():

    def __init__(self, provider):
        self.urls = settings.GEOCODING_PROVIDER['user_data']
        self.providers=[]
        self.set_database_config(provider)
        self.providers.append(provider)

    def __del__(self):
        for p in self.providers:
            if p.connection is not None:
                p.cursor.close()
                p.connection.close()
                p.connection = None

    def get_type(self):
        return 'user_data'


    def is_unique_instance(self):
        return False

    def _set_fields_and_srs(self, provider, introspect_conn):
        #geom_column_literal = sql.Literal(quote_ident(provider.dbfieldGeom, introspect_conn.conn))
        geom_column_identifier = sql.Identifier(provider.dbfieldGeom)
        if provider.dbfield == provider.dbfieldId:
            if provider.dbfieldId != 'id':
                alias = 'id'
            else:
                alias = 'idcol'
        else:
            alias = provider.dbfieldId
        idfield_sql = sql.SQL('{idfield} as {alias}').format(idfield=sql.Identifier(provider.dbfieldId), alias=sql.Identifier(alias))
        
        fields = [
            #sql.SQL('{dbfield}').format(dbfield=sql.Identifier(provider.dbfield)),
            sql.Identifier(provider.dbfield),
            idfield_sql
        ]
        fields_with_geom = fields + [
            sql.SQL('st_transform(ST_PointOnSurface({geom_column}), 4326) AS P').format(geom_column=geom_column_identifier),
            sql.SQL('st_asgeojson(st_transform({geom_column}, 4326)) as G').format(geom_column=geom_column_identifier)
        ]
        """
            'st_transform(ST_PointOnSurface(' + provider.dbfieldGeom + '), 4326) AS P,', 'st_asgeojson(st_transform(' + provider.dbfieldGeom + ', 4326)) as G ']
        provider.fieldsWithGeom = (provider.dbfield + ', ' + provider.dbfieldId + ', ' +
                           'st_transform(ST_PointOnSurface(' + provider.dbfieldGeom + '), 4326) AS P,' +
                           'st_asgeojson(st_transform(' + provider.dbfieldGeom + ', 4326)) as G ')
        provider.fields = (provider.dbfield + ', ' + provider.dbfieldId )
        """
        
        fields_sql = sql.SQL(", ").join(fields)
        provider.fields = fields_sql.as_string(introspect_conn.conn)
        fields_with_geom_sql = sql.SQL(", ").join(fields_with_geom)
        provider.fieldsWithGeom = fields_with_geom_sql.as_string(introspect_conn.conn)
        field_info = introspect_conn.get_geometry_column_info(provider.dbtable, provider.dbfieldGeom, provider.dbschema)
        provider.srs = field_info[0][4]

    def _set_geocode_query(self, provider):
        provider.geocoder_query = sql.SQL("""SELECT {fields} FROM {schema}.{table} WHERE immutable_unaccent({dbfield}) %% %s  ORDER BY SIMILARITY( {dbfield}, %s) DESC LIMIT 10""").format(
                fields = sql.SQL(provider.fields),
                schema = sql.Identifier(provider.dbschema),
                table = sql.Identifier(provider.dbtable),
                dbfield = sql.Identifier(provider.dbfield)
            )

    def set_database_config(self, provider):
        params = json.loads(provider.params)

        datastore_id = params["datastore_id"]
        provider.dbtable = params['resource']
        provider.dbfield = params['text_field']
        datastore = Datastore.objects.get(id=datastore_id)
        datastore_params = json.loads(datastore.connection_params)
        
        dbhost = datastore_params['host']
        dbport = datastore_params['port']
        dbname = datastore_params['database']
        dbuser = datastore_params['user']
        dbpassword = datastore_params['passwd']
        provider.dbtable = params['resource']
        provider.dbfield = params['text_field']
        provider.dbfieldId = params['id_field']
        provider.dbfieldGeom = params['geom_field']
        provider.dbschema = datastore_params['schema']
        try:
            with Introspect(database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpassword) as i:
                self._set_fields_and_srs(provider, i)
            self._set_geocode_query(provider)
            provider.connection = psycopg2.connect("host=" + dbhost +" port=" + dbport +" dbname=" + dbname +" user=" + dbuser +" password="+ dbpassword);
            provider.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            print("Connect ... ")
        
        except Exception as e:
            print("Failed to connect!", e)
            return False

        provider.cursor = provider.connection.cursor() 
        #self.cursor.close()
        #self.connection = None

        return True # Updated data ok


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
        sanitized_q = query.replace("'", " ")

        resul = []
        for provider in self.providers:
            """
            auxSql =  " '%s' ORDER BY SIMILARITY( %s, '%s') DESC LIMIT 10" % (sanitized_q, provider.dbfield, sanitized_q)
            sqlQuery = ("SELECT " + provider.fields +  " FROM " + provider.dbschema + "." + 
                        provider.dbtable + " WHERE immutable_unaccent(" + provider.dbfield + ") % " + 
                        auxSql)
            # print 'SQL:' + sqlQuery            
            provider.cursor.execute(sqlQuery)        
            """
            
            t1 = time()
            #print(provider.geocoder_query.as_string(provider.cursor))
            provider.cursor.execute(provider.geocoder_query, (query, query))
            rows = provider.cursor.fetchall()
            for r in rows:                
                a = {
                    'address': r[0],
                    'id': r[1],
                    'source': 'postgres',
                    'category': provider.category,
                    'image': str(provider.image),
                    'srs': 'EPSG:4326'
                }
                resul.append(a)
            
            if core_settings.DEBUG:
                t2 = time()
                print('T geocoder postgres ' + provider.dbtable + ':', (t2-t1)*1000, ' msecs')
        return resul

    def find(self, address_str, exactly_one):
        """
        select nameunit, ogc_fid, st_x(P) as lng, st_y(P) as lat, G from
            (SELECT nameunit, ogc_fid, st_transform(ST_PointOnSurface(wkb_geometry), 4326) AS P, st_asgeojson(st_transform(wkb_geometry, 4326)) as G 
            FROM cartociudad.municipio WHERE 
             nameunit like 'Villalpardo') s
        """
        # No entiendo porqué sigue este formato, pero es heredado... :-(
        address = json.loads(address_str)
        the_address = address['address[address]']
        the_category = address['address[category]']
        resul = {}
        for provider in self.providers:
            if the_category == provider.category:
                t1 = time()
                
                sqlQuery = ("SELECT " + provider.fields +  ", st_x(P) as lng, st_y(P) as lat, G FROM \n" +
                             "(SELECT " +  provider.fieldsWithGeom + " FROM " + provider.dbschema + "." + 
                             provider.dbtable + " WHERE " + provider.dbfield + " like %s ) s"  )
                print(sqlQuery)
                provider.cursor.execute(sqlQuery, (the_address, ))        
                rows = provider.cursor.fetchall()
                for r in rows:                
                    resul = {
                        'address': r[0],
                        'id': r[1],
                        'lat': r[3],
                        'lng': r[2],
                        'geom': r[4],                    
                        'source': 'postgres',
                        'category': provider.category,
                        'image': str(provider.image),
                        'srs': 'EPSG:4326'
                    }
                t2 = time()
                print('T geocoder postgres find ' + provider.dbtable + ':', (t2-t1)*1000, ' msecs')
            

        return resul


    def reverse(self, coordinate, exactly_one, language):
        lat =  str(coordinate[1])
        lng =  str(coordinate[0])
        resul = []
        for provider in self.providers:
            t1 = time()
            str_order_by = " ORDER BY st_transform(" + provider.dbfieldGeom + ",4326) <-> 'SRID=4326;POINT(" + lng + " " + lat + ")'::geometry LIMIT 1";
            
            sqlQuery = ("SELECT " + provider.fields +  ", st_x(P) as lng, st_y(P) as lat, G FROM \n" +
                         "(SELECT " +  provider.fieldsWithGeom + " FROM " + provider.dbschema + "." + 
                         provider.dbtable + str_order_by + ") s;"  )
            provider.cursor.execute(sqlQuery)        
            rows = provider.cursor.fetchall()
            for r in rows:                
                a = {
                    'address': r[0],
                    'id': r[1],
                    'lat': r[3],
                    'lng': r[2],
                    'geom': r[4],                    
                    'source': 'postgres',
                    'category': provider.category,
                    'image': str(provider.image),
                    'srs': 'EPSG:4326'
                }
                resul.append(a)
            t2 = time()
            print('T geocoder postgres reverse ' + provider.dbtable + ':', (t2-t1)*1000, ' msecs')

        return resul



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
