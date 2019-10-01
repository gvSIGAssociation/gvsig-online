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
@author: <jvhigon@scolab.es>
'''

from gvsigol_core.models import Project
import subprocess
import os


#
# Only support tif files
#
def create_service_wms(project_id, path):
    mapfile = path + "/" + str(project_id) + ".map"
    shape = str(project_id) + ".shp"
    print ("Creando mapfile ..." + mapfile)
    try:
        os.remove(path + "/" + shape)
    except OSError:
        pass
    try:
        cmd = "gdaltindex " + shape + " *.tif" 
        cmd = "gdaltindex -t_srs EPSG:4326 -src_srs_name src_srs " + shape + " *.tif" 
        r = subprocess.call([cmd], cwd=path, shell=True)
        _create_mapfile(mapfile, project_id)  
        if r == 0:
            return True
        else:
            return False      
    except Exception as e:        
        print (e)
        return False
    
def _create_mapfile(mapfile, project_id):
    f = open(mapfile,'w')
    text = r"""
         MAP
        
        OUTPUTFORMAT
        NAME "bil16"
        DRIVER "GDAL/EHdr"
        MIMETYPE "application/bil16"
        EXTENSION "bil"
        IMAGEMODE INT16
        END
        
        NAME "Elevation"
        PROJECTION
          "init=epsg:4326"
        END
        UNITS meters
        WEB
          METADATA
            "ows_enable_request" "*"
            "wms_title" "Elevation"
            "wms_abstract" "Powered by gvSIG Online"
            "wms_srs" "EPSG:4326 EPSG:900913 EPSG:3857"
            "wms_encoding" "UTF-8"
          END
        END
        
        LAYER
            NAME "elevation"
            STATUS ON
            TYPE RASTER
            TILEINDEX "@@@.shp"
            TILEITEM "LOCATION"
            TILESRS "src_srs"
            PROJECTION
               AUTO
            END
        END
        LAYER
            NAME "grid"
            METADATA
                "DESCRIPTION" "Grid"
            END
            TYPE LINE
            STATUS ON
            CLASS
                NAME "Graticule"
                COLOR 0 0 0
            END
            PROJECTION
                "init=epsg:4326"
            END
            GRID
                LABELFORMAT "DD"
            END
        END

        END"""
    text = text.replace('@@@', str(project_id))
    f.write(text)
    f.close() 
 
    return True
