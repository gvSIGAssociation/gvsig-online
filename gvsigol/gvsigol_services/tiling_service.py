#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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

import base64
from math import floor
import math
import os.path
import shutil
import ssl
import time
import urllib2
import zipfile
from time import time as t
from datetime import datetime, timedelta

from gvsigol import settings
from gvsigol_core.models import Project
from gvsigol_services.decorators import start_new_thread
from gvsigol_services.models import Server


class Tiling():
    
    directory = None
    mode = 'OSM'
    tilematrixset = None
    layer = None
    ctx = None
    gsuser = None
    gspaswd = None
    #Son siempre en geográficas
    min_lon = None
    min_lat = None
    max_lon = None
    max_lat = None
    prj_id = None

    def __init__(self, folder, type_, tilematrixset, url, prj_id):
        self.prj_id = prj_id
        
        if folder is not None:
            self.directory = folder 
        
        try:
            self.tile_url1 = settings.OSM_TILING_1
            self.tile_url2 = settings.OSM_TILING_2
            self.tile_url3 = settings.OSM_TILING_3
        except Exception:
            pass

        self.tilematrixset = tilematrixset
        if type_ is not None:
            self.mode = type_
            if type_ == "OSM":
                self.tile_url = self.tile_url1
            else:
                self.tile_url = url 
        
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        
        server = Server.objects.filter(default=True)
        if server is not None and len(server) > 0:
            self.gsuser = server[0].user
            self.gspaswd = server[0].password
    
    def set_layer_name(self, lyr_name):
        self.layer = lyr_name
        
    def set_layer_extent(self, minx, miny, maxx, maxy):
        self.min_lon = minx
        self.min_lat = miny
        self.max_lon = maxx
        self.max_lat = maxy
                
    def _deg2num(self, lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        aux = math.tan(lat_rad) + (1 / math.cos(lat_rad))
        if(aux == 0):
            aux = 1
        ytile = int((1.0 - math.log(aux) / math.pi) / 2.0 * n)
        return (xtile, ytile)
    
    def _utm2num(self, y, x, zoom):
        minX = -20037508.34
        minY = -20037508.34
        maxX = 20037508.34
        maxY = 20037508.34 
        n = 2**zoom
        xtile = int(floor((n * (x - minX)) / (maxX - minX)))
        ytile = int(floor((n * (maxY - y)) / (maxY - minY)))
        return (xtile, ytile)
    
    def _download_wmts(self, zoom, xtile, ytile, format_):
        params = "?REQUEST=GetTile&&TILEMATRIXSET=" + self.tilematrixset + "&LAYER=" + self.layer + "&FORMAT=" + format_ 
        url = self.tile_url + params
        
        url = "%s&TILEMATRIX=%s&TILECOL=%d&TILEROW=%d" % (url, (self.tilematrixset + ':' + str(zoom)), xtile, ytile)
        dir_path = "%s/%d/%d/" % (self.directory,zoom, xtile)
        
        if(format_.endswith("png")):
            download_path = "%s/%d/%d/%d.png" % (self.directory, zoom, xtile, ytile)
        else:
            download_path = "%s/%d/%d/%d.jpg" % (self.directory, zoom, xtile, ytile)
        
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        if(not os.path.isfile(download_path)):
            #print "downloading %r" % url
            try:
                request = urllib2.Request(url)
                base64string = base64.b64encode('%s:%s' % (self.gsuser, self.gspaswd))
                request.add_header("Authorization", "Basic %s" % base64string)
                source = urllib2.urlopen(request, context=self.ctx)
                content = source.read()
                source.close()
                destination = open(download_path,'wb')
                destination.write(content)
                destination.close()
            except Exception as e:
                print "ERROR: " + str(e)
        else: 
        #print "skipped %r" % url
            pass
    
    def _download_url(self, zoom, xtile, ytile):
        #No hay 3 hilos, simplemente se turna las URLs para no tirar solo de un servidor
        if self.tile_url == self.tile_url1:
            self.tile_url = self.tile_url2
        elif self.tile_url == self.tile_url2:
            self.tile_url = self.tile_url3
        elif self.tile_url == self.tile_url3:
            self.tile_url = self.tile_url1
         
        url = "%s/%d/%d/%d.png" % (self.tile_url, zoom, xtile, ytile)
        dir_path = "%s/%d/%d/" % (self.directory, zoom, xtile)
        download_path = "%s/%d/%d/%d.png" % (self.directory, zoom, xtile, ytile)
        
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        if(not os.path.isfile(download_path)):
            print "downloading %r" % url
            source = urllib2.urlopen(url)
            content = source.read()
            source.close()
            destination = open(download_path,'wb')
            destination.write(content)
            destination.close()
        else: 
            print "skipped %r" % url
            pass
    
    #No se usa
    def create_tiles(self, min_lon, min_lat, max_lon, max_lat, maxzoom, format_):
            #from 0 to 6 download all
        if self.mode  != "OSM":
            for zoom in range(0,7,1):
                #break;
                for x in range(0,2**zoom,1):        
                    for y in range(0,2**zoom,1):
                        self._download_wmts(zoom, x, y, format_)
                    
        # from 6 to 15 ranges
        for zoom in range(7, int(maxzoom)+1, 1):
            xtile, ytile = self._deg2num(float(min_lat), float(min_lon), zoom)
            final_xtile, final_ytile = self._deg2num(float(max_lat), float(max_lon), zoom)
    
            #print "%d:%d-%d/%d-%d" % (zoom, xtile, final_xtile, ytile, final_ytile)
            for x in range(xtile, final_xtile + 1, 1):
                for y in range(ytile, final_ytile - 1, -1):  
                    if self.mode == "OSM":
                        self._download_url(zoom, x, y)
                    else:
                        self._download_wmts(zoom, x, y, format_)   
                          
                        
    def create_tiles_from_utm(self, base_layer_process, min_x, min_y, max_x, max_y, maxzoom, format_):
        #from 0 to 6 download all
#         if self.mode  != "OSM":
#             for zoom in range(0,7,1):
#                 break;
#                 for x in range(0,2**zoom,1):        
#                     for y in range(0,2**zoom,1):
#                         self._download_wmts(zoom, x, y)
        
        start_time = t()

        if self.mode  != "OSM":
            #Si la capa es WMTS:
            #De los niveles 0-6 se descargan todos los tiles de la capa ajustandose al extent de esta
            #para no pedir tiles que no contenga.
            # Como el extent de la capa siempre viene en geográficas se usa deg2num
            for zoom in range(0, 7, 1):
                xtile, ytile = self._deg2num(float(self.min_lat), float(self.min_lon), zoom)
                final_xtile, final_ytile = self._deg2num(float(self.max_lat), float(self.max_lon), zoom)

                for x in range(xtile, final_xtile + 1, 1):
                    for y in range(ytile, final_ytile - 1, -1):  
                        self._download_wmts(zoom, x, y, format_)
                        if base_layer_process is not None:
                            if base_layer_process[str(self.prj_id)]['stop'] == 'true':
                                return
                            base_layer_process[str(self.prj_id)]['active'] = 'true'
                            base_layer_process[str(self.prj_id)]['processed_tiles'] = base_layer_process[str(self.prj_id)]['processed_tiles'] + 1
                            base_layer_process[str(self.prj_id)]['time'] = self.get_estimated_time(start_time, base_layer_process)
                            
                        
            #Si la capa es OSM los niveles 0-6 ya están en un zip
                        
        #Para cualquier capa base se descargan los siguientes niveles               
        #solo de la extensión del proyecto
        for zoom in range(7, int(maxzoom) + 1, 1):
            xtile, ytile = self._utm2num(min_y, min_x, zoom)
            final_xtile, final_ytile = self._utm2num(max_y, max_x, zoom)
      
            #print "%d:%d-%d/%d-%d" % (zoom, xtile, final_xtile, ytile, final_ytile)
            for x in range(xtile, final_xtile + 1, 1):
                for y in range(ytile, final_ytile - 1, -1):  
                    if self.mode == "OSM":
                        self._download_url(zoom, x, y)
                    else:
                        self._download_wmts(zoom, x, y, format_) 
                    if base_layer_process is not None:
                        if str(self.prj_id) in base_layer_process:
                            if base_layer_process[str(self.prj_id)]['stop'] == 'true':
                                return
                            base_layer_process[str(self.prj_id)]['active'] = 'true'
                            base_layer_process[str(self.prj_id)]['processed_tiles'] = base_layer_process[str(self.prj_id)]['processed_tiles'] + 1
                            base_layer_process[str(self.prj_id)]['time'] = self.get_estimated_time(start_time, base_layer_process)
                            
                            #base_layer_process[str(self.prj_id)] = {
                            #    'active' : 'true',
                            #    'total_tiles' : base_layer_process[str(self.prj_id)]['total_tiles'],
                            #    'processed_tiles' : base_layer_process[str(self.prj_id)]['processed_tiles'] + 1,
                            #    'version' : base_layer_process[str(self.prj_id)]['version'],
                            #    'time' : self.get_estimated_time(start_time, base_layer_process),
                            #    'stop' : base_layer_process[str(self.prj_id)]['stop']
                            #}    
     
    def get_estimated_time(self, start_time, base_layer_process):
        elapsed_time = t() - start_time
        processed_tiles = base_layer_process[str(self.prj_id)]['processed_tiles'] + 1
        total_tiles = base_layer_process[str(self.prj_id)]['total_tiles']
        total_estimated_secs = (total_tiles * elapsed_time) / processed_tiles
        estimated_secs = ((total_tiles - processed_tiles) * total_estimated_secs) / total_tiles
        return self.display_time(estimated_secs)      
    
    def display_time(self, seconds, granularity=2):
        intervals = (
            ('semanas', 604800),  # 60 * 60 * 24 * 7
            ('dias', 86400),    # 60 * 60 * 24
            ('horas', 3600),    # 60 * 60
            ('minutos', 60),
            ('segundos', 1),
            )
        result = []
    
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])   
     
    def get_number_of_tiles(self, min_x, min_y, max_x, max_y, maxzoom, base_layer_process):
        num_tiles = 0
        
        #Niveles de 0 al 7 sólo capas WMTS (pq OSM ya están descargados)
        if self.mode  != "OSM":
            for zoom in range(0, 7, 1):
                xtile, ytile = self._deg2num(float(self.min_lat), float(self.min_lon), zoom)
                final_xtile, final_ytile = self._deg2num(float(self.max_lat), float(self.max_lon), zoom)
                w = abs(final_xtile - xtile) + 1
                h = abs(final_ytile - ytile) + 1
                num_tiles = num_tiles + (w * h)
                        
        #Para cualquier capa base se descargan los siguientes niveles               
        #solo de la extensión del proyecto
        for zoom in range(7, int(maxzoom) + 1, 1):
            xtile, ytile = self._utm2num(min_y, min_x, zoom)
            final_xtile, final_ytile = self._utm2num(max_y, max_x, zoom)
            w = abs(final_xtile - xtile) + 1
            h = abs(final_ytile - ytile) + 1
            num_tiles = num_tiles + (w * h)
            
        if base_layer_process is not None:
            base_layer_process[str(self.prj_id)] = {
                'active' : 'true',
                'total_tiles' : num_tiles,
                'processed_tiles' : base_layer_process[str(self.prj_id)]['processed_tiles'],
                'version' : base_layer_process[str(self.prj_id)]['version'],
                'time' : '-',
                'stop' : 'false'
            }
            
        return num_tiles
        
                       
    def get_zoom_level(self, dist, tiles_side):
        max_ = tiles_side # num tiles max por lado en el nivel ultimo
        ww = 40000
        tiles_side_level = (max_ * ww) / dist
        return self.get_level(tiles_side_level) 
 
    def get_level(self, tiles):
        if(tiles >= 1048576):
            return 20
        elif(tiles >= 524288):
            return 19 
        elif(tiles >= 262144):
            return 18
        elif(tiles >= 131072):
            return 17
        elif(tiles >= 65536):
            return 16
        elif(tiles >= 32768):
            return 15
        elif(tiles >= 16384):
            return 14
        elif(tiles >= 8192):
            return 13
        elif(tiles >= 4096):
            return 12
        elif(tiles >= 2048):
            return 11
        elif(tiles >= 1024):
            return 10
        elif(tiles >= 512):
            return 9
        elif(tiles >= 256):
            return 8
        elif(tiles >= 128):
            return 7                      

#***********END TILING CLASS********************


@start_new_thread
def tiling_base_layer(base_layer_process, base_lyr, prj_id, num_res_levels, tilematrixset, format_='image/png'):
    prj = Project.objects.get(id = prj_id)
    if prj.extent is not None:
        bbox = prj.extent.split(',')
        min_x = float(bbox[0])
        min_y = float(bbox[1])
        max_x = float(bbox[2])
        max_y = float(bbox[3])
        
        url = None
        if base_lyr.datastore is not None:
            url = base_lyr.datastore.workspace.wmts_endpoint
        
        layers_dir = os.path.join(settings.MEDIA_ROOT, settings.LAYERS_ROOT)
        
        millis = int(round(time.time() * 1000))
        folder_prj =  os.path.join(layers_dir, prj.name) + "_prj_" + str(millis) 
        folder_package = os.path.join(folder_prj, 'EPSG3857')
        if not os.path.exists(layers_dir):
            os.mkdir(layers_dir)
        
        old_version = prj.baselayer_version
        prj.baselayer_version = -99999
        prj.save()
        
        try:
            mode = base_lyr.type
            tiling = Tiling(folder_package, mode, tilematrixset, url, prj_id)
            #num_res_levels = tiling.get_zoom_level(floor(max_x - min_x)/1000, tiles_side) 
            
            if mode == 'OSM':
                base_zip = os.getcwd() + "/gvsigol_services/static/data/osm_tiles_levels_0-6.zip"
                with zipfile.ZipFile(base_zip, 'r') as zipObj:
                    zipObj.extractall(path=layers_dir)
                    shutil.move(layers_dir + '/tiles_download', folder_package)
            else:
                lyr_name = base_lyr.datastore.workspace.name + ":" + base_lyr.name
                tiling.set_layer_name(lyr_name)
                
                extent = base_lyr.latlong_extent
                extent = extent.split(',')
                lyr_min_x = float(extent[0])
                lyr_min_y = float(extent[1])
                lyr_max_x = float(extent[2])
                lyr_max_y = float(extent[3])
                tiling.set_layer_extent(lyr_min_x, lyr_min_y, lyr_max_x, lyr_max_y)
               
            if base_layer_process is not None:
                base_layer_process[str(prj_id)] = {
                    'active' : 'true',
                    'total_tiles' : 0,
                    'processed_tiles' : 0,
                    'version' : millis,
                    'time' : '-',
                    'stop' : 'false'
                }
            number_of_tiles = tiling.get_number_of_tiles(min_x, min_y, max_x, max_y, num_res_levels, base_layer_process)    
            
            #Genera el tileado a partir de coords en 3857 q es en las que está el extent del proyecto
            tiling.create_tiles_from_utm(base_layer_process, min_x, min_y, max_x, max_y, num_res_levels, format_)
            
            #Ahora ya no lo quieren con el extent del proyecto sino de la capa. Transformamos a 3857 para seguir usando create_tiles_from_utm
            #inProj = Proj(init='epsg:4326')
            #outProj = Proj(init='epsg:3857')
            #tile_min_x, tile_min_y = transform(inProj, outProj, lyr_min_x, lyr_min_y)
            #tile_max_x, tile_max_y = transform(inProj, outProj, lyr_max_x, lyr_max_y)
            #tiling.create_tiles_from_utm(tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, format_)
            
            #TODO;
            #Shutil tiene un bug en algunos SO que hace que te meta una carpeta ./ dentro del zip (a los de SAV no les sirve). 
            #A partir de la 3.6 de python está resuelto. Mientras tanto lo hago con ZipFile. Queda pendiente volverlo a dejar con shutil  
            #shutil.make_archive(folder_prj, 'zip', folder_prj)
            zipf = zipfile.ZipFile(folder_prj + '.zip', 'w', zipfile.ZIP_DEFLATED)
            lenDirPath = len(folder_prj)
            for root, _, files in os.walk(folder_prj):
                for file_ in files:
                    filePath = os.path.join(root, file_)
                    zipf.write(filePath, filePath[lenDirPath :])
            zipf.close()
            
            shutil.rmtree(folder_prj)
            
            if base_layer_process is not None:
                base_layer_process[prj_id] = {
                    'active' : 'false',
                    'total_tiles' : number_of_tiles,
                    'processed_tiles' : number_of_tiles,
                    'version' : millis,
                    'time' : '-',
                    'stop' : 'false'
                }
              
        except Exception:
            #Si ha habido algún problema restauramos la versión vieja
            prj.baselayer_version = old_version
            prj.save()
            return
        
        prj.baselayer_version = millis
        prj.save()
            
def exists_base_layer_tiled(prj_id):
    prj = Project.objects.get(id = prj_id)
    layers_dir = os.path.join(settings.MEDIA_ROOT, settings.LAYERS_ROOT)
    file_ =  os.path.join(layers_dir, prj.name) + "_prj.zip"
    return os.path.isfile(file_)
                
