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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

import hashlib
import json
import os
from string import strip

from django.http.response import HttpResponse
import psycopg2

import geographic_servers
from gvsigol import settings
from gvsigol.settings import MEDIA_ROOT
from gvsigol_auth.models import UserGroup
from gvsigol_services.backend_postgis import Introspect
from gvsigol_services.models import Datastore, LayerResource, \
    LayerFieldEnumeration, EnumerationItem, Enumeration, Layer, LayerGroup
from models import LayerReadGroup, LayerWriteGroup


def get_all_user_groups_checked_by_layer(layer):
    groups_list = UserGroup.objects.all()
    read_groups = LayerReadGroup.objects.filter(layer=layer)
    write_groups = LayerWriteGroup.objects.filter(layer=layer)

    groups = []
    for g in groups_list:
        if g.name != 'admin' and g.name != 'public':
            group = {}
            for lrg in read_groups:
                if lrg.group_id == g.id:
                    group['read_checked'] = True

            for lwg in write_groups:
                if lwg.group_id == g.id:
                    group['write_checked'] = True

            group['id'] = g.id
            group['name'] = g.name
            group['description'] = g.description
            groups.append(group)

    return groups

def get_read_roles(layer):
    roles = []
    layer_read_groups = LayerReadGroup.objects.filter(layer_id=layer.id)
    for layer_read_group in layer_read_groups:
        group = UserGroup.objects.get(id=layer_read_group.group_id)
        roles.append(group.name)

    return roles

def get_write_roles(layer):
    roles = []
    layer_write_groups = LayerWriteGroup.objects.filter(layer_id=layer.id)
    for layer_write_group in layer_write_groups:
        group = UserGroup.objects.get(id=layer_write_group.group_id)
        roles.append(group.name)

    return roles

#TODO: llevar al paquete del core
def create_datastore(request, username, ds_name, ws):

    ds_type = 'v_PostGIS'
    description = 'BBDD ' + ds_name

    dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
    dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
    dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
    dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
    dbpassword = settings.GVSIGOL_USERS_CARTODB['dbpassword']
    connection_params = '{ "host": "' + dbhost + '", "port": "' + dbport + '", "database": "' + dbname + '", "schema": "' + ds_name + '", "user": "' + dbuser + '", "passwd": "' + dbpassword + '", "dbtype": "postgis" }'

    if create_schema(ds_name):
        gs = geographic_servers.get_instance().get_server_by_id(ws.server.id)
        if gs.createDatastore(ws, ds_type, ds_name, description, connection_params):
            # save it on DB if successfully created
            datastore = Datastore(
                workspace = ws,
                type = ds_type,
                name = ds_name,
                description = description,
                connection_params = connection_params,
                created_by=username
            )
            datastore.save()

            return datastore

#TODO: llevar al paquete del core
def create_schema(ds_name):
    dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
    dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
    dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
    dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
    dbpassword = settings.GVSIGOL_USERS_CARTODB['dbpassword']

    connection = get_connection(dbhost, dbport, dbname, dbuser, dbpassword)
    cursor = connection.cursor()

    try:
        create_schema = "CREATE SCHEMA IF NOT EXISTS " + ds_name + " AUTHORIZATION " + dbuser + ";"
        cursor.execute(create_schema)

    except StandardError, e:
        print "SQL Error", e
        if e.pgcode == '42710':
            return True
        else:
            return False

    close_connection(cursor, connection)
    return True

#TODO: llevar al paquete del core
def create_schema_for_datastore(connection_params):
    host = connection_params.get('host')
    port = connection_params.get('port')
    database = connection_params.get('database')
    user = connection_params.get('user')
    passwd = connection_params.get('passwd')
    schema = connection_params.get('schema')

    connection = get_connection(host, port, database, user, passwd)
    cursor = connection.cursor()

    try:
        create_schema = "CREATE SCHEMA IF NOT EXISTS " + schema + " AUTHORIZATION " + user + ";"
        cursor.execute(create_schema)

    except StandardError, e:
        print "SQL Error", e
        if e.pgcode == '42710':
            return True
        else:
            return False

    close_connection(cursor, connection)
    return True

#TODO: llevar al paquete del core
def delete_schema_for_datastore(connection_params):
    host = connection_params.get('host')
    port = connection_params.get('port')
    database = connection_params.get('database')
    user = connection_params.get('user')
    passwd = connection_params.get('passwd')
    schema = connection_params.get('schema')

    connection = get_connection(host, port, database, user, passwd)
    cursor = connection.cursor()

    try:
        delete_schema = "DROP SCHEMA IF EXISTS " + schema +  ";"
        cursor.execute(delete_schema)

    except StandardError, e:
        print "SQL Error", e
        if e.pgcode == '42710':
            return True
        else:
            return False

    close_connection(cursor, connection)
    return True

#TODO: llevar al paquete del core
def get_connection(host, port, database, user, password):
    try:
        conn = psycopg2.connect("host=" + host +" port=" + port +" dbname=" + database +" user=" + user +" password="+ password);
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        print "Connect ... "

    except StandardError, e:
        print "Failed to connect!", e
        return []

    return conn;

def get_distinct_query(host, port, schema, database, user, password, layer, field, where=None):
    values = []
    conn = get_connection(host, port, database, user, password)
    cursor = conn.cursor()

    where_query = ''
    if where:
        where_query = " " + str(where) + " "

    try:
        sql = 'SELECT DISTINCT("' + field + '") FROM ' + schema + '.' + layer + where_query + ' ORDER BY "' + field + '" ASC;'

        cursor.execute(sql);
        rows = cursor.fetchall()
        for row in rows:
            if row[0] is not None:
                val = row[0]
                if isinstance(val, basestring):
                    values.append(val)
                else:
                    val = str(val)
                    values.append(val)

    except StandardError, e:
        print "Query error!", e
        return []

    close_connection(cursor, conn)
    return values

def get_minmax_query(host, port, schema, database, user, password, layer, field):
    conn = get_connection(host, port, database, user, password)
    cursor = conn.cursor()

    try:
        sql = 'SELECT MIN("' + field + '") AS MinValue, MAX("' + field + '") AS MaxValue FROM ' + schema + '.' + layer + ' WHERE "' + field + '" IS NOT NULL;'

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

#TODO: llevar al paquete del core
def close_connection(cursor, conn):
    #Close connection and exit
    cursor.close();
    conn.close();

def get_fields(resource):
    fields = None
    if resource != None:
        fields = resource.get('featureType').get('attributes').get('attribute')

    return fields

def get_alphanumeric_fields(fields):
    alphanumeric_fields = []
    for field in fields:
        if not 'jts.geom' in field.get('binding'):
            alphanumeric_fields.append(field)

    return alphanumeric_fields

def get_resources_dir(resource_type):

    if resource_type == LayerResource.EXTERNAL_IMAGE:
        the_path = os.path.join(MEDIA_ROOT, "resources/image")
    elif  resource_type == LayerResource.EXTERNAL_PDF:
        the_path = os.path.join(MEDIA_ROOT, "resources/pdf")
    elif  resource_type == LayerResource.EXTERNAL_DOC:
        the_path = os.path.join(MEDIA_ROOT, "resources/docs")
    elif  resource_type == LayerResource.EXTERNAL_VIDEO:
        the_path = os.path.join(MEDIA_ROOT, "resources/videos")
    else:
        the_path = os.path.join(MEDIA_ROOT, "resources/files")
    if not os.path.exists(the_path):
        os.makedirs(the_path, 0700)
    return the_path

def get_resource_type(lr):
    url = None
    type = None
    if lr.type == LayerResource.EXTERNAL_IMAGE:
        type = 'image'
        url = os.path.join(settings.MEDIA_URL, lr.path)
    elif lr.type == LayerResource.EXTERNAL_PDF:
        type = 'pdf'
        url = os.path.join(settings.MEDIA_URL, lr.path)
    elif lr.type == LayerResource.EXTERNAL_DOC:
        type = 'doc'
        url = os.path.join(settings.MEDIA_URL, lr.path)
    elif lr.type == LayerResource.EXTERNAL_FILE:
        type = 'file'
        url = os.path.join(settings.MEDIA_URL, lr.path)
    elif lr.type == LayerResource.EXTERNAL_VIDEO:
        type = 'video'
        url = os.path.join(settings.MEDIA_URL, lr.path)
    elif lr.type == LayerResource.EXTERNAL_ALFRESCO_DIR:
        type = 'alfresco_dir'
        url = lr.path

    return [type, url]

def is_field_enumerated(column_name, table_name, datastore):    
    """
    Returns true if the field is enumerated and false if not. The second parameter is true if the enumeration is multiple
    """
    enums = LayerFieldEnumeration.objects.filter(layername=table_name, schema=datastore, field=column_name)
    if len(enums) > 0:
        return True, enums[0].multiple
    return False, False

def get_enum_item_list(column_name, lyr_name, workspace_name):    
    """
    Gets the list of items of a enumerated field
    """
    lyr_obj = Layer.objects.get(name=lyr_name, datastore__workspace__name=workspace_name)
    if(lyr_obj is not None):
        enums = LayerFieldEnumeration.objects.filter(layername=lyr_name, schema=lyr_obj.datastore.name, field=column_name)
        if len(enums) > 0:
            return EnumerationItem.objects.filter(enumeration_id=enums[0].enumeration_id)
        
def get_enum_entry(column_name, lyr_name, workspace_name):    
    """
    Gets the list of items of a enumerated field
    """
    lyr_obj = Layer.objects.get(name=lyr_name, datastore__workspace__name=workspace_name)
    if(lyr_obj is not None):
        enums = LayerFieldEnumeration.objects.filter(layername=lyr_name, schema=lyr_obj.datastore.name, field=column_name)
        if len(enums) > 0:
            return Enumeration.objects.get(id=enums[0].enumeration_id)
            
def get_layer_img(layerid, filename):
    """
    Devuelve la ruta y la URL de un icono asociado a una capa. 
    
    Una imagen de una capa se guarda en media/images y su nombre es un md5 de layer + id de la capa. 
    Cuando se sube el fichero este se guarda con la extensión del original ('png', 'jpg', 'jpeg', 'gif' o 'tif') 
    pero cuando se consulta no se conoce la extensión con la que se guardó por lo que el parámetro filename será null. 
    
    Si quiero obtener la imagen de una capa se llamará a get_layer_img(idcapa, None)
    """
    path_ = None
    url = None
    m = hashlib.md5()
    m.update("layer" + str(layerid))
    if(filename is not None):
        suffix = filename.split('.')
        ext = ''
        if(suffix is not None and len(suffix) > 0):
            ext = suffix[-1]
        filename = m.hexdigest() + "." + ext
        path_ = settings.MEDIA_ROOT + "images/" + filename
        url = settings.MEDIA_URL + "images/" + filename
    else:
        suffix_list = ['png', 'jpg', 'jpeg', 'gif', 'tif', 'svg']
        filename = m.hexdigest()
        for ext in suffix_list:
            test = filename + "." + ext
            path_ = settings.MEDIA_ROOT + "images/" + test
            if os.path.exists(path_):
                url = settings.MEDIA_URL + "images/" + test
                break
            else:
                path_ = None
            
    
    return path_, url

def get_db_connect_from_layer(layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    params = json.loads(datastore.connection_params)
    host = params['host']
    port = params['port']
    dbname = params['database']
    user = params['user']
    passwd = params['passwd']
    i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
    return i, layer.name, params['schema']
     
def get_exception(code, msg):
    response = HttpResponse(msg)
    response.status_code = code
    return response    