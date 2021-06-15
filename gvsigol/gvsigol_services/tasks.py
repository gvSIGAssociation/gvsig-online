from gvsigol.celery import app as celery_app
from gvsigol import settings
import time
import json
import os
import zipfile
import shutil
import gvsigol_services.tiling_service as ts_ #Tiling, create_status, _zipFolder, get_extent
from pyproj import Proj, transform
from gvsigol_services.models import Layer

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
        return

@celery_app.task
def tiling_layer_celery_task(version, process_data, lyr_id, geojson_list, num_res_levels, tilematrixset, format_, matrixset_prefix, properties, download_first_levels):
    MAX_TILES_PACKAGE = 16384
    lyr = Layer.objects.get(id=lyr_id)
    
    if(version is None):
        version = int(round(time.time() * 1000))

    url = None
    if lyr.datastore is not None:
        url = lyr.datastore.workspace.wmts_endpoint
        lyr_name = lyr.datastore.workspace.name + ":" + lyr.name
    else:
        ext_lyr = json.loads(lyr.external_params)
        lyr_name = ext_lyr['layers']
        url = ext_lyr['url']
    
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
            tiling = ts_.Tiling(folder_package, mode, tilematrixset, url, identif)
            tiling.set_matrixset_prefix(matrixset_prefix)
            if mode != 'OSM':
                tiling.set_layer_name(lyr_name)
                extent = lyr.latlong_extent
                extent = extent.split(',')
                tiling.set_layer_extent(float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3]))

            min_lon, min_lat, max_lon, max_lat = ts_.get_extent(geojson, properties) 
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

        tiling_status = ts_.create_status(process_data[str(identif)], lyr.id)

        if(number_of_tiles == 0):
            return 

        if(download_first_levels == False):
            start_level = 2
        tiles_already_downloaded = {}
        for t in tilingList:
            t['tiling'].retry_tiles_from_utm(process_data, t['tile_min_x'], t['tile_min_y'], t['tile_max_x'], t['tile_max_y'], num_res_levels, format_, start_level, None, None, tiling_status, tiles_already_downloaded)
            start_level =  2 #Para al 1ra geom se descargan los niveles de 0-4 completos pero para las sgtes ya no hace falta
       
        ts_._zipFolder(folder_lyr)
    except Exception as e:
        print(e)
        return
        