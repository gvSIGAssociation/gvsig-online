# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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

OGR2OGR_PATH = '/usr/bin/ogr2ogr'
GDALINFO_PATH = '/usr/bin/gdalinfo'

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
    stats_str = gdalinfo(raster_path)
    buf = io.StringIO(stats_str)
    result = []
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

def shp2postgis(shp_path, table_name, srs, host, port, dbname, schema, user, password, creation_mode=MODE_CREATE, encoding="autodetect"):          
    conn_string = "PG:host='{host}' port='{port}' user='{user}' dbname='{dbname}' password='{password}'".format(host=host, port=port, user=user, dbname=dbname, password=password, schema=schema)
    args = [OGR2OGR_PATH, "-f", "PostgreSQL", "-nlt", "PROMOTE_TO_MULTI"]
    if creation_mode==MODE_APPEND:
        args.extend(["-append", "-update"])
    elif creation_mode==MODE_OVERWRITE:
        args.extend(['-overwrite'])
    args.extend(["-nln", schema+"."+table_name])
    args.extend(["-s_srs", srs, "-a_srs", srs])
    # GDAL >=1.9 && < 2.0
    if encoding != "autodetect":
        args.extend(["--config", "SHAPE_ENCODING", encoding])
    args.extend(["-lco", "LAUNDER=NO"])
    args.extend([conn_string, shp_path])
    print " ".join(args).replace("password='{password}'".format(password=password), "password='xxxxxx'")
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
    output, err = p.communicate()
    rc = p.returncode
    print "return code: " + str(rc)
    if rc>0:
        msg = _("Error when loading the layer to PostGIS. Ogr2ogr error: {msg}").format(msg=err)
        logging.error(msg)
        raise GdalError(rc, msg)
    return args