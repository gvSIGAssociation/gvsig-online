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
from gvsigol_symbology.models import Style
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
#logging.basicConfig()
logger = logging.getLogger(__name__)

  

class StyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Style
        fields = '__all__'


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
    
    def info_by_point(self, validation, layer, lat, lon, epsg, buffer, return_geom, lang, blank, getbuffer, cql_filter_read=None):
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

                native_epsg = 4326
                tbuffer = buffer
                if layer.native_srs:
                    native_epsg = layer.native_srs.split(':')[1]
                    native_epsg = int(native_epsg)
                    if(native_epsg != 4326):
                        tbuffer = self.get_transformed_buffer_distance(con, 4326, native_epsg, buffer, lon, lat)
                   
                epsilon = self.get_epsilon(con, geom_col, epsg, native_epsg, table, schema, buffer, lon, lat)
                #get_buffer_params = " "
                #if(getbuffer == True):
                #    get_buffer_params = ", ST_AsGeoJSON(st_buffer('SRID=4326;POINT({lon} {lat})'::geometry, {buffer}))"
                if cql_filter_read:
                    cql_filter = sqlbuilder.SQL('{cql_filter} AND').format(cql_filter=self._get_cql_permissions_filter(cql_filter_read))
                else:
                    cql_filter = sqlbuilder.SQL('')
                sql = sqlbuilder.SQL("""
                    SELECT
                    ST_AsGeoJSON(ST_Transform({geom}, {epsg})), row_to_json((SELECT d FROM (SELECT {col_names_values}) d)), ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, {epsg}), {epsilon})), ST_NPoints({geom}) as props
                    FROM {schema}.{table}
                    WHERE
                    {cql_filter} ST_INTERSECTS(st_buffer(st_transform('SRID=4326;POINT({lon} {lat})'::geometry, {native_epsg}), {tbuffer}), {geom})
                    ORDER BY st_distance(st_transform('SRID=4326;POINT({lon} {lat})'::geometry, {native_epsg}), {geom})
                """)
                query = sql.format(
                    geom=sqlbuilder.Identifier(geom_col),
                    epsg=sqlbuilder.Literal(epsg),
                    native_epsg=sqlbuilder.Literal(native_epsg),
                    col_names_values=properties_query,
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    tbuffer=sqlbuilder.Literal(tbuffer),
                    lat=sqlbuilder.Literal(lat),
                    lon=sqlbuilder.Literal(lon),
                    epsilon=sqlbuilder.Literal(epsilon),
                    cql_filter=cql_filter,
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
        
    def info_by_point_without_simplify(self, validation, layer, lat, lon, source_epsg, buffer, return_geom, lang, blank, getbuffer, cql_filter_read=None):
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

                native_epsg = 4326
                if layer.native_srs:
                    native_epsg = layer.native_srs.split(':')[1]
                    native_epsg = int(native_epsg)

                # Mantengo la lógica original pero con optimización mínima
                if cql_filter_read:
                    cql_filter = sqlbuilder.SQL('{cql_filter} AND').format(cql_filter=self._get_cql_permissions_filter(cql_filter_read))
                else:
                    cql_filter = sqlbuilder.SQL('')
                
                # Consulta optimizada: mantiene lógica espacial original pero usa índices eficientemente  
                sql = sqlbuilder.SQL("""
                    WITH 
                    query_point_4326 AS (
                        SELECT ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326) as geom_4326
                    ),
                    query_point_native AS (
                        SELECT ST_Transform(geom_4326, {native_epsg}) as geom_native
                        FROM query_point_4326
                    ),
                    query_buffer_4326 AS (
                        SELECT ST_Buffer(geom_4326::geography, {buffer})::geometry as buffer_geom_4326
                        FROM query_point_4326
                    ),
                    query_buffer_native AS (
                        SELECT ST_Transform(buffer_geom_4326, {native_epsg}) as buffer_geom_native
                        FROM query_buffer_4326
                    ),
                    bbox_candidates AS (
                        SELECT {geom} as geom_original, 
                               {col_names_values}
                        FROM {schema}.{table}, query_buffer_native
                        WHERE {cql_filter} query_buffer_native.buffer_geom_native && {geom}
                    ),
                    filtered_features AS (
                        SELECT geom_original,
                               ST_Transform(geom_original, 4326) as geom_4326_transformed,
                               {col_names_values}
                        FROM bbox_candidates, query_buffer_native
                        WHERE ST_Intersects(query_buffer_native.buffer_geom_native, bbox_candidates.geom_original)
                    )
                    SELECT ST_AsGeoJSON(geom_4326_transformed), 
                           row_to_json((SELECT d FROM (SELECT {col_names_values}) d)),
                           ST_AsGeoJSON(geom_4326_transformed),
                           ST_NPoints(geom_original) as numpoints
                    FROM filtered_features, query_point_native
                    ORDER BY ST_Distance(query_point_native.geom_native, filtered_features.geom_original)
                """)
                query = sql.format(
                    geom=sqlbuilder.Identifier(geom_col),
                    native_epsg=sqlbuilder.Literal(native_epsg),
                    col_names_values=properties_query,
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    buffer=sqlbuilder.Literal(buffer),
                    lat=sqlbuilder.Literal(lat),
                    lon=sqlbuilder.Literal(lon),
                    cql_filter=cql_filter
                )
                
                con.cursor.execute(query)
                from gvsigol_plugin_featureapi.serializers import LayerResourceSerializer

                feat_list = []
                for feat in con.cursor.fetchall():
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


    def get_epsilon(self, con, geom_col, epsg, native_epsg, table, schema, buffer, lon, lat):
        '''
        Epsilon es un número que sirve para la simplificación de polígonos y tiene relación con el número de puntos a simplificar en una curva
        por la distancia de los puntos a sus extremos.  Como las geometrías están en 4326 epsilon está en grados. Cuanto más grande es epsilon menos
        se simplifica. Lo calculamos de forma aproximada a partir del perímetro del polígono. Si aumentamos div se simplifica más y si lo disminuimos
        se simplifica menos.

        Esto se usa desde la app móvil para dibujar poligonos seleccionados porque si metemos muchos vértices petamos la app. 
        '''
        div = 10000
        sql = sqlbuilder.SQL("SELECT ST_Perimeter(ST_Transform({geom}, {epsg})) FROM {schema}.{table} WHERE ST_INTERSECTS(st_buffer(st_transform('SRID=4326;POINT({lon} {lat})'::geometry, {native_epsg}), {buffer}), {geom}) ORDER BY st_distance(st_transform('SRID=4326;POINT({lon} {lat})'::geometry, {native_epsg}), {geom})")
        query = sql.format(
            geom=sqlbuilder.Identifier(geom_col),
            epsg=sqlbuilder.Literal(epsg),
            native_epsg=sqlbuilder.Literal(native_epsg),
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

    def transform_lonlat_to_epsg(self, con, target_epsg, lon, lat):
        """
        Transforma coordenadas (lon, lat) desde EPSG:4326 al sistema de referencia target_epsg.

        Args:
            con: conexión psycopg2 a la base de datos.
            target_epsg: EPSG de destino (int).
            lon: longitud (float).
            lat: latitud (float).

        Returns:
            (x, y): coordenadas transformadas como tuple de float.
        """
        sql = sqlbuilder.SQL("""
            SELECT ST_X(transf_geom), ST_Y(transf_geom)
            FROM (
                SELECT ST_Transform(
                    ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326),
                    {target_epsg}
                ) AS transf_geom
            ) AS sub
        """).format(
            lon=sqlbuilder.Literal(lon),
            lat=sqlbuilder.Literal(lat),
            target_epsg=sqlbuilder.Literal(target_epsg)
        )

        con.cursor.execute(sql)
        for feat in con.cursor.fetchall():
            return feat
        
    def get_transformed_buffer_distance(self, con, source_epsg, target_epsg, buffer, lon, lat):
        query_point = [lon, lat] # 0.39059, 39.48329 x, y
        (x1, y1) = query_point
        x2 = x1 + buffer
        y2 = y1

        sql = sqlbuilder.SQL("SELECT ST_Length(ST_Transform(ST_GeomFromText('LINESTRING({x1} {y1},{x2} {y2})',{source_epsg}), {target_epsg}))")

        query = sql.format(
            x1=sqlbuilder.Literal(x1),
            y1=sqlbuilder.Literal(y1),
            x2=sqlbuilder.Literal(x2),
            y2=sqlbuilder.Literal(y2),
            source_epsg=sqlbuilder.Literal(source_epsg),
            target_epsg=sqlbuilder.Literal(target_epsg),
        )
        con.cursor.execute(query)
        for feat in con.cursor.fetchall():
            return feat[0]


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
    
    def _get_sql_columns_for_get_operation(self, pk_col, col_names_query, geom_col, target_epsg_code):
        sql = """
            {pk_col} pk,
            ST_AsGeoJSON(ST_Transform({geom}, {epsg})) geom, 
            row_to_json((SELECT d FROM (SELECT {col_names_query}) d)) props,
            ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, {epsg}),
                ST_Perimeter(ST_Transform({geom}, 4326)) / 10000)) simplegeom,
            ST_NPoints({geom}) numpoints
            """
        return sqlbuilder.SQL(sql).format(
            pk_col = sqlbuilder.Identifier(pk_col),
            col_names_query=col_names_query,
            geom=sqlbuilder.Identifier(geom_col),
            epsg=sqlbuilder.Literal(target_epsg_code)
        )

    def _get_sql_columns_for_sqlreturning(self, pk_col, col_names_query_with_id, geom_col, target_epsg_code, use_versions=False, col_names_query=None):
        if use_versions:
            sql = """
                {sql_get_columns},
                {geom} wkbgeom,
                row_to_json((SELECT d FROM (SELECT {col_names}) d)) props,
                {feat_version_gvol} feat_version,
                {feat_date_gvol} feat_date
                """
            return sqlbuilder.SQL(sql).format(
                sql_get_columns=self._get_sql_columns_for_get_operation(pk_col, col_names_query_with_id, geom_col, target_epsg_code),
                col_names=col_names_query,
                geom=sqlbuilder.Identifier(geom_col),
                feat_version_gvol=sqlbuilder.Identifier(settings.VERSION_FIELD),
                feat_date_gvol=sqlbuilder.Identifier(settings.DATE_FIELD),
            )
        else:
            return self._get_sql_columns_for_get_operation(pk_col, col_names_query_with_id, geom_col, target_epsg_code)

    def _process_query_result_for_get_operation(self, rows, epsg):
        if(rows is not None and len(rows) > 0):
            feat = rows[0]

            geometry = 'null'
            simplegeom = 'null'
            if feat[1] is not None:
                geometry = json.loads(feat[1])
                if 'crs' not in geometry:
                    geometry['crs'] = json.loads('{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:' + str(epsg) + '\"}}')

                if feat[3] is not None:
                    simplegeom = json.loads(feat[3])
                    if 'crs' not in simplegeom:
                        simplegeom['crs'] = json.loads('{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:' + str(epsg) + '\"}}')

            return {
                "type":"Feature",
                "geometry" : geometry,
                "properties" : feat[2],
                "simplegeom" : simplegeom,
                "numpoints" : feat[4]
            }

    def get(self, validation, lyr_id, feat_id, epsg):
        layer = Layer.objects.get(id = int(lyr_id))
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose
                table_info = con.get_table_info(table, schema=schema)
                try:
                    pk_field = util.get_default_pk_name(table_info)
                except:
                    raise HttpException(404, "Feature NOT found. Layer has no primary key")
                
                #Se considera que las capas tienen una sola clave primaria
                where = sqlbuilder.SQL("WHERE {pk_col} = {feat_id}").format(
                            pk_col = sqlbuilder.Identifier(pk_field),
                            feat_id=sqlbuilder.Literal(feat_id)
                )
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties_query = self._get_properties_names(con, schema, table, exclude_cols=geom_cols, fields=table_info.get_columns())
                geom_col = geom_cols[0]
                #De este serializador no ha modelo. Hay que hacerlo por consulta
                sql = sqlbuilder.SQL("SELECT {select_cols} FROM {schema}.{table} {where}")
                query = sql.format(
                    select_cols = self._get_sql_columns_for_get_operation(pk_field, properties_query, geom_col, epsg),
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    where=where
                )
                con.cursor.execute(query)
                rows = con.cursor.fetchall()
                if len(rows) > 0:
                    return self._process_query_result_for_get_operation(rows, epsg)
                raise HttpException(404, "Feature NOT found")
        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Features cannot be queried. Unexpected error: " + format(e))
        
    def list(self, validation, lyr_id, pagination, epsg, date, strict_search, onlyprops = False, text = None, filter = None, cql_filter_read=None):
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            raise HttpException(400, "La capa no es del tipo correcto. Debería ser una capa PostGIS")
        con = None
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose
                where_components = []
                where_count_components = []
                if cql_filter_read:
                    where_components.append(self._get_cql_permissions_filter(cql_filter_read))
                    where_count_components.append(self._get_cql_permissions_filter(cql_filter_read))
                if(date is not None):
                    #Es importante +00 para que considere que la fecha de entrada es UTC
                    date_val =  str(date) + "+00"
                    """
                    where = sqlbuilder.SQL("WHERE {date_field} >={date_val}").format(
                               date_field=sqlbuilder.Identifier(settings.DATE_FIELD),
                               date_val=sqlbuilder.Literal(date_val)
                    )
                    """
                    where_components.append(sqlbuilder.SQL("({date_field} >= {date_val})").format(
                               date_field=sqlbuilder.Identifier(settings.DATE_FIELD),
                               date_val=sqlbuilder.Literal(date_val))
                    )
                    where_count_components.append(sqlbuilder.SQL("({date_field} >= {date_val})").format(
                               date_field=sqlbuilder.Identifier(settings.DATE_FIELD),
                               date_val=sqlbuilder.Literal(date_val))
                    )

                max_feat, page = pagination.get_pagination_params()
                offset = max_feat * page
                if pagination.page < 0:
                    raise HttpException(404, "Page NOT found")
                limit_offset = sqlbuilder.SQL("LIMIT {max_feat} OFFSET {offset}").format(
                            max_feat=sqlbuilder.Literal(max_feat),
                            offset=sqlbuilder.Literal(offset))
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties = self._get_properties_names(con, schema, table, exclude_cols=geom_cols)
                geom_col = geom_cols[0]

                if filter is not None:
                    where_components.append(self._get_filter_where(filter))
                    where_count_components.append(self._get_filter_where(filter))
                if text is not None: # text search must be the last one in the where parts because it sometimes adds an ORDER BY clause
                    excluded = [geom_cols[0], 'modified_by', 'feat_date_gvol', 'feat_version_gvol', 'last_modification']
                    if strict_search == True:
                        where_components.append(self._get_strict_search_where(con, schema, table, text, exclude_cols=excluded))
                        where_count_components.append(self._get_strict_search_where(con, schema, table, text, exclude_cols=excluded))
                    else:
                        if self._exists_trigram_extension(con):
                            where_components.append(self._get_search_where_trigram(con, True, schema, table, text, exclude_cols=excluded))
                            where_count_components.append(self._get_search_where_trigram(con, False, schema, table, text, exclude_cols=excluded))
                            self._set_limit_trigram(con)
                        else:
                            where_components.append(self._get_search_where_tsvector(con, schema, table, text, exclude_cols=excluded))
                            where_count_components.append(self._get_search_where_tsvector(con, schema, table, text, exclude_cols=excluded))

                if len(where_count_components)>0:
                    sqlCount = sqlbuilder.SQL("SELECT count(*) FROM {schema}.{table} WHERE {where}")
                    queryCount = sqlCount.format(
                        schema=sqlbuilder.Identifier(schema),
                        table=sqlbuilder.Identifier(table),
                        where=sqlbuilder.SQL(" AND ").join(where_count_components),
                    )
                    con.cursor.execute(queryCount)
                    for r in con.cursor.fetchall():
                        num_entries = r[0]
                        break
                else:
                    num_entries = util.count(con, schema, table)
                if pagination.page > math.floor(num_entries/float(pagination.max_)):
                    raise HttpException(404, "Page NOT found")

                if len(where_components)>0:
                    where = sqlbuilder.SQL(" WHERE {conditions}").format(conditions=sqlbuilder.SQL(" AND ").join(where_components))
                else:
                    where = sqlbuilder.SQL('')
                if onlyprops == False:
                    sql = sqlbuilder.SQL("SELECT ST_AsGeoJSON(ST_Transform({geom}, {epsg})), row_to_json((SELECT d FROM (SELECT {properties}) d)) as props FROM {schema}.{table} {where} {limit_offset}")
                else:
                    sql = sqlbuilder.SQL("SELECT row_to_json((SELECT d FROM (SELECT {properties}) d)) as props, ST_AsGeoJSON(ST_Centroid({geom})) FROM {schema}.{table} {where} {limit_offset}")
                
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
            logger.exception("Error processing query")
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
            

    def list_by_extent(self, validation, lyr_id, epsg, minlat, minlon, maxlat, maxlon, zip, resources, max_feat, page, pagination):
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            raise HttpException(400, "La capa no es del tipo correcto. Debería ser una capa PostGIS")
        con = None
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con:
                idfield = util.get_layer_pk_name(con, schema, table)

                if max_feat or page:
                    if not max_feat:
                        max_feat = settings.NUM_MAX_FEAT
                    if not page:
                        page = 0

                    pagination.page = page
                    pagination.max_ = max_feat

                    num_entries = util.count(con, schema, table)
                    offset = max_feat * page
                    if(page > math.floor(num_entries/float(max_feat)) or page < 0):
                        raise HttpException(404, "Page NOT found")
                    limit_offset = sqlbuilder.SQL('ORDER BY {id_field} LIMIT {max_feat} OFFSET {offset}').format(
                                max_feat=sqlbuilder.Literal(max_feat),
                                offset=sqlbuilder.Literal(offset),
                                id_field=sqlbuilder.Identifier(idfield))

                    links = [pagination.get_links(num_entries)]
                else:
                    limit_offset = sqlbuilder.SQL("")
                    links = []
                
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties = self._get_properties_names(con, schema, table, exclude_cols=geom_cols)
                geom_col = geom_cols[0]

                epsilon = "ST_Perimeter(ST_Transform({geom}, {epsg})) / 10000"
                params = "st_AsGeoJSON(st_transform({geom}, {epsg})), row_to_json((SELECT d FROM (SELECT {properties}) d)) as props, ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, {epsg}), " + epsilon + "  )), ST_NPoints({geom})"
                where = "ST_INTERSECTS('SRID={epsg};POLYGON(({minlon} {maxlat}, {maxlon} {maxlat}, {maxlon} {minlat}, {minlon} {minlat}, {minlon} {maxlat}))'::geometry, st_transform({geom}, {epsg}))"
                
                
                sql = "SELECT count(*) FROM {schema}.{table} WHERE " + where
                query = sqlbuilder.SQL(sql).format(
                    geom=sqlbuilder.Identifier(geom_col),
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    minlon=sqlbuilder.Literal(minlon),
                    maxlat=sqlbuilder.Literal(maxlat),
                    maxlon=sqlbuilder.Literal(maxlon),
                    minlat=sqlbuilder.Literal(minlat),
                    epsg=sqlbuilder.Literal(epsg),
                    properties=properties
                )

                con.cursor.execute(query)
                for feat in con.cursor.fetchall():
                    lendata = feat[0]
                
                sql = "SELECT " + params + " FROM {schema}.{table} WHERE " + where + ' {limit_offset}'
                query = sqlbuilder.SQL(sql).format(
                    geom=sqlbuilder.Identifier(geom_col),
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    minlon=sqlbuilder.Literal(minlon),
                    maxlat=sqlbuilder.Literal(maxlat),
                    maxlon=sqlbuilder.Literal(maxlon),
                    minlat=sqlbuilder.Literal(minlat),
                    epsg=sqlbuilder.Literal(epsg),
                    properties=properties,
                    limit_offset=limit_offset
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
                        "lendata": lendata,
                        "features" : feat_list,
                        "links": links
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
            table_info = con.get_table_info(table, schema=schema)
            use_versions = validation.check_version_and_date_columns(lyr_id, con, schema, table, table_info)
            try:
                pk_field = util.get_default_pk_name(table_info)
            except:
                raise HttpException(400, "Feature cannot be deleted. Tables without primary key are not supported")
            try:
                (_, _, geom_column, _, target_crs, _, _, _) = con.get_geometry_columns_info(table=table, schema=schema)[0]
            except:
                logger.exception("Error getting CRS")
                target_crs = None
            if use_versions and version:
                # set a transaction to lock the row and avoid to be
                # concurrently modified
                con.conn.set_session(autocommit=False)
                validation.check_feature_version_for_update(con, schema, table, pk_field, feat_id, version)            
            try:
                if use_versions:
                    exclude_cols = [ pk_field, geom_column, settings.VERSION_FIELD]
                    properties_query = self._get_properties_names(con, schema, table, exclude_cols=exclude_cols, fields=table_info.get_columns())
                        
                    returning_sql = """
                        RETURNING {pk_col} pk,
                        {geom} wkbgeom,
                        row_to_json((SELECT d FROM (SELECT {col_names}) d)) props,
                        ({feat_version_gvol} + 1) feat_version,
                        now() feat_date
                        """
                    returning_query = sqlbuilder.SQL(returning_sql).format(
                        pk_col = sqlbuilder.Identifier(pk_field),
                        col_names=properties_query,
                        geom=sqlbuilder.Identifier(geom_column),
                        feat_version_gvol=sqlbuilder.Identifier(settings.VERSION_FIELD),
                        feat_date_gvol=sqlbuilder.Identifier(settings.DATE_FIELD),
                    )
                else:
                    returning_sql = """
                        RETURNING {pk_col} pk
                        """
                    returning_query = sqlbuilder.SQL(returning_sql).format(
                        pk_col = sqlbuilder.Identifier(pk_field)
                    )
                sql = "DELETE FROM {schema}.{table} WHERE {idfield} = %s {returning_query}"
                query = sqlbuilder.SQL(sql).format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    idfield=sqlbuilder.Identifier(pk_field),
                    returning_query=returning_query
                    )
                con.cursor.execute(query, [feat_id])
                rows = con.cursor.fetchall()
                con.conn.commit()
                con.conn.set_session(autocommit=False)
                if len(rows) == 0:
                    raise HttpException(404, "Feature NOT found")
                if use_versions:
                    for r in rows:
                        util.save_feature_version(
                            lyr_id=lyr_id,
                            feat_id=r[0],
                            wkb_geom=r[1],
                            properties=r[2],
                            version=r[3],
                            date=r[4],
                            usr=validation.usr,
                            operation=3)
            except HttpException:
                raise
            except Exception as e:
                try:
                    con.conn.rollback()
                    con.conn.set_session(autocommit=False)
                except:
                    pass
                raise HttpException(400, "Feature cannot be deleted. Unexpected error: " + format(e))

    def update(self, validation, lyr_id, data, override, version_to_override, username):
        """
        Update and return a new Feature instance, given the validated data.
        """
        layer = Layer.objects.get(id=int(lyr_id))
        
        #Hay que hacer inserciones en tabla con Introspect porque de las capas no hay modelo
        i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
        with i as con: # connection will autoclose
            table_info = con.get_table_info(table, schema=schema)
            try:
                idfield = util.get_default_pk_name(table_info)
            except:
                raise HttpException(400, "Feature cannot be updaed in database. Tables without primary key are not supported")
            feat_id = data['properties'][idfield]
            
            data = self._process_link_fields(layer, data, feat_id)
            pk_is_serial = table_info.get_column_info(idfield).get('is_serial')
            if pk_is_serial:
                try:
                    del data[idfield]
                except KeyError:
                    pass

            use_versions = validation.check_version_and_date_columns(lyr_id, con, schema, table, table_info)
            if use_versions:
                # set a transaction to lock the row and avoid to be
                # concurrently modified
                con.conn.set_session(autocommit=False)
                version = data['properties'][settings.VERSION_FIELD]
                data['properties'][settings.DATE_FIELD] =  "now()"
                if override:
                    if version_to_override != -1:
                        validation.check_feature_version_for_update(con, schema, table, idfield, feat_id, version_to_override)
                else:
                    validation.check_feature_version_for_update(con, schema, table, idfield, feat_id, version)

            data = self._add_user_to_props(username, table, schema, con, data)

            return_crs = 4326
            geom = data.get('geometry')
            try:
                sql, values = self._get_sql_update(con, table, schema, data['properties'], feat_id, geom, table_info, idfield, return_crs, use_versions=use_versions)
                con.cursor.execute(sql, values)
                rows = con.cursor.fetchall()
                con.conn.commit()
                con.conn.set_session(autocommit=False)
                if use_versions:
                    try:
                        for r in rows:
                            util.save_feature_version(
                                lyr_id=lyr_id,
                                feat_id=r[0],
                                wkb_geom=r[5],
                                properties=r[6],
                                version=r[7],
                                date=r[8],
                                usr=validation.usr,
                                operation=2)
                    except:
                        raise HttpException(400, "Feature change cannot be inserted in database history. Unexpected error: " + format(e))
                try:
                    return self._process_query_result_for_get_operation(rows, return_crs)
                except Exception as e:
                    raise HttpException(400, "Error retrieving the updated feature. Error: " + format(e))
            except HttpException as e:
                raise
            except Exception as e:
                try:
                    con.conn.rollback()
                    con.conn.set_session(autocommit=False)
                except:
                    pass
                raise HttpException(400, "Feature cannot be updated in database. Unexpected error: " + format(e))
        
    def create(self, validation, lyr_id, data, username):
        """
        Create and return a new Feature instance, given the validated data.
        """
        
        layer = Layer.objects.get(id=int(lyr_id))
        
        # Como no tenemos feat_id aún pasamos None
        data = self._process_link_fields(layer, data, feat_id=None)
        
        i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
        with i as con: # connection will autoclose
            table_info = con.get_table_info(table, schema=schema)
            try:
                idfield = util.get_default_pk_name(table_info)
            except:
                raise HttpException(400, "Feature cannot be inserted in database. Tables without primary key are not supported")
            pk_is_serial = table_info.get_column_info(idfield).get('is_serial')
            if pk_is_serial:
                try:
                    del data[idfield]
                except KeyError:
                    pass

            use_versions = validation.check_version_and_date_columns(lyr_id, con, schema, table, table_info)
            if use_versions:
                data['properties'][settings.VERSION_FIELD] = 1
                data['properties'][settings.DATE_FIELD] =  "now()"#time.strftime("%Y-%m-%d %H:%M:%S") #datetime.utcnow()
            
            data = self._add_user_to_props(username, table, schema, con, data)

            return_crs = 4326
            try:
                sql = self._get_sql_insert(table, schema, data['properties'], data['geometry'], table_info, idfield, pk_is_serial, return_crs, con, use_versions=use_versions)
            except Exception as e:
                if(hasattr(e, 'msg') and e.msg != ''):
                    raise e
                raise HttpException(400, "Feature cannot be inserted in database. Unexpected error: " + format(e))
            rows = None
            try:
                con.cursor.execute(sql)
                rows = con.cursor.fetchall()
                if use_versions:
                    try:
                        for r in rows:
                            util.save_feature_version(
                                lyr_id=lyr_id,
                                feat_id=r[0],
                                wkb_geom=r[5],
                                properties=r[6],
                                version=r[7],
                                date=r[8],
                                usr=validation.usr,
                                operation=1)
                    except Exception as e:
                        raise HttpException(400, "Feature cannot be inserted in database history. Unexpected error: " + format(e))
                # Después de insertar, actualizamos las URLs de los campos link con el feat_id real
                if rows and len(rows) > 0:
                    real_feat_id = rows[0][0]
                    data = self._process_link_fields(layer, data, real_feat_id)
                    if layer.conf:
                        try:
                            conf = ast.literal_eval(layer.conf)
                            if 'fields' in conf:
                                for field_conf in conf['fields']:
                                    if field_conf.get('gvsigol_type') == 'link':
                                        field_name = field_conf.get('name')
                                        if field_name in data['properties']:
                                            update_sql = sqlbuilder.SQL("UPDATE {schema}.{table} SET {field} = {value} WHERE {pk_field} = {feat_id}").format(
                                                schema=sqlbuilder.Identifier(schema),
                                                table=sqlbuilder.Identifier(table),
                                                field=sqlbuilder.Identifier(field_name),
                                                value=sqlbuilder.Literal(data['properties'][field_name]),
                                                pk_field=sqlbuilder.Identifier(idfield),
                                                feat_id=sqlbuilder.Literal(real_feat_id)
                                            )
                                            con.cursor.execute(update_sql)
                        except Exception as e:
                            logger.warning(f"Error actualizando URLs de campos link: {str(e)}")
                
                try:
                    return self._process_query_result_for_get_operation(rows, return_crs)
                except Exception as e:
                    raise HttpException(400, "Error retrieving the inserted feature. Error: " + format(e))
            except HttpException as e:
                raise
            except Exception as e:
                raise HttpException(400, "Feature change cannot be inserted in database. Unexpected error: " + format(e))
            

    def _add_user_to_props(self, username, table, schema, con, data):
        fields = con.get_fields(table, schema=schema)
        #Si los datos tienen el campo modified_by pero este no viene en los datos de entrada se asigna el usuario

        if 'properties' in data and 'modified_by' in fields:
            data['properties']['modified_by'] = username
        return data

    def _process_link_fields(self, layer, data, feat_id=None):
        """
        Procesa los campos de tipo "link" en la configuración de la capa.
        Si un campo de tipo link tiene un related_field con valor, construye
        la URL del endpoint de la API para acceder al archivo.
        """
        try:
            if not layer.conf:
                return data
            
            conf = ast.literal_eval(layer.conf)
            if 'fields' not in conf:
                return data

            link_fields = []
            for field_conf in conf['fields']:
                if field_conf.get('gvsigol_type') == 'link':
                    link_fields.append(field_conf)
            
            for link_field in link_fields:
                field_name = link_field.get('name')
                type_params = link_field.get('type_params', {})
                base_folder = type_params.get('base_folder', '')
                related_field = type_params.get('related_field', '')
                
                if not field_name or not base_folder or not related_field:
                    continue
                
                if related_field not in data.get('properties', {}):
                    continue
                
                related_value = data['properties'][related_field]
                
                if related_value and str(related_value).strip():
                    # Construir la URL para acceder al archivo a través del endpoint de la API
                    if feat_id is not None:
                        link_value = f"/api/v1/layers/{layer.id}/{feat_id}/linkurl/{field_name}/"
                    else:
                        # Para operaciones de creación, usar placeholder que se reemplazará después
                        link_value = f"/api/v1/layers/{layer.id}/{{feat_id}}/linkurl/{field_name}/"
                    data['properties'][field_name] = link_value
                else:
                    data['properties'][field_name] = ""
        
        except Exception as e:
            logger.warning(f"Error procesando campos link: {str(e)}")
        
        return data
        


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
        logger.debug('CHECK_GEOM: ' + query.as_string(con.cursor))
        con.cursor.execute(query)
        rows = con.cursor.fetchone()
        if rows[0] == False:
            raise HttpException(400, "Geometry malformed")

    def _get_properties_names(self, introspect, schema, tablename, exclude_cols=[], fields=None):
        if fields is None:
            fields = introspect.get_fields(tablename, schema=schema)
        properties = [ f for f in fields if f not in exclude_cols]
        colnames = [ sqlbuilder.Identifier(c) for c in properties ]
        return sqlbuilder.SQL(", ").join(colnames)

    def _get_strict_search_where(self, introspect, schema, tablename, text, exclude_cols=[]):
        #fields = introspect.get_fields_by_datatype('character varying', tablename, schema=schema)
        fields = introspect.get_fields(tablename, schema=schema)
        colnames = [ f for f in fields if f not in exclude_cols]
        
        text_sql=sqlbuilder.Literal("%" + text + "%")
        where_parts = [
            sqlbuilder.SQL('(lower(unaccent(CAST({column} AS VARCHAR))) like lower(unaccent({text})))').format(
                    column=sqlbuilder.Identifier(column),
                    text=text_sql
                )
                for column in colnames
        ]
        return sqlbuilder.SQL("({condition})").format(condition=sqlbuilder.SQL(" OR ").join(where_parts))

    def _get_cql_permissions_filter(self, cql_filter):
        """
        Limits the rows available for the user according to the geoserver-acl config
        """
        return sqlbuilder.SQL(" ( {cql_filter} )").format(cql_filter=sqlbuilder.SQL(cql_filter))

    def _get_filter_where(self, filter):
        filter_queries = filter['filterQueries']
        filter_operator = filter.get('filterOperator', 'AND').strip()
        if filter_operator in ['AND', 'OR']:
            query_parts = []
            for q in filter_queries:
                if q['type'] == 'query':
                    operator = q['operator'].strip()
                    if operator == 'IN':
                        query = sqlbuilder.SQL("{column} IN ({values})").format(
                            column=sqlbuilder.Identifier(q['field']),
                            value=sqlbuilder.SQL(str(q['value']))
                            )
                    elif operator in ['IS NULL', 'IS NOT NULL']:
                        query = sqlbuilder.SQL("{column} {operator}").format(
                            column=sqlbuilder.Identifier(q['field']),
                            operator=sqlbuilder.SQL(operator)
                            )
                    elif operator in ['=', '<>', 'LIKE', 'ILIKE', '<', '>', '<=', '>=', '']:
                        query = sqlbuilder.SQL("{column} {operator} {value}").format(
                            column=sqlbuilder.Identifier(q['field']),
                            operator=sqlbuilder.SQL(operator),
                            value=sqlbuilder.Literal(str(q['value']))
                            )
                    else:
                        raise HttpException(400, f"Invalid operator: {operator}")
                    if q.get('notop'):
                        query = sqlbuilder.SQL("(NOT {query})").format(query=query)
                    else:
                        query = sqlbuilder.SQL("({query})").format(query=query)
                    query_parts.append(query)
                elif q['type'] == 'qGroup':
                    queries = q['querys']
                    query_group_parts = []
                    qGroup_operator = q.get('op', 'AND').strip()
                    if qGroup_operator in ['AND', 'OR']:
                        for gq in queries:
                            operator = gq['operator'].strip()
                            if operator == 'IN':
                                query = sqlbuilder.SQL("{column} IN ({values})").format(
                                    column=sqlbuilder.Identifier(gq['field']),
                                    value=sqlbuilder.SQL(str(gq['value']))
                                    )
                            elif operator in ['IS NULL', 'IS NOT NULL']:
                                query = sqlbuilder.SQL("{column} {operator}").format(
                                    column=sqlbuilder.Identifier(gq['field']),
                                    operator=sqlbuilder.SQL(operator)
                                    )
                            elif operator in ['=', '<>', 'LIKE', 'ILIKE', '<', '>', '<=', '>=', '']:
                                query = sqlbuilder.SQL("{column} {operator} {value}").format(
                                    column=sqlbuilder.Identifier(gq['field']),
                                    operator=sqlbuilder.SQL(operator),
                                    value=sqlbuilder.Literal(str(gq['value']))
                                    )
                            else:
                                raise HttpException(400, f"Invalid operator: {operator}")
                            if gq.get('notop'):
                                query = sqlbuilder.SQL("(NOT {query})").format(query=query)
                            else:
                                query = sqlbuilder.SQL("({query})").format(query=query)
                            query_group_parts.append(query)
                        query = sqlbuilder.SQL(f" {qGroup_operator} ").join(query_group_parts)
                        query_parts.append(query)
            if len(query_parts)>0:
                conditions = sqlbuilder.SQL(f" {filter_operator} ").join(query_parts)
                return sqlbuilder.SQL("({conditions})").format(
                    conditions=conditions
                    )
        return sqlbuilder.SQL('(1 = 1)')
  
    def _get_search_where_tsvector(self, introspect, schema, tablename, text, exclude_cols=[]):
        fields = introspect.get_fields_by_datatype('character varying', tablename, schema=schema)
        colnames = [ f for f in fields if f not in exclude_cols]
        where_parts = [
            sqlbuilder.SQL("to_tsvector({languaje}, coalesce({column}, '')::varchar)").format(
                language=sqlbuilder.Literal("spanish"),
                column=column)
                for column in colnames
        ]
        return sqlbuilder.SQL("({condition}) @@ plainto_tsquery({language}, {text})").format(condition=sqlbuilder.SQL(" || ").join(where_parts),
                                                                                               language=sqlbuilder.Literal("spanish"),
                                                                                               text=sqlbuilder.Literal(text))

    def _set_limit_trigram(self, con):
        sql = "SELECT set_limit(0.17)"
        query = sqlbuilder.SQL(sql)
        con.cursor.execute(query)


    def _get_search_where_trigram(self, introspect, order, schema, tablename, text, exclude_cols=[]):
        fields = introspect.get_fields_by_datatype('character varying', tablename, schema=schema)
        colnames = [ f for f in fields if f not in exclude_cols]

        where_parts = [ sqlbuilder.SQL("{column} % unaccent({text})").format(column=sqlbuilder.Identifier(column), text=sqlbuilder.Literal(text))
                    for column in colnames]
        where = sqlbuilder.SQL("({condition})").format(condition=sqlbuilder.SQL(" OR ").join(where_parts))
        if order == True:
            order_by_parts = [sqlbuilder.SQL(" SIMILARITY( unaccent({column}), unaccent({text}))").format(column=sqlbuilder.Identifier(column),
                                                                                                          text=sqlbuilder.Literal(text))
                                                                                                          for column in colnames]
            order_by = sqlbuilder.SQL(" ORDER BY (SELECT max(x) FROM unnest(ARRAY[{cols}]) as x) DESC").format(cols=sqlbuilder.SQL(" , ").join(order_by_parts))
            where = where + order_by
        return where

    def _exists_trigram_extension(self, con):
        sql = "SELECT count(*) from pg_extension where extname = 'pg_trgm'"
        query = sqlbuilder.SQL(sql)
        con.cursor.execute(query)
        row = con.cursor.fetchone()
        if row[0] <= 0:
            return False
        else:
            return True

    def _get_sql_insert(self, table, schema, props, geom, table_info, pk_field, pk_is_serial, return_crs, con, use_versions):
        #TODO:quitar para V2
        #El CRS de origen si no viene se presupone en 4326. El de destino se lee de la capa
        #Ojo! esto es un problema pq se acostumbran a no meter CRS y luego meten coordenadas en otro sistema y ya está liada

        try:
            (_, _, geom_column, _, target_crs, _, _, _) = con.get_geometry_columns_info(table=table, schema=schema)[0]
        except:
            logger.exception("Error getting CRS")
            target_crs = None
        if "crs" not in geom: 
            geom['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")
        self._check_geom(geom, con)
        
        properties_query_with_id = self._get_properties_names(con, schema, table, exclude_cols=[geom_column], fields=table_info.get_columns())
        exclude_cols = [ pk_field, geom_column, settings.VERSION_FIELD]
        properties_query = self._get_properties_names(con, schema, table, exclude_cols=exclude_cols, fields=table_info.get_columns())
        
        returning_sql = sqlbuilder.SQL(
                "RETURNING {get_op_cols}"
            ).format(
                get_op_cols=self._get_sql_columns_for_sqlreturning(pk_field, properties_query_with_id, geom_column, return_crs, use_versions=use_versions, col_names_query=properties_query)
            )
        if pk_is_serial:
            colnames = []
            colvalues = []
        else:
            colnames = [sqlbuilder.Identifier(pk_field)]
            colvalues = [sqlbuilder.SQL(
                    "SELECT COALESCE(MAX({pk_field}), 0) + 1 FROM {schema}.{table}"
                ).format(
                    idfield=sqlbuilder.Identifier(pk_field),
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table)
                )
            ]
        colnames.append(sqlbuilder.Identifier(geom_column))
        colvalues.append(sqlbuilder.SQL("ST_TRANSFORM(ST_GeomFromGeoJSON({geojson}),{crs})").format(
                    geojson=sqlbuilder.Literal(json.dumps(geom)),
                    crs=sqlbuilder.Literal(target_crs)
                    ))
        for i in list(props.keys()):
            colnames.append(sqlbuilder.Identifier(i))
            colvalues.append(sqlbuilder.Literal(props[i]))

        sql = "INSERT INTO {schema}.{table} ({colnames}) VALUES ({colvalues}) {returning_sql}"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            colnames=sqlbuilder.SQL(", ").join(colnames),
            colvalues=sqlbuilder.SQL(", ").join(colvalues),
            pk_field=sqlbuilder.Identifier(pk_field),
            returning_sql = returning_sql
            )
        return query

    def _get_sql_update(self, con, table, schema, props, id_feat, geom, table_info, pk_field, return_crs, use_versions):
        try:
            (_, _, geom_column, _, target_crs, _, _, _) = con.get_geometry_columns_info(table=table, schema=schema)[0]
        except:
            logger.exception("Error getting CRS")
            target_crs = None
        if "crs" not in geom:
            #El CRS de origen si no viene se presupone en 4326. El de destino se lee de la capa
            geom['crs'] = json.loads("{\"type\":\"name\",\"properties\":{\"name\":\"EPSG:4326\"}}")

        self._check_geom(geom, con)
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
            
        value = sqlbuilder.SQL("ST_TRANSFORM(ST_GeomFromGeoJSON({geojson}),{crs})").format(
            geojson=sqlbuilder.Literal(json.dumps(geom)),
            crs=sqlbuilder.Literal(target_crs)
            )
        col_values.append(sqlbuilder.SQL("{field} = {value}").format(
            field=sqlbuilder.Identifier(geom_column),
            value=value))
        values.append(id_feat)

        properties_query_with_id = self._get_properties_names(con, schema, table, exclude_cols=[geom_column], fields=table_info.get_columns())
        exclude_cols = [ pk_field, geom_column, settings.VERSION_FIELD]
        properties_query = self._get_properties_names(con, schema, table, exclude_cols=exclude_cols, fields=table_info.get_columns())
        returning_sql = sqlbuilder.SQL(
            "RETURNING {get_op_cols}"
        ).format(
            get_op_cols=self._get_sql_columns_for_sqlreturning(pk_field, properties_query_with_id, geom_column, return_crs, use_versions=use_versions, col_names_query=properties_query)
        )

        sql = "UPDATE {schema}.{table} SET {col_values} WHERE {idfield} = %s  {returning_sql}"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            col_values=sqlbuilder.SQL(", ").join(col_values),
            idfield=sqlbuilder.Identifier(pk_field),
            returning_sql=returning_sql
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
    external_tilematrix = serializers.SerializerMethodField('get_external_tilematrix_')
    workspace = serializers.SerializerMethodField('get_layer_workspace_')
    writable = serializers.SerializerMethodField('is_writable')
    service_version = serializers.SerializerMethodField('get_external_service_version')
    native_srs = serializers.SerializerMethodField('get_native_srs')

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

    def get_external_tilematrix_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['tilematrix']
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

    def get_native_srs(self, obj):
        try:
            return obj.native_srs
        except Exception:
            pass

        
    class Meta:
        model = Layer
        fields = ['id', 'name', 'title', 'abstract', 'type', 'visible', 'queryable', 'cached', 'single_image', 'created_by', 
                  'thumbnail', 'layer_group_id', 'icon', 'last_change', 'latlong_extent', 'native_extent', 'external_layers', 
                  'external_url', 'external_tilematrixset', 'external_tilematrix', 'workspace', 'image_type', 'writable', 'external', 'service_version', 
                  'native_srs', 'time_enabled', 'allow_download']


class LayerTimeSerializer(serializers.ModelSerializer):
        
    class Meta:
        model = Layer
        fields = ['id', 'name', 'time_enabled', 'time_enabled_endfield', 'time_enabled_field', 'time_default_value', 'time_default_value_mode', 
                  'time_presentation', 'time_resolution_day', 'time_resolution_hour', 'time_resolution_minute', 'time_resolution_month', 'time_resolution_second',
                  'time_resolution_week', 'time_resolution_year', 'time_resolution']  



class LayerCreateSerializer(serializers.Serializer):
    geom_type = serializers.CharField(max_length=25, min_length=5, default='Point')
    datastore = serializers.IntegerField(default=10)
    name = serializers.CharField(max_length=25, min_length=3, default='testlayer')
    title = serializers.CharField(max_length=25, min_length=3, default='Test layer')
    srs = serializers.CharField(max_length=25, min_length=5, default='EPSG:4326')
    layer_group = serializers.IntegerField(default=5)
    fields = serializers.CharField(min_length=2, default='[{\"id\":\"klt01kb332\",\"name\":\"fieldName\",\"type\":\"character_varying\",\"calculation\":\"\",\"calculationLabel\":\"\"}]')
    md_abstract = serializers.CharField(max_length=2048, min_length=5, default='')