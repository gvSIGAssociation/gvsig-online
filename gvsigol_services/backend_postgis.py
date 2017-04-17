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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

"""
Postgis_introspect: a standalone library to do Postgresql/Postgis
introspection using Pythonic style.

This library easily gets the table names, the column names of a
specific table, the available geometry columns, etc.
"""

import psycopg2

class Introspect:
    def __init__(self, database, host='localhost', port='5432', user='postgres', password='postgres'):
        self.conn = psycopg2.conn = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.conn.cursor()
    
    def get_tables(self, schema='public'):
        self.cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s 
        """, [schema])    
        return [r[0] for r in self.cursor.fetchall()]
    
    def get_geometry_tables(self, schema='public'):
        self.cursor.execute("""
        SELECT f_table_name FROM  public.geometry_columns
        WHERE f_table_schema = %s GROUP BY f_table_name;
        """, [schema])
        return [r[0] for r in self.cursor.fetchall()]

    def get_geography_tables(self, schema='public'):
        self.cursor.execute("""
        SELECT f_table_name FROM  public.geography_columns
        WHERE f_table_schema = %s GROUP BY f_table_name;
        """, [schema])
        return [r[0] for r in self.cursor.fetchall()]
    
    def get_geometry_columns(self, table, schema='public'):
        self.cursor.execute("""
        SELECT f_geometry_column
        FROM public.geometry_columns
        WHERE f_table_schema = %s AND f_table_name = %s
        """, [schema, table])        
        return [r[0] for r in self.cursor.fetchall()]
    
    def get_geometry_columns_info(self, table=None, schema='public'):
        """
        Returns a tuple formed of:
         (f_table_schema, table_name, geom_column, coord_dimension, srid, type, key_column, fields)
        """
        if table:
            self.cursor.execute("""
            SELECT f_table_schema, f_table_name, f_geometry_column, coord_dimension, srid, type,
            array (SELECT a.attname AS data_type
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                        WHERE
                        i.indrelid = ('"'||replace(f_table_schema, '"', '""')||'"."'||replace(f_table_name, '"', '""')||'"')::regclass
                        AND i.indisprimary) key_column,
            array(SELECT column_name::text
                        FROM information_schema.columns
                        WHERE table_schema = f_table_schema 
                        AND table_name = f_table_name) fields
            FROM public.geometry_columns
            WHERE f_table_schema = %s AND f_table_name = %s
            """, [schema, table])
        else:
            self.cursor.execute("""
            SELECT f_table_schema, f_table_name, f_geometry_column, coord_dimension, srid, type,
            array (SELECT a.attname AS data_type
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                        WHERE
                        i.indrelid = ('"'||replace(f_table_schema, '"', '""')||'"."'||replace(f_table_name, '"', '""')||'"')::regclass
                        AND i.indisprimary) key_column,
            array(SELECT column_name::text
                        FROM information_schema.columns
                        WHERE table_schema = f_table_schema 
                        AND table_name = f_table_name) fields
            FROM public.geometry_columns
            WHERE f_table_schema = %s
            """, [schema])
        
        return [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in self.cursor.fetchall()]
    
    def get_geography_columns(self, table, schema='public'):
        self.cursor.execute("""
        SELECT  f_geography_column, coord_dimension, srid, type
        FROM  public.geography_columns
        WHERE f_table_schema = %s AND f_table_name = %s
        """, [schema, table])        
        return [(r[0]) for r in self.cursor.fetchall()]

    def get_geography_columns_info(self, table=None, schema='public'):
        """
        Returns a tuple formed of:
         (f_table_schema, table_name, geom_column, coord_dimension, srid, type, key_column, fields)
        """
        if table:
            self.cursor.execute("""
            SELECT f_table_schema, f_table_name, f_geography_column, coord_dimension, srid, type,
            array (SELECT a.attname AS data_type
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                        WHERE
                        i.indrelid = ('"'||replace(f_table_schema, '"', '""')||'"."'||replace(f_table_name, '"', '""')||'"')::regclass
                        AND i.indisprimary) key_column,
            array(SELECT column_name::text
                        FROM information_schema.columns
                        WHERE table_schema = f_table_schema 
                        AND table_name = f_table_name) fields
            FROM public.geography_columns
            WHERE f_table_schema = %s AND f_table_name = %s
            """, [schema, table])
        else:
            self.cursor.execute("""
            SELECT f_table_schema, f_table_name, f_geography_column, coord_dimension, srid, type,
            array (SELECT a.attname AS data_type
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                        WHERE
                        i.indrelid = ('"'||replace(f_table_schema, '"', '""')||'"."'||replace(f_table_name, '"', '""')||'"')::regclass
                        AND i.indisprimary) key_column,
            array(SELECT column_name::text
                        FROM information_schema.columns
                        WHERE table_schema = f_table_schema 
                        AND table_name = f_table_name) fields
            FROM public.geography_columns
            WHERE f_table_schema = %s
            """, [schema])
        
        return [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in self.cursor.fetchall()]
    

    def get_pk_columns(self, table, schema='public'):
        self.cursor.execute("""
        SELECT a.attname AS field_name
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                        WHERE
                        i.indrelid = ('"'||replace(%s, '"', '""')||'"."'||replace(%s, '"', '""')||'"')::regclass
                        AND i.indisprimary
        """, [schema, table])
        
        return [r[0] for r in self.cursor.fetchall()]
    
    def get_fields(self, table, schema='public'):
        self.cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s 
        """, [schema, table])
        
        return [r[0] for r in self.cursor.fetchall()]
    
    def create_table(self, schema, table_name, geom_type, srs, fields):
        query = ""
        
        if geom_type == 'Point':
            geom_type = 'MultiPoint'
        if geom_type == 'LineString':
            geom_type = 'MultiLineString'
        if geom_type == 'Polygon':
            geom_type = 'MultiPolygon'
        
        query += "CREATE TABLE " + schema + "." + table_name + " ("
        query += "    gid serial NOT NULL,"
        query += "    wkb_geometry geometry(" + geom_type + "," + srs + "),"
        
        for field in fields:
            if field.get('type') == 'character_varying':
                query += field.get('name').lower() + " character varying,"
                    
            elif field.get('type') == 'integer':
                query += field.get('name').lower() + " integer,"                    
                    
            elif field.get('type') == 'double':
                query += field.get('name').lower() + " double precision,"
                    
            elif field.get('type') == 'boolean':
                query += field.get('name').lower() + " boolean DEFAULT FALSE,"
                    
            elif field.get('type') == 'date':
                query += field.get('name').lower() + " date,"
                
            elif field.get('type') == 'enumeration':
                query += field.get('name').lower() + " character varying,"
            
        query += "    CONSTRAINT " + table_name + "_pkey PRIMARY KEY (gid)"
        query += ");"
        
        self.cursor.execute(query)
        
    def close(self):
        """
        Closes the connection. The Introspect object can't be used afterwards
        """
        self.conn.close()
            