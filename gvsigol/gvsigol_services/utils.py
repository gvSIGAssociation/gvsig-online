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
from models import LayerReadGroup, LayerWriteGroup
from gvsigol_auth.models import UserGroup
from gvsigol_services.models import Datastore
from gvsigol_services.backend_mapservice import backend as mapservice_backend
from gvsigol import settings
import psycopg2

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
                else:
                    group['read_checked'] = False
            
            for lwg in write_groups:
                if lwg.group_id == g.id:
                    group['write_checked'] = True
                else:
                    group['write_checked'] = False
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
def create_datastore(request, ds_name, ws):
    
    ds_type = 'v_PostGIS'
    description = 'BBDD ' + ds_name
    
    dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
    dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
    dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
    dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
    dbpassword = settings.GVSIGOL_USERS_CARTODB['dbpassword']
    connection_params = '{ "host": "' + dbhost + '", "port": "' + dbport + '", "database": "' + dbname + '", "schema": "' + ds_name + '", "user": "' + dbuser + '", "passwd": "' + dbpassword + '", "dbtype": "postgis" }'
    
    if create_schema(ds_name):
        if mapservice_backend.createDatastore(ws, ds_type, ds_name, description, connection_params, session=request.session):
            # save it on DB if successfully created
            datastore = Datastore(
                workspace = ws, 
                type = ds_type, 
                name = ds_name, 
                description = description, 
                connection_params = connection_params
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
        print "Connect ..."
        
    except StandardError, e:
        print "Failed to connect!", e
        return []
    
    return conn;

#TODO: llevar al paquete del core
def close_connection(cursor, conn):
    #Close connection and exit
    cursor.close();
    conn.close();