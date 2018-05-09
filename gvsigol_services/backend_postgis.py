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
from django.contrib.gis.db.models import sql
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
import json

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

    def get_sequences(self, table, schema='public'):
        self.cursor.execute("""
        SELECT column_name, column_default FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        AND column_default LIKE %s
        """, [schema, table, 'nextval%'])

        result = []
        for (col, col_default) in self.cursor.fetchall():
            try:
              s = col_default[9:]
              seq = s[:s.find("'")]
              result.append((col, seq))
            except:
              pass

        return result

    def get_pk_sequences(self, table, schema='public'):
        seqs = self.get_sequences(table, schema)
        pks = self.get_pk_columns(table, schema)
        result = []
        for (col, seq) in seqs:
            if col in pks:
              result.append((col, seq))
        return result

    def update_pk_sequences(self, table, schema='public'):
        """
        Ensures the sequence start value is higher than any existing value for the column.
        """
        seqs = self.get_pk_sequences(table, schema)
        for (col, seq) in seqs:
            sql = "SELECT setval('" + seq + "', max(" + col + ")) FROM " + schema + "." + table + " ;"
            self.cursor.execute(sql)
    
    def get_fields_info(self, table, schema='public'):
        self.cursor.execute("""
        SELECT ordinal_position, column_name, data_type, character_maximum_length, numeric_precision, numeric_scale, is_nullable FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s 
        """, [schema, table])
        
        return [{'order':r[0], 'name': r[1], 'type': r[2], 'length': r[3], 'precision': r[4], 'scale': r[5], 'nullable': r[6]} for r in self.cursor.fetchall()]
    
    
    def get_mosaic_temporal_info(self, table, schema='public',default_mode=None, default_value=None):
        query = "SELECT COALESCE(to_char(MIN(date), 'YYYY-MM-DD HH24:MI:SS'), '') FROM "+schema+"."+table+""
        self.cursor.execute(query, [])
        min = None
        for r in self.cursor.fetchall():
            min = r[0]
        
        query = "SELECT COALESCE(to_char(MAX(date), 'YYYY-MM-DD HH24:MI:SS'), '') FROM "+schema+"."+table+""
        self.cursor.execute(query, [])
        max = None
        for r in self.cursor.fetchall():
            max = r[0]
        
        values=[]
        query = "SELECT COALESCE(to_char(date, 'YYYY-MM-DD HH24:MI:SS'), '') FROM "+schema+"."+table+""
        self.cursor.execute(query, [])
        for r in self.cursor.fetchall():
            values.append(r[0])
        
        return [{'min_value':min, 'max_value':max, 'values': values}]
    
    
    def delete_mosaic(self, table, schema='public'):
        query = "DROP TABLE IF EXISTS "+schema+"."+table+" CASCADE"
        self.cursor.execute(query, [])
                
        return True
    
    
    def get_temporal_info(self, table, schema='public', field1=None, field2=None, default_mode=None, default_value=None):
        query = "SELECT COALESCE(to_char(MIN(x.a), 'YYYY-MM-DD HH24:MI:SS'), '') FROM (SELECT "+field1+" a FROM "+schema+"."+table+") x"
        self.cursor.execute(query, [])
        min = None
        for r in self.cursor.fetchall():
            min = r[0]
        
        if field2 == None or field2 =='' or field2 == field1:
            query = """
                    SELECT COALESCE(to_char(MAX(x.a), 'YYYY-MM-DD HH24:MI:SS'), '') FROM
                    (
                    SELECT """+field1+""" a FROM """+schema+"""."""+table+""" WHERE  """+field1+""" IS NOT NULL
                    ) x
                    """
        else:
            #query = """
            #        SELECT COALESCE(to_char(MAX(x.a), 'YYYY-MM-DD HH24:MI:SS'), '') FROM
            #        (
            #        SELECT """+field1+""" a FROM """+schema+"""."""+table+""" WHERE  """+field2+""" IS NULL
            #        UNION
            #        SELECT """+field2+""" a FROM """+schema+"""."""+table+""" WHERE  """+field2+""" IS NOT NULL
            #        ) x
            #        """
            query = """
                    SELECT COALESCE(to_char(MAX(x.a), 'YYYY-MM-DD HH24:MI:SS'), '') FROM
                    (
                    SELECT """+field2+""" a FROM """+schema+"""."""+table+""" WHERE  """+field2+""" IS NOT NULL
                    ) x
                    """
        self.cursor.execute(query, [])
        max = None
        for r in self.cursor.fetchall():
            max = r[0]
            
        return [{'min_value':min, 'max_value':max}]
    
    
    def get_widget_geometry_info(self, table, schema='public', field=None, value=None, default_geometry_field='wkb_geometry'):
        query = "SELECT json_build_object('type','Feature', 'geometry', ST_AsGeoJSON("+ default_geometry_field +")::json, 'srs', ST_SRID("+ default_geometry_field +"), 'properties', to_json(row)) FROM (SELECT * FROM "+schema+"."+table+" WHERE " + field + " = '" + value +"' LIMIT 1) row;"
        self.cursor.execute(query, [])
        geom = None
        for r in self.cursor.fetchall():
            geom = r[0]
        
        return geom
    
    
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
                
            elif field.get('type') == 'time':
                query += field.get('name').lower() + " time,"
                
            elif field.get('type') == 'timestamp':
                query += field.get('name').lower() + " timestamp,"
                
            elif field.get('type') == 'cd_json':
                query += 'cd_json_' + field.get('name').lower() + " character varying,"
                
            elif field.get('type') == 'enumeration':
                query += field.get('name').lower() + " character varying,"
            
            elif field.get('type') == 'multiple_enumeration':
                name = field.get('name').lower().replace('enm_', 'enmm_')
                query += name + " character varying,"
                
            elif field.get('type') == 'form':
                query += field.get('name').lower() + " character varying,"
            
        query += "    CONSTRAINT " + table_name + "_pkey PRIMARY KEY (gid)"
        query += ");"
        
        self.cursor.execute(query)
        
    def delete_table(self, schema, table_name):
        query = "DROP TABLE IF EXISTS " + schema + "." + table_name + ";"
        
        self.cursor.execute(query)
        
    def insert_sql(self, schema, table_name, sql):
        query = "INSERT INTO " + schema + "." + table_name + " " + sql + ";"
        self.cursor.execute(query)
           
    def set_transaction(self, schema, table_name):
        query = "BEGIN;"
        self.cursor.execute(query)
    
    def end_transaction_commit(self, schema, table_name):
        query = "COMMIT;"
        self.cursor.execute(query)
        
    def end_transaction_rollback(self, schema, table_name):
        query = "ROLLBACK;"
        self.cursor.execute(query)
    
    def remove_data(self, schema, table_name, sql=None):
        query = "DELETE FROM " + schema + "." + table_name
        if sql:
            query = query + ' WHERE ' + sql
        query = query + ';'
        
        self.cursor.execute(query)
        
    def get_count(self, schema, layer_name):
        query = "SELECT COUNT(*) FROM " + schema + "." + layer_name;
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        count = rows[0]
        
        return count
    def get_estimated_count(self, schema, layer_name):
        query = "SELECT reltuples::BIGINT AS estimate FROM pg_class WHERE relname='" + layer_name + "'";
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        if self.cursor.rowcount == 1:
            return rows[0]
        else:
            return self.get_count(schema,layer_name)
    
    def get_bbox_firstgeom(self, schema, layer_name, expand):
        column_name = self.get_geometry_columns(layer_name,schema)
        if expand is None:
            ex = 0
        else:
            ex = str(expand)
        query = "SELECT BOX2D(ST_EXPAND(ST_TRANSFORM(" + column_name[0] + ",4326),"  + ex + ")) FROM " + schema + "." + layer_name + " WHERE " + column_name[0] + " IS NOT NULL LIMIT 1"
        self.cursor.execute(query)
        rows = self.cursor.fetchone()
        bb = rows[0]
        bb = bb.replace("BOX(","").replace(")","").replace(" ", ",")        
        return bb
        
    def close(self):
        """
        Closes the connection. The Introspect object can't be used afterwards
        """
        self.conn.close()

