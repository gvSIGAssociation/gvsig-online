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
from django.http import response
from gvsigol_services.models import CLONE_PERMISSION_CLONE, CLONE_PERMISSION_SKIP
from django.contrib.auth.models import AnonymousUser
import hashlib
import json
import os
from django.http.response import HttpResponse
from django.db.models.query import QuerySet
from django.db.models import Q
import psycopg2
from . import geographic_servers
from gvsigol import settings
from gvsigol.settings import MEDIA_ROOT
from gvsigol_auth.models import UserGroup, User
from gvsigol_auth.auth_backend import get_roles
from gvsigol_services.backend_postgis import Introspect
from gvsigol_services.models import Datastore, LayerResource, \
    LayerFieldEnumeration, EnumerationItem, Enumeration, Layer, LayerGroup, Workspace, Server
from .models import LayerReadRole, LayerWriteRole
from gvsigol_core import utils as core_utils
import ast
from django.utils.crypto import get_random_string
from psycopg2 import sql as sqlbuilder
import logging
logger = logging.getLogger("gvsigol")
from gvsigol_auth import auth_backend
from gvsigol_auth import services as auth_services
from gvsigol_auth.utils import ascii_norm_username
import re

def get_all_user_roles_checked_by_layer(layer, creator_user_role=None):
    role_list = auth_backend.get_all_roles_details()
    if layer:
        read_roles = LayerReadRole.objects.filter(layer=layer).values_list('role', flat=True)
        write_roles = LayerWriteRole.objects.filter(layer=layer).values_list('role', flat=True)
    else:
        read_roles = []
        write_roles = []
    return get_checked_roles_from_user_input(read_roles, write_roles, creator_user_role=creator_user_role)
 
def get_read_roles(layer):
    return list(LayerReadRole.objects.filter(layer_id=layer.id).values_list('role', flat=True))

def get_write_roles(layer):
    return list(LayerWriteRole.objects.filter(layer_id=layer.id).values_list('role', flat=True))

def can_write_layer(request, layer):
    """
    Checks whether the user has permissions to write the provided layer.
    It accepts a layer instance or a layer id.
    """
    try:
        if not isinstance(layer, Layer):
            layer = Layer.objects.get(id=layer)
        
        if request.user.is_superuser:
            return True
        if isinstance(request.user, AnonymousUser):
            return False
        roles = get_roles(request)
        return LayerWriteRole.objects.filter(layer=layer, role__in=roles).exists()
    except Exception as e:
        print(e)
    return False

def can_read_layer(request, layer):
    """
    Checks whether the user has permissions to manage the provided layer.
    It accepts a layer instance or a layer id.
    """
    try:
        if not isinstance(layer, Layer):
            layer = Layer.objects.get(id=layer)

        if layer.public or request.user.is_superuser:
            return True
        if isinstance(request.user, AnonymousUser):
            return False
        roles = get_roles(request)
        return LayerReadRole.objects.filter(layer=layer, role__in=roles).exists()
    except Exception as e:
        print(e)
    return False

def can_manage_layer(user, layer):
    """
    Checks whether the user has permissions to manage the provided layer.
    It accepts a layer instance or a layer id.
    """
    try:
        if isinstance(user, str):
            user = User.objects.get(username=user)
        if not isinstance(layer, Layer):
            layer = Layer.objects.get(id=layer)
        if user.is_superuser:
            return True
        if layer.created_by == user.username:
            return True
    except Exception as e:
        print(e)
    return False

def can_manage_datastore(user, datastore):
    """
    Checks whether the user has permissions to manage the provided datastore.
    It accepts a datastore instance or a datastore id.
    """
    try:
        if isinstance(user, str):
            user = User.objects.get(username=user)
        if not isinstance(datastore, Datastore):
            datastore = Datastore.objects.get(id=datastore)
        if user.is_superuser:
            return True
        if datastore.created_by == user.username:
            return True
    except Exception as e:
        print(e)
    return False

def can_manage_layergroup(user, layergroup):
    """
    Checks whether the user has permissions to manage the provided layergroup.
    It accepts a layergroup instance or a layergroup id.
    """
    try:
        if isinstance(user, str):
            user = User.objects.get(username=user)
        if not isinstance(layergroup, LayerGroup):
            layergroup = LayerGroup.objects.get(id=layergroup)
        if user.is_superuser:
            return True
        if layergroup.created_by == user.username:
            return True
    except Exception as e:
        print(e)
    return False

def add_datastore(workspace, type, name, description, connection_params, username):
    gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    # first create the datastore on the backend
    if gs.createDatastore(workspace,
                          type,
                          name,
                          description,
                          connection_params):
        
        # save it on DB if successfully created
        datastore = Datastore(
            workspace=workspace,
            type=type,
            name=name,
            description=description,
            connection_params=connection_params,
            created_by=username
        )
        datastore.save()
        return datastore

def create_workspace(server_id, ws_name, uri, values, username):
    # first create the ws on the backend
    gs = geographic_servers.get_instance().get_server_by_id(server_id)
    if gs.createWorkspace(ws_name, uri):
        # save it on DB if successfully created
        newWs = Workspace(**values)
        newWs.created_by = username
        newWs.save()
        gs.reload_nodes()
        return newWs

def create_datastore(username, ds_name, ws):
    ds_type = 'v_PostGIS'
    description = 'BBDD ' + ds_name

    dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
    dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
    dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
    dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
    dbpassword = settings.GVSIGOL_USERS_CARTODB['dbpassword']
    connection_params = '{ "host": "' + dbhost + '", "port": "' + dbport + '", "database": "' + dbname + '", "schema": "' + ds_name + '", "user": "' + dbuser + '", "passwd": "' + dbpassword + '", "dbtype": "postgis" }'

    if create_schema(ds_name):
        return add_datastore(ws, ds_type, ds_name, description, connection_params, username)

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

    except Exception as e:
        print("SQL Error", e)
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

    except Exception as e:
        print("SQL Error", e)
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

    except Exception as e:
        print("SQL Error", e)
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
        print("Connect ... ")

    except Exception as e:
        print("Failed to connect!", e)
        return []

    return conn

def get_minmax_query(host, port, schema, database, user, password, layer, field):
    conn = get_connection(host, port, database, user, password)
    cursor = conn.cursor()

    try:
        sql = 'SELECT MIN("' + field + '") AS MinValue, MAX("' + field + '") AS MaxValue FROM ' + schema + '.' + layer + ' WHERE "' + field + '" IS NOT NULL;'

        cursor.execute(sql);
        rows = cursor.fetchall()

    except Exception as e:
        print("Fallo en el getMIN y getMAX", e)
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
    fields = []
    if resource != None:
        fields = resource.get('featureType', {}).get('attributes', {}).get('attribute', [])

    return fields

def get_alphanumeric_fields(fields):
    alphanumeric_fields = []
    for field in fields:
        if not 'jts.geom' in field.get('binding'):
            alphanumeric_fields.append(field)

    return alphanumeric_fields

def get_resources_dir(layer_id, resource_type):
    resource_dir='resources'
    if resource_type == LayerResource.EXTERNAL_IMAGE:
        the_path = os.path.join(MEDIA_ROOT, resource_dir , str(layer_id), "image")
    elif  resource_type == LayerResource.EXTERNAL_PDF:
        the_path = os.path.join(MEDIA_ROOT, resource_dir , str(layer_id), "pdf")
    elif  resource_type == LayerResource.EXTERNAL_DOC:
        the_path = os.path.join(MEDIA_ROOT, resource_dir , str(layer_id), "docs")
    elif  resource_type == LayerResource.EXTERNAL_VIDEO:
        the_path = os.path.join(MEDIA_ROOT, resource_dir , str(layer_id), "videos")
    else:
        the_path = os.path.join(MEDIA_ROOT, resource_dir , str(layer_id), "files")
    if not os.path.exists(the_path):
        os.makedirs(the_path)
        # makedirs permissions are umasked, so we need to explicitly set permissions afterwards
        for root, dirs, _ in os.walk(os.path.join(MEDIA_ROOT, resource_dir , str(layer_id)), followlinks=True):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o0750)
    return the_path

def get_historic_resources_dir(path, layer_id):
    historic_base_path = os.path.join(MEDIA_ROOT, 'historic_resources')
    if not os.path.exists(historic_base_path):
        os.makedirs(historic_base_path)
        os.chmod(historic_base_path, 0o0750)
    
    if not os.path.isabs(path):
        path = os.path.join(MEDIA_ROOT, path)
    rel_path = os.path.relpath(os.path.dirname(path), os.path.join(MEDIA_ROOT, 'resources'))
    historic_path = os.path.join(historic_base_path, rel_path)
    if not os.path.exists(historic_path):
        os.makedirs(historic_path)
        
        # makedirs permissions are umasked, so we need to explicitly set permissions afterwards
        for root, dirs, _ in os.walk(os.path.join(MEDIA_ROOT, 'historic_resources' , str(layer_id)), followlinks=True):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o0750)
    return historic_path

def get_resource_type(content_type):
    if 'image/' in content_type:
        return LayerResource.EXTERNAL_IMAGE
    elif content_type == 'application/pdf':
        return LayerResource.EXTERNAL_PDF
    elif content_type in [ #.doc, .docx, .odt,
                          'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/vnd.oasis.opendocument.text',
                          # .xls, .xlsx, .ods
                          'application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'application/vnd.oasis.opendocument.spreadsheet',
                          # .ppt, .pptx, .odp
                          'application/vnd.ms-powerpoint',
                          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                          'application/vnd.oasis.opendocument.presentation'
                          ]:
        return LayerResource.EXTERNAL_DOC
    elif 'video/' in content_type:
        return LayerResource.EXTERNAL_VIDEO
    else:
        return LayerResource.EXTERNAL_FILE

def get_resource_type_label(resource_type):
    if resource_type == LayerResource.EXTERNAL_IMAGE:
        return 'image'
    elif resource_type == LayerResource.EXTERNAL_PDF:
        return 'pdf'
    elif resource_type == LayerResource.EXTERNAL_DOC:
        return 'doc'
    elif resource_type == LayerResource.EXTERNAL_VIDEO:
        return 'video'
    elif resource_type == LayerResource.EXTERNAL_ALFRESCO_DIR:
        return 'alfresco_dir'
    else:
        return 'file'

def is_field_enumerated(layer, column_name):
    """
    Returns true if the field is enumerated and false if not. The second parameter is true if the enumeration is multiple
    """
    enums = LayerFieldEnumeration.objects.filter(layer=layer, field=column_name)
    if len(enums) > 0:
        return True, enums[0].multiple
    return False, False

def get_enum_item_list(layer, column_name, enum=None):
    """
    Gets the list of items of a enumerated field
    """
    try:
        if not enum:
            enum = LayerFieldEnumeration.objects.get(layer=layer, field=column_name).enumeration
        return enum.enumerationitem_set.all().order_by('order')
    except:
        pass
    return []
        
def get_enum_entry(layer, column_name):
    """
    Gets the enumeration object associated to the provided column, or None if the field is not enumerated
    """
    try:
        return LayerFieldEnumeration.objects.get(layer=layer, field=column_name).enumeration
    except:
        pass
    
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
    m.update(("layer" + str(layerid)).encode("utf-8"))
    if filename is not None:
        suffix = filename.split('.')
        ext = ''
        if(suffix is not None and len(suffix) > 0):
            ext = suffix[-1]
        filename = m.hexdigest() + "." + ext
        path_ = settings.MEDIA_ROOT + "images/" + filename
        url = settings.MEDIA_URL + "images/" + filename
        url = url.replace(settings.BASE_URL, '')
    else:
        suffix_list = ['png', 'jpg', 'jpeg', 'gif', 'tif', 'svg']
        filename = m.hexdigest()
        for ext in suffix_list:
            test = filename + "." + ext
            path_ = settings.MEDIA_ROOT + "images/" + test
            if os.path.exists(path_):
                url = settings.MEDIA_URL + "images/" + test
                url = url.replace(settings.BASE_URL, '')
                break
            else:
                path_ = None
            
    
    return path_, url

def get_db_connect_from_datastore(datastore):
    if not isinstance(datastore, Datastore):
        datastore = Datastore.objects.get(id=int(datastore))
    return datastore.get_db_connection()

def get_db_connect_from_layer(layer):
    if not isinstance(layer, Layer):
        layer = Layer.objects.select_related('datastore').get(id=int(layer))
    return layer.get_db_connection()
     
def get_exception(code, msg):
    response = HttpResponse(msg)
    response.status_code = code
    return response

def check_schema_exists(schema):
    dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
    dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
    dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
    dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
    dbpassword = settings.GVSIGOL_USERS_CARTODB['dbpassword']
    i = Introspect(database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpassword)
    exists = i.schema_exists(schema)
    i.close()
    return exists


def set_layer_extent(layer, ds_type, layer_info, server):
    try:
        if ds_type == 'imagemosaic':
            ds_type = 'coverage'
        layer.native_srs = layer_info[ds_type]['srs']
        layer.native_extent = str(layer_info[ds_type]['nativeBoundingBox']['minx']) + ',' + str(layer_info[ds_type]['nativeBoundingBox']['miny']) + ',' + str(layer_info[ds_type]['nativeBoundingBox']['maxx']) + ',' + str(layer_info[ds_type]['nativeBoundingBox']['maxy'])
        layer.latlong_extent = str(layer_info[ds_type]['latLonBoundingBox']['minx']) + ',' + str(layer_info[ds_type]['latLonBoundingBox']['miny']) + ',' + str(layer_info[ds_type]['latLonBoundingBox']['maxx']) + ',' + str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
        
    except Exception as e:
        layer.native_srs = 'EPSG:4326'
        layer.native_extent = '-180,-90,180,90'
        layer.latlong_extent = '-180,-90,180,90' 
        

def set_time_enabled(server, layer):
        time_resolution = 0
        if (layer.time_resolution_year != None and layer.time_resolution_year > 0) or (layer.time_resolution_month != None and layer.time_resolution_month > 0) or (layer.time_resolution_week != None and layer.time_resolution_week > 0) or (layer.time_resolution_day != None and layer.time_resolution_day > 0):
            if (layer.time_resolution_year != None and layer.time_resolution_year > 0):
                time_resolution = time_resolution + (int(layer.time_resolution_year) * 3600 * 24 * 365)
            if (layer.time_resolution_month != None and layer.time_resolution_month > 0):
                time_resolution = time_resolution + (int(layer.time_resolution_month) * 3600 * 24 * 31)
            if (layer.time_resolution_week != None and layer.time_resolution_week > 0):
                time_resolution = time_resolution + (int(layer.time_resolution_week) * 3600 * 24 * 7)
            if (layer.time_resolution_day != None and layer.time_resolution_day > 0):
                time_resolution = time_resolution + (int(layer.time_resolution_day) * 3600 * 24 * 1)
        if (layer.time_resolution_hour != None and layer.time_resolution_hour > 0) or (layer.time_resolution_minute != None and layer.time_resolution_minute > 0) or (layer.time_resolution_second != None and layer.time_resolution_second > 0):
            if (layer.time_resolution_hour != None and layer.time_resolution_hour > 0):
                time_resolution = time_resolution + (int(layer.time_resolution_hour) * 3600)
            if (layer.time_resolution_minute != None and layer.time_resolution_minute > 0):
                time_resolution = time_resolution + (int(layer.time_resolution_minute) * 60)
            if (layer.time_resolution_second != None and layer.time_resolution_second > 0):
                time_resolution = time_resolution + (int(layer.time_resolution_second))
        server.setTimeEnabled(layer.datastore.workspace.name, layer.datastore.name, layer.datastore.type, layer.name, layer.time_enabled, layer.time_enabled_field, layer.time_enabled_endfield, layer.time_presentation, time_resolution, layer.time_default_value_mode, layer.time_default_value)


def clone_layer(target_datastore, layer, layer_group, copy_data=True, permissions=CLONE_PERMISSION_CLONE):
    if layer.type == 'v_PostGIS': # operation not defined for the rest of types
        # create the table
        dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
        dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
        dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
        dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
        dbpassword = settings.GVSIGOL_USERS_CARTODB['dbpassword']
        i = Introspect(database=dbname, host=dbhost, port=dbport, user=dbuser, password=dbpassword)
        table_name = layer.source_name if layer.source_name else layer.name
        new_table_name = i.clone_table(layer.datastore.name, table_name, target_datastore.name, table_name, copy_data=copy_data)
        i.close()

        from gvsigol_services import views
        server = geographic_servers.get_instance().get_server_by_id(target_datastore.workspace.server.id)

        layerConf = ast.literal_eval(layer.conf) if layer.conf else {}
        extraParams = {
            "max_features": layerConf.get('featuretype', {}).get('', 0)
        }
        # add layer to Geoserver
        views.do_add_layer(server, target_datastore, new_table_name, layer.title, layer.queryable, extraParams)
        
        new_name = new_table_name
        if Layer.objects.filter(name=new_name, datastore=target_datastore).exists():
            base_name = target_datastore.workspace.name + "_" + layer.name
            new_name = base_name
            i = 1
            salt = ''
            while Layer.objects.filter(name=layer.name, datastore=target_datastore).exists():
                new_name = base_name + '_' + str(i) + salt
                i = i + 1
                if (i%1000) == 0:
                    salt = '_' + get_random_string(3)
        
        # clone layer
        old_id = layer.pk
        layer.pk = None
        layer.name = new_name
        layer.datastore = target_datastore
        if layer_group is not None:
            layer.layer_group = layer_group
        layer.save()

        new_layer_instance = Layer.objects.get(id=layer.pk)
        old_instance = Layer.objects.get(id=old_id)
        
        if permissions != CLONE_PERMISSION_SKIP:
            admin_role = auth_backend.get_admin_role()
            read_roles = [ admin_role ]
            write_roles = [ admin_role ]

            for layer_read_role in LayerReadRole.objects.filter(layer=old_instance):
                layer_read_role.pk = None
                layer_read_role.layer = new_layer_instance
                layer_read_role.save()
                read_roles.append(layer_read_role.role)
            
            for layer_write_role in LayerWriteRole.objects.filter(layer=old_instance):
                layer_write_role.pk = None
                layer_write_role.layer = new_layer_instance
                layer_write_role.save()
                write_roles.append(layer_write_role.role)
            server.setLayerDataRules(layer, read_roles, write_roles)
        
        set_time_enabled(server, new_layer_instance)
        
        for enum in LayerFieldEnumeration.objects.filter(layer=old_instance):
            enum.pk = None
            enum.layer = new_layer_instance
            enum.save()
        
        from gvsigol_symbology.services import clone_layer_styles
        clone_layer_styles(server, old_instance, new_layer_instance)
        
        for lyr_res in LayerResource.objects.filter(layer=old_instance):
            lyr_res.pk = None
            lyr_res.layer = new_layer_instance
            lyr_res.save()
        """
        TODO:
        - models from plugins (for instance metadata, charts, etc)
        """
        server.updateThumbnail(new_layer_instance, 'create')
    
        core_utils.toc_add_layer(new_layer_instance)
        server.createOrUpdateGeoserverLayerGroup(new_layer_instance.layer_group)
        return new_layer_instance
    return layer

def get_feat_version(introspect_con, schema, table, featid):
    try:
        pks = introspect_con.get_pk_columns(table, schema=schema)
        if(pks and len(pks) == 1):
            sqlst = "SELECT {version} FROM {schema}.{table} WHERE {pkfield} = %s"
            query = sqlbuilder.SQL(sqlst).format(
                version=sqlbuilder.Identifier(settings.VERSION_FIELD),
                schema=sqlbuilder.Identifier(schema),
                table=sqlbuilder.Identifier(table),
                pkfield=sqlbuilder.Identifier(pks[0]))
            introspect_con.cursor.execute(query, [featid])
            for r in introspect_con.cursor.fetchall():
                return r[0]
    except Exception:
        return None

def check_feature_version(layer, feature_id, feat_version):
    """
    Returns True if the provided version matches the current feature version, False if
    they don't match and None if the version could not be checked
    """
    i, table, schema = get_db_connect_from_layer(layer)
    with i as con: # conn will autoclose
        version = get_feat_version(i, schema, table, feature_id)
        if version is not None:
            if feat_version == version:
                return True
            return False


def update_feat_version(layer, featid):
    """
    Increments the version of a feature and sets the current date.
    Returns a tuple containing the new version and date,
    or None if the version is not
    updated (because the feature is not found, has no version field,
    
    """
    try:
        i, table, schema = get_db_connect_from_layer(layer)
        with i as introspect_conn:
            pks = introspect_conn.get_pk_columns(table, schema=schema)
            if len(pks) != 1:
                return None, None
            pk = pks[0]
            sql = """UPDATE {schema}.{table} SET {versionfield} = (COALESCE({versionfield}, 0)+1),
                     {datefield} = now() WHERE {idfield} = %s
                     RETURNING {versionfield}, {datefield}"""
            query = sqlbuilder.SQL(sql).format(
                versionfield = sqlbuilder.Identifier(settings.VERSION_FIELD),
                datefield = sqlbuilder.Identifier(settings.DATE_FIELD),
                schema = sqlbuilder.Identifier(schema),
                table = sqlbuilder.Identifier(table),
                idfield = sqlbuilder.Identifier(pk)
                )
            introspect_conn.cursor.execute(query, [featid])
            for r in introspect_conn.cursor.fetchall():
                return r[0], r[1]
    except:
        logger.exception("Error updating feature version")
    return None, None

def set_layer_permissions(layer, is_public, assigned_read_roles, assigned_write_roles):
    layer.public = is_public
    layer.save()
    admin_role = auth_backend.get_admin_role()
    assigned_read_roles.append(admin_role)
    if layer.type.startswith('c_'):
        assigned_write_roles = []
    else:
        assigned_write_roles.append(admin_role)

    read_roles = []
    write_roles = []

    # clean existing groups and assign them again if necessary
    LayerReadRole.objects.filter(layer=layer).delete()
    all_roles = auth_backend.get_all_roles()
    for role in assigned_read_roles:
        try:
            if role in all_roles:
                lyr_read_role = LayerReadRole()
                lyr_read_role.layer = layer
                lyr_read_role.role = role
                lyr_read_role.save()
                read_roles.append(role)
        except:
            pass

    LayerWriteRole.objects.filter(layer=layer).delete()
    for role in assigned_write_roles:
        try:
            if role in all_roles:
                layer_write_role = LayerWriteRole()
                layer_write_role.layer = layer
                layer_write_role.role = role
                layer_write_role.save()
                write_roles.append(role)
        except:
            pass
            
    gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
    gs.setLayerDataRules(layer, read_roles, write_roles)

def get_checked_roles_from_user_input(layer_read_roles, layer_write_roles, creator_user_role=None):
    role_list = auth_backend.get_all_roles_details()
    roles = []
    admin_roles = [ auth_backend.get_admin_role()]
    for role in role_list:
        # FIXME OIDC CMI: ROLE_ prefix?
        if role['name'] not in admin_roles:
            for layer_read_role in layer_read_roles:
                if layer_read_role == role['name']:
                    role['read_checked'] = True

            for layer_write_role in layer_write_roles:
                if layer_write_role == role['name']:
                    role['write_checked'] = True
            if creator_user_role is not None and role['name'] == creator_user_role:
                role['read_checked'] = True
            roles.append(role)
    return roles

def get_public_layers_query():
    '''
    Devuelve un objecto Q con la query para obtener las capas públicas.
    '''
    return Q(public=True)

def get_layerread_by_user_query(user_roles):
    '''
    Devuelve un objecto Q con la query para obtener las capas sobre las que
    el usuario tiene permisos explícitos de lectura.

    Parámetros
    ==========
    user_roles: List[str]
        Lista de roles del usuario
    '''
    return Q(layerreadrole__role__in=user_roles)


def get_layerread_by_user(request):
    '''
    Obtiene las capas en las que el usuario tiene permiso de lectura.
    Estas son todas las públicas más todas las privadas sobre las que tiene permisos
    explícitos de lectura.

    Parámetros
    ==========
    request: HttpRequest
        Objeto HttpRequest de Django con la petición en curso
    '''    
    if request.user.is_superuser:
        return Layer.objects.all()
    roles = get_roles(request)
    return Layer.objects.filter(get_layerread_by_user_query(roles) \
             | get_public_layers_query()).distinct()

def set_default_permissions(file_path):
    """
    Sets the default permissions to the provided file. We set 0o640
    by default and substract the system umask to get the most
    restrictive default.
    """
    umask = os.umask(0o666) # set a random mask to retrive the system mask
    os.umask(umask) # restore system mask
    os.chmod(file_path, 0o640 & ~umask)

def create_user_workspace(username, role):
    """
    Creates the user workspace and datastore if they don't exist
    """
    gs = geographic_servers.get_instance().get_default_server()
    server_object = Server.objects.get(id=int(gs.id))

    auth_services.get_services().add_data_directory(role)
    url = server_object.frontend_url + '/'
    ascii_username = ascii_norm_username(username)
    ws_name = 'ws_' + ascii_norm_username
    if gs.createWorkspace(ws_name, url + ws_name):          
        # save it on DB if successfully created
        newWs = Workspace(
            server = server_object,
            name = ws_name,
            description = '',
            uri = url + ws_name,
            wms_endpoint = url + ws_name + '/wms',
            wfs_endpoint = url + ws_name + '/wfs',
            wcs_endpoint = url + ws_name + '/wcs',
            wmts_endpoint = url + 'gwc/service/wmts',
            cache_endpoint = url + 'gwc/service/wms',
            created_by = username,
            is_public = False
        )
        newWs.save()
        
        ds_name = 'ds_' + ascii_username
        create_datastore(username, ds_name, newWs)
        gs.reload_nodes()