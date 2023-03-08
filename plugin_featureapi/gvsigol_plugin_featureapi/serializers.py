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

@author: Nacho Brodin <nbrodin@scolab.es>
'''
import json
import math

from rest_framework import serializers

from django.contrib.auth.models import User
from gvsigol_core.models import Project, ProjectLayerGroup, ProjectZone, ZoneLayers
from gvsigol_plugin_featureapi import util
from gvsigol_plugin_featureapi.models import FeatureVersions
from gvsigol_plugin_baseapi.validation import HttpException
from gvsigol_services.models import LayerGroup, Layer, LayerResource, Server
from gvsigol import settings
from datetime import datetime
import time
from gvsigol_services import utils as services_utils
from django.utils import timezone
from django.urls import reverse
from psycopg2 import sql as sqlbuilder
from pyproj import Proj, transform
from gvsigol_services.tasks import tiling_layer
import logging
import ast
from gvsigol_services import views as serviceviews
from gvsigol_plugin_featureapi.export import VectorLayerExporter
import sys
logging.basicConfig()
logger = logging.getLogger(__name__)

  
class FeatureChangeSerializer(serializers.ModelSerializer):
    resource = serializers.SerializerMethodField('get_resource_')

    def get_resource_(self, obj):
        try:
            return settings.BASE_URL + util.get_historic_resource_urlpath(obj.layer_id, obj.feat_id, obj.version) 
        except Exception:
            pass

    class Meta:
        model = FeatureVersions
        fields = ['version', 'wkb_geometry', 'fields', 'date', 'feat_id', 'layer_id', 'usr', 'operation', 'resource']
        
class LayerResourceSerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField('get_url_')

    def get_url_(self, obj):
        try:
            return reverse('gvsigol_plugin_featureapi:get_attached_file', args=[obj.id])
        except Exception as e:
            print(e)
            pass

    class Meta:
        model = LayerResource
        fields = '__all__'


class FileUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, default='')
    image = serializers.FileField()
    
    
class GeometrySerializer(serializers.Serializer):
    coordinates = serializers.ListField(
          child=serializers.ListField(
              child=serializers.DecimalField(max_digits=12, decimal_places=6)
          )
    )
    type = serializers.CharField(default="Point", allow_blank=False, max_length=25)
   
class FeatureSerializer(serializers.Serializer):
    type = serializers.CharField(default="Feature", allow_blank=False, max_length=25)
    geometry = GeometrySerializer()
    properties = serializers.DictField(child=serializers.CharField())
    
    def info_by_point(self, validation, layer, lat, lon, epsg, buffer, return_geom, lang, blank, getbuffer):
        if layer.type != 'v_PostGIS':
            raise HttpException(400, "Wrong layer type. It must be a PostGIS type")
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose
                geom_cols = con.get_geometry_columns(table, schema=schema)

                #Devuelve un registro en blanco con los identificadores de campos y sus traducciones
                if(blank):
                    return self.get_blank_registry(con, table, schema, geom_cols, layer, lang)

                properties_query = self._get_properties_names(con, schema, table, exclude_cols=geom_cols)
                idfield = util.get_layer_pk_name(con, schema, table)

                geom_col = geom_cols[0]

                epsilon = self.get_epsilon(con, geom_col, epsg, table, schema, buffer, lon, lat)

                #get_buffer_params = " "
                #if(getbuffer == True):
                #    get_buffer_params = ", ST_AsGeoJSON(st_buffer('SRID=4326;POINT({lon} {lat})'::geometry, {buffer}))"

                params = "ST_AsGeoJSON(ST_Transform({geom}, {epsg})), row_to_json((SELECT d FROM (SELECT {col_names_values}) d)), ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, {epsg}), {epsilon})), ST_NPoints({geom}) as props"
                where = "ST_INTERSECTS(st_buffer('SRID=4326;POINT({lon} {lat})'::geometry, {buffer}), st_transform({geom}, 4326))"
                sql = sqlbuilder.SQL("SELECT " + params + " FROM {schema}.{table} WHERE " + where + " ORDER BY st_distance('SRID=4326;POINT({lon} {lat})'::geometry, st_transform({geom}, 4326))")
                query = sql.format(
                    geom=sqlbuilder.Identifier(geom_col),
                    epsg=sqlbuilder.Literal(epsg),
                    col_names_values=properties_query,
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    buffer=sqlbuilder.Literal(buffer),
                    lat=sqlbuilder.Literal(lat),
                    lon=sqlbuilder.Literal(lon),
                    epsilon=sqlbuilder.Literal(epsilon),
                )
                
                con.cursor.execute(query)
                from gvsigol_plugin_featureapi.serializers import LayerResourceSerializer

                feat_list = []
                for feat in con.cursor.fetchall():
                    #self.showSimplification(epsilon, feat)
                    resourceset = LayerResource.objects.filter(layer_id=layer.id, feature=feat[1][idfield])
                    serializer = LayerResourceSerializer(resourceset, many=True)
                    properties = feat[1]
                    if 'feat_version_gvol' not in properties:
                        properties['feat_version_gvol'] = 1

                    if return_geom == True:
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

                        element = {
                            "type":"Feature",
                            "properties" : properties,
                            #"translates" : self.translate(layer.conf, feat[1], lang),
                            "geometry" : geometry,
                            "simplegeom" : simplegeom,
                            "resources" : serializer.data,
                            "numpoints" : feat[3]
                        }
                    else:
                        element = {
                            "type":"Feature",
                            "properties" : properties,
                            #"translates" : self.translate(layer.conf, feat[1], lang),
                            "resources" : serializer.data
                        }
                        
                    feat_list.append(element)

                bufferGeom = 'null'
                if(getbuffer == True):
                    bufferGeom = self.getBufferGeometry(con, lon, lat, buffer)
                    bufferGeom = json.loads(bufferGeom)
                    if 'crs' not in bufferGeom:
                        bufferGeom['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")

                return {
                        "type":"FeatureCollection",
                        "lang" : lang,
                        "totalfeatures" : len(feat_list),
                        "features" : feat_list,
                        "buffer": bufferGeom
                }
        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Features cannot be queried. Unexpected error: " + format(e))

    def getBufferGeometry(self, con, lon, lat, buffer):
        sql = sqlbuilder.SQL("SELECT ST_AsGeoJSON(st_buffer('SRID=4326;POINT({lon} {lat})'::geometry, {buffer}))")
        query = sql.format(
            buffer=sqlbuilder.Literal(buffer),
            lat=sqlbuilder.Literal(lat),
            lon=sqlbuilder.Literal(lon),
        )
        con.cursor.execute(query)
        r = con.cursor.fetchone()
        return r[0]



    def showSimplification(self, epsilon, feat):
        print("************************************************")
        print(".........E=" + str(epsilon))
        a = json.loads(feat[0])
        b = json.loads(feat[2])
        print(".........Src len =" + str(len(a['coordinates'])))
        print(".........Dst len =" + str(len(b['coordinates'])))

        for block in a['coordinates']:
            print(".........Src " + str(len(block)) + " " )
            for coor in block:
                print(".........Src Num:" + str(len(coor)) + " " )

        for block in b['coordinates']:
            print(".........Dst " + str(len(block)) + " " )
            for coor in block:
                print(".........Dst Num:" + str(len(coor)) + " " )


    def get_epsilon(self, con, geom_col, epsg, table, schema, buffer, lon, lat):
        '''
        Epsilon es un número que sirve para la simplificación de polígonos y tiene relación con el número de puntos a simplificar en una curva
        por la distancia de los puntos a sus extremos.  Como las geometrías están en 4326 epsilon está en grados. Cuanto más grande es epsilon menos
        se simplifica. Lo calculamos de forma aproximada a partir del perímetro del polígono. Si aumentamos div se simplifica más y si lo disminuimos
        se simplifica menos.

        Esto se usa desde la app móvil para dibujar poligonos seleccionados porque si metemos muchos vértices petamos la app. 
        '''
        div = 10000
        sql = sqlbuilder.SQL("SELECT ST_Perimeter(ST_Transform({geom}, {epsg})) FROM {schema}.{table} WHERE ST_INTERSECTS(st_buffer('SRID=4326;POINT({lon} {lat})'::geometry, {buffer}), st_transform({geom}, 4326)) ORDER BY st_distance('SRID=4326;POINT({lon} {lat})'::geometry, st_transform({geom}, 4326))")
        query = sql.format(
            geom=sqlbuilder.Identifier(geom_col),
            epsg=sqlbuilder.Literal(epsg),
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            buffer=sqlbuilder.Literal(buffer),
            lat=sqlbuilder.Literal(lat),
            lon=sqlbuilder.Literal(lon),
        )
        con.cursor.execute(query)
        for feat in con.cursor.fetchall():
            perimeter = feat[0]
            return perimeter / div


    def get_blank_registry(self, con, tablename, schema, exclude_cols, layer, lang):
        fields = con.get_fields(tablename, schema=schema)
        properties = {}
        for f in fields:
            if f not in exclude_cols:
                properties[f] = "" #asigna blancos a cada propiedad del registro
        #properties = [ f for f in fields if f not in exclude_cols]
        result = serviceviews.describe_feature_type(tablename, layer.datastore.workspace.name)
        geom_type = None
        if result['fields'] :
            for f in result['fields']:
                if f['type']:
                    type_ = f['type'].upper()
                    if type_ == 'POINT' or type_ == 'MULTIPOINT' or type_ == 'LINESTRING' or type_ == 'MULTILINESTRING' or type_ == 'POLYGON' or type_ == 'MULTIPOLYGON':
                        geom_type = type_
                    if type_ == 'INTEGER' or type_ == 'BIGINT':
                        properties[f['name']] = 0
                    if type_ == 'NUMERIC' or type_ == 'DOUBLE PRECISION':
                        properties[f['name']] = 0.0
                    if type_ == 'BOOLEAN':
                        properties[f['name']] = False
                    if type_.startswith('TIME') or type_ == 'DATE':
                        properties[f['name']] = None
    
        return {
                    "type":"FeatureCollection",
                    "lang" : lang,
                    "totalfeatures" : 1,
                    "features" : [{
                        "type":"Feature",
                        "geometry" : {
                            "type" : geom_type
                        },
                        "properties" : properties,
                        "translates" : self.translate(layer.conf, properties, lang)
                    }]
                }

    def translate(self, conf, feat, lang):
        try:
            conf = ast.literal_eval(conf)
            translate = {}
            for i in feat:
                locate_translate = False
                for j in conf['fields']:
                    if i == j['name']:
                        #translate[j['title-' + lang]] = feat[i]
                        translate[i] = j['title-' + lang]
                        locate_translate = True
                if not locate_translate:
                    #translate[i] = feat[i]
                    translate[i] = i

            return translate
        except Exception:
            return feat
        

    def get(self, validation, lyr_id, feat_id, epsg):
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            raise HttpException(400, "Wrong layer type. It must be a PostGIS type")
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose
                pk_list = con.get_pk_columns(table, schema=schema)
                if(len(pk_list) > 0):
                    #Se considera que las capas tienen una sola clave primaria
                    where = sqlbuilder.SQL("WHERE {pk_col} = {feat_id}").format(
                              pk_col = sqlbuilder.Identifier(pk_list[0]),
                              feat_id=sqlbuilder.Literal(feat_id)
                    )
                else:
                    where = sqlbuilder.SQL("WHERE ogc_fid={feat_id}").format(feat_id=feat_id)
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties_query = self._get_properties_names_with_id(con, schema, table, exclude_cols=geom_cols)
                geom_col = geom_cols[0]
                #De este serializador no ha modelo. Hay que hacerlo por consulta
                epsilon = "ST_Perimeter(ST_Transform({geom}, 4326)) / 10000"
                select0 = "ST_AsGeoJSON(ST_Transform({geom}, {epsg})), "
                select1 = "row_to_json((SELECT d FROM (SELECT {col_names_values}) d)), "
                select2 = "ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, {epsg}), " + epsilon + ")), "
                select3 = "ST_NPoints({geom})"
                sql = sqlbuilder.SQL("SELECT " + select0 + select1 + select2 + select3 + " FROM {schema}.{table} {where}")
                query = sql.format(
                    geom=sqlbuilder.Identifier(geom_col),
                    epsg=sqlbuilder.Literal(epsg),
                    col_names_values=properties_query,
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    where=where
                )
                con.cursor.execute(query)
                rows = con.cursor.fetchall()
                
                if(rows is not None and len(rows) > 0):
                    feat = rows[0]

                    geometry = 'null'
                    simplegeom = 'null'
                    if feat[0] is not None:
                        geometry = json.loads(feat[0])
                        if 'crs' not in geometry:
                            geometry['crs'] = json.loads('{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:' + str(epsg) + '\"}}')

                        if feat[2] is not None:
                            simplegeom = json.loads(feat[2])
                            if 'crs' not in simplegeom:
                                simplegeom['crs'] = json.loads('{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:' + str(epsg) + '\"}}')

                    return {
                        "type":"Feature",
                        "geometry" : geometry,
                        "properties" : feat[1],
                        "simplegeom" : simplegeom,
                        #"resources" : serializer.data,
                        "numpoints" : feat[3]
                    }
                raise HttpException(404, "Feature NOT found")
        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Features cannot be queried. Unexpected error: " + format(e))
        
    def list(self, validation, lyr_id, pagination, epsg, date, strict_search, onlyprops = False, text = None, filter = None):
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            raise HttpException(400, "La capa no es del tipo correcto. Debería ser una capa PostGIS")
        con = None
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose
                if(date is not None):
                    #Es importante +00 para que considere que la fecha de entrada es UTC
                    date_val =  str(date) + "+00"
                    where = sqlbuilder.SQL("WHERE {date_field} >={date_val}").format(
                               date_field=sqlbuilder.Identifier(settings.DATE_FIELD),
                               date_val=sqlbuilder.Literal(date_val)
                    )
                    num_entries = util.count(con, schema, table, ">=", field=settings.DATE_FIELD, value=date_val)
                else:
                    where = sqlbuilder.SQL("")
                    num_entries = util.count(con, schema, table)
                max_feat, page = pagination.get_pagination_params()
                offset = max_feat * page
                if(pagination.page > math.floor(num_entries/float(pagination.max_)) or pagination.page < 0):
                    raise HttpException(404, "Page NOT found")
                limit_offset = sqlbuilder.SQL("LIMIT {max_feat} OFFSET {offset}").format(
                            max_feat=sqlbuilder.Literal(max_feat),
                            offset=sqlbuilder.Literal(offset))
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties = self._get_properties_names(con, schema, table, exclude_cols=geom_cols)
                geom_col = geom_cols[0]
                whereCount = None

                if text is not None:
                    excluded = [geom_cols[0], 'modified_by', 'feat_date_gvol', 'feat_version_gvol', 'last_modification']
                    where = None
                    #whereCount = None
                    if strict_search == True:
                        where = self._get_strict_search_where(con, schema, table, text, exclude_cols=excluded)
                        whereCount = where
                    else:
                        if self._exists_trigram_extension(con):
                            where = self._get_search_where_trigram(con, True, schema, table, text, exclude_cols=excluded)
                            whereCount = self._get_search_where_trigram(con, False, schema, table, text, exclude_cols=excluded)
                            self._set_limit_trigram(con)
                        else:
                            where = self._get_search_where_tsvector(con, schema, table, text, exclude_cols=excluded)
                            whereCount = where
                if filter is not None:
                    if text is not None:
                        where = where + self._get_filter_where_and(filter)
                        whereCount = where
                    
                    else:
                        where = self._get_filter_where(filter)
                        whereCount = where
                    
                if whereCount is not None:                    
                    sqlCount = sqlbuilder.SQL("SELECT count(*) FROM {schema}.{table} {where}")
                    queryCount = sqlCount.format(
                        schema=sqlbuilder.Identifier(schema),
                        table=sqlbuilder.Identifier(table),
                        where=whereCount,
                    )
                    con.cursor.execute(queryCount)
                    for r in con.cursor.fetchall():
                        num_entries = r[0]
                        break
                    
                if onlyprops == False:
                    sql = sqlbuilder.SQL("SELECT ST_AsGeoJSON(ST_Transform({geom}, {epsg})), row_to_json((SELECT d FROM (SELECT {properties}) d)) as props FROM {schema}.{table} {where} {limit_offset}")
                else:
                    sql = sqlbuilder.SQL("SELECT row_to_json((SELECT d FROM (SELECT {properties}) d)) as props, ST_AsGeoJSON(ST_Transform(ST_Centroid({geom}), {epsg})) FROM {schema}.{table} {where} {limit_offset}")
                
                query = sql.format(
                    geom=sqlbuilder.Identifier(geom_col),
                    epsg=sqlbuilder.Literal(epsg),
                    properties=properties,
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    where=where,
                    limit_offset=limit_offset
                )
                con.cursor.execute(query)
                feat_list = []
                for feat in con.cursor.fetchall():
                    if(onlyprops == True):
                        element = {
                            "type":"Feature",
                            "properties" : feat[0],
                            "centroid" : json.loads(feat[1]) if feat[1] is not None else 'null'
                        }
                    else:
                        element = {
                            "type":"Feature",
                            "geometry" : json.loads(feat[0]) if feat[0] is not None else 'null',
                            "properties" : feat[1]
                        }
                    feat_list.append(element)
                return {
                    "content" : {
                        "type":"FeatureCollection",
                        "totalfeatures" : len(feat_list),
                        "lendata" : num_entries,
                        "features" : feat_list
                    },
                    "links" : [pagination.get_links(num_entries)]
                }
        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Features cannot be queried. Unexpected error: " + format(e))
            

    def list_field_options(self, lyr_id, fieldSelected):
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            raise HttpException(400, "La capa no es del tipo correcto. Debería ser una capa PostGIS")
        con = None
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose                    
                sql = sqlbuilder.SQL("SELECT DISTINCT {fieldSelected} FROM {schema}.{table}")

                query = sql.format(
                    fieldSelected=sqlbuilder.Identifier(fieldSelected),
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                )
                con.cursor.execute(query)
                feat_list = []
                for feat in con.cursor.fetchall():
                    feat_list.append(feat[0])

                return feat_list

        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Field options cannot be queried. Unexpected error: " + format(e))
            

    def list_by_extent(self, validation, lyr_id, epsg, minlat, minlon, maxlat, maxlon, zip, resources):
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            raise HttpException(400, "La capa no es del tipo correcto. Debería ser una capa PostGIS")
        con = None
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: 
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties = self._get_properties_names(con, schema, table, exclude_cols=geom_cols)
                idfield = util.get_layer_pk_name(con, schema, table)
                geom_col = geom_cols[0]

                epsilon = "ST_Perimeter(ST_Transform({geom}, 4326)) / 10000"
                params = "st_AsGeoJSON(st_transform({geom}, 4326)), row_to_json((SELECT d FROM (SELECT {properties}) d)) as props, ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, 4326), " + epsilon + "  )), ST_NPoints({geom})"
                where = "ST_INTERSECTS('SRID=4326;POLYGON(({minlon} {maxlat}, {maxlon} {maxlat}, {maxlon} {minlat}, {minlon} {minlat}, {minlon} {maxlat}))'::geometry, st_transform({geom}, 4326))"
                sql = "SELECT " + params + " FROM {schema}.{table} WHERE " + where
                query = sqlbuilder.SQL(sql).format(
                    geom=sqlbuilder.Identifier(geom_col),
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    minlon=sqlbuilder.Literal(minlon),
                    maxlat=sqlbuilder.Literal(maxlat),
                    maxlon=sqlbuilder.Literal(maxlon),
                    minlat=sqlbuilder.Literal(minlat),
                    properties=properties,
                )

                con.cursor.execute(query)
                nbytes = 0

                feat_list = []

                count = 0
                for feat in con.cursor.fetchall():
                    geometry = 'null'
                    simplegeom = 'null'
                    if feat[0] is not None:
                        nbytes += sys.getsizeof(feat[0])
                        geometry = json.loads(feat[0])
                        if 'crs' not in geometry:
                            geometry['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")

                    if feat[2] is not None:
                        nbytes += sys.getsizeof(feat[2])
                        simplegeom = json.loads(feat[2])
                        if 'crs' not in simplegeom:
                            simplegeom['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")

                    nbytes += sys.getsizeof(feat[1])
                    nbytes += sys.getsizeof(feat[3])
                    element = {
                        "type":"Feature",
                        "geometry" : geometry,
                        "simplegeom" : simplegeom,
                        "properties" : feat[1],
                        "numpoints" : feat[3],
                        "resources" : []
                    }
                    nbytes += sys.getsizeof(element)

                    feat_list.append(element)


                if(not zip):
                    return {
                        #"crs": { "type":"name","properties":{"name":"EPSG:4326"}},
                        "type":"FeatureCollection",
                        "totalfeatures" : con.cursor.rowcount,
                        "features" : feat_list
                    }
                else:
                    result = self.splitArray(nbytes, feat_list)
                    exp = VectorLayerExporter()
                    return exp.create_package_from_geojson(result, layer.datastore.workspace.name, layer.name, idfield, resources)
        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Features cannot be queried. Unexpected error: " + format(e))


    def splitArray(self, nbytes, feat_list):
        parts = 4
        length = len(feat_list)
        if(nbytes > 9000000 and length >= parts):
            result = []
            list_ = [ feat_list[i * length // parts: (i + 1) * length // parts] for i in range(parts) ]
            for i in list_:
                result.append({
                    "type":"FeatureCollection",
                    "totalfeatures" : len(i),
                    "features" : i
                })
            return result 
        else:
            return {
                "type":"FeatureCollection",
                "totalfeatures" : length,
                "features" : feat_list
            }


    def delete(self, validation, lyr_id, feat_id, version):
        i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
        with i as con: # connection will autoclose
            layer = Layer.objects.get(id = lyr_id)
            validation.check_version_and_date_columns(layer, con, schema, table)
            if(version):
                validation.check_feature_version(con, schema, table, feat_id, version)
                
            idfield = util.get_layer_pk_name(con, schema, table)
            validation.check_feat_exists(con, schema, table, feat_id, idfield=idfield)
            try:
                util.update_feat_version(con, schema, table, feat_id)
                sql = "DELETE FROM {schema}.{table} WHERE {idfield} = %s"
                query = sqlbuilder.SQL(sql).format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    idfield=sqlbuilder.Identifier(idfield)
                    )
                util.save_version_history(con, schema, table, lyr_id, feat_id, validation.usr, 3)
                con.cursor.execute(query, [feat_id])
            except Exception as e:
                raise HttpException(400, "Feature cannot be deleted. Unexpected error: " + format(e))


    def update(self, validation, lyr_id, data, override, version_to_override):
        """
        Update and return a new Feature instance, given the validated data.
        """
        #Hay que hacer inserciones en tabla con Introspect porque de las capas no hay modelo
        i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
        with i as con: # connection will auoclose
            idfield = util.get_layer_pk_name(con, schema, table)
            try:
                (_, _, geom_column, _, crs_dst, _, _, _) = con.get_geometry_columns_info(table=table, schema=schema)[0]
            except:
                logger.exception("Error getting CRS")
                crs_dst = None
            feat_id = data['properties'][idfield]
            layer = Layer.objects.get(id = lyr_id)
            validation.check_version_and_date_columns(layer, con, schema, table)
            data['properties'][settings.DATE_FIELD] = "now()"#datetime.now()
            version = data['properties']['feat_version_gvol']
            if not override:
                validation.check_feature_version(con, schema, table, feat_id, version)
            else:
                if(version_to_override != -1):
                    validation.check_version_to_overwrite(con, schema, table, feat_id, version_to_override)
        
        
            geom = None
            if "geometry" in data:
                geom = data['geometry'] 
            print('GEOMETRY: ' + str(geom))
            self._check_geom(geom, con)
            
            try:
                sql, values = self._get_sql_update(table, schema, data['properties'], feat_id, geom, geom_column, crs_dst, idfield)
                con.cursor.execute(sql, values)
                util.save_version_history(con, schema, table, lyr_id, feat_id, validation.usr, 2)
                return util.get_feat_by_id(con, feat_id, schema, table, idfield, geom_column)
            except Exception as e:
                raise HttpException(400, "Feature cannot be updated in database. Unexpected error: " + format(e))
        
        
    def create(self, validation, lyr_id, data):
        """
        Create and return a new Feature instance, given the validated data.
        """

        #En la creación no puede venir el campo ogc_fid porque ya lo pone el servidor y da un error de 
        #campo duplicado. Si la app lo manda hay que eliminarlo
        if 'ogc_fid' in data['properties']:
            del data['properties']['ogc_fid']

        #Hay que hacer inserciones en tabla con Introspect porque de las capas no hay modelo
        i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
        with i as con: # connection will auoclose
            try:
                id_feat = util.get_layer_id(con, schema, table)
            except Exception:
                id_feat = None
            idfield = util.get_layer_pk_name(con, schema, table)
            try:
                (_, _, geom_column, _, crs_dst, _, _, _) = con.get_geometry_columns_info(table=table, schema=schema)[0]
            except:
                logger.exception("Error getting CRS")
                crs_dst = None

            layer = Layer.objects.get(id = lyr_id)
            validation.check_version_and_date_columns(layer, con, schema, table)
            data['properties'][settings.VERSION_FIELD] = 1
            data['properties'][settings.DATE_FIELD] =  "now()"#time.strftime("%Y-%m-%d %H:%M:%S") #datetime.utcnow()
            
            try:
                sql = self._get_sql_insert(table, schema, data['properties'], id_feat, data['geometry'], geom_column, crs_dst, idfield, con)
            except Exception as e:
                if(hasattr(e, 'msg') and e.msg != ''):
                    raise e
                raise HttpException(400, "Feature cannot be inserted in database. Unexpected error: " + format(e))
            try:
                con.cursor.execute(sql)
                util.save_version_history(con, schema, table, lyr_id, id_feat, validation.usr, 1)
            except Exception as e:
                raise HttpException(400, "Feature cannot be inserted in database. Unexpected error: " + format(e))
                
            data['properties'][idfield] = id_feat
            
            data['properties'][settings.DATE_FIELD] = timezone.now()

            #Devolvemos el registro que se ha almacenado en la BBDD. Hay que consultarlo
            #pq puede haber triggers que modifiquen campos 
            
            return self.get(validation, lyr_id, id_feat, 4326)

            # geom_cols = con.get_geometry_columns(table, schema=schema)
            # properties = self._get_properties_names(con, schema, table, exclude_cols=geom_cols)
            # sql = "SELECT row_to_json((SELECT d FROM (SELECT {properties}) d)) as props FROM {schema}.{table} WHERE {idfield} = %s"
            # query = sqlbuilder.SQL(sql).format(
            #     schema=sqlbuilder.Identifier(schema),
            #     table=sqlbuilder.Identifier(table),
            #     idfield=sqlbuilder.Identifier(idfield),
            #     properties=properties
            # )
            # con.cursor.execute(query, [id_feat])
            # row = con.cursor.fetchone()

            # return row[0]
               

    def _check_geom(self, geomjson, con):
        """
        Comprueba que la geometría sea válida
        """
        if geomjson is None:
            return
        sql = "SELECT st_isvalid(ST_TRANSFORM(ST_GeomFromGeoJSON({geojson}),4258))"
        query = sqlbuilder.SQL(sql).format(
            geojson=sqlbuilder.Literal(json.dumps(geomjson))
            )
        print ('CHECK_GEOM: ' + query.as_string(con.cursor))
        con.cursor.execute(query)
        rows = con.cursor.fetchone()
        if rows[0] == False:
            raise HttpException(400, "Geometry malformed")


    def _get_properties_names_with_id(self, introspect, schema, tablename, exclude_cols=[]):
        fields = introspect.get_fields(tablename, schema=schema)
        properties = [ f for f in fields if f not in exclude_cols]
        col_names_values = []
        for p in properties:
             #col_names_values.append(sqlbuilder.Literal(p))
             col_names_values.append(sqlbuilder.Identifier(p))
        return sqlbuilder.SQL(", ").join(col_names_values)


    def _get_properties_names(self, introspect, schema, tablename, exclude_cols=[]):
        fields = introspect.get_fields(tablename, schema=schema)
        properties = [ f for f in fields if f not in exclude_cols]
        colnames = [ sqlbuilder.Identifier(c) for c in properties ]
        return sqlbuilder.SQL(", ").join(colnames)


    def _get_strict_search_where(self, introspect, schema, tablename, text, exclude_cols=[]):
        fields = introspect.get_fields_by_datatype('character varying', tablename, schema=schema)
        colnames = [ f for f in fields if f not in exclude_cols]
        where = None
        for i in colnames:
            if where is not None :
                where = where + " OR "
            else:
                where = " WHERE ("
            where = where + "lower(unaccent(" + i + ")) like lower(unaccent({text}))"

        where = where + ")"

        return sqlbuilder.SQL(where).format(
            text=sqlbuilder.Literal("%" + text + "%"))

    def _get_filter_where(self, filter):
        where = self._get_filter_query(filter)
        where = " WHERE (" + where + ")"
        return sqlbuilder.SQL(where)

    def _get_filter_where_and(self, filter):
        where = self._get_filter_query(filter)
        where_and = " AND (" + where + ")"
        return sqlbuilder.SQL(where_and)

    def _get_filter_query(self, filter):
        filter_queries = filter['filterQueries']
        filter_operator = None
        where = None
        if 'filterOperator' in filter:
            filter_operator = filter['filterOperator']
        for i, q in enumerate(filter_queries):
            query = None
            if q['type'] == 'query':
                query = q['field'] + q['operator'] + "'" + str(q['value']) + "'"
                if q['notop'] == True:
                    query = "NOT " + query
            elif q['type'] == 'qGroup':
                query = "("
                queries = q['querys']
                qGroup_operator = None
                if 'op' in q:
                    qGroup_operator = q['op']
                for j, gq in enumerate(queries):
                    opNOT = False
                    if 'notop' in gq:
                        opNOT = gq['notop']
                    gQuery = gq['field'] + gq['operator'] + "'" + str(gq['value']) + "'"
                    if opNOT == True:
                        gQuery = "NOT " + gQuery
                    if j != len(queries) -1:
                        gQuery = gQuery + qGroup_operator
                    query = query + gQuery
                query = query + ")"
            if i != len(filter_queries) - 1:
                query = query + filter_operator
            if where is not None:
                where = where + query
            else:
                where = query
        return where
  
    def _get_search_where_tsvector(self, introspect, schema, tablename, text, exclude_cols=[]):
        fields = introspect.get_fields_by_datatype('character varying', tablename, schema=schema)
        colnames = [ f for f in fields if f not in exclude_cols]
        where = None
        for i in colnames:
            if where is not None :
                where = where + " || "
            else:
                where = " WHERE "
            where = where + "to_tsvector({languaje}, coalesce(" + i + ", '')::varchar)"
        where = where + " @@ plainto_tsquery({languaje}, {text})"

        return sqlbuilder.SQL(where).format(
            text=sqlbuilder.Literal(text),
            languaje=sqlbuilder.Literal("spanish"))


    def _set_limit_trigram(self, con):
        sql = "SELECT set_limit(0.17)"
        query = sqlbuilder.SQL(sql)
        con.cursor.execute(query)


    def _get_search_where_trigram(self, introspect, order, schema, tablename, text, exclude_cols=[]):
        fields = introspect.get_fields_by_datatype('character varying', tablename, schema=schema)
        colnames = [ f for f in fields if f not in exclude_cols]
        where = None
        for i in colnames:
            if where is not None :
                where = where + " OR  "
            else:
                where = " WHERE "
            where = where + i + " % unaccent({text})"

        if order == True:
            where = where + " ORDER BY (SELECT max(x) FROM unnest(ARRAY["

            for i in colnames:
                if where.endswith(")"):
                    where = where + " ,  "
                where = where + " SIMILARITY( unaccent(" + i + "), unaccent({text}))"

            where = where + "]) as x) DESC"

        return sqlbuilder.SQL(where).format(
            text=sqlbuilder.Literal(text),
        )


    def _exists_trigram_extension(self, con):
        sql = "SELECT count(*) from pg_extension where extname = 'pg_trgm'"
        query = sqlbuilder.SQL(sql)
        con.cursor.execute(query)
        row = con.cursor.fetchone()
        if row[0] <= 0:
            return False
        else:
            return True


    def _get_sql_insert(self, table, schema, props, id_feat, geom, geom_column, crs, idfield, con):
        #TODO:quitar para V2
        #El CRS de origen si no viene se presupone en 4326. El de destino se lee de la capa
        #Ojo! esto es un problema pq se acostumbran a no meter CRS y luego meten coordenadas en otro sistema y ya está liada
        if "crs" not in geom: 
            geom['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")
            
        self._check_geom(geom, con)
        
        colnames = [sqlbuilder.Identifier(idfield), sqlbuilder.Identifier(geom_column)]
        colvalues = [
            sqlbuilder.Literal(id_feat),
            sqlbuilder.SQL("ST_TRANSFORM(ST_GeomFromGeoJSON({geojson}),{crs})").format(
                geojson=sqlbuilder.Literal(json.dumps(geom)),
                crs=sqlbuilder.Literal(crs)
                )
            ]
        for i in list(props.keys()):
            colnames.append(sqlbuilder.Identifier(i))
            colvalues.append(sqlbuilder.Literal(props[i]))

        sql = "INSERT INTO {schema}.{table} ({colnames}) VALUES ({colvalues})"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            colnames=sqlbuilder.SQL(", ").join(colnames),
            colvalues=sqlbuilder.SQL(", ").join(colvalues),
            )
        return query
    
    def _get_sql_update(self, table, schema, props, id_feat, geom, geom_column, crs, idfield):
        values = []
        col_values = []
        for i in list(props.keys()):
            col_values.append(sqlbuilder.SQL("{field} = %s").format(field=sqlbuilder.Identifier(i)))
            if(i == settings.VERSION_FIELD):
                try:
                    values.append(int(props[i]) + 1)
                except Exception:
                    values.append(props[i])
            else:
                values.append(props[i])
            
        if geom is not None:
            #El CRS de origen si no viene se presupone en 4326. El de destino se lee de la capa
            if "crs" not in geom: 
                geom['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")
            value = sqlbuilder.SQL("ST_TRANSFORM(ST_GeomFromGeoJSON({geojson}),{crs})").format(
                geojson=sqlbuilder.Literal(json.dumps(geom)),
                crs=sqlbuilder.Literal(crs)
                )
            col_values.append(sqlbuilder.SQL("{field} = {value}").format(
                field=sqlbuilder.Identifier(geom_column),
                value=value))
        values.append(id_feat)

        sql = "UPDATE {schema}.{table} SET {col_values} WHERE {idfield} = %s"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            col_values=sqlbuilder.SQL(", ").join(col_values),
            idfield=sqlbuilder.Identifier(idfield)
            )
        return (query, values)


class LayerChangesSerializer(serializers.Serializer):
    
    def check_changes(self, timestamp, layer, ncolumns, layertype, zone):
        if(layertype == 'tiles'):
            return self.check_tiled_layer_changes(timestamp, layer, zone)

        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose
                if timestamp <= 0:
                    return 0
                
                sql = sqlbuilder.SQL("SELECT count(*) FROM {schema}.{table} WHERE (extract(epoch from feat_date_gvol) *  1000) > {timestamp}")
                query = sql.format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    timestamp=sqlbuilder.Literal(timestamp),
                )
                try:
                    con.cursor.execute(query)
                    result = con.cursor.fetchone()
                    if result[0] > 0:
                        return result[0]
                except Exception as e:
                    pass #Puede pasar que no exista feat_date_gvol y de un error

                sql = sqlbuilder.SQL("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema={schema} AND table_name={table}")
                query = sql.format(
                    schema=sqlbuilder.Literal(schema),
                    table=sqlbuilder.Literal(table)
                )

                con.cursor.execute(query)
                result = con.cursor.fetchone()
                if result[0] != ncolumns:
                    return 1 # Si ha cambiado el num de columnas devolvemos una modificación para que la app se actualice

            return 0

        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Features cannot be queried. Unexpected error: " + format(e))


    def check_tiled_layer_changes(self, timestamp, layer, zone):
        lyrs = ZoneLayers.objects.filter(zone__title=zone, layer=layer)
        for lyr in lyrs:
            if lyr.version > timestamp:
                return lyr.version
        return 0


class LayerSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField('get_layer_icon')
    last_change = serializers.SerializerMethodField('get_last_change_')
    external_url = serializers.SerializerMethodField('get_external_url_')
    external_layers = serializers.SerializerMethodField('get_external_layers_')
    image_type = serializers.SerializerMethodField('get_image_type_')
    external_tilematrixset = serializers.SerializerMethodField('get_external_tilematrixset_')
    workspace = serializers.SerializerMethodField('get_layer_workspace_')
    writable = serializers.SerializerMethodField('is_writable')
    service_version = serializers.SerializerMethodField('get_external_service_version')

    def is_writable(self, obj):
        try:
            if(obj.external):
                return False    
            return services_utils.can_write_layer(self.context['request'], obj)
        except Exception:
            return False

    def get_layer_workspace_(self, obj):
        try:
            #layer = Layer.objects.get(id=obj.id)
            if obj.datastore and obj.datastore.workspace:
                return obj.datastore.workspace.name
        except Exception:
            pass

    def get_external_tilematrixset_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['matrixset']
        except Exception:
            pass
    def get_external_service_version(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['version']
        except Exception:
            pass
    def get_external_url_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['url']
        except Exception:
            pass

    def get_external_layers_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['layers']
        except Exception:
            pass

    def get_image_type_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['format']
        except Exception:
            pass

    def get_layer_icon(self, obj):
        _, url = services_utils.get_layer_img(obj.id, None)
        return url 

    def get_last_change_(self, obj):
        try:
            #Si hay muchas capas se abren y cierran constantemente conexiones a la bd lo que ralentiza. 
            #Almacenamos en un array las conexiones y al acabar las consultas se cierran
            #De esta forma solo se abre una por datastore y no una por capa.
            if obj.datastore:
                con = self.root.instance.connections[obj.datastore.id]
                table = obj.source_name if obj.source_name else obj.name
                sql = "select max({date_col}) as max from {schema}.{table}"
                query = sqlbuilder.SQL(sql).format(
                    date_col=sqlbuilder.Identifier(settings.DATE_FIELD),
                    schema=sqlbuilder.Identifier(obj.datastore.name),
                    table=sqlbuilder.Identifier(table))
                con.cursor.execute(query, [])
                for r in con.cursor.fetchall():
                    return r[0]
        except Exception as e:
            pass
        return datetime(2000, 1, 1)

        
    class Meta:
        model = Layer
        fields = ['id', 'name', 'title', 'abstract', 'type', 'visible', 'queryable', 'cached', 'single_image', 'created_by', 'thumbnail', 'layer_group_id', 'icon', 'last_change', 'latlong_extent', 'native_extent', 'external_layers', 'external_url', 'external_tilematrixset', 'workspace', 'image_type', 'writable', 'external', 'service_version']



class LayerCreateSerializer(serializers.Serializer):
    geom_type = serializers.CharField(max_length=25, min_length=5, default='Point')
    datastore = serializers.IntegerField(default=10)
    name = serializers.CharField(max_length=25, min_length=3, default='testlayer')
    title = serializers.CharField(max_length=25, min_length=3, default='Test layer')
    srs = serializers.CharField(max_length=25, min_length=5, default='EPSG:4326')
    layer_group = serializers.IntegerField(default=5)
    fields = serializers.CharField(min_length=2, default='[{\"id\":\"klt01kb332\",\"name\":\"fieldName\",\"type\":\"character_varying\",\"calculation\":\"\",\"calculationLabel\":\"\"}]')
    md_abstract = serializers.CharField(max_length=2048, min_length=5, default='')