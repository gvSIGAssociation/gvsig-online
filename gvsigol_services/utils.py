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
from gvsigol.settings import MEDIA_ROOT
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from models import LayerReadGroup, LayerWriteGroup
from gvsigol_auth.models import UserGroup
from gvsigol_services.models import Datastore, LayerResource
import geographic_servers
from gvsigol import settings
import psycopg2
import json
import os

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
def get_connection(host, port, database, user, password):    
    try:
        conn = psycopg2.connect("host=" + host +" port=" + port +" dbname=" + database +" user=" + user +" password="+ password);
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        print "Connect ... "
        
    except StandardError, e:
        print "Failed to connect!", e
        return []
    
    return conn;

def get_distinct_query(host, port, schema, database, user, password, layer, field):
    values = []
    conn = get_connection(host, port, database, user, password)
    cursor = conn.cursor()
    
    try:
        sql = 'SELECT DISTINCT("' + field + '") FROM ' + schema + '.' + layer + ' ORDER BY "' + field + '" ASC;'
        
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
