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

from datetime import datetime
from gvsigol_plugin_baseapi.validation import HttpException
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
from gvsigol_core.utils import get_absolute_url, get_user_projects
from gvsigol import settings
from gvsigol_plugin_featureapi.models import FeatureVersions
from gvsigol_services.backend_postgis import Introspect
from gvsigol_services.models import Datastore, Layer, LayerGroup, Server
from gvsigol_services import utils
from gvsigol_services.utils import get_public_layers_query, get_layerread_by_user_query
from psycopg2 import sql as sqlbuilder
from psycopg2.extensions import quote_ident
from rest_framework.exceptions import ParseError, UnsupportedMediaType
import logging
logging.basicConfig()
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

def get_default_pk_name(table_info, default='ogc_fid'):
    """
    Obtiene la columna que es clave primaria de una capa. Si una tabla
    no tiene clave primaria pero existe una columna con el nombre
    'ogc_fid' (o el valor pasado en el parámetro default),
    se devuelve el valor de default.
    Si no, se lanza una excepción.
    Limitación: Se considera que las capas tienen una clave primaria no compuesta,
    formada por un único campo.
    """
    pk = table_info.get_pk()
    if pk is None:
        if default in table_info.get_columns():
            return default
    else:
        return pk
    raise Exception('Layer has no primary key')

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
    return 'ogc_fid'


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
        

# def save_attached_history(path_):
#     """
#     Hace una copia del fichero adjunto para el historico
#     """
#     millis = int(round(time.time() * 1000))
#     suffix = "_" + str(millis)
#     if(not path.exists(path_)):
#         path_ = core_settings.MEDIA_ROOT + path_
#     li = path_.rsplit(".", 1)
#     try:
#         new_path = li[0] + suffix  + "." + li[1]
#     except Exception:
#         new_path = li[0] + suffix
#     if(path.exists(path_)):
#         copyfile(path_, new_path)
#         new_path = new_path.replace(core_settings.MEDIA_ROOT, '')
#         url = core_settings.MEDIA_URL + new_path
#     return url
        
        
def save_version_history(con, schema, table, lyr_id, feat_id, usr, operation, resource = None):
    """
    Cuando se edita una geometria se guarda antes en el historial. El tipo de operacion es:
    
    1-Crear, 
    2-Actualizar, 
    3-Borrar, 
    4-Anyadir recurso, 
    5-Borrar recurso
    """
    properties = []
    pks = con.get_pk_columns(table, schema=schema)
    geom_cols = con.get_geometry_columns(table, schema=schema)
    exclude_cols = pks + geom_cols + [settings.VERSION_FIELD]
    properties = _get_properties_names(con, schema, table, exclude_cols=exclude_cols)
    idfield = pks[0] if len(pks)>0 else 'ogc_fid'
    geom_column = geom_cols[0]
    sql = "SELECT {geom_column}, {idfield}, {feat_version_gvol}, row_to_json((SELECT d FROM (SELECT {properties}) d)) as props, {feat_date_gvol} FROM {schema}.{table} WHERE {idfield}= %s"
    query = sqlbuilder.SQL(sql).format(
        geom_column=sqlbuilder.Identifier(geom_column),
        idfield=sqlbuilder.Identifier(idfield),
        feat_version_gvol=sqlbuilder.Identifier(settings.VERSION_FIELD),
        feat_date_gvol=sqlbuilder.Identifier(settings.DATE_FIELD),
        properties=properties,
        schema=sqlbuilder.Identifier(schema),
        table=sqlbuilder.Identifier(table))
    con.cursor.execute(query, [feat_id])
    for r in con.cursor.fetchall():
        save_feature_version(lyr_id, r[1], r[0], r[3], r[2], timezone.now(), usr, operation, resource)

def save_feature_version(lyr_id, feat_id, wkb_geom, properties, version, date, usr, operation, resource = None):
    """
    Cuando se edita una geometria se guarda en el historial. El tipo de operacion es:
    
    1-Crear, 
    2-Actualizar, 
    3-Borrar, 
    4-Anyadir recurso, 
    5-Borrar recurso
    """
    change = FeatureVersions()
    change.version = version
    change.wkb_geometry = wkb_geom
    change.fields = properties
    change.date = date
    change.feat_id = feat_id
    change.layer_id = lyr_id
    change.usr = usr
    change.operation = operation
    change.resource = resource
    change.save()

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
    return LayerGroup.objects.filter(id__in=layergroup_ids)

def get_layergroups_by_user_and_project(request, project_id):
    '''
    Devuelve los grupos de capas que tienen capas para las que el usuario tiene permiso de lectura
    junto con los grupos de capas que tienen capas públicas y que están dentro del proyecto indicado.
    '''
    layergroup_ids = set([l.layer_group.id for l in utils.get_layerread_by_user(request)])
    return LayerGroup.objects.filter( \
        projectlayergroup__project__id=project_id,
        id__in=layergroup_ids).distinct()

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

def getResourceType(name):
    name = name.lower()
    if(name.endswith(".png") or name.endswith(".jpg") or 
       name.endswith(".jpeg") or name.endswith(".gif")):
        type_ = 1
    elif(name.endswith(".pdf")):
        type_ = 2
    elif(name.endswith(".doc") or name.endswith(".docx")):
        type_ = 3
    elif(name.endswith(".mp4") or name.endswith(".mkv") or 
         name.endswith(".avi") or name.endswith(".ogg") or 
         name.endswith(".mpeg")  or name.endswith(".mpg") or 
         name.endswith(".3gp")):
        type_ = 5
    else:
        type_ = 4
    return type_


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
    
def get_historic_resource_urlpath(layer_id, feature_id, version):
    try:
        return reverse('get_layer_historic_resource', args=[layer_id, feature_id, version])
    except:
        return ''

    
def get_historic_resource_url(request, layer_id, feature_id, version):
    try:
        url = get_historic_resource_urlpath(layer_id, feature_id, version)
        headers = request.META if request and request.META else None
        return get_absolute_url(url, headers)
    except:
        return ''


def get_feat_by_id(con, feat_id, schema, table, id_column, geom_column):
    epsilon = "ST_Perimeter(ST_Transform({geom}, 4326)) / 10000"
    properties = _get_properties_names(con, schema, table, exclude_cols=geom_column)
    params = "st_AsGeoJSON(st_transform({geom}, 4326)), row_to_json((SELECT d FROM (SELECT {properties}) d)) as props, ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, 4326), " + epsilon + "  ))"
    sql = "SELECT " + params + " FROM {schema}.{table} WHERE {id_column} = %s"
    query = sqlbuilder.SQL(sql).format(
        geom=sqlbuilder.Identifier(geom_column),
        schema=sqlbuilder.Identifier(schema),
        table=sqlbuilder.Identifier(table),
        id_column=sqlbuilder.Identifier(id_column),
        properties=properties,
    )
    con.cursor.execute(query, [feat_id])
    
    feat = con.cursor.fetchone()
    geometry = 'null'
    simplegeom = 'null'
    if feat[0] is not None:
        geometry = json.loads(feat[0])
        if 'crs' not in geometry:
            geometry['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")

    if feat[2] is not None:
        simplegeom = json.loads(feat[2])
        if 'crs' not in simplegeom:
            simplegeom['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")

    return {
        "type":"FeatureCollection",
        "geometry" : geometry,
        "properties" : feat[1],
        "simplegeom" : simplegeom,
    }


def _get_properties_names(con, schema, tablename, exclude_cols=[]):
    fields = con.get_fields(tablename, schema=schema)
    properties = [ f for f in fields if f not in exclude_cols]
    colnames = [ sqlbuilder.Identifier(c) for c in properties ]
    return sqlbuilder.SQL(", ").join(colnames)

def get_plugins(project):
    plugins = []
    tools = json.loads(project.tools)
    for tool in tools:
        if tool['checked']:
            plugins.append(tool['name'])

    return plugins

def get_order_in_project(project_id, layergroup_name):
    project = Project.objects.get(id=project_id)
    toc_order = json.loads(project.toc_order)
    order = 1000
    for key in toc_order:
        if key == layergroup_name:
            order = toc_order[key]['order']
    return order

def get_param_date(request):
        try:
            if 'date' in request.GET:
                datestr = request.GET['date']
                if(datestr is not None):
                    return datetime.strptime(datestr, '%d/%m/%Y %H:%M')
        except Exception:
            raise HttpException(400, "Bad parameter date. The format must be d/m/Y H:M")


def get_content(request):
    try:
        if(request.body != '' and request.body != b''):
            body_unicode = request.body.decode('utf-8')
            return json.loads(body_unicode)
    except Exception as e:
        raise HttpException(400, "Feature malformed." + format(e))
