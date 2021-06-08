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
import urllib.request, urllib.error, urllib.parse
import zipfile
import os
import re
from time import time as t
from datetime import datetime, timedelta
import pytz
from django.utils import timezone

from gvsigol import settings
from gvsigol_core.models import Project, ProjectBaseLayerTiling, TilingProcessStatus
from gvsigol_services import tasks
from gvsigol_services.decorators import start_new_thread
from gvsigol_services.models import Server, Layer
from pyproj import Proj, transform
import json


class Tiling():
    
    directory = None
    mode = 'OSM'
    tilematrixset = None
    matrixset_prefix = None
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
    level_download_all_tiles = 5

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
        self.matrixset_prefix = tilematrixset + ":"
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

    def set_matrixset_prefix(self, prefix):
        if prefix is None:
            self.matrixset_prefix = ""
        else:
            self.matrixset_prefix = prefix
        
    def set_layer_extent(self, minx, miny, maxx, maxy):
        self.min_lon = minx
        self.min_lat = miny
        self.max_lon = maxx
        if(maxy == 90):
            maxy = 89
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
        params = "?REQUEST=GetTile&SERVICE=WMTS&TILEMATRIXSET=" + self.tilematrixset + "&LAYER=" + self.layer + "&FORMAT=" + format_ 
        url = self.tile_url + params
        
        url = "%s&TILEMATRIX=%s&TILECOL=%d&TILEROW=%d" % (url, (self.matrixset_prefix + str(zoom)), xtile, ytile)
        dir_path = "%s/%d/%d/" % (self.directory,zoom, xtile)
        
        if(format_.endswith("png")):
            download_path = "%s/%d/%d/%d.png" % (self.directory, zoom, xtile, ytile)
        else:
            download_path = "%s/%d/%d/%d.jpg" % (self.directory, zoom, xtile, ytile)
        
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        if(not os.path.isfile(download_path) and not os.path.exists(download_path)):
            #print "downloading %r" % url
            try:
                request = urllib.request.Request(url)
                encoded = ('%s:%s' % (self.gsuser, self.gspaswd)).encode('ascii')
                base64string = base64.b64encode(encoded)
                request.add_header("Authorization", "Basic %s" % base64string.decode("ascii"))
                source = urllib.request.urlopen(request, context=self.ctx)
                content = source.read()
                source.close()
                destination = open(download_path,'wb')
                destination.write(content)
                destination.close()
            except Exception as e:
                #Si el servicio no está disponible terminamos la descarga
                if(e.code and e.code == 503): 
                    return False
                else:
                    print("ERROR: " + str(e))
        else: 
        #print "skipped %r" % url
            pass

        return True
    
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
            print("downloading %r" % url)
            source = urllib.request.urlopen(url)
            content = source.read()
            source.close()
            destination = open(download_path,'wb')
            destination.write(content)
            destination.close()
        else: 
            print("skipped %r" % url)
            pass
    
    #No se usa
    def create_tiles(self, min_lon, min_lat, max_lon, max_lat, maxzoom, format_):
            #from 0 to 6 download all
        if self.mode  != "OSM":
            for zoom in range(0,7,1):
                #break;
                for x in range(0,2**zoom,1):        
                    for y in range(0,2**zoom,1):
                        if self._download_wmts(zoom, x, y, format_) is False:
                            return False
                    
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
                        if self._download_wmts(zoom, x, y, format_) is False:
                            return False
        return True

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
                        if self._download_wmts(zoom, x, y, format_) is False:
                            return False
                        if base_layer_process is not None:
                            if base_layer_process[str(self.prj_id)]['stop'] == 'true':
                                return False
                            base_layer_process[str(self.prj_id)]['active'] = 'true'
                            base_layer_process[str(self.prj_id)]['processed_tiles'] = base_layer_process[str(self.prj_id)]['processed_tiles'] + 1
                            base_layer_process[str(self.prj_id)]['time'] = self.get_estimated_time(start_time, base_layer_process, 0)
                            
                        
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
                        if self._download_wmts(zoom, x, y, format_) is False:
                            return False
                    if base_layer_process is not None:
                        if str(self.prj_id) in base_layer_process:
                            if base_layer_process[str(self.prj_id)]['stop'] == 'true':
                                return False
                            base_layer_process[str(self.prj_id)]['active'] = 'true'
                            base_layer_process[str(self.prj_id)]['processed_tiles'] = base_layer_process[str(self.prj_id)]['processed_tiles'] + 1
                            base_layer_process[str(self.prj_id)]['time'] = self.get_estimated_time(start_time, base_layer_process, 0)
                              
     
        return True



    def retry_tiles_from_utm(self, base_layer_process, min_x, min_y, max_x, max_y, maxzoom, format_, start_level, start_x, start_y, tiling_status = None, tiles_already_download = None):
        '''
        Parameters
        ----------
        base_layer_process : str
            Estructura de datos para mantener la ejecución del proceso
        min_x, min_y, max_x, max_y : float
            extent de la petición
        maxzoom : int
            Máx nivel de zoom de la petición
        format_ : str
            Formato de los tiles descargados
        start_level : int
            Nivel de resolución inicial. Si es None empieza en el cero
        start_x, start_y: int
            a descarga empieza en estos tiles. Esto sirve para cuando se ha detenido y se quiere reiniciar
            la descarga desde donde se quedó.
        tiling_status: model
            tabla de la bbdd para mantener el estado del proceso de descarga
        tiles_already_download: dict
            si se le pasa este hash comprobará si los tiles que contiene ya han sido descargados para no repetir
            tiles existentes. Esto es útil en la descarga por interseccion de zonas ya que se llama varias veces
            a esta función para el mismo paquete.
        '''
        start_time = t()
        first_entry = True   
        init_processed_tiles = base_layer_process[str(self.prj_id)]['processed_tiles']
        if start_level == None:
            start_level = 0   

        if self.mode  != "OSM" and start_level <= (self.level_download_all_tiles - 1):
            #Si la capa es WMTS:
            #De los niveles 0-4 se descargan todos los tiles de la capa ajustandose al extent de esta
            #para no pedir tiles que no contenga.
            # Como el extent de la capa siempre viene en geográficas se usa deg2num
            for zoom in range(start_level, self.level_download_all_tiles, 1):
                xtile, ytile = self._deg2num(float(self.min_lat), float(self.min_lon), zoom)
                cpy_ytile = ytile
                final_xtile, final_ytile = self._deg2num(float(self.max_lat), float(self.max_lon), zoom)
                if(first_entry == True and start_x != None and start_y != None):
                    xtile = start_x
                    ytile = start_y - 1
                    first_entry = False

                for x in range(xtile, final_xtile + 1, 1):
                    for y in range(ytile, final_ytile - 1, -1):  
                        if self._download_wmts(zoom, x, y, format_) is False:
                            return False
                        if base_layer_process is not None:
                            if base_layer_process[str(self.prj_id)]['stop'] == 'true':
                                return False
                            base_layer_process[str(self.prj_id)]['active'] = 'true'
                            base_layer_process[str(self.prj_id)]['processed_tiles'] = base_layer_process[str(self.prj_id)]['processed_tiles'] + 1
                            base_layer_process[str(self.prj_id)]['time'] = self.get_estimated_time(start_time, base_layer_process, init_processed_tiles)
                    ytile = cpy_ytile
                    self.saveProcessInfo(base_layer_process[str(self.prj_id)], tiling_status) 

            start_x = None
            start_y = None
            start_level = self.level_download_all_tiles
                                             

        for zoom in range(start_level, int(maxzoom) + 1, 1):
            xtile, ytile = self._utm2num(min_y, min_x, zoom)
            cpy_ytile = ytile
            final_xtile, final_ytile = self._utm2num(max_y, max_x, zoom)
            if(first_entry == True and start_x != None and start_y != None):
                xtile = start_x
                ytile = start_y - 1
                first_entry = False
      
            #print "%d:%d-%d/%d-%d" % (zoom, xtile, final_xtile, ytile, final_ytile)
            for x in range(xtile, final_xtile + 1, 1):
                for y in range(ytile, final_ytile - 1, -1):  

                    downloadTile = True
                    #Comprueba si el tile ya se bajó. En ese caso pasa al siguiente
                    if tiles_already_download is not None:
                        label = str(zoom) + "_" + str(x) + "_" + str(y)
                        if label in tiles_already_download:
                            print("Tile ya descargado:" + label)
                            downloadTile = False
                        tiles_already_download[label] = True

                    if downloadTile == True:
                        if self.mode == "OSM":
                            self._download_url(zoom, x, y)
                        else:
                            if self._download_wmts(zoom, x, y, format_) is False:
                                return False

                    if base_layer_process is not None:
                        if str(self.prj_id) in base_layer_process:
                            if base_layer_process[str(self.prj_id)]['stop'] == 'true':
                                return False
                            base_layer_process[str(self.prj_id)]['active'] = 'true'
                            base_layer_process[str(self.prj_id)]['processed_tiles'] = base_layer_process[str(self.prj_id)]['processed_tiles'] + 1
                            base_layer_process[str(self.prj_id)]['time'] = self.get_estimated_time(start_time, base_layer_process, init_processed_tiles)
                ytile = cpy_ytile
                self.saveProcessInfo(base_layer_process[str(self.prj_id)], tiling_status)              
     
        return True


    def saveProcessInfo(self, layer_process, tiling_status):
        if(tiling_status is not None):
            tiling_status.processed_tiles = layer_process['processed_tiles']
            tiling_status.time = layer_process['time']
            if tiling_status.processed_tiles == tiling_status.total_tiles:
                tiling_status.active = "false" 
                tiling_status.end_time = timezone.now()
            tiling_status.save()


    def get_estimated_time(self, start_time, base_layer_process, init_processed_tiles):
        """
        Calcula el tiempo estimado de los tiles que faltan por descargar en función de lo que ha tardado los ya descargados.
        Cuando se hace un retry es necesario saber los tiles que ya habia descargados (init_processed_tiles) porque no entran
        en el cálculo de la descarga
        """
        elapsed_time = t() - start_time
        total_tiles = base_layer_process[str(self.prj_id)]['total_tiles']
        
        processed_tiles = base_layer_process[str(self.prj_id)]['processed_tiles'] - init_processed_tiles
        total_tiles = total_tiles - init_processed_tiles

        processed_tiles = min(processed_tiles + 1, total_tiles)
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

     
    def get_number_of_tiles(self, min_x, min_y, max_x, max_y, maxzoom, base_layer_process, count_base=True):
        num_tiles = 0

        #Niveles de 0 al level_download_all_tiles sólo capas WMTS (pq OSM ya están descargados)

        if count_base and self.mode  != "OSM":
            for zoom in range(0, self.level_download_all_tiles, 1):
                xtile, ytile = self._deg2num(float(self.min_lat), float(self.min_lon), zoom)
                final_xtile, final_ytile = self._deg2num(float(self.max_lat), float(self.max_lon), zoom)
                w = abs(final_xtile - xtile) + 1
                h = abs(final_ytile - ytile) + 1
                num_tiles = num_tiles + (w * h)
                        
        #Para cualquier capa base se descargan los siguientes niveles               
        #solo de la extensión del proyecto
        for zoom in range(self.level_download_all_tiles, int(maxzoom) + 1, 1):
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
                'stop' : 'false',
                'format_processed' : base_layer_process[str(self.prj_id)]['format_processed'],
                'extent_processed' : base_layer_process[str(self.prj_id)]['extent_processed'],
                'zoom_levels_processed' : base_layer_process[str(self.prj_id)]['zoom_levels_processed']
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

"""
Dado un extent o una lista de extents en GeoJSON genera un paquete con los tiles de la capa que caen dentro de 
las geometrías. Las geometrías pasadas pueden ser de tipo Polygon o Point. Si son Polygon se usará la extensión
del poligono. Si son de tipo Point se usará la extensión de un buffer definido en una propiedad del geoJson llamada 
buffer con un entero que indique el buffer en metros alrededor de la coordenada. 

Las coordenadas siempre serán en geográficas.

Los niveles de 0 al 4 se empaquetan completos y del 5 en adelante solo los tiles que caen dentro de los polígonos o
puntos con buffer definidos. Si se pasa el parámetro download_first_levels a False no se empaquetan los niveles del
0 al 4.

El objeto process_data es una estructura en la que se va actualizando el número de tiles procesados y otra información
del proceso de descarga y empaquetado
"""

def tiling_layer(version, process_data, lyr, geojson_list, num_res_levels, tilematrixset, format_='image/png', matrixset_prefix=None, properties=None, download_first_levels=True):
    try:
        tasks.tiling_layer_celery_task.apply_async(args=[version, process_data, lyr.id, geojson_list, num_res_levels, tilematrixset, format_, matrixset_prefix, properties, download_first_levels])
    except Exception as e:
        print(e)
        return

def create_status(process_data, id):
    status = TilingProcessStatus()
    status.layer = id
    status.format_processed = process_data['format_processed']
    status.processed_tiles = process_data['processed_tiles']
    status.total_tiles = process_data['total_tiles']
    status.version = process_data['version']
    status.time = process_data['time']
    status.active = process_data['active']
    status.stop = process_data['stop']
    status.extent_processed = process_data['extent_processed']
    status.zoom_levels_processed = process_data['zoom_levels_processed']
    status.start_time = timezone.now()
    status.save()
    return status

def get_extent(json, properties):
    if(json['type'] == 'Polygon'):
        min_lon = float('Inf')
        min_lat = float('Inf')
        max_lon = -float('Inf') 
        max_lat = -float('Inf')
        coords = json['coordinates']
        for coord in coords:
            for c in coord:
                min_lon = min(c[1], min_lon)
                min_lat = min(c[0], min_lat)
                max_lon = max(c[1], max_lon)
                max_lat = max(c[0], max_lat)
        return min_lon, min_lat, max_lon, max_lat
    if(json['type'] == 'Point'):
        try:
            buffer = int(properties['buffer'])
        except Exception:
            buffer = 500

        coords = json['coordinates']
        x, y = transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), coords[1], coords[0])
        minx = x - buffer
        miny = y - buffer
        maxx = x + buffer
        maxy = y + buffer
        min_lon, min_lat = transform(Proj(init='epsg:3857'), Proj(init='epsg:4326'), minx, miny)
        max_lon, max_lat = transform(Proj(init='epsg:3857'), Proj(init='epsg:4326'), maxx, maxy)
        return min_lon, min_lat, max_lon, max_lat

@start_new_thread
def retry_base_layer_tiling(base_layer_process, tiling_data):
    prj = tiling_data.project

    if base_layer_process is not None:
        lyr = Layer.objects.get(id=tiling_data.layer)
        if lyr.datastore is not None:
            url = lyr.datastore.workspace.wmts_endpoint
            if(tiling_data.tilematrixset == 'EPSG:900913'):
                dir = 'EPSG3857'
            else:
                dir = tiling_data.tilematrixset.replace(":", "")
            folder_package = os.path.join(tiling_data.folder_prj, dir)
            start_level, start_x, start_y, processed_tiles = _get_retry_titing_params(folder_package)

            base_layer_process[str(prj.id)] = {
                'active' : 'true',
                'total_tiles' : 0,
                'processed_tiles' : processed_tiles,
                'version' : tiling_data.version,
                'time' : '-',
                'stop' : 'false',
                'format_processed' : tiling_data.format,
                'extent_processed' : tiling_data.extentid,
                'zoom_levels_processed' : tiling_data.levels
            }

            tiling = Tiling(folder_package, lyr.type, tiling_data.tilematrixset, url, tiling_data.project.id)

            if lyr.type != 'OSM':
                tiling.set_layer_name(lyr.datastore.workspace.name + ":" + lyr.name)
                extent = lyr.latlong_extent
                extent = extent.split(',')
                lyr_min_x = float(extent[0])
                lyr_min_y = float(extent[1])
                lyr_max_x = float(extent[2])
                lyr_max_y = float(extent[3])
                tiling.set_layer_extent(lyr_min_x, lyr_min_y, lyr_max_x, lyr_max_y)

            if(tiling_data.extentid == 'project'):
                if prj.extent is not None:
                    bbox = prj.extent.split(',')
                    min_x = float(bbox[0])
                    min_y = float(bbox[1])
                    max_x = float(bbox[2])
                    max_y = float(bbox[3])
                    min_x, min_y, max_x, max_y = _adjustExtent(min_x, min_y, max_x, max_y)
                    number_of_tiles = tiling.get_number_of_tiles(min_x, min_y, max_x, max_y, tiling_data.levels, base_layer_process)    
                    #Genera el tileado a partir de coords en 3857 q es en las que está el extent del proyecto
                    status = tiling.retry_tiles_from_utm(base_layer_process, min_x, min_y, max_x, max_y, tiling_data.levels, tiling_data.format, start_level, start_x, start_y)
            else:
                #Si hay que usar el extent de la capa hay que transformar las coordenadas geográficas a 3857
                inProj = Proj(init='epsg:4326')
                outProj = Proj(init='epsg:3857')
                tile_min_x, tile_min_y = transform(inProj, outProj, lyr_min_x, lyr_min_y)
                tile_max_x, tile_max_y = transform(inProj, outProj, lyr_max_x, lyr_max_y)
                number_of_tiles = tiling.get_number_of_tiles(tile_min_x, tile_min_y, tile_max_x, tile_max_y, tiling_data.levels, base_layer_process) 
                status = tiling.retry_tiles_from_utm(base_layer_process, tile_min_x, tile_min_y, tile_max_x, tile_max_y, tiling_data.levels, tiling_data.format, start_level, start_x, start_y)

            _close_download(base_layer_process, prj, tiling_data.folder_prj, number_of_tiles, tiling_data.version, status)


def _get_retry_titing_params(dir):
    """
    Calcula los parámetros nivel de resolución y tile de inicio (x,y)
    Para reanudar la descarga de la capa
    """
    levels = _sorted_alphanumeric(os.listdir(dir))
    level = levels[len(levels) - 1]

    leveldir = os.path.join(dir, level)
    xlist = _sorted_alphanumeric(os.listdir(leveldir))
    x = xlist[len(xlist) - 1]

    xdir = os.path.join(leveldir, x)
    ylist = _sorted_alphanumeric(os.listdir(xdir))
    y = ylist[0]
    y = y[0:y.rindex(".")]

    return int(level), int(x), int(y), _get_number_of_tiles(dir, levels)


def _sorted_alphanumeric(data):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(data, key=alphanum_key)


def _get_number_of_tiles(dir, levels):
    """
    Obtiene el número de tiles ya descargados en un directorio
    Es necesario calcularlo cuando se reanuda una descarga
    """
    count = 0
    for level in levels:
        leveldir = os.path.join(dir, level)
        xlist = os.listdir(leveldir)
        for x in xlist:
            xdir = os.path.join(leveldir, x)
            xlist = os.listdir(xdir)
            count = count + len(xlist)
    return count

def _delete_pending_downloads(dir, prefix):
    """
    @deprecated: pongo esto deprecated porque al implementar el retry no podemos eliminar los directorios pendientes de descarga
    Borra los directorios pendientes de descarga si se inicia una nueva para evitar acumular basura
    """
    content = os.listdir(dir)
    for file in content:
        path = os.path.join(dir, file)
        if(os.path.isdir(path) and file.startswith(prefix)):
            shutil.rmtree(path)

@start_new_thread
def tiling_base_layer(base_layer_process, base_lyr, prj_id, num_res_levels, tilematrixset, format_='image/png', extentid='project'):
    prj = Project.objects.get(id = prj_id)
    millis = int(round(time.time() * 1000))
    if(tilematrixset == 'EPSG:900913'):
        dir = 'EPSG3857'
    else:
        dir = tilematrixset.replace(":", "")

    url = None
    if base_lyr.datastore is not None:
        url = base_lyr.datastore.workspace.wmts_endpoint
    
    layers_dir = os.path.join(settings.MEDIA_ROOT, settings.LAYERS_ROOT)
    #_delete_pending_downloads(layers_dir, prj.name + "_prj_")
    folder_prj =  os.path.join(layers_dir, prj.name) + "_prj_" + str(millis)
    folder_package = os.path.join(folder_prj, dir)
    if not os.path.exists(layers_dir):
        os.mkdir(layers_dir)
    
    try:
        store = ProjectBaseLayerTiling()
        store.id = prj_id
        store.project = prj
        store.format = format_
        store.extentid = extentid
        store.tilematrixset = tilematrixset
        store.levels = num_res_levels
        store.version = millis
        store.running = True
        store.layer = base_lyr.id 
        store.folder_prj = folder_prj
        store.save()

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
                'stop' : 'false',
                'format_processed' : format_,
                'extent_processed' : extentid,
                'zoom_levels_processed' : num_res_levels
            }

        if(extentid == 'project'):
            if prj.extent is not None:
                bbox = prj.extent.split(',')
                min_x = float(bbox[0])
                min_y = float(bbox[1])
                max_x = float(bbox[2])
                max_y = float(bbox[3])
                min_x, min_y, max_x, max_y = _adjustExtent(min_x, min_y, max_x, max_y)
                number_of_tiles = tiling.get_number_of_tiles(min_x, min_y, max_x, max_y, num_res_levels, base_layer_process)    
                #Genera el tileado a partir de coords en 3857 q es en las que está el extent del proyecto
                status = tiling.retry_tiles_from_utm(base_layer_process, min_x, min_y, max_x, max_y, num_res_levels, format_, None, None, None)
        else:
            #Si hay que usar el extent de la capa hay que transformar las coordenadas geográficas a 3857
            inProj = Proj(init='epsg:4326')
            outProj = Proj(init='epsg:3857')
            tile_min_x, tile_min_y = transform(inProj, outProj, lyr_min_x, lyr_min_y)
            tile_max_x, tile_max_y = transform(inProj, outProj, lyr_max_x, lyr_max_y)
            number_of_tiles = tiling.get_number_of_tiles(tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, base_layer_process) 
            status = tiling.retry_tiles_from_utm(base_layer_process, tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, format_, None, None, None)

        _close_download(base_layer_process, prj, folder_prj, number_of_tiles, millis, status)
    except Exception as e:
        return
        

def _close_download(base_layer_process, prj, folder_prj, number_of_tiles, version, status):
    """
    Acciones de fin de descarga
    - Empaquetado
    - Actualización del interfaz web
    - Salvar la versión
    - Marcar como proceso terminado
    """
    #Empaquetamos y borramos el directorio si no se ha pulsado el botón de stop
    #Si se ha pulsado lo dejamos como está para poder hacer retry cuando se ponga el botón
    if base_layer_process[str(prj.id)]['stop'] == 'false': 
        _zipFolder(folder_prj)

    #Actualiza la estructura de datos de refresco del interfaz web
    if base_layer_process is not None:
        base_layer_process[str(prj.id)] = {
            'active' : 'false',
            'total_tiles' : number_of_tiles,
            'processed_tiles' : number_of_tiles,
            'version' : version,
            'time' : '-',
            'stop' : 'false',
            'format_processed' : '-',
            'extent_processed' : '-',
            'zoom_levels_processed' : '-'
        }

    #Si no se ha parado y ha terminado bien se guarda la nueva versión en Project
    if(status is not False):
        prj.baselayer_version = version
        prj.save()

    #Se guarda en bd como proceso acabado
    store = ProjectBaseLayerTiling.objects.get(id=prj.id)
    store.running = False
    store.save()


def _zipFolder(folder_prj):
    #TODO;
    #Shutil tiene un bug en algunos SO que hace que te meta una carpeta ./ dentro del zip (a los de SAV no les sirve). 
    #A partir de la 3.6 de python está resuelto. Mientras tanto lo hago con ZipFile. Queda pendiente volverlo 
    # a dejar con shutil cuando se migre a python 3 
    #Sería así: shutil.make_archive(folder_prj, 'zip', folder_prj)
    zipf = zipfile.ZipFile(folder_prj + '.zip', 'w', zipfile.ZIP_DEFLATED)
    lenDirPath = len(folder_prj)
    for root, _, files in os.walk(folder_prj):
        for file_ in files:
            filePath = os.path.join(root, file_)
            zipf.write(filePath, filePath[lenDirPath :])
    zipf.close()
    shutil.rmtree(folder_prj)

            
def exists_base_layer_tiled(prj_id):
    prj = Project.objects.get(id = prj_id)
    layers_dir = os.path.join(settings.MEDIA_ROOT, settings.LAYERS_ROOT)
    file_ =  os.path.join(layers_dir, prj.name) + "_prj.zip"
    return os.path.isfile(file_)
                

def _adjustExtent(minx, miny, maxx, maxy):
    """
    Hay ocasiones en que el extent puede ser mayor o menor que el max/min del planeta. Esto es porque OSM
    es un mapa corrido y sin querer puedes centrar el extent del proyecto en el mapa de la derecha o la izda
    Cuando esto pasa te vuelves loco para saber porque los tiles no se están generando por lo que meto está
    función para asegurar que el extent es correcto y si no lo es lo rectifica.
    """
    while minx > 20037508.34 and maxx > 20037508.34:
        minx = minx - 40075016.68
        maxx = maxx - 40075016.68

    while minx < -20037508.34 and maxx < -20037508.34:
        minx = minx + 40075016.68
        maxx = maxx + 40075016.68

    return minx, miny, maxx, maxy

