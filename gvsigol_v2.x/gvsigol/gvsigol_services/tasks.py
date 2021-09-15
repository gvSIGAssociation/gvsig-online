#!/usr/bin/python
# -*- coding: utf-8 -*-
#
from gvsigol.celery import app as celery_app
from gvsigol import settings
import time
import json
import os
import zipfile
import shutil
from gvsigol_services import tiling_service as tiling_service #Tiling, create_status, _zipFolder, get_extent
from pyproj import Proj, transform
from gvsigol_services.models import Layer
from celery.utils.log import get_task_logger
from gvsigol_core.models import Project, ProjectBaseLayerTiling
from gvsigol_services.decorators import start_new_thread
logger = get_task_logger(__name__)

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
        #tiling_layer_celery_task(version, process_data, lyr.id, geojson_list, num_res_levels, tilematrixset, format_, matrixset_prefix, properties, download_first_levels)
        tiling_layer_celery_task.apply_async(args=[version, process_data, lyr.id, geojson_list, num_res_levels, tilematrixset, format_, matrixset_prefix, properties, download_first_levels])
    except Exception as e:
        raise RuntimeError 


#@start_new_thread
def retry_tiles_from_utm(base_layer_process, 
    tile_min_x, 
    tile_min_y, 
    tile_max_x, 
    tile_max_y, 
    num_res_levels, 
    format_, start_level, 
    start_x, 
    start_y, 
    tiling_status,
    prj, folder_prj, version, tiling):
     try:
        #retry_tiles_from_utm_celery_task(base_layer_process, tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, format_, start_level, start_x, start_y, tiling_status, prj, folder_prj, version, tiling)
        retry_tiles_from_utm_celery_task.apply_async(args=[base_layer_process, tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, format_, start_level, start_x, start_y, tiling_status, prj, folder_prj, version, tiling])
     except Exception as e:
        raise RuntimeError 


@celery_app.task
def tiling_layer_celery_task(version, process_data, lyr_id, geojson_list, num_res_levels, tilematrixset, format_, matrixset_prefix, properties, download_first_levels):
    MAX_TILES_PACKAGE = 16384
    lyr = Layer.objects.get(id=lyr_id)

    if(version is None):
        version = int(round(time.time() * 1000))

    url = None
    if lyr.datastore is not None:
        #url = lyr.datastore.workspace.wmts_endpoint
        url = lyr.datastore.workspace.server.getWmtsEndpoint()
        lyr_name = lyr.datastore.workspace.name + ":" + lyr.name
    else:
        try:
            ext_lyr = json.loads(lyr.external_params)
            lyr_name = ext_lyr['layers']
            url = ext_lyr['url']
        except Exception:
            pass
    
    layers_dir = os.path.join(settings.MEDIA_ROOT, settings.LAYERS_ROOT)
    folder_lyr =  os.path.join(layers_dir, lyr.name) + "_lyr_" + str(version)
    folder_package = os.path.join(folder_lyr, 'EPSG3857')
    if not os.path.exists(layers_dir):
        os.mkdir(layers_dir)
    
    try:
        identif = "lyr_" + str(lyr.id)
        mode = lyr.type
        
        #num_res_levels = tiling.get_zoom_level(floor(max_x - min_x)/1000, tiles_side) 
        
        if mode == 'OSM':
            base_zip = os.getcwd() + "/gvsigol_services/static/data/osm_tiles_levels_0-6.zip"
            with zipfile.ZipFile(base_zip, 'r') as zipObj:
                zipObj.extractall(path=layers_dir)
                shutil.move(layers_dir + '/tiles_download', folder_package)

        if process_data is not None:
            process_data[str(identif)] = {
                'active' : 'true',
                'total_tiles' : 0,
                'processed_tiles' : 0,
                'version' : version,
                'time' : '-',
                'stop' : 'false',
                'format_processed' : format_,
                'extent_processed' : 'geometries',
                'zoom_levels_processed' : num_res_levels
            }

        number_of_tiles = 0
        tilingList = [] 
        for geojson in geojson_list:
            tiling = tiling_service.Tiling(folder_package, mode, tilematrixset, url, identif)
            tiling.set_matrixset_prefix(matrixset_prefix)
            if mode != 'OSM':
                tiling.set_layer_name(lyr_name)
                extent = lyr.latlong_extent
                extent = extent.split(',')
                tiling.set_layer_extent(float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3]))

            min_lon, min_lat, max_lon, max_lat = tiling_service.get_extent(geojson, properties) 
            tile_min_x, tile_min_y = transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), min_lon, min_lat)
            tile_max_x, tile_max_y = transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), max_lon, max_lat)
            count_base_level = True if (number_of_tiles == 0 and download_first_levels == True) else False
            number_of_tiles = number_of_tiles + tiling.get_number_of_tiles(tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, process_data, count_base_level) 
            tilingList.append({
                'tiling': tiling,
                'tile_min_x': tile_min_x,
                'tile_min_y': tile_min_y,
                'tile_max_x': tile_max_x,
                'tile_max_y': tile_max_y
            })

        if(number_of_tiles == 0):
            process_data[str(identif)]['active'] = 'false' 

        process_data[str(identif)]['total_tiles'] = number_of_tiles

        start_level = 0

        if(number_of_tiles > MAX_TILES_PACKAGE):
            process_data[str(identif)]['extent_processed'] = 'too_many_tiles'
            process_data[str(identif)]['stop'] = 'true'

        tiling_status = tiling_service.create_status(process_data[str(identif)], lyr.id)

        if(number_of_tiles == 0):
            return 

        if(download_first_levels == False):
            start_level = 2
        tiles_already_downloaded = {}
        for t in tilingList:
            t['tiling'].retry_tiles_from_utm(process_data, t['tile_min_x'], t['tile_min_y'], t['tile_max_x'], t['tile_max_y'], num_res_levels, format_, start_level, None, None, tiling_status, tiles_already_downloaded)
            start_level =  2 #Para al 1ra geom se descargan los niveles de 0-1 completos pero para las sgtes ya no hace falta
       
        tiling_service._zipFolder(folder_lyr)
    except Exception as e:
        logger.exception(str(e))
        print e
        return

@celery_app.task
def retry_tiles_from_utm_celery_task(base_layer_process, 
    tile_min_x, 
    tile_min_y, 
    tile_max_x, 
    tile_max_y, 
    num_res_levels, 
    format_, start_level, 
    start_x, 
    start_y, 
    tiling_status,
    prj, folder_prj, version, tiling):
     status = tiling.retry_tiles_from_utm(base_layer_process, tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, format_, start_level, start_x, start_y, tiling_status)
     tiling_service._close_download(base_layer_process, prj, folder_prj, version, status)


def retry_base_layer_tiling(base_layer_process, tiling_data, tiling_status):
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
            start_level, start_x, start_y, processed_tiles = tiling_service._get_retry_titing_params(folder_package)

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

            tiling = tiling_service.Tiling(folder_package, lyr.type, tiling_data.tilematrixset, url, tiling_data.project.id)

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
                    min_x, min_y, max_x, max_y = tiling_service._adjustExtent(min_x, min_y, max_x, max_y)
                    number_of_tiles = tiling.get_number_of_tiles(min_x, min_y, max_x, max_y, tiling_data.levels, base_layer_process)    
                    #Genera el tileado a partir de coords en 3857 q es en las que está el extent del proyecto
                    status = retry_tiles_from_utm(base_layer_process, min_x, min_y, max_x, max_y, tiling_data.levels, tiling_data.format, 
                        start_level, start_x, start_y, tiling_status, prj, tiling_data.folder_prj, tiling_data.version, tiling)
            else:
                #Si hay que usar el extent de la capa hay que transformar las coordenadas geográficas a 3857
                inProj = Proj(init='epsg:4326')
                outProj = Proj(init='epsg:3857')
                tile_min_x, tile_min_y = transform(inProj, outProj, lyr_min_x, lyr_min_y)
                tile_max_x, tile_max_y = transform(inProj, outProj, lyr_max_x, lyr_max_y)
                number_of_tiles = tiling.get_number_of_tiles(tile_min_x, tile_min_y, tile_max_x, tile_max_y, tiling_data.levels, base_layer_process) 
                status = retry_tiles_from_utm(base_layer_process, tile_min_x, tile_min_y, tile_max_x, tile_max_y, tiling_data.levels, tiling_data.format, 
                    start_level, start_x, start_y, tiling_status, prj, tiling_data.folder_prj, tiling_data.version, tiling)

            #tiling_service._close_download(base_layer_process, prj, tiling_data.folder_prj, number_of_tiles, tiling_data.version, status)


def tiling_base_layer(base_layer_process, version, base_lyr, prj_id, num_res_levels, tilematrixset, format_='image/png', extentid='project'):
    prj = Project.objects.get(id = prj_id)
    if(tilematrixset == 'EPSG:900913'):
        dir = 'EPSG3857'
    else:
        dir = tilematrixset.replace(":", "")

    url = None
    if base_lyr.datastore is not None:
        url = base_lyr.datastore.workspace.wmts_endpoint
    
    layers_dir = os.path.join(settings.MEDIA_ROOT, settings.LAYERS_ROOT)
    #_delete_pending_downloads(layers_dir, prj.name + "_prj_")
    folder_prj =  os.path.join(layers_dir, prj.name) + "_prj_" + str(version)
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
        store.version = version
        store.running = True
        store.layer = base_lyr.id 
        store.folder_prj = folder_prj
        store.save()

        mode = base_lyr.type
        tiling = tiling_service.Tiling(folder_package, mode, tilematrixset, url, prj_id)
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
            
        
        base_layer_process[str(prj_id)] = {
            'active' : 'true',
            'total_tiles' : 0,
            'processed_tiles' : 0,
            'version' : version,
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
                min_x, min_y, max_x, max_y = tiling_service._adjustExtent(min_x, min_y, max_x, max_y)
                number_of_tiles = tiling.get_number_of_tiles(min_x, min_y, max_x, max_y, num_res_levels, base_layer_process) 
                base_layer_process = tiling_service.load_number_of_tiles(base_layer_process, prj_id, number_of_tiles)   
                tiling_status = tiling_service.create_status(base_layer_process[str(prj_id)], base_lyr.id)
                #Genera el tileado a partir de coords en 3857 q es en las que está el extent del proyecto
                status = retry_tiles_from_utm(base_layer_process, min_x, min_y, max_x, max_y, num_res_levels, format_, 
                        None, None, None, tiling_status, prj, folder_prj, version, tiling)
        else:
            #Si hay que usar el extent de la capa hay que transformar las coordenadas geográficas a 3857
            inProj = Proj(init='epsg:4326')
            outProj = Proj(init='epsg:3857')
            tile_min_x, tile_min_y = transform(inProj, outProj, lyr_min_x, lyr_min_y)
            tile_max_x, tile_max_y = transform(inProj, outProj, lyr_max_x, lyr_max_y)
            number_of_tiles = tiling.get_number_of_tiles(tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, base_layer_process) 
            base_layer_process = tiling_service.load_number_of_tiles(base_layer_process, prj_id, number_of_tiles)  
            tiling_status = tiling_service.create_status(base_layer_process[str(prj_id)], base_lyr.id) 
            status = retry_tiles_from_utm(base_layer_process, tile_min_x, tile_min_y, tile_max_x, tile_max_y, num_res_levels, format_, 
                    None, None, None, tiling_status, prj, folder_prj, version, tiling)

       
    except Exception as e:
        return






        

