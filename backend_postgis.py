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
from psycopg2 import sql as sqlbuilder
from psycopg2.extensions import quote_ident
import re

plainIdentifierPattern = re.compile("^[a-zA-Z][a-zA-Z0-9_]*$")
plainSchemaIdentifierPattern = re.compile("^[a-zA-Z][a-zA-Z0-9_]*(.[a-zA-Z][a-zA-Z0-9_]*)?$")

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

    def get_geometry_column_info(self, table=None, column=None, schema='public'):
        """
        Gives information about a geometry column. Use exact name.
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
            WHERE f_table_schema = %s AND f_table_name = %s and f_geometry_column = %s
            """, [schema, table, column])
        
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
        qualified_table = quote_ident(schema, self.conn) + "." + quote_ident(table, self.conn) 

        query = sqlbuilder.SQL("""
        SELECT a.attname AS field_name
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                        WHERE
                        i.indrelid = ({schema_table})::regclass
                        AND i.indisprimary
        """).format(schema_table=sqlbuilder.Literal(qualified_table))
        self.cursor.execute(query)
        return [r[0] for r in self.cursor.fetchall()]
    
    def get_fields(self, table, schema='public'):
        self.cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s 
        """, [schema, table])
        
        return [r[0] for r in self.cursor.fetchall()]

    def _parse_sql_identifier(self, s, expected_next_char, pattern=plainIdentifierPattern):
        """
        Parses the provided string an returns a tuple with the parsed identifier and the rest of the string.
        Returns a tuple of empty strings if the provided string could not be properly parsed
        """
        if len(s) > 0 and s[0] != '"':
            # unquoted, normal identifier
            
            pos = s.find(expected_next_char)
            if pos > 0:
                identifier = s[:pos]
                if pattern.match(identifier):
                    return (identifier, s[pos+1:])
        else:
            s = s[1:]
            prev_escape_char = ''
            seq_name_list = []
            for idx, c in enumerate(s):
                if c == '"':
                    if prev_escape_char == '"':
                        seq_name_list.append('"')
                        prev_escape_char = ''
                    else:
                        prev_escape_char = '"'
                elif prev_escape_char != '"':
                    seq_name_list.append(c)
                else:
                    seq_name = u''.join(seq_name_list)
                    str_end = s[idx:]
                    break
            if len(str_end) > 0 and str_end[0] == expected_next_char:
                return (seq_name, str_end[1:])
        return ('', '')
    
    def _parse_sequence_name(self, default_value_def):
        s = default_value_def[9:]
        
        # faster check for plain unquoted identifiers (common case)
        (schema_seq_name, str_end) =  self._parse_sql_identifier(s, "'", plainSchemaIdentifierPattern)
        if len(schema_seq_name) > 0:
            parts = schema_seq_name.split(".")
            if len(parts) > 1:
                return (parts[0], parts[1])
            else:
                return ('', parts[0])

        # deep check for quoted identifiers
        (schema, str_end) =  self._parse_sql_identifier(s, '.')
        if schema != '':
            (seq_name, str_end) =  self._parse_sql_identifier(str_end, "'")
        else:
            (seq_name, str_end) =  self._parse_sql_identifier(s, "'")
        return (schema, seq_name)
        
    def get_sequences(self, table, schema='public'):
        """
        Returns a list of tuples, each tuple containing:
        (col_name, full_sequence_name, schema, sequence_name)
        """
        self.cursor.execute("""
        SELECT column_name, column_default FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        AND column_default LIKE %s
        """, [schema, table, 'nextval%'])

        result = []
        for (col, col_default) in self.cursor.fetchall():
            try:
                schema, seq_name = self._parse_sequence_name(col_default)
                if seq_name != '':
                    if schema != '':
                        result.append((col, schema + u'.' + seq_name, schema, seq_name))
                    else:
                        result.append((col, seq_name, schema, seq_name))
            except:
              pass

        return result

    def schema_exists(self, schema):
        self.cursor.execute("""
        SELECT count(*) FROM information_schema.schemata WHERE schema_name = %s
        """, [schema])
        results = self.cursor.fetchall()
        exists = results[0][0]
        return (exists > 0)
        
    def get_pk_sequences(self, table, schema='public'):
        seqs = self.get_sequences(table, schema)
        pks = self.get_pk_columns(table, schema)
        result = []
        for (col, seq, _, _) in seqs:
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
    
    
    def get_fields_mv_info(self, table, schema='public'):
        self.cursor.execute("""   
        SELECT a.attnum, a.attname,
        pg_catalog.format_type(a.atttypid, a.atttypmod), NULL, NULL, NULL,
        (CASE WHEN (a.attnotnull IS NOT NULL AND a.attnotnull = TRUE) THEN 'YES' ELSE 'NO' END)
        FROM pg_attribute a
        JOIN pg_class t on a.attrelid = t.oid
        JOIN pg_namespace s on t.relnamespace = s.oid
        WHERE a.attnum > 0 
        AND NOT a.attisdropped
        AND s.nspname = %s 
        AND t.relname = %s
        ORDER BY a.attnum;
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
        
        if not field or not value:
            where = ''
        else:
            where = " WHERE " + field + " = '" + value +"'" 
            
        query = "SELECT json_build_object('type','Feature', 'geometry', ST_AsGeoJSON("+ default_geometry_field +")::json, 'srs', ST_SRID("+ default_geometry_field +"), 'properties', to_json(row)) FROM (SELECT * FROM "+schema+"."+table + where+" LIMIT 1) row;"
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
                query += field.get('name').lower() + " character varying,"
                
            elif field.get('type') == 'form':
                query += field.get('name').lower() + " character varying,"
            
        query += "    CONSTRAINT " + table_name + "_pkey PRIMARY KEY (gid)"
        query += ");"
        
        self.cursor.execute(query)
        
    
    def clone_sequence(self, target_schema, target_table, column, seq_name, source_schema, source_table):
        query = sqlbuilder.SQL("CREATE SEQUENCE {target_schema}.{seq_name} OWNED BY {target_schema}.{target_table}.{column}").format(
            target_schema=sqlbuilder.Identifier(target_schema),
            seq_name=sqlbuilder.Identifier(seq_name),
            target_table=sqlbuilder.Identifier(target_table),
            column=sqlbuilder.Identifier(column))
        print query.as_string(self.conn)
        self.cursor.execute(query,  [])
        
        full_sequence = quote_ident(target_schema, self.conn) + "." + quote_ident(seq_name, self.conn) 
        query = sqlbuilder.SQL("ALTER TABLE {target_schema}.{target_table} ALTER COLUMN  {column} SET DEFAULT nextval({full_sequence})").format(
            target_schema=sqlbuilder.Identifier(target_schema),
            target_table=sqlbuilder.Identifier(target_table),
            column=sqlbuilder.Identifier(column),
            full_sequence=sqlbuilder.Literal(full_sequence))
        self.cursor.execute(query, [])

        query = sqlbuilder.SQL("ALTER TABLE {target_schema}.{target_table} ALTER COLUMN  {column} SET NOT NULL").format(
            target_schema=sqlbuilder.Identifier(target_schema),
            target_table=sqlbuilder.Identifier(target_table),
            column=sqlbuilder.Identifier(column))
        self.cursor.execute(query, [])
        """
        CREATE SEQUENCE wds_testclonado43.countries4326_ogc_fid_seq OWNED BY wds_testclonado43.countries4326.ogc_fid;  
        ALTER TABLE wds_testclonado43.countries4326 ALTER COLUMN  ogc_fid SET DEFAULT nextval('wds_testclonado43.countries4326_ogc_fid_seq');
        ALTER TABLE wds_testclonado43.countries4326 ALTER COLUMN  ogc_fid SET NOT NULL;
        ALTER SEQUENCE wds_testclonado43.countries4326_ogc_fid_seq OWNED BY wds_testclonado43.countries4326.ogc_fid;    -- 8.2 or later
        """
    
    def clone_pks(self, target_schema, target_table, source_schema, source_table):
        pks = self.get_pk_columns(source_table, source_schema)
        if len(pks) > 0:
            pk_fields = [sqlbuilder.Identifier(pk) for pk in pks]
            query = sqlbuilder.SQL("ALTER TABLE {schema}.{table}  ADD PRIMARY KEY ({fields})").format(
                schema=sqlbuilder.Identifier(target_schema),
                table=sqlbuilder.Identifier(target_table),
                fields=sqlbuilder.SQL(',').join(pk_fields)
            )
            self.cursor.execute(query)
        
    
    def clone_spatial_index(self, target_schema, target_table, geom_col):
        idx_name = target_table + "_" + geom_col + "_geom_idx"
        query = sqlbuilder.SQL("""
            CREATE INDEX {idx_name}
            ON {schema}.{table}
            USING gist
            ({geom_col});
            """).format(
            schema=sqlbuilder.Identifier(target_schema),
            table=sqlbuilder.Identifier(target_table),
            geom_col=sqlbuilder.Identifier(geom_col),
            idx_name=sqlbuilder.Identifier(idx_name)
        )
        self.cursor.execute(query)
    
    def clone_table(self, schema, table_name, target_schema, new_table_name, clone_data=True):
        query = sqlbuilder.SQL("CREATE TABLE {target_schema}.{new_table} AS TABLE {schema}.{table}").format(
            target_schema=sqlbuilder.Identifier(target_schema),
            new_table=sqlbuilder.Identifier(new_table_name),
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name))
        if not clone_data:
            query += " WITH NO DATA"
        self.cursor.execute(query)
        
        for (column, _, schema, seq_name) in self.get_sequences(table_name, schema):
            self.clone_sequence(target_schema, new_table_name, column, seq_name, schema, table_name)
        
        self.clone_pks(target_schema, new_table_name, schema, table_name)
        
        geom_cols = self.get_geometry_columns(table_name, schema)
        for geom_col in geom_cols:
            self.clone_spatial_index(target_schema, new_table_name, geom_col)
        
    def delete_table(self, schema, table_name):
        query = "DROP TABLE IF EXISTS " + schema + "." + table_name + ";"
        
        self.cursor.execute(query)
        
    def insert_sql(self, schema, table_name, sql):
        query = "INSERT INTO " + schema + "." + table_name + " " + sql + ";"
        self.cursor.execute(query)

    def select_sql(self, schema, table_name, sql):
        query = "SELECT * FROM " + schema + "." + table_name + " " + sql + ";"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        return rows

    def custom_query(self, query):
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        return rows
    
    def custom_query_fetchone(self, query):
        self.cursor.execute(query)
        row = self.cursor.fetchone()

        return row

    def custom_no_return_query(self, query):
        self.cursor.execute(query)


    def set_transaction(self):
        query = "BEGIN;"
        self.cursor.execute(query)
    
    def end_transaction_commit(self):
        query = "COMMIT;"
        self.cursor.execute(query)
        
    def end_transaction_rollback(self):
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
    
    def set_field_mandatory(self, schema, table, field):
        """
        Sets a column to NOT NULL
        """
        query = "ALTER TABLE " + schema + "." + table + " ALTER COLUMN " + field + " SET NOT NULL ;"
        self.cursor.execute(query)
        
    def set_field_not_mandatory(self, schema, table, field):
        """
        Sets a column to NOT NULL
        """
        query = "ALTER TABLE " + schema + "." + table + " ALTER COLUMN " + field + " DROP NOT NULL ;"
        self.cursor.execute(query)
        
    def check_has_null_values(self, schema, table, field):
        """
        Returns True if the column has any null values and False otherwise
        """
        query = "SELECT * FROM " + schema + "." + table + " WHERE " + field + " IS NULL ;"
        self.cursor.execute(query)
        if self.cursor.rowcount > 0:
            return True
        return False
    
    def is_column_nullable(self, schema, table, field):
        self.cursor.execute("""
        select c.is_nullable
        from information_schema.columns c
        join information_schema.tables t on c.table_schema = t.table_schema 
        and c.table_name = t.table_name
        where c.table_schema not in ('pg_catalog', 'information_schema')
          and t.table_type = 'BASE TABLE' and c.table_name=%s and c.table_schema=%s and column_name=%s;
        """, [table, schema, field])
        rows = self.cursor.fetchall()
        if(rows[0][0] == 'YES'):
            return False
        else:
            return True
        
    def nullable_cols(self, schema, table):
        self.cursor.execute("""
        select c.column_name, c.is_nullable
        from information_schema.columns c
        join information_schema.tables t on c.table_schema = t.table_schema 
        and c.table_name = t.table_name
        where c.table_schema not in ('pg_catalog', 'information_schema')
          and t.table_type = 'BASE TABLE' and c.table_name=%s and c.table_schema=%s;
        """, [table, schema])
        rows = self.cursor.fetchall()
        res = {}
        for r in rows:
            if(r[1] == 'YES'):
                res[r[0]] = False
            else:
                res[r[0]] = True
        return res
        
    def close(self):
        """
        Closes the connection. The Introspect object can't be used afterwards
        """
        self.conn.close()

