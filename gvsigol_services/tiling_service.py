#!/usr/bin/python
# -*- coding: utf-8 -*-
#

from math import floor
import math
import os.path
import shutil
import urllib2
import zipfile

from gvsigol import settings
from gvsigol_core.models import Project


class Tiling():

    mode = "OSM"
    #mode = "WMTS"
    
    directory = None

    def __init__(self, folder):
        if folder is not None:
            self.directory = folder 
        self.tile_url1 = settings.OSM_TILING_1
        self.tile_url2 = settings.OSM_TILING_2
        self.tile_url3 = settings.OSM_TILING_3
        self.tile_url = self.tile_url1
            
    def _deg2num(self, lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
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
    
    def _download_wmts(self, zoom, xtile, ytile):
        #TILEMATRIX=14&TILEROW=3065&TILECOL=4758
        url = "%s&TILEMATRIX=%d&TILECOL=%d&TILEROW=%d" % (self.tile_url, zoom, xtile, ytile)
        dir_path = "%s/%d/%d/" % (self.directory,zoom, xtile)
        download_path = "%s/%d/%d/%d.png" % (self.directory, zoom, xtile, ytile)
        
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        if(not os.path.isfile(download_path)):
            print "downloading %r" % url
            try:
                source = urllib2.urlopen(url)
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
    
    def create_tiles(self, min_lon, min_lat, max_lon, max_lat, maxzoom):
        
    #    from 0 to 6 download all
    #     for zoom in range(6,7,1):
    #         #break;
    #         for x in range(0,2**zoom,1):        
    #             for y in range(0,2**zoom,1):
    #                 if mode == "OSM":
    #                     download_url(zoom, x, y)
    #                 else:
    #                     download_wmts(zoom, x, y)
                    
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
                        self._download_wmts(zoom, x, y)   
                          
                        
    def create_tiles_from_utm(self, min_x, min_y, max_x, max_y, maxzoom):
        # from 6 to 15 ranges
        for zoom in range(7, int(maxzoom)+1, 1):
            xtile, ytile = self._utm2num(min_y, min_x, zoom)
            final_xtile, final_ytile = self._utm2num(max_y, max_x, zoom)
    
            #print "%d:%d-%d/%d-%d" % (zoom, xtile, final_xtile, ytile, final_ytile)
            for x in range(xtile, final_xtile + 1, 1):
                for y in range(ytile, final_ytile - 1, -1):  
                    if self.mode == "OSM":
                        self._download_url(zoom, x, y)
                    else:
                        self._download_wmts(zoom, x, y)     
                        
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


def tiling_base_layer(prj_id, tiles_side):
    prj = Project.objects.get(id = prj_id)
    if prj.extent is not None:
        bbox = prj.extent.split(',')
        min_x = float(bbox[0])
        min_y = float(bbox[1])
        max_x = float(bbox[2])
        max_y = float(bbox[3])
        
        
        layers_dir = os.path.join(settings.MEDIA_ROOT, 'layer_downloads')
        folder_prj =  os.path.join(layers_dir, prj.name) + "_prj"
        folder_package = os.path.join(folder_prj, 'EPSG3857')
        base_zip = os.getcwd() + "/gvsigol/gvsigol_services/static/data/osm_tiles_levels_0-6.zip"
        if not os.path.exists(layers_dir):
            os.mkdir(layers_dir)
        with zipfile.ZipFile(base_zip, 'r') as zipObj:
            zipObj.extractall(path=layers_dir)
            shutil.move(layers_dir + '/tiles_download', folder_package)
            tiling = Tiling(folder_package)
            tiling.create_tiles_from_utm(min_x, min_y, max_x, max_y, tiling.get_zoom_level(floor(max_x - min_x)/1000, tiles_side))
            shutil.make_archive(folder_prj, 'zip', folder_prj)
            shutil.rmtree(folder_prj)
            
def exists_base_layer_tiled(prj_id):
    prj = Project.objects.get(id = prj_id)
    layers_dir = os.path.join(settings.MEDIA_ROOT, 'layer_downloads')
    file_ =  os.path.join(layers_dir, prj.name) + "_prj.zip"
    return os.path.isfile(file_)
                
