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
from models import  StyleLayer
import tempfile, zipfile
import os, shutil, errno
import psycopg2
import json

def __get_uncompressed_file_upload_path(f):
    dir_path = tempfile.mkdtemp(suffix='', prefix='tmp-library-')
    z = zipfile.ZipFile(f, "r")
    z.extractall(dir_path)
    return dir_path

def __delete_temporaries(file_path):
    try:
        # delete the whole dir if file_path is a dir
        # otherwise just delete file_path
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
    except:
        # ignore any errors deleting temporaries
        pass

def __compress_folder(file_path):
        #(fd, zip_path) = tempfile.mkstemp(prefix='tmp-library-', suffix=".zip")
        #os.close(fd)
        s = tempfile.TemporaryFile()
        
        relroot = file_path
        with zipfile.ZipFile(s, "w", zipfile.ZIP_DEFLATED) as zip:
            for root, dirs, files in os.walk(file_path):
                # add directory (needed for empty dirs)
                rel_path = os.path.relpath(root, relroot)
                if rel_path != ".":
                    zip.write(root, os.path.relpath(root, relroot))
                for file in files:
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename): # regular files only
                        arcname = os.path.join(os.path.relpath(root, relroot), file)
                        zip.write(filename, arcname)

        return zip
    
def copyrecursively(source_folder, destination_folder):
    for root, dirs, files in os.walk(source_folder):
        for item in files:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(destination_folder, src_path.replace(source_folder, ""))
            if os.path.exists(dst_path):
                if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                    shutil.copyfile(src_path, dst_path)
            else:
                shutil.copyfile(src_path, dst_path)
        for item in dirs:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(destination_folder, src_path.replace(source_folder, ""))
            if not os.path.exists(dst_path):
                os.mkdir(dst_path)

def copy(src, dest):
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dest, False, None)
        else:
            if dest.rfind('/') >= 0:
                local_dir_url = dest[:dest.rfind('/')]
                if not os.path.exists(local_dir_url):
                    os.mkdir(local_dir_url)
            shutil.copy2(src, dest)
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            print('Directory not copied. Error: %s' % e)
    
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

def create_style_name(layer):
    layer_styles = StyleLayer.objects.filter(layer=layer)
    index = len(layer_styles)
    style_name = layer.name + '_' + str(index)
    
    return style_name