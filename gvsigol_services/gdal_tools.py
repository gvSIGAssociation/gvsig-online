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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from django.utils.translation import ugettext_lazy as _
import StringIO as io
import subprocess
import logging
import re
import os
from os import listdir
from os.path import isfile, join

OGR2OGR_PATH = '/usr/bin/ogr2ogr'
GDALINFO_PATH = '/usr/local/bin/gdalinfo'
GDALSRSINFO_PATH = '/usr/local/bin/gdalsrsinfo'

__BAND_PATTERN=re.compile("Band ([0-9]+).*")
__BAND_STATS_PATTERN=re.compile("  Minimum=([-+]?\d*\.\d+|\d+), Maximum=([-+]?\d*\.\d+|\d+), Mean=([-+]?\d*\.\d+|\d+), StdDev=([-+]?\d*\.\d+|\d+).*")
__BAND_NO_DATA_PATTERN=re.compile("  NoData Value=(.*)")

MODE_CREATE="CR"
MODE_APPEND="AP"
MODE_OVERWRITE="OW"

class GdalError(Exception):
    def __init__(self, code=-1, message=None):
        self.code = code
        self.message=message

def get_raster_stats(raster_path):
    """
    Gets the statistics of the raster using gdalinfo command.
    Returns an array of tuples, containing the min, max, mean and stdev values
    for each band.
    
    Usage:
    import gdal_tools
    stats = gdal_tools.get_raster_stats('path_to_my_raster')
    (band0_ min, band0_max, band0_mean, band0_stdev) = stats[0]
    (band1_ min, band1_max, band1_mean, band1_stdev) = stats[1]
    """
    
    files = []
    main_path = raster_path.replace("file://", "")
    result = []
    
    if os.path.isdir(main_path):
        files = [f for f in listdir(main_path) if isfile(join(main_path, f)) and str(f).endswith('.tif')]
    else:
        files.append(main_path)
    
    for file_path in files:
        stats_str = gdalinfo(join(main_path, file_path))
        buf = io.StringIO(stats_str)
        
        band_results = __process_band(buf)
        while band_results != None:
            result.append(band_results)
            band_results = __process_band(buf)
        buf.close()
    return result

def __process_band(buf):
    __find_band(buf)
    line = buf.readline()
    while line != "":
        m = __BAND_STATS_PATTERN.match(line)
        if m: # stats found
            return (float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))
        line = buf.readline()
    return None
    
def __find_band(buf):
    line = buf.readline()
    while line != "":
        m = __BAND_PATTERN.match(line)
        if m: # band found
            return
        line = buf.readline()
    

def gdalinfo(raster_path):
    """
    Returns the output of gdalinfo command on the provided raster.
    """
    args = [GDALINFO_PATH, "-stats", raster_path] 
    print " ".join(args)
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, bufsize=-1)
    output, err = p.communicate()
    rc = p.returncode
    if rc>0:
        msg = _("Error calculating raster stats. Gdalinfo error: {msg}").format(msg=err)
        logging.error(msg)
        raise GdalError(rc, msg)
    else:
        return output

def gdalsrsinfo(raster_path):
    """
    Returns the output of gdalinfo command on the provided raster.
    """
    args = [GDALSRSINFO_PATH, raster_path] 
    print " ".join(args)
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,stderr=subprocess.PIPE, bufsize=-1)
    output, err = p.communicate()
    rc = p.returncode
    if rc>0:
        msg = _("Error calculating raster stats. Gdalinfo error: {msg}").format(msg=err)
        logging.error(msg)
        raise GdalError(rc, msg)
    else:
        return output

def shp2postgis(shp_path, table_name, srs, host, port, dbname, schema, user, password, creation_mode=MODE_CREATE, encoding="autodetect"):
    conn_string = "PG:host='{host}' port='{port}' user='{user}' dbname='{dbname}' password='{password}'".format(host=host, port=port, user=user, dbname=dbname, password=password, schema=schema)
    args = [OGR2OGR_PATH, "-f", "PostgreSQL", "-nlt", "PROMOTE_TO_MULTI"]
    if creation_mode==MODE_APPEND:
        args.extend(["-append", "-update"])
    elif creation_mode==MODE_OVERWRITE:
        args.extend(['-overwrite'])
    args.extend(["-nln", schema+"."+table_name])
    args.extend(["-dim", "2"])
    args.extend(["-s_srs", srs, "-a_srs", srs])
    # GDAL >=1.9 && < 2.0
    if encoding != "autodetect":
        args.extend(["--config", "SHAPE_ENCODING", encoding])
    args.extend(["-lco", "LAUNDER=YES"])
    args.extend(["-lco", "precision=NO"])
    args.extend([conn_string, shp_path])
    print " ".join(args).replace("password='{password}'".format(password=password), "password='xxxxxx'")
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
    output, err = p.communicate()
    rc = p.returncode
    print "return code: " + str(rc)
    if rc>0:
        msg = _("Error when loading the layer to PostGIS. Ogr2ogr error: {msg}").format(msg=err)
        logging.error(msg)
        message_already_exists = "FAILED: Layer "+str(schema)+"."+str(table_name)+" already exists, and -append not specified"
        if err.startswith(message_already_exists):
            rc=2
        raise GdalError(rc, msg)
    return args

def postgis2spatialite(table_name, out_spatialite_path, pg_conn_str, out_table_name=None, srs=None, creation_mode=MODE_CREATE, update=True):
    """
    Exports a single postgis table to spatialite
    """
    if not out_table_name:
        out_table_name = table_name
    args = [OGR2OGR_PATH, "-f", "SQLite", "-dsco", "SPATIALITE=YES", out_spatialite_path]
    if update:
        if os.path.exists(out_spatialite_path):
        # we behave different to OGR, we allow the database to be created in update mode
            args.extend("-update")
    if creation_mode==MODE_APPEND:
        args.extend(["-append"])
    elif creation_mode==MODE_OVERWRITE:
        args.extend(['-overwrite'])
    args.extend(["-nln", out_table_name])
    if srs:
        args.extend(["-s_srs", srs, "-a_srs", srs])
    args.extend(["-lco", "LAUNDER=NO"])
    safe_args = list(args)
    args.extend([pg_conn_str.encode(), table_name])
    safe_args.extend([unicode(pg_conn_str), table_name])
    print " ".join(safe_args)
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
    output, err = p.communicate()
    rc = p.returncode
    print "return code: " + str(rc)
    if rc>0:
        msg = _("Error exporting layer from PostGIS to Spatialite. Ogr2ogr error: {msg}").format(msg=err)
        logging.error(msg)
        raise GdalError(rc, msg)
    return args


class ConnectionString():
    def encode(self):
        pass

class PgConnectionString(ConnectionString):
    conn_string_tpl = u"PG:host='{host}' port='{port}' user='{user}' dbname='{dbname}' password='{password}'"
    def __init__(self, host=None, port=None, dbname=None, schema=None, user=None, password=None):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.schema = schema
        self.user = user
        self.password = password

    def encode(self):
        return self.conn_string_tpl.format(host=self.host, port=self.port, user=self.user, dbname=self.dbname, password=self.password, schema=self.schema)

    def __unicode__(self):
        return '"' + self.conn_string_tpl.format(host=self.host, port=self.port, user=self.user, dbname=self.dbname, password='xxxxxx', schema=self.schema) + '"'

    def __str__(self):
        return self.__unicode__().encode('utf-8') 

class FileConnectionString():
    
    def __init__(self, file_path):
        self.file_path = file_path

    def encode(self):
        return self.file_path

    def __unicode__(self):
        return '"' + self.file_path + '"'


def ogr2ogr(version=1):
    return Ogr2ogr(version)

class Wrapper():
    def __init__(self, version=1, command_path=None):
        self.version = version
        if command_path:
            self.command = command_path
        else:
            self.command = self._get_default_command()
    
    def _get_default_command(self):
        pass
    
    def _do_execute(self, args):
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
        output, err = p.communicate()
        rc = p.returncode
        print "return code: " + str(rc)
        if rc>0:
            msg = _("Error exporting layer from PostGIS to Spatialite. Ogr2ogr error: {msg}").format(msg=err)
            logging.error(msg)
            raise GdalError(rc, msg)
        return args

class Ogr2ogr(Wrapper):
    """
    Wrapper for the ogr2ogr command
    """
    MODE_LAYER_CREATE="CR"
    MODE_LAYER_APPEND="AP"
    MODE_LAYER_OVERWRITE="OW"
    
    MODE_DS_CREATE="CR"
    MODE_DS_UPDATE="CR"
    MODE_DS_CREATE_OR_UPDATE="CR"
    
    OGR2OGR_PATH = '/usr/bin/ogr2ogr'
    
    def __init__(self, version=1, command_path=None):
        Wrapper.__init__(self, version, command_path)
        self.set_launder()
        self.set_output_mode()
        self._dataset_creation_options = {}
        self._layer_creation_options = {}
        self._dataset_creation_options_internal = {}
        self._layer_creation_options_internal = {}
        self._config_options = {}
        self._config_options_internal = {}
        self.geom_type = None
        
    def _get_default_command(self):
        return OGR2OGR_PATH
    
    def set_input(self, input_ds, table_name=None, srs=None, encoding=None):
        """
        Sets the input layer
        
        :param input_ds: The path to the input data source (shapefile, spatialite, etc)
        or a ConnectionString object
        :param table_name: The name of the input table name in the data source. Can be
        omitted for some data source types such as Shapefiles or CSVs
        :param srs: Defines the SRS of the input layer, using a EPSG code string
        (e.g. "EPSG:4326"). Ogr will try to autodetect the SRS if this parameter is omitted,
        but autodetection will fail in a number of situations, so it is always recommended
        to explicitly set the SRS parameter
        :param encoding: Defines the character encoding of the input layer.
        Ogr will try to autodetect the encoding if this parameter is omitted,
        but autodetection will fail in a number of situations, so it is always recommended
        to explicitly set the encoding.
        Only supported for Shapefiles, it will be ignored for other data source types
        """
        if isinstance(input_ds, ConnectionString):
            self.in_ds = input_ds
        else:
            self.in_ds = FileConnectionString(input_ds)
        self.in_table = table_name
        self.in_srs = srs
        self.in_encoding = encoding
        if encoding:
            self._config_options_internal["SHAPE_ENCODING"]=encoding
    
    def set_output(self, output_ds, file_type=None, table_name=None, srs=None):
        """
        Sets the output layer
        :param output_ds: The path to the output data source (shapefile, spatialite, etc)
        or a ConnectionString object (for Postgresql connections, etc)
        :param file_type: The output data source type (e.g. "ESRI Shapefile", "GML",
        "GeoJSON", "PostgreSQL", etc). See ogr2ogr documentation for the full list
        of valid types
        :param table_name: The name of the output table name in the data source. If omitted,
        the name of the input table will be used. It will be ignored for some data source types
        such as Shapefiles or CSVs which don't have the concept of table
        :param srs: Defines a transformation from the input SRS to this SRS.
        It expects a EPSG code string (e.g. "EPSG:4326"). If omitted and the input SRS
        has been defined, then the input SRS will also be used as output SRS
        """
        if isinstance(output_ds, ConnectionString):
            self.out_ds = output_ds
        else:
            self.out_ds = FileConnectionString(output_ds)

        if file_type:
            self.out_file_type = file_type
        else:
            dslower = self.out_ds.encode().lower()
            if dslower.endswith(".shp"):
                self.out_file_type = "ESRI Shapefile"
            elif dslower.startswith("pg:"):
                self.out_file_type = "PostgreSQL"
            elif dslower.endswith(".sqlite"):
                self.out_file_type = "SQLite"
            elif dslower.endswith(".json") or dslower.endswith(".geojson"):
                self.out_file_type = "GeoJSON"
            elif dslower.endswith(".gml"):
                self.out_file_type = "GML"
            elif dslower.endswith(".csv"):
                self.out_file_type = "CSV"
            elif dslower.endswith(".gpx"):
                self.out_file_type = "GPX"
            elif dslower.endswith(".kml"):
                self.out_file_type = "KML"
            else:
                self.out_file_type = "ESRI Shapefile"

        if file_type=="SQLite":
            self._dataset_creation_options_internal["SPATIALITE"]="YES"

        self.out_table = table_name
        self.out_srs = srs

    @property
    def geom_type(self):
        if self.out_file_type=="PostgreSQL" and not self._geom_type: 
            return "PROMOTE_TO_MULTI"
        else:
            return self._geom_type
    
    @geom_type.setter
    def geom_type(self, geom_type):
        self._geom_type = geom_type
    
    def set_output_mode(self, layer_mode=MODE_LAYER_CREATE, data_source_mode=MODE_DS_CREATE):
        self.layer_mode = layer_mode
        self.data_source_mode = data_source_mode

    @property
    def dataset_creation_options(self):
        """
        Dataset creation options, expressed as a dict of options such as
        such as {"SPATIALITE": "YES", "METADATA", "YES"}
        """
        result = self._dataset_creation_options_internal.copy()
        result.update(self._dataset_creation_options)
        return result

    @dataset_creation_options.setter
    def dataset_creation_options(self, ds_creation_options):
        self._dataset_creation_options = ds_creation_options

    @property
    def layer_creation_options(self):
        """
        Sets layer creation options, expressed as a dict of options such as
        {"SPATIAL_INDEX": "YES", "RESIZE": "YES"}
        """
        result = self._layer_creation_options_internal.copy()
        result.update(self._layer_creation_options)
        return result

    @layer_creation_options.setter 
    def layer_creation_options(self, layer_creation_options):
        self._layer_creation_options = layer_creation_options

    @property
    def config_options(self):
        """
        Gdal/ogr config options, expressed as a dict of options such as
        {"SHAPE_ENCODING": "latin1"}, {"OGR_ENABLE_PARTIAL_REPROJECTION": "YES"}
        """
        result = self._config_options_internal.copy()
        result.update(self._config_options)
        return result

    @config_options.setter
    def config_options(self, options):
        self._config_options = options

    def execute(self):
        args = [self.command]

        if self.data_source_mode==self.MODE_DS_UPDATE:
            args.extend("-update")
        if self.data_source_mode==self.MODE_DS_CREATE_OR_UPDATE:
            if isinstance(self.out_ds, FileConnectionString) and os.path.exists(self.out_ds):
                # if it is a FileConnectionString, only use -update if the file exists
                args.extend("-update")
            else:
                args.extend("-update")

        if self.layer_mode==self.MODE_LAYER_APPEND:
            args.extend(["-append"])
        elif self.layer_mode==self.MODE_LAYER_OVERWRITE:
            args.extend(['-overwrite'])
        
        if self.out_srs:
            args.extend(['-t_srs', self.out_srs])

        if self.in_srs:
            args.extend(['-a_srs', self.in_srs])
            args.extend(['-s_srs', self.in_srs])
        
        args.extend("-f", self.out_file_type)
        
        for key, value in self.dataset_creation_options.iteritems():
            args.extend(["-dsco", key+"="+value])
        for key,value in self.layer_creation_options.iteritems():
            args.extend(["-lco", key+"="+value])
        for key,value in self.config_options.iteritems():
            args.extend(["--config", key, value])

        if self.out_table:
            args.extend(["-nln", self.out_table])
        elif self.in_table:
            args.extend(["-nln", self.in_table])
        elif isinstance(self.in_ds, FileConnectionString):
            args.extend(["-nln", os.path.basename(self.in_ds.encode())])
        
        if self.geom_type:
            args.extend(["-nlt", self.geom_type])

        safe_args = list(args)
        if self.in_table:
            args.extend([self.out_ds.encode(), self.in_ds.encode(), self.in_table])
            safe_args.extend([unicode(self.out_ds), unicode(self.in_ds), self.in_table])
        else:
            args.extend([self.out_ds.encode(), self.in_ds.encode()])
            safe_args.extend([unicode(self.out_ds), unicode(self.in_ds)])
        print " ".join(safe_args)
        
        return self._do_execute(args)