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
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
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


def _invert_geos_coords(geom):
    """
    Recibe una instancia de GEOSGeometry y devuelve otra con los ejes invertidos.
    """
    if geom.geom_type == 'Point':
        return Point(geom.y, geom.x, srid=geom.srid)

    elif geom.geom_type == 'LineString':
        return LineString([(y, x) for x, y in geom.coords], srid=geom.srid)

    elif geom.geom_type == 'Polygon':
        shell = [(y, x) for x, y in geom[0].coords]
        holes = [[(y, x) for x, y in ring.coords] for ring in geom[1:]]
        return Polygon(shell, *holes, srid=geom.srid)

    elif geom.geom_type == 'MultiPoint':
        return MultiPoint([Point(y, x) for x, y in geom.coords], srid=geom.srid)

    elif geom.geom_type == 'MultiLineString':
        return MultiLineString([LineString([(y, x) for x, y in line.coords]) for line in geom], srid=geom.srid)

    elif geom.geom_type == 'MultiPolygon':
        polygons = []
        for poly in geom:
            shell = [(y, x) for x, y in poly[0].coords]
            holes = [[(y, x) for x, y in ring.coords] for ring in poly[1:]]
            polygons.append(Polygon(shell, *holes, srid=geom.srid))
        return MultiPolygon(polygons, srid=geom.srid)

    else:
        raise TypeError(f"Tipo de geometría no soportado: {geom.geom_type}")

def _invert_wkt_coords(wkt, srid):
    """
    Recibe una instancia de GEOSGeometry y devuelve una GeosGeometry con los ejes invertidos.
    """
    geos_geom = GEOSGeometry(wkt, srid=srid)
    return _invert_geos_coords(geos_geom)

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
            p = f'POINT({y_or_lat} {x_or_lon})' # usamos lat, lon; orden incorrecto en wkt para sortear error de django
    else:
        p = f'POINT({x_or_lon} {y_or_lat})' # usamos lon, lat; orden correcto en wkt 
    geos_geom = GEOSGeometry(p, srid=source_crs)
    transformed_geom = geos_geom.transform(target_crs, clone=True)
    if DJANGO_BROKEN_GEOSGEOMETRY and \
        is_neu_axis_order(target_crs):
        transformed_geom = GeosPointWrapper(transformed_geom)
    return transformed_geom


def transform_wkt(wkt, source_crs, target_crs):
    """
    Experimental function to transform a wkt geometry from source_crs to target_crs
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
        GEOSGeometry-like object with the transformed point in target_crs.
        Only the following properties are supported:
        - x
        - y
        - wkt
        - geojson
        - coords
        - dims
        - geom_type
        - srid
        - empty
    """
    if DJANGO_BROKEN_GEOSGEOMETRY and \
        is_neu_axis_order(source_crs):
        geos_geom = _invert_wkt_coords(wkt, srid=source_crs)
    else:
        geos_geom = GEOSGeometry(wkt, srid=source_crs)
    transformed_geom = geos_geom.transform(target_crs, clone=True)
    if DJANGO_BROKEN_GEOSGEOMETRY and \
        is_neu_axis_order(target_crs):
        transformed_geom = GeosGeometryWrapper(transformed_geom)
    return transformed_geom

class GeosPointWrapper():
    def __init__(self, geos_geometry):
        self.geos_geometry = geos_geometry
        self.is_neu_axis_order = is_neu_axis_order(geos_geometry.srid)
        if not DJANGO_BROKEN_GEOSGEOMETRY:
            raise Exception("GeosGeometryWrapper shall only be used to fix broken Django/GDAL environments. Do not use it in other scenarios")
    
    @property
    def x(self):
        if self.is_neu_axis_order:
            return self.geos_geometry.y
        return self.geos_geometry.x
    
    @property
    def y(self):
        if self.is_neu_axis_order:
            return self.geos_geometry.x
        return self.geos_geometry.y
    
    @property
    def wkt(self):
        if self.is_neu_axis_order:
            return Point(self.geos_geometry.y, self.geos_geometry.x).wkt
        return self.geos_geometry.wkt
    
    @property
    def geojson(self):
        if self.is_neu_axis_order:
            return Point(self.geos_geometry.y, self.geos_geometry.x).geojson
        return self.geos_geometry.geojson

class GeosGeometryWrapper():
    def __init__(self, geos_geometry):
        self.geos_geometry = geos_geometry
        self.is_neu_axis_order = is_neu_axis_order(geos_geometry.srid)
        if not DJANGO_BROKEN_GEOSGEOMETRY:
            raise Exception("GeosGeometryWrapper shall only be used to fix broken Django/GDAL environments. Do not use it in other scenarios")
    
    @property
    def x(self):
        if self.dims > 0:
            raise Exception("x is only supported for Points")
        if self.is_neu_axis_order:
            return self.geos_geometry.y
        return self.geos_geometry.x
    
    @property
    def y(self):
        if self.dims > 0:
            raise Exception("x is only supported for Points")
        if self.is_neu_axis_order:
            return self.geos_geometry.x
        return self.geos_geometry.y
    
    @property
    def wkt(self):
        if self.is_neu_axis_order:
            return _invert_geos_coords(self.geos_geometry).wkt
        return self.geos_geometry.wkt
    
    @property
    def geojson(self):
        """
        print(f"geojson: {self.geos_geometry.geojson}")
        if self.is_neu_axis_order:
            print(f"inverted geojson: {_invert_geos_coords(self.geos_geometry).geojson}")
            return _invert_geos_coords(self.geos_geometry).geojson
        """
        #print(f"coords: {self.geos_geometry.coords}")
        return self.geos_geometry.geojson

    @property
    def srid(self):
        return self.geos_geometry.srid

    @property
    def dims(self):
        return self.geos_geometry.dims
    
    @property
    def geom_type(self):
        return self.geos_geometry.geom_type
    
    @property
    def empty(self):
        return self.geos_geometry.empty
    
    @property
    def coords(self):
        if self.is_neu_axis_order:
            return _invert_geos_coords(self.geos_geometry).coords
        return self.geos_geometry.coords
    