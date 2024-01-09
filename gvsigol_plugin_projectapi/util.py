# -*- coding: utf-8 -*-
'''
    gvSIG Online.
    Copyright (C) 2010-2019 SCOLAB.

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

@author: Nacho Brodin <nbrodin@scolab.es>
'''

import json

from django.contrib.auth.models import User
from django.db.models.query import QuerySet
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse
from django import apps
from django.utils.translation import ugettext as _
import gvsigol
from gvsigol_auth.auth_backend import get_roles
from gvsigol_core.models import Project, ProjectLayerGroup
from gvsigol_core.utils import get_absolute_url, get_user_projects, get_user_applications
from gvsigol import settings
from gvsigol_services.backend_postgis import Introspect
from gvsigol_services.models import Datastore, Layer, LayerGroup, Server
from gvsigol_services import utils
from gvsigol_services.utils import get_public_layers_query, get_layerread_by_user_query
from psycopg2 import sql as sqlbuilder
from psycopg2.extensions import quote_ident
import logging
#logging.basicConfig()
logger = logging.getLogger(__name__)

def count(con, schema, table, comparator='=', field=None, value=None):
    count = 0
    if field and value is not None:
        where = sqlbuilder.SQL(" WHERE {field} " + comparator + " %s").format(field=sqlbuilder.Identifier(field))
    else:
        where = sqlbuilder.SQL("")
    sql = "SELECT count(*) FROM {schema}.{table} {where}"
    query = sqlbuilder.SQL(sql).format(
        schema=sqlbuilder.Identifier(schema),
        table=sqlbuilder.Identifier(table),
        where=where)
    con.cursor.execute(query, [value])
    for r in con.cursor.fetchall():
        return r[0]

def get_layer_id(con, schema, layer):
    pk_list = con.get_pk_columns(layer, schema=schema)
    idfield = "ogc_fid="
    #Se considera que las capas tienen una sola clave primaria
    if (len(pk_list) > 0):
        idfield = pk_list[0]
    
    schema_table = quote_ident(schema, con.cursor) + "." + quote_ident(layer, con.cursor) 
    sql = "SELECT nextval(pg_get_serial_sequence({schema_table}, {idfield})) as new_id"
    query = sqlbuilder.SQL(sql).format(
        schema_table=sqlbuilder.Literal(schema_table),
        idfield=sqlbuilder.Literal(idfield)
        )
    con.cursor.execute(query)
    r = con.cursor.fetchall()
    id_ = r[0][0] 
    if(r[0][0] is None): # El campo no es autoincrementable
        sql = "SELECT MAX({idfield}) FROM {schema}.{table}"
        query = sqlbuilder.SQL(sql).format(
            idfield=sqlbuilder.Identifier(idfield),
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(layer)
            )
        con.cursor.execute(query)
        r = con.cursor.fetchall()
        id_ = r[0][0] + 1
    return id_


def get_layer_pk_name(con, schema, table_name):
    """
    Obtiene la columna que es clave primaria de una capa
    Se considera que las capas tienen una sola clave primaria. Por eso es get_layer_pk_name y NO get_pk_name
    """
    try:
        pks = con.get_pk_columns(table_name, schema=schema)
        if len(pks)>0:
            return pks[0]
    except Exception:
        logger.exception("Error getting pk")
    return "ogc_fid"


def update_feat_version(con, schema, table, featid):
    """
    Incrementa la version de una feature y fija la fecha a la actual
    """
    pk = get_layer_pk_name(con, schema, table)
    sql = "SELECT {versionfield} FROM {schema}.{table} WHERE {idfield} = %s"
    select_query = sqlbuilder.SQL(sql).format(
        versionfield = sqlbuilder.Identifier(settings.VERSION_FIELD),
        schema = sqlbuilder.Identifier(schema),
        table = sqlbuilder.Identifier(table),
        idfield = sqlbuilder.Identifier(pk)
        )
    con.cursor.execute(select_query, [featid])
    r = con.cursor.fetchall()
    if(r is not None and len(r) > 0):
        current_version = r[0][0]
        if current_version is None:
            version = 1
        else:
            version = current_version + 1
        sql = "UPDATE {schema}.{table} SET {versionfield} = %s, {datefield} = now() WHERE {idfield} = %s"
        query = sqlbuilder.SQL(sql).format(
            versionfield = sqlbuilder.Identifier(settings.VERSION_FIELD),
            datefield = sqlbuilder.Identifier(settings.DATE_FIELD),
            schema = sqlbuilder.Identifier(schema),
            table = sqlbuilder.Identifier(table),
            idfield = sqlbuilder.Identifier(pk)
            )
        con.cursor.execute(query, [version, featid])
        
        #Volvemos a consultar el valor que se ha escrito para poder devolverlo
        sql = "SELECT {versionfield}, {datefield} FROM {schema}.{table} WHERE {idfield} = %s"
        select_query = sqlbuilder.SQL(sql).format(
            versionfield = sqlbuilder.Identifier(settings.VERSION_FIELD),
            datefield = sqlbuilder.Identifier(settings.DATE_FIELD),
            schema = sqlbuilder.Identifier(schema),
            table = sqlbuilder.Identifier(table),
            idfield = sqlbuilder.Identifier(pk)
            )
        con.cursor.execute(select_query, [featid])
        r = con.cursor.fetchall()
        if(r is not None and len(r) > 0):
            return (r[0][0], r[0][1])
        


# def _get_properties_names(introspect, schema, tablename, exclude_cols=[]):
#     """
#     Obtiene la lista de propiedades de una tabla
#     """
#     fields = introspect.get_fields(tablename, schema=schema)
#     return [ f for f in fields if f not in exclude_cols]

def get_layerread_by_user_and_project(request, project_id):
    '''
    Devuelve todas las capas de un proyecto sobre las que el usuario tiene permisos
    de lectura. Esto incluye las capas sobre las que tiene permisos explícitos de
    lectura y las capas públicas.

    Parámetros
    ==========
    request: HttpRequest
        Objeto HttpRequest de Django con la petición en curso
    project_id: integer
        id del proyecto (pk en el modelo Project)
    '''
    layers_by_project_query = Q(layer_group__projectlayergroup__project__id=project_id)
    if request.user.is_superuser:
        return Layer.objects.filter(layers_by_project_query).select_related('datastore')
    roles = get_roles(request)
    return Layer.objects.filter( \
                layers_by_project_query & \
                (get_layerread_by_user_query(roles) | get_public_layers_query())).distinct().select_related('datastore')

def get_layerread_by_user_and_group(request, group_id):
    '''
    Devuelve todas las capas de un grupo sobre las que el usuario tiene permisos de lectura. Esto
    incluye las capas públicas y las capas sobre las que tiene permisos explícitos de lectura.

    Parámetros
    ==========
    request: HttpRequest
        Objeto HttpRequest de Django con la petición en curso
    group_id: integer
        id del grupo de capas (pk en el modelo LayerGroup)
    '''
    layers_by_group_query = Q(layer_group_id=group_id)
    if request.user.is_superuser:
        return Layer.objects.filter(layers_by_group_query).select_related('datastore')
    roles = get_roles(request)
    return Layer.objects.filter(layers_by_group_query &
                (get_layerread_by_user_query(roles) | get_public_layers_query())).distinct().select_related('datastore')


def get_layerread_by_group(group_id):
    '''
    Devuelve todas las capas de un grupo de capas

    Parámetros
    ==========
    group_id: integer
        id del grupo de capas (pk en el modelo LayerGroup)
    '''
    return Layer.objects.filter(
        layer_group_id=group_id).distinct().select_related('datastore')

def get_projects_ids_by_user(request, mobile=False):
    '''
    Obtiene los projectos en los que un usuario tiene permisos, es decir que aparece
    con el check activo en la pestaña "Grupo de usuarios" del proyecto.
    Además incluye los proyectos públicos.
    FIXME: No se usa el parámetro mobile

    Parámetros
    ==========
    request: HttpRequest
        Objeto HttpRequest de Django con la petición en curso
    '''
    return [p.id for p in get_user_projects(request)]

def get_applications_ids_by_user(request, mobile=False):
    '''
    Obtiene las aplicaciones en las que un usuario tiene permisos, es decir que aparece
    con el check activo en la pestaña "Grupo de usuarios" de la aplicación.
    Además incluye las aplicaciones públicas.
    FIXME: No se usa el parámetro mobile

    Parámetros
    ==========
    request: HttpRequest
        Objeto HttpRequest de Django con la petición en curso
    '''
    return [app.id for app in get_user_applications(request)]

def get_layergroups_by_user(request):
    '''
    Obtiene los grupos de capas que tienen capas para las que el usuario tiene permiso de lectura
    junto con los grupos de capas que tienen capas públicas.

    Parámetros
    ==========
    request: HttpRequest
        Objeto HttpRequest de Django con la petición en curso
    '''
    layergroup_ids = set([l.layer_group.id for l in utils.get_layerread_by_user(request)])
    return LayerGroup.objects.filter(id__in=layergroup_ids) | LayerGroup.objects.filter(created_by=request.user.username)

def get_layergroups_by_user_and_project(request, project_id):
    '''
    Devuelve los grupos de capas que tienen capas para las que el usuario tiene permiso de lectura
    junto con los grupos de capas que tienen capas públicas y que están dentro del proyecto indicado.
    '''
    layergroup_ids = set([l.layer_group.id for l in utils.get_layerread_by_user(request)])
    return LayerGroup.objects.filter( \
        projectlayergroup__project__id=project_id,
        id__in=layergroup_ids) | LayerGroup.objects.filter(created_by=request.user.username, projectlayergroup__project__id=project_id)

def get_layergroups_by_project(project_id):
    '''
    Devuelve los grupos de capas que tienen capas públicas y que están dentro del proyecto indicado.
    FIXME: realmente devuelve todos los grupos aunque no tengan capas públicas
    '''
    return LayerGroup.objects.filter( \
        projectlayergroup__project__id=project_id)

def get_geoserver_instances(qs_layer_groups):
    '''
    Obtiene las distintas instancias de geoserver a partir de los grupos de capas. 
    De esta forma el cliente web se autenticará contra cada una de estas instancias.
    '''
    gs_instances = []
    for lg in qs_layer_groups:
        gs = Server.objects.get(id=lg.server_id)
        gs_instances.append(gs.frontend_url)

    return gs_instances

def get_public_groups():
    '''
    Obtiene los grupos donde hay capas públicas
    '''
    public_groups_ids = list(dict.fromkeys([i.layer_group_id for i in get_public_layers()]))
    return LayerGroup.objects.filter(id__in=public_groups_ids)


def get_public_layers():
    '''
    Obtiene la lista de capas públicas
    '''
    return Layer.objects.filter(public=True)


def get_layer(layerid, lyrname, workspace):
    if(layerid):
        return Layer.objects.get(id=layerid)
    return Layer.objects.get(name = lyrname, datastore__workspace__name = workspace)


def get_pool_connection(layers):
    connections = {}
    if(isinstance(layers, Layer)):
        if(layers.datastore and layers.datastore.id not in connections):
            con, _, _ = utils.get_db_connect_from_layer(layers)
            connections[layers.datastore.id] = con
    else:
        for lyr in layers:
            if lyr.type.startswith("v_"):
                if(lyr.datastore and lyr.datastore.id not in connections):
                    con, _, _ = utils.get_db_connect_from_layer(lyr)
                    connections[lyr.datastore.id] = con
    return connections


def destroy_pool_connection(connections):
    for i in connections:
        try:
            connections[i].close()
        except Exception:
            pass



def _get_properties_names(con, schema, tablename, exclude_cols=[]):
    fields = con.get_fields(tablename, schema=schema)
    properties = [ f for f in fields if f not in exclude_cols]
    colnames = [ sqlbuilder.Identifier(c) for c in properties ]
    return sqlbuilder.SQL(", ").join(colnames)

def get_plugins(project):
    plugins = []
    try:
        tools = json.loads(project.tools)
        for tool in tools:
            if tool['checked']:
                plugins.append(tool['name'])
    except:
        pass

    return plugins

def get_order_in_project(project_id, layergroup_name):
    project = Project.objects.get(id=project_id)
    try:
        toc_order = json.loads(project.toc_order)
        for key in toc_order:
            if key == layergroup_name:
                return toc_order[key].get('order', 1000)
    except:
        pass
    return 1000

