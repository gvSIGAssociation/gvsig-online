# -*- coding: utf-8 -*-

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
import psycopg2
import json
    
def get_connection(connection):
    #Conectamos a la base de datos
    try:
        conn = psycopg2.connect("host=" + connection.get('host') +" port=" + connection.get('port') +" dbname=" + connection.get('database') +" user=" + connection.get('user') +" password="+ connection.get('passwd') );
        #conn = psycopg2.connect("host=test.scolab.eu" +" port=" + connection.get('port') +" dbname=" + connection.get('database') +" user=" + connection.get('user') +" password="+ connection.get('passwd') );
        print "Conectado ..."
    except StandardError, e:
        print "Fallo al conectar!", e
        return []
    
    #creamos un cursor y ejecutamos las sentencias
    return conn;

def close_connection(cursor, conn):
    #cerramos conexion y salimos
    cursor.close();
    conn.close();

def get_distinct_query(connection, layer, field):
    values = []
    conn = get_connection(connection)
    cursor = conn.cursor()
    
    try:
        sql = "SELECT DISTINCT("+ field +") FROM "+ layer +" ORDER BY "+ field +" ASC;"
        
        cursor.execute(sql);
        rows = cursor.fetchall()
        for row in rows:
            values.append(row[0])

    except StandardError, e:
        print "Fallo en el select", e
        return []
    
    close_connection(cursor, conn)
    return values           


def get_minmax_query(connection, layer, field):
    values = []
    conn = get_connection(connection)
    cursor = conn.cursor()
    
    try:
        sql = "SELECT MIN("+ field +") AS MinValue, MAX("+ field +") AS MaxValue FROM "+ layer +" WHERE "+ field +" IS NOT NULL;"
        
        cursor.execute(sql);
        rows = cursor.fetchall()

    except StandardError, e:
        print "Fallo en el getMIN y getMAX", e
        return {}
    
    close_connection(cursor, conn)
    
    if len(rows) > 0:
        minmax = rows[0]
        if len(minmax) == 2:
            min = minmax[0]
            max = minmax[1]
            return json.dumps({'min': float(min), 'max': float(max)})
    
    return {}


def sortFontsArray(array):
    sortedArray = sorted(array)
    output = {}
    seen = set()
    for val in sortedArray:
        value = str(val)
        index = value.find(".") 
        
        if index != -1:
            value = value[0:index]
        
        if value not in seen:
            output[value] = value
            seen.add(value)
    return output