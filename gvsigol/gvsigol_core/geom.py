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
"""

"""
Defines the geometry types for gvSIG Online, based on the WKT representation
defined by the OGC Simple Feature specification. 

@author: Cesar Martinez Izquierdo, SCOLAB
'''

from gvsigol import settings
from django.contrib.gis.geos import GEOSGeometry
from gvsigol_core.settings import NEU_AXIS_ORDER_SRSS, DJANGO_BROKEN_GEOSGEOMETRY
import os

POINT = "Point"
POINTM = "Point M"
POINTZ = "Point Z"
POINTZM = "Point ZM"

MULTIPOINT = "MultiPoint"
MULTIPOINTM = "MultiPoint M"
MULTIPOINTZ = "MultiPoint Z"
MULTIPOINTZM = "MultiPoint ZM"

LINESTRING = "LineString"
LINESTRINGM = "LineString M"
LINESTRINGZ = "LineString Z"
LINESTRINGZM = "LineString ZM"

MULTILINESTRING = "MultiLineString"
MULTILINESTRINGM = "MultiLineString M"
MULTILINESTRINGZ = "MultiLineString Z"
MULTILINESTRINGZM = "MultiLineString ZM"

POLYGON = "Polygon"
POLYGONM = "Polygon M"
POLYGONZ = "Polygon Z"
POLYGONZM = "Polygon ZM"

MULTIPOLYGON = "MultiPolygon"
MULTIPOLYGONM = "MultiPolygon M"
MULTIPOLYGONZ = "MultiPolygon Z"
MULTIPOLYGONZM = "MultiPolygon ZM"

RASTER = "raster"

SUPPORTED_GEOMS = (POINT, POINTZ, POINTM, POINTZM,
               MULTIPOINT, MULTIPOINTM, MULTIPOINTZ, MULTIPOINTZM,
               LINESTRING, LINESTRINGM, LINESTRINGZ, LINESTRINGZM,
               MULTILINESTRING, MULTILINESTRINGM, MULTILINESTRINGZ, MULTILINESTRINGZM,
               POLYGON, POLYGONM, POLYGONZ, POLYGONZM,
               MULTIPOLYGON, MULTIPOLYGONM, MULTIPOLYGONZ, MULTIPOLYGONZM,
               RASTER
    )

__JTS_GEOM_PACKAGE = 'com.vividsolutions.jts.geom.'

def isPoint(geom_type):
    return "Point" in geom_type

def isLine(geom_type):
    return "Line" in geom_type

def isPolygon(geom_type):
    return "Polygon" in geom_type

def isRaster(geom_type):
    return geom_type==RASTER

def toGeopaparazzi(geom_type):
    """
    Converts from gvSIG Online geometry definition to Geopaparazzi definition 
    """
    geopap_geom = geom_type.lower()
    if ' ' in geopap_geom:
        geopap_geom.replace(' ', '_xy')
    else:
        geopap_geom += '_xy'
    return geopap_geom

def fromGeopaparazzi(geom_type):
    """
    Converts from Geopaparazzi geometry definition to gvSIG Online definition.
    Returns None if the geom is not supported in gvSIG Online
    """
    for type in SUPPORTED_GEOMS:
        if toGeopaparazzi(type)==geom_type:
            return type

def validateGeomDef(geom_type):
    """
    Returns True if the provided geom_def is a supported geometry, false
    otherwise
    """
    if geom_type in SUPPORTED_GEOMS:
        return True
    return False

def fromJTS(geom_type):
    """
    Converts from JTS geometry definition to gvSIG Online definition.
    Returns None if the geom is not supported in gvSIG Online
    """
    if 'jts.geom' in geom_type:
        geom_type = geom_type.split('.')[-1]
        if validateGeomDef(geom_type):
            return geom_type


def toJTS(geom_type):
    return __JTS_GEOM_PACKAGE + geom_type.split(" ")[0]

def epsgToSrid(epsg_def):
    """
    Transforms "EPSG:code" to "code", returns None if the provided def
    does not start with "EPSG:" 
    """
    try:
        if 'EPSG:' == epsg_def[:5]:
            return int(epsg_def[5:])
    except:
        pass


def is_neu_axis_order(srid):
    if srid in NEU_AXIS_ORDER_SRSS:
        return True
    return False

def xor(a, b):
    return (a and not b) or (not a and b)

def transform_point_bak(x_or_lon, y_or_lat, source_crs, target_crs):
    """
    Experimental function to transform a point from source_crs to target_crs
    circunventing the django GEOSGeometry bug in versions < 4.2 with GDAL >= 3.x.

    Parameters:
    ------------
    lon: float
        longitude of the point
    lat: float
        latitude of the point
    source_crs: integer
        EPSG code of the source coordinate reference system
    target_crs: integer
        EPSG code of the target coordinate reference system
    Returns:
        GEOSGeometry object with the transformed point in target_crs
    """
    if DJANGO_BROKEN_GEOSGEOMETRY and \
        xor(is_neu_axis_order(source_crs), is_neu_axis_order(target_crs)):
            p = f'POINT({y_or_lat} {x_or_lon})' # usamos lat, lon; orden incorrecto en wkt para sortear error de django
    else:
        p = f'POINT({x_or_lon} {y_or_lat})' # usamos lon, lat; orden correcto en wkt 
    print(p)
    geos_geom = GEOSGeometry(p, srid=source_crs)
    transformed_geom = geos_geom.transform(target_crs, clone=True)
    return transformed_geom

def transform_point(x_or_lon, y_or_lat, source_crs, target_crs):
    """
    Experimental function to transform a point from source_crs to target_crs
    circunventing the django GEOSGeometry bug in versions < 4.2 with GDAL >= 3.x.

    Parameters:
    ------------
    lon: float
        longitude of the point
    lat: float
        latitude of the point
    source_crs: integer
        EPSG code of the source coordinate reference system
    target_crs: integer
        EPSG code of the target coordinate reference system
    Returns:
        GEOSGeometry object with the transformed point in target_crs
    """
    if DJANGO_BROKEN_GEOSGEOMETRY and \
        is_neu_axis_order(source_crs):
            print("source is neu")
            p = f'POINT({y_or_lat} {x_or_lon})' # usamos lat, lon; orden incorrecto en wkt para sortear error de django
    else:
        p = f'POINT({x_or_lon} {y_or_lat})' # usamos lon, lat; orden correcto en wkt 
    print(p)
    geos_geom = GEOSGeometry(p, srid=source_crs)
    print(geos_geom.wkt)
    print(geos_geom.x)
    print(geos_geom.y)
    print(geos_geom.geojson)
    transformed_geom = geos_geom.transform(target_crs, clone=True)
    if DJANGO_BROKEN_GEOSGEOMETRY and \
        is_neu_axis_order(target_crs):
        print("target is neu")
        #transformed_geom = GEOSGeometry(f'POINT({transformed_geom.y} {transformed_geom.x})', srid=target_crs)
        transformed_geom = GEOSGeometry(f'POINT({transformed_geom.x} {transformed_geom.y})', srid=target_crs)
    print(transformed_geom.wkt)
    print(transformed_geom.x)
    print(transformed_geom.y)
    print(transformed_geom.geojson)
    return transformed_geom