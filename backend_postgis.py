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
from psycopg2._psycopg import quote_ident
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
import random, string

plainIdentifierPattern = re.compile("^[a-zA-Z][a-zA-Z0-9_]*$")
plainSchemaIdentifierPattern = re.compile("^[a-zA-Z][a-zA-Z0-9_]*(.[a-zA-Z][a-zA-Z0-9_]*)?$")


class Introspect:
    def __init__(self, database, host='localhost', port='5432', user='postgres', password='postgres'):
        self.conn = None
        self.database = database
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.__enter__()

    def __enter__(self):
        if not self.conn:
            self.conn = psycopg2.connect(database=self.database, user=self.user, password=self.password, host=self.host, port=self.port)
            delattr(self, 'user')
            delattr(self, 'password')
            self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.conn.cursor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        return exc_type is None
    
    def get_tables(self, schema='public'):
        self.cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s 
        """, [schema])    
        return [r[0] for r in self.cursor.fetchall()]

    def table_exists(self, table_name, schema='public'):
        self.cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = %s and table_schema = %s 
        """, [table_name, schema])
        return (self.cursor.rowcount == 1)
    
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
    
    def _parse_sequence_name(self, definition):
        schema, seq_name, _ = self._parse_qualified_identifier(definition, "'", "nextval('")
        return (schema, seq_name)
    
    def _parse_function_def(self, definition):
        return self._parse_qualified_identifier(definition, "(", 'CREATE OR REPLACE FUNCTION ')
    
    def _parse_function_call(self, definition):
        (schema, func_name, end_str) = self._parse_qualified_identifier(definition, '(', 'EXECUTE PROCEDURE ')
        params = end_str[:-1]
        return (schema, func_name, params)

    def _parse_qualified_identifier(self, definition, end_char, skip_string):
        s = definition[len(skip_string):]
        
        # faster check for plain unquoted identifiers (common case)
        (schema_seq_name, str_end) =  self._parse_sql_identifier(s, end_char, plainSchemaIdentifierPattern)
        if len(schema_seq_name) > 0:
            parts = schema_seq_name.split(".")
            if len(parts) > 1:
                return (parts[0], parts[1], str_end)
            else:
                return ('', parts[0], str_end)

        # deep check for quoted identifiers
        (schema, str_end) =  self._parse_sql_identifier(s, '.')
        if schema != '':
            (seq_name, str_end) =  self._parse_sql_identifier(str_end, end_char)
        else:
            (seq_name, str_end) =  self._parse_sql_identifier(s, end_char)
        return (schema, seq_name, str_end)
        
    def sequence_exists(self, schema, sequence):
        query = """SELECT 1 FROM pg_class c
            LEFT JOIN pg_namespace n on c.relnamespace = n.oid
            WHERE c.relkind = 'S' AND n.nspname = %s AND relname = %s"""
        self.cursor.execute(query, [schema, sequence])
        return (self.cursor.rowcount > 0)
                 
    def get_sequences(self, table, schema='public'):
        """
        Returns a list of tuples, each tuple containing:
        (col_name, full_sequence_name, schema, sequence_name)
        """
        query = """SELECT column_name, column_default FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        AND column_default LIKE %s
        """
        self.cursor.execute(query, [schema, table, 'nextval%'])

        result = []
        for (col, col_default) in self.cursor.fetchall():
            try:
                schema, seq_name = self._parse_sequence_name(col_default)
                if seq_name != '':
                    result.append((col, schema, seq_name))
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
        for (col, schema, seq_name) in seqs:
            if col in pks:
              result.append((col, schema, seq_name))
        return result

    def update_pk_sequences(self, table, schema='public'):
        """
        Ensures the sequence start value is higher than any existing value for the column.
        """
        seqs = self.get_pk_sequences(table, schema)
        sql = "SELECT setval({seq}, max({col})) FROM {schema}.{table}"
        for (col, seq_schema, seq_name) in seqs:
            full_sequence = quote_ident(seq_schema, self.conn) + "." + quote_ident(seq_name, self.conn)
            query = sqlbuilder.SQL(sql).format(
                seq=sqlbuilder.Literal(full_sequence),
                col=sqlbuilder.Literal(col),
                schema=sqlbuilder.Identifier(schema),
                table=sqlbuilder.Identifier(table))
            self.cursor.execute(query)
    
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
    
    def validate_data_type(self, data_type_def):
        """
        Returns a PostgreSQL data type if the provided data_type_def is valid,
        or None otherwise.
        """
        if data_type_def == 'character_varying' or data_type_def == 'character varying':
            return 'character varying'
        elif data_type_def == 'integer':
            return 'integer'
        elif data_type_def == 'double':
            return 'double precision'
        elif data_type_def == 'boolean':
            return 'boolean'
        elif data_type_def == 'date':
            return 'date'
        elif data_type_def == 'time':
            return 'time'
        elif data_type_def == 'timestamp':
            return 'timestamp'
        elif data_type_def == 'timestamp_with_time_zone' or data_type_def == 'timestamp with time zone':
            return 'timestamp with time zone'
        elif data_type_def == 'cd_json':
            return 'character varying'
        elif data_type_def == 'enumeration' or \
                data_type_def == 'multiple_enumeration' or \
                data_type_def == 'form':
            return 'character varying'

    def create_table(self, schema, table_name, geom_type, srs, fields):
        if geom_type == 'Point':
            geom_type = 'MultiPoint'
        if geom_type == 'LineString':
            geom_type = 'MultiLineString'
        if geom_type == 'Polygon':
            geom_type = 'MultiPolygon'
        geom_column = 'wkb_geometry'
        create_table_sqls = [
            sqlbuilder.SQL('ogc_fid serial NOT NULL'),
            sqlbuilder.SQL('{geom_column} geometry({geom_type},{srs})').format(
                                geom_type=sqlbuilder.Identifier(geom_type),
                                srs=sqlbuilder.Literal(int(srs)),
                                geom_column=sqlbuilder.Identifier(geom_column))
        ]
        
        for field in fields:
            data_type = self.validate_data_type(field.get('type'))
            if not data_type:
                continue
            if not field.get('nullable', True):
                nullable_sql = sqlbuilder.SQL('NOT NULL')
            else:
                nullable_sql = sqlbuilder.SQL('')
            if data_type == 'character varying' or \
                data_type == 'integer' or \
                data_type == 'double precision' or \
                data_type == 'boolean' or \
                data_type == 'date' or \
                data_type == 'time' or \
                data_type == 'timestamp' or \
                data_type == 'timestamp with time zone' or \
                data_type == 'enumeration' or \
                data_type == 'multiple_enumeration' or \
                data_type == 'form':
                field_name_sql = sqlbuilder.Identifier(field.get('name'))
                if field.get('default'):
                    default_sql = sqlbuilder.SQL('DEFAULT ' + field.get('default'))
                else:
                    default_sql = sqlbuilder.SQL('')
            elif field.get('type') == 'boolean':
                field_name_sql = sqlbuilder.Identifier(field.get('name'))
                if field.get('default'):
                    default_sql = sqlbuilder.SQL('DEFAULT ' + field.get('default'))
                else:
                    default_sql = sqlbuilder.SQL('DEFAULT FALSE')
            elif field.get('type') == 'cd_json':
                field_name_sql = sqlbuilder.Identifier('cd_json_' + field.get('name'))
                if field.get('default'):
                    default_sql = sqlbuilder.SQL('DEFAULT ' + field.get('default'))
                else:
                    default_sql = sqlbuilder.SQL('')
            else:
                #logger.warning("Invalid type: " + data_type + " - Field: " + field.get('name', ''))
                continue
            field_sql = '{field_name} {data_type} {nullable} {default}'
            create_table_sqls.append(sqlbuilder.SQL(field_sql).format(
                    field_name=field_name_sql,
                    data_type=sqlbuilder.SQL(data_type),
                    nullable=nullable_sql,
                    default=default_sql
                ))
        
        create_table_sqls.append(
            sqlbuilder.SQL('CONSTRAINT {pkey_constraint} PRIMARY KEY (ogc_fid)').format(
                pkey_constraint=sqlbuilder.Identifier(table_name + '_pkey')
            ))
        
        sql = "CREATE TABLE {schema}.{table_name} ({fields_sql})"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table_name=sqlbuilder.Identifier(table_name),
            fields_sql=sqlbuilder.SQL(', ').join(create_table_sqls))
        print(query.as_string(self.conn))
        self.cursor.execute(query)
        spatial_idx_name = table_name + "_" + geom_column + "_geom_idx"
        query = sqlbuilder.SQL("""
            CREATE INDEX {idx_name}
            ON {schema}.{table}
            USING gist
            ({geom_col});
            """).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name),
            geom_col=sqlbuilder.Identifier(geom_column),
            idx_name=sqlbuilder.Identifier(spatial_idx_name)
        )
        self.cursor.execute(query)
        
    def get_triggers(self, schema, table):
        """
        Returns a list of tuples:
        (table_schema, table_name, trigger_schema, trigger_name, event, orientation, activation, condition, definition)
        """
        
        query = """
            SELECT event_object_schema as table_schema,
                   event_object_table as table_name,
                   trigger_schema,
                   trigger_name,
                   string_agg(event_manipulation, ' OR ') as event,
                   action_orientation as orientation,
                   action_timing as activation,
                   action_condition as condition,
                   action_statement as definition
            FROM information_schema.triggers
            WHERE trigger_schema = %s AND event_object_table = %s
            GROUP BY table_schema,table_name,trigger_schema,trigger_name,orientation,activation,condition,definition

            ORDER BY table_schema,
                     table_name;
            """
        # print query
        self.cursor.execute(query, [schema, table])
        return self.cursor.fetchall()

    def clone_sequence(self, target_schema, target_table, column, seq_name, source_schema, source_table):
        if source_table != target_table:
            seq_name.replace(source_table, target_table)
        if seq_name.endswith("_gid_seq"):
            base_name = seq_name[:-8]
            suffix = "_gid_seq"
        elif seq_name.endswith("_ogc_fid_seq"):
            base_name = seq_name[:len("_ogc_fid_seq")]
            suffix = "_ogc_fid_seq"
        else:
            base_name = seq_name
            suffix = "_ogc_fid_seq"
        i = 0
        salt = ''
        while self.sequence_exists(target_schema, seq_name):
            seq_name = base_name + '_' + str(i) + salt + suffix
            i = i + 1
            if (i%1000) == 0:
                salt = '_' + "".join([ random.choice(string.ascii_uppercase + string.digits) for i in range(0,3)])
        query = sqlbuilder.SQL("CREATE SEQUENCE {target_schema}.{seq_name} OWNED BY {target_schema}.{target_table}.{column}").format(
            target_schema=sqlbuilder.Identifier(target_schema),
            seq_name=sqlbuilder.Identifier(seq_name),
            target_table=sqlbuilder.Identifier(target_table),
            column=sqlbuilder.Identifier(column))
        # print query.as_string(self.conn)
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

    def get_function(self, schema, function_name):
        """
        Returns a tuple:
        (schema, func_name, funct_lang, definition, args, return_type)
        """
        query = sqlbuilder.SQL("""
            SELECT n.nspname as function_schema,
               p.proname as function_name,
               l.lanname as function_language,
               CASE when l.lanname = 'internal' then p.prosrc
                ELSE pg_get_functiondef(p.oid)
                END as definition,
               pg_get_function_arguments(p.oid) as function_arguments,
               t.typname as return_type
            FROM pg_proc p
                LEFT JOIN pg_namespace n on p.pronamespace = n.oid
                LEFT JOIN pg_language l on p.prolang = l.oid
                LEFT JOIN pg_type t on t.oid = p.prorettype 
            WHERE n.nspname not in ('pg_catalog', 'information_schema', 'public')
                AND p.proname = {function}
                AND n.nspname = {schema}
            ORDER BY function_schema, function_name;
        """).format(
            schema=sqlbuilder.Literal(schema),
            function=sqlbuilder.Literal(function_name))
        self.cursor.execute(query)

        result = self.cursor.fetchall()
        if len(result)>0:
            return result[0]

    def clone_function(self, target_schema, source_schema, source_function):
        function_tuple = self.get_function(source_schema, source_function)
        if function_tuple is not None:
            target_function = source_function
            (_, _, _, definition, _, _) = function_tuple
            function_tuple = self.get_function(target_schema, target_function)
            
            i = 1
            salt = ''
            while function_tuple is not None:
                target_function = source_function + '_' + str(i) + salt
                i = i + 1
                if (i%1000) == 0:
                    salt = '_' + "".join([ random.choice(string.ascii_uppercase + string.digits) for i in range(0,3)])
                function_tuple = self.get_function(target_schema, target_function)
        
        (_, _, end_str) = self._parse_function_def(definition)
        
        query = sqlbuilder.SQL("""
            CREATE OR REPLACE FUNCTION {schema}.{function}({definition}
        """).format(
            schema=sqlbuilder.Identifier(target_schema),
            function=sqlbuilder.Identifier(target_function),
            definition=sqlbuilder.SQL(end_str))
        # print query.as_string(self.conn)
        self.cursor.execute(query)
        return target_function

    def install_trigger(self, trigger_name, target_schema, target_table,
                        activation, event, orientation, condition, func_schema, func_name, params):
        if not activation in ['BEFORE', 'AFTER', 'INSTEAD OF']:
            # FIXME: use a specific exception class
            raise Exception('Invalid activation value')
        if not re.match("^(INSERT|UPDATE|DELETE|TRUNCATE)( +(?:OR) +(INSERT|UPDATE|DELETE|TRUNCATE))*$", event):
            raise Exception('Unsupported event value')
        if not orientation in ['ROW', 'STATEMENT']:
            raise Exception('Invalid orientation value')
        if not isinstance(condition, sqlbuilder.SQL):
            condition = sqlbuilder.SQL(condition)
                
        if isinstance(params, list):
            params = sqlbuilder.SQL(', ').join([sqlbuilder.Literal(p) for p in params])
        else:
            params = sqlbuilder.SQL(params)
            
        definition = sqlbuilder.SQL("EXECUTE PROCEDURE {schema}.{function}({params})").format(
            schema=sqlbuilder.Identifier(func_schema),
            function=sqlbuilder.Identifier(func_name),
            params=params)
        query = sqlbuilder.SQL("""
            CREATE TRIGGER {trigger_name} {activation} {event}
            ON {schema}.{table}
            FOR EACH {orientation} {condition} {definition};
            """).format(
                trigger_name=sqlbuilder.Identifier(trigger_name),
            schema=sqlbuilder.Identifier(target_schema),
            table=sqlbuilder.Identifier(target_table),
            activation=sqlbuilder.SQL(activation),
            event=sqlbuilder.SQL(event),
            orientation=sqlbuilder.SQL(orientation),
            condition=condition,
            definition=definition
        )
        #print query.as_string(self.conn)
        self.cursor.execute(query)
    
    def drop_trigger(self, trigger_name, target_schema, target_table):
        sql_tpl = 'DROP TRIGGER IF EXISTS {trigger_name} ON {schema}.{table}'
        query = sqlbuilder.SQL(sql_tpl).format(
            trigger_name=sqlbuilder.Identifier(trigger_name),
            schema=sqlbuilder.Identifier(target_schema),
            table=sqlbuilder.Identifier(target_table)
            )
        print query.as_string(self.conn)
        self.cursor.execute(query)
        
    def clone_triggers(self, target_schema, target_table, source_schema, source_table):
        for trigger in self.get_triggers(source_schema, source_table):
            """
            table_schema = trigger[0]
            table_name = trigger[1]
            trigger_schema = trigger[2]
            trigger_name = trigger[3]
            event = trigger[4]
            orientation = trigger[5]
            activation = trigger[6]
            print trigger_name
            condition = trigger[7]
            definition = trigger[8]
            """
            (_, _, _, trigger_name, event, orientation, activation, condition, definition) = trigger
            if source_table != target_table and trigger_name.startswith(source_table):
                # try to get a equivalent name
                trigger_name = target_table + trigger_name[len(source_table):]
            if condition:
                condition = sqlbuilder.SQL("WHEN {condition}").format(condition=sqlbuilder.SQL(condition))
            else:
                condition = sqlbuilder.SQL("")
            (func_schema, func_name, end_str) = self._parse_function_call(definition)
            params = end_str[:-1]
            if func_schema == source_schema:
                func_name = self.clone_function(target_schema, source_schema, func_name)
                func_schema = target_schema
                
            definition = sqlbuilder.SQL("EXECUTE PROCEDURE {schema}.{function}({params})").format(
                schema=sqlbuilder.Identifier(target_schema),
                function=sqlbuilder.Identifier(func_name),
                params=sqlbuilder.SQL(params))
            
            self.install_trigger(trigger_name, target_schema, target_table, activation, event, orientation, condition, func_schema, func_name, params)

    def clone_table(self, schema, table_name, target_schema, new_table_name, copy_data=True):
        base_name = new_table_name
        i = 0
        while self.table_exists(new_table_name, target_schema):
            # get a unique name
            salt = ''
            new_table_name = base_name + '_' + str(i) + salt
            i = i + 1
            if (i%1000) == 0:
                salt = '_' + "".join([ random.choice(string.ascii_uppercase + string.digits) for i in range(0,3)])
        
        query_tpl = "CREATE TABLE {target_schema}.{new_table} AS TABLE {schema}.{table}"
        if not copy_data:
            query_tpl += " WITH NO DATA"
        query = sqlbuilder.SQL(query_tpl).format(
            target_schema=sqlbuilder.Identifier(target_schema),
            new_table=sqlbuilder.Identifier(new_table_name),
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name))
        # print query.as_string(self.conn)
        self.cursor.execute(query)
        
        for (column, schema, seq_name) in self.get_sequences(table_name, schema):
            self.clone_sequence(target_schema, new_table_name, column, seq_name, schema, table_name)
        
        self.clone_pks(target_schema, new_table_name, schema, table_name)
        
        geom_cols = self.get_geometry_columns(table_name, schema)
        for geom_col in geom_cols:
            self.clone_spatial_index(target_schema, new_table_name, geom_col)
        
        self.clone_triggers(target_schema, new_table_name, schema, table_name)
        return new_table_name
        
    def delete_table(self, schema, table_name):
        query = sqlbuilder.SQL("DROP TABLE IF EXISTS {schema}.{table}").format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name))
        self.cursor.execute(query,  [])
        
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
        
    def get_count(self, schema, table):
        sql = "SELECT COUNT(*) FROM {schema}.{table}"
        query = sqlbuilder.SQL(sql).format(
                schema=sqlbuilder.Identifier(schema),
                table=sqlbuilder.Identifier(table))
        self.cursor.execute(query)
        row = self.cursor.fetchone()
        return row[0]

    def get_estimated_count(self, schema, table):
        query = "SELECT reltuples::BIGINT AS estimate FROM pg_class WHERE relname = %s";
        self.cursor.execute(query, [table])
        rows = self.cursor.fetchall()
        if self.cursor.rowcount == 1:
            return rows[0][0]
        else:
            return self.get_count(schema, table)
    
    def get_bbox_firstgeom(self, schema, table, expand):
        column_name = self.get_geometry_columns(table, schema)[0]
        if expand is None:
            expand = 0
        sql = """SELECT ST_XMin(bbox) xmin, ST_YMin(bbox) ymin, ST_XMax(bbox) xmax, ST_YMax(bbox) ymax
        FROM
        (SELECT BOX2D(ST_EXPAND(ST_TRANSFORM({column_name}, 4326), {expand})) bbox
        FROM {schema}.{table}
        WHERE %s IS NOT NULL LIMIT 1) as s0"""
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            column_name=sqlbuilder.Identifier(column_name),
            expand=sqlbuilder.Literal(expand)
            )
        self.cursor.execute(query, [column_name])
        row = self.cursor.fetchone()
        return (row[0], row[1], row[2], row[3])
    
    def get_bbox(self, schema, table_name, geom_field):
        """
        Returns a tuple containing the bounding box of the layer using the format (minx, miny, maxx, maxy)
        """
        sql = """
        SELECT ST_XMin(bbox) xmin, ST_YMin(bbox) ymin, ST_XMax(bbox) xmax, ST_YMax(bbox) ymax
        FROM
        (SELECT ST_Extent({geom_field}) bbox FROM {schema}.{table} as s1) as s0
        """
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name),
            geom_field=sqlbuilder.Identifier(geom_field))
        self.cursor.execute(query,  [])
        row = self.cursor.fetchone()
        return (row[0], row[1], row[2], row[3])
    
    def set_field_nullable(self, schema, table, field, nullable):
        """
        Sets a column to NULL / NOT NULL
        """
        if nullable:
            sql = "ALTER TABLE {schema}.{table} ALTER COLUMN {field} DROP NOT NULL ;"
        else:
            sql = "ALTER TABLE {schema}.{table} ALTER COLUMN {field} SET NOT NULL ;"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            field=sqlbuilder.Identifier(field))
        self.cursor.execute(query)

    def set_field_default(self, schema, table, field, default_value=None):
        """
        Sets a column default value. Use None to drop the default value of a column.
        Warning: 'default_value' parameter is not protected against SQL injection.
        Always validate user input to feed this parameter.
        """
        if default_value is None:
            sql = "ALTER TABLE {schema}.{table} ALTER COLUMN {field} DROP DEFAULT"
        else:
            sql = "ALTER TABLE {schema}.{table} ALTER COLUMN {field} SET DEFAULT " + default_value
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            field=sqlbuilder.Identifier(field))
        self.cursor.execute(query)

    def check_has_null_values(self, schema, table, field):
        """
        Returns True if the column has any null values and False otherwise
        """
        sql = "SELECT 1 FROM {schema}.{table} WHERE {field} IS NULL LIMIT 1;"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            field=sqlbuilder.Identifier(field))
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

    def delete_column(self, schema, table_name, column_name):
        query = sqlbuilder.SQL("ALTER TABLE {schema}.{table} DROP COLUMN {column}").format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name),
            column=sqlbuilder.Identifier(column_name))
        self.cursor.execute(query,  [])

    def rename_column(self, schema, table_name, column_name, new_column_name):
        query = sqlbuilder.SQL("ALTER TABLE {schema}.{table} RENAME COLUMN {column_name} TO {new_column_name}").format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name),
            column_name=sqlbuilder.Identifier(column_name),
            new_column_name=sqlbuilder.Identifier(new_column_name))
        self.cursor.execute(query,  [])

    def add_column(self, schema, table_name, column_name, sql_type, nullable=True, default=None):
        """
        Warning: 'default' parameter is not protected against SQL injection. Always validate
        user input to feed this parameter.
        """
        data_type = self.validate_data_type(sql_type)
        if not data_type:
            raise Exception('Invalid data type')
        if not nullable:
            nullable_query = sqlbuilder.SQL("NOT NULL")
        else:
            nullable_query = sqlbuilder.SQL("")
        if default:
            default_query = sqlbuilder.SQL("DEFAULT " + default)
        else:
            default_query = sqlbuilder.SQL("")
        query = sqlbuilder.SQL("ALTER TABLE {schema}.{table} ADD COLUMN {column_name} {sql_type} {nullable} {default}").format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name),
            column_name=sqlbuilder.Identifier(column_name),
            sql_type=sqlbuilder.SQL(data_type),
            nullable=nullable_query,
            default=default_query)
        self.cursor.execute(query,  [])
    """
    def allowed_conversion(self, new_type, old_type):
        " ""
        TO BE COMPLETED
        Note that some conversions are allowed but can fail depending on the input data (e.g. text to int with not int values)
        " ""
        if new_type == 'integer' and (old_type == 'character varying'
                                      or old_type == 'text'
                                      or old_type == 'double precision'
                                      or old_type == 'numeric'
                                      or old_type == 'boolean'):
            return True
        if new_type == 'double precision' and (old_type == 'character varying'
                                      or old_type == 'text'
                                      or old_type == 'double precision'
                                      or old_type == 'numeric'
                                      or old_type == 'boolean'):
            return True
        return False
        " ""
    """
    
    """
    def alter_column_type(self, schema, table_name, column_name, new_type, old_type, expression=None, cast=None):
        " ""
        TO BE COMPLETED
        " ""
        if not expression:
            expression = column_name
        
        if not cast:
            if new_type == 'integer' and (old_type == 'character varying' or old_type == 'text' or old_type == 'double precision'):
                cast = 'integer'
            if new_type == 'double precision' and (old_type == 'character varying' or old_type == 'text'):
                cast = 'double precision'
            else:
                cast = new_type
        if cast:
            sql = "ALTER TABLE {schema}.{table} ALTER COLUMN {column_name} TYPE {new_type} USING CAST ( {expression} AS {cast})"
        else:
            sql = "ALTER TABLE {schema}.{table} ALTER COLUMN {column_name} TYPE {new_type}"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table_name),
            column_name=sqlbuilder.Identifier(column_name),
            expression=sqlbuilder.Identifier(expression),
            new_type=sqlbuilder.Identifier(new_type))
        self.cursor.execute(query,  [])
    """
        
    def close(self):
        """
        Closes the connection. The Introspect object can't be used afterwards
        """
        self.conn.close()

