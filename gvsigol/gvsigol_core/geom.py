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
