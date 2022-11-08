#!/usr/bin/python
# -*- coding: utf-8 -*-
#
from gvsigol.celery import app as celery_app
from gvsigol_services.models import LayerGroup, Layer, LayerResource
from gvsigol_plugin_baseapi.validation import HttpException
from gvsigol_services import utils as services_utils
from psycopg2 import sql as sqlbuilder
from gvsigol_plugin_projectapi import util
import sys
import json
from gvsigol_plugin_projectapi.export import VectorLayerExporter
from django.utils import timezone
from gvsigol_plugin_projectapi.models import FeatureProcessStatus

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

def pack_properties(lyr_id, epsg, page, entries_per_page, version):
    try:
        #return list_properties(lyr_id, epsg, page, entries_per_page, version)
        result = list_properties.apply_async(args=[lyr_id, epsg, page, entries_per_page, version])
        if(type(result.info) is str): 
            return result.info
        elif('code' in result.info):
            raise HttpException(result.info.code, result.info.error)
        else:
            return result.info
    except Exception as e:
        pass
        #raise RuntimeError 

def pack_geometries(lyr_id, epsg, minlat, minlon, maxlat, maxlon, zip, resources, version):
    try:
        #return list_by_extent(lyr_id, epsg, minlat, minlon, maxlat, maxlon, zip, resources, version)
        result = list_by_extent.apply_async(args=[lyr_id, epsg, minlat, minlon, maxlat, maxlon, zip, resources, version])
        if(type(result.info) is str): 
            return result.info
        elif('code' in result.info):
            raise HttpException(result.info.code, result.info.error)
        else:
            return result.info
    except Exception as e:
        pass
        #raise RuntimeError 

@celery_app.task(ignore_result=False)
def list_properties(lyr_id, epsg, page, entries_per_page, version):
        status = create_status(version, lyr_id, -90, -180, 90, 180)
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            error = {'code': 400, 'error': "La capa no es del tipo correcto. Debería ser una capa PostGIS"}
            finish_status(status, error, True)
            return error
        con = None  
        
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: 
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties = get_properties_names(con, schema, table, exclude_cols=geom_cols)
                idfield = util.get_layer_pk_name(con, schema, table)
                geom_col = geom_cols[0]

                limit = entries_per_page
                offset = page * entries_per_page
                pagination = ""
                if page > 0:
                    pagination = " LIMIT {limit} OFFSET {offset}"

                params = "row_to_json((SELECT d FROM (SELECT {properties}) d)) as props"
                sql = "SELECT " + params + " FROM {schema}.{table}" + pagination
                query = sqlbuilder.SQL(sql).format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    limit=sqlbuilder.Literal(limit),
                    offset=sqlbuilder.Literal(offset),
                    properties=properties,
                )

                con.cursor.execute(query)
                nbytes = 0
                feat_list = []

                for feat in con.cursor.fetchall():
                    element = {
                        "type":"Feature",
                        "properties" : feat[0],
                    }
                    nbytes += sys.getsizeof(feat[0])
                    nbytes += sys.getsizeof(element)

                    feat_list.append(element)


                result = splitArray(nbytes, feat_list)
                exp = VectorLayerExporter()
                result = exp.create_package_from_geojson(result, layer.datastore.workspace.name, layer.name, idfield, False, version)
                finish_status(status, str(result), False)
                return result
        except Exception as e:
            error = {'code': 400, 'error': "Features cannot be queried. Unexpected error: " + format(e)}
            finish_status(status, error, True)
            if isinstance(e, HttpException):
                raise e
            return error

            
@celery_app.task(ignore_result=False)
def list_by_extent(lyr_id, epsg, minlat, minlon, maxlat, maxlon, zip, resources, version):
        status = create_status(version, lyr_id, minlat, minlon, maxlat, maxlon)
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.type != 'v_PostGIS':
            error = {'code': 400, 'error': "La capa no es del tipo correcto. Debería ser una capa PostGIS"}
            finish_status(status, error, True)
            return error
        con = None
        
        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: 
                geom_cols = con.get_geometry_columns(table, schema=schema)
                properties = get_properties_names(con, schema, table, exclude_cols=geom_cols)
                idfield = util.get_layer_pk_name(con, schema, table)
                geom_col = geom_cols[0]

                time_field = layer.time_enabled_field if layer.time_enabled_field is not None else ''
                time_value = layer.time_default_value if layer.time_default_value is not None else ''
                nearest_value = get_nearest_temporal_value(con, layer, schema, table, time_field, time_value)
                temp_where = get_where_temporal_params(layer, time_value)
                

                epsilon = "ST_Perimeter(ST_Transform({geom}, 4326)) / 10000"
                params = "st_AsGeoJSON(st_transform({geom}, 4326)), row_to_json((SELECT d FROM (SELECT {properties}) d)) as props, ST_AsGeoJSON(ST_Simplify(ST_Transform({geom}, 4326), " + epsilon + "  )), ST_NPoints({geom})"
                where = "ST_INTERSECTS('SRID=4326;POLYGON(({minlon} {maxlat}, {maxlon} {maxlat}, {maxlon} {minlat}, {minlon} {minlat}, {minlon} {maxlat}))'::geometry, st_transform({geom}, 4326))"
                sql = "SELECT " + params + " FROM {schema}.{table} WHERE " + where + temp_where

                #print(">>>>>PARAMS SQL: " + str(geom_col) + " " + str(schema) + " " + str(table) + " " + str(minlon) + " " + str(time_field) + " " + str(time_value))


                query = sqlbuilder.SQL(sql).format(
                    geom=sqlbuilder.Identifier(geom_col),
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    minlon=sqlbuilder.Literal(minlon),
                    maxlat=sqlbuilder.Literal(maxlat),
                    maxlon=sqlbuilder.Literal(maxlon),
                    minlat=sqlbuilder.Literal(minlat),
                    time_field=sqlbuilder.Identifier(time_field),
                    time_value=sqlbuilder.Literal(time_value),
                    nearest_value=sqlbuilder.Literal(nearest_value),
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
                    result = splitArray(nbytes, feat_list)
                    exp = VectorLayerExporter()
                    result = exp.create_package_from_geojson(result, layer.datastore.workspace.name, layer.name, idfield, resources, version)
                    finish_status(status, str(result), False)
                    return result
        except Exception as e:
            error = {'code': 400, 'error': "Features cannot be queried. Unexpected error: " + format(e)}
            finish_status(status, error, True)
            if isinstance(e, HttpException):
                raise e
            return error


def get_where_temporal_params(layer, time_value):
    if not isinstance(layer, Layer):
        layer = Layer.objects.select_related('datastore').get(id=int(layer))
    
    if layer.time_enabled == True:
        if layer.time_presentation == 'CONTINUOUS_INTERVAL':
            if layer.time_default_value_mode == 'MAXIMUM':
                return " AND {time_field} = (SELECT MAX({time_field}) FROM {schema}.{table})"
            if layer.time_default_value_mode == 'MINIMUM':
                return " AND {time_field} = (SELECT MIN({time_field}) FROM {schema}.{table})"
            if layer.time_default_value_mode == 'FIXED' and time_value is not None:
                values = time_value.split('-')
                if len(values) >= 3:
                    return " AND {time_field} = {time_value}"
                if len(values) == 2 and int(values[0]) > 0 and int(values[0]) < 5000 and int(values[1]) >= 1 and int(values[1]) <= 12:
                    return " AND EXTRACT(YEAR FROM {time_field}) = " + values[0] + "::INTEGER AND EXTRACT(MONTH FROM {time_field}) = " + values[1] + "::INTEGER"
                if len(values) == 1 and int(values[0]) > 0 and int(values[0]) < 5000:
                    return " AND EXTRACT(YEAR FROM {time_field}) = " + values[0] + "::INTEGER"
            if layer.time_default_value_mode == 'NEAREST':
                return " AND {time_field} = {nearest_value}"
    return ''


def get_nearest_temporal_value(con, layer, schema, table, time_field, time_value):
    '''
    Obtiene el valor más cercano al de referencia en caso de que no haya en la tabla ningún valor exacto
    igual al de referencia
    '''

    if layer.time_enabled == True:
        if layer.time_presentation == 'CONTINUOUS_INTERVAL':
            if layer.time_default_value_mode == 'NEAREST':
                sql = "SELECT count(*) FROM {schema}.{table} WHERE {time_field} = {time_value}"
                query = sqlbuilder.SQL(sql).format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    time_field=sqlbuilder.Identifier(time_field),
                    time_value=sqlbuilder.Literal(time_value),
                )
                con.cursor.execute(query)
                result = con.cursor.fetchone()
                #No hay valores igual a time_value por lo que hay que calcular el más cercano
                if len(result) > 0 and result[0] == 0:
                    try:
                        values = time_value.split('-')
                        if len(values) >= 3:
                            #Para obtener el valor mas cercano se ordena por la diferencia con el valor de referencia en millis y se coge el que menos diferencia tiene
                            sql = "SELECT {time_field} FROM {schema}.{table} WHERE {time_field} IS NOT NULL ORDER BY abs(EXTRACT(EPOCH FROM {time_field}) - EXTRACT(EPOCH FROM timestamp {time_value})) LIMIT 1"
                            query = sqlbuilder.SQL(sql).format(
                                schema=sqlbuilder.Identifier(schema),
                                table=sqlbuilder.Identifier(table),
                                time_field=sqlbuilder.Identifier(time_field),
                                time_value=sqlbuilder.Literal(time_value),
                            )
                            con.cursor.execute(query)
                            result = con.cursor.fetchone()
                            if len(result) > 0:
                                return result[0]
                    except Exception:
                        pass #devuelve time_value
    return time_value


def get_properties_names(introspect, schema, tablename, exclude_cols=[]):
    fields = introspect.get_fields(tablename, schema=schema)
    properties = [ f for f in fields if f not in exclude_cols]
    colnames = [ sqlbuilder.Identifier(c) for c in properties ]
    return sqlbuilder.SQL(", ").join(colnames)


def splitArray(nbytes, feat_list):
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


def create_status(version, lyrid, minlat, minlon, maxlat, maxlon):
    status = FeatureProcessStatus()
    status.layer = lyrid
    status.uri = ''
    status.version = version
    status.active = True
    status.stop = False
    status.error = False
    status.extent_processed = str(minlat) + "," + str(minlon) + "," + str(maxlat) + "," + str(maxlon)
    status.start_time = timezone.now()
    status.save()
    return status     

def finish_status(status, uri, error):
    status.uri = uri
    status.active = False
    status.stop = False
    status.error = error
    status.end_time = timezone.now()
    status.save()
    return status 
