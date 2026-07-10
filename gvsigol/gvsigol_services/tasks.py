from gvsigol.celery import app as celery_app
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from gvsigol import settings
import time
import json
import os
import zipfile
import shutil
import gvsigol_services.tiling_service as tiling_service #Tiling, create_status, _zipFolder, get_extent
from pyproj import Proj, transform
from gvsigol_services.models import Layer
from gvsigol_core.models import Project
#from gvsigol_services.decorators import start_new_thread
from gvsigol_services import geographic_servers
from gvsigol_services.models import Layer, LayerGroup
from gvsigol_services.utils import set_layer_extent, get_wmts_options_from_layer, get_wmts_options, AuthPatch
import logging
from owslib.wmts import WebMapTileService

logger = logging.getLogger('gvsigol')

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
            start_level =  2 #Para al 1ra geom se descargan los niveles de 0-4 completos pero para las sgtes ya no hace falta
       
        tiling_service._zipFolder(folder_lyr)
    except Exception as e:
        print(e)
        return

@celery_app.task
def check_gdal_env():
    try:
        import osgeo
        gdal_version = osgeo.__version__
        logger.info("GDAL correctly configured. Version {0}".format(gdal_version))
    except:
        logger.exception("GDAL not correclty configured")

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    my_task_name = 'gvsigol_services.tasks.update_layer_info'
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='01',
        hour='4',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*'
    )
    PeriodicTask.objects.get_or_create(
        name=my_task_name,
        task=my_task_name,
        defaults={'crontab': schedule}
    )

def do_layer_cache_clear(layer, server):
    server.clearCache(layer.datastore.workspace.name, layer)
    layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
    server.createOrUpdateGeoserverLayerGroup(layer_group)
    server.clearLayerGroupCache(layer_group.name)

def do_refresh_layer_extent(layer, server):
    try:
        server.updateBoundingBoxFromData(layer)
        (ds_type, layer_info) = server.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, "json")
        set_layer_extent(layer, ds_type, layer_info, server)
        layer.save()
        # restore dynamic grid subsets for gwc layers
        server.set_gwclayer_dynamic_subsets(layer.datastore.workspace, layer.name)
    except Exception as e:
        logger.exception('error refreshing layer info - {0}'.format(str(layer)))

def do_update_thumbnail(layer, server):
    server.updateThumbnail(layer, 'update')

@celery_app.task(bind=True)
def refresh_layer_info(self, layer_id):
    try:
        layer = Layer.objects.select_related("datastore__workspace").get(id=layer_id)
        server = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        do_refresh_layer_extent(layer, server)
        update_internal_wmts_layer_options(layer)
        do_layer_cache_clear(layer, server)
        do_update_thumbnail(layer, server)
        server.reload_nodes()
    except Exception as e:
        logger.exception('error refreshing layer info - layer_id=%s', layer_id)

@celery_app.task(bind=True)
def update_layer_info(self):
    servers = []
    for layer in Layer.objects.all().select_related("datastore__workspace", "layer_group"):
        if layer.external:
            if layer.type == 'WMTS':
                update_external_wmts_layer_options(layer)
            elif layer.type == 'WMS' and layer.cached:
                update_external_cached_wms_wmts_options(layer)
        else:
            try:
                server = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
                do_refresh_layer_extent(layer, server)
                servers.append(server)
            except Exception as e:
                logger.exception('error refreshing layer info - {0}'.format(str(layer)))
            if layer.cached:
                update_internal_wmts_layer_options(layer)
    
    for server in set(servers):
        server.reload_nodes()


def update_internal_wmts_layer_options(layer):
    try:
        # logger.info(f"Updating wmts options for internal layer {layer.id} - {layer.name}")
        wmts_options = get_wmts_options_from_layer(layer)
        if wmts_options:
            external_params = json.loads(layer.external_params) if layer.external_params else {}
            external_params['wmts_options'] = wmts_options
            layer.external_params = json.dumps(external_params)
            layer.save()
    except Exception as e:
        logger.exception(f"Error getting wmts options for layer {layer.id} - {layer.name}")

def update_external_wmts_layer_options(layer):
    try:
        if layer.type == 'WMTS':
            from gvsigol_core.utils import get_absolute_url
            params = json.loads(layer.external_params)
            if params.get('url') and params.get('layers'):
                url = get_absolute_url(params.get('url'))
                auth = AuthPatch(verify=False)
                wmts = WebMapTileService(url, version=settings.WMTS_MAX_VERSION, auth=auth)
                wmts_options = get_wmts_options(wmts, params['layers'])
                if wmts_options:
                    params['wmts_options'] = wmts_options
                    layer.external_params = json.dumps(params)
                    layer.save()
    except Exception as e:
        logger.exception(f"Error getting wmts options for layer {layer.id} - {layer.name}")


def update_external_cached_wms_wmts_options(layer):
    """
    Persist wmts_options for external WMS layers cached in GeoWebCache (GWC layer name = layer.name, e.g. externallayer_<id>).
    Uses this deployment's GeoServer WMTS endpoint (not the remote WMS URL). External layers have no datastore;
    server comes from layer.layer_group.
    """
    try:
        if not (layer.external and layer.type == 'WMS' and layer.cached):
            return False
        if not layer.name or not layer.layer_group_id:
            return False
        layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
        # get_server_by_id returns backend Geoserver(), not Django Server; WMTS URL lives on the model.
        server_model = geographic_servers.get_instance().get_server_model(layer_group.server_id)
        url = server_model.getWmtsEndpoint()
        params = json.loads(layer.external_params) if layer.external_params else {}

        auth = AuthPatch(username=server_model.user, password=server_model.password, verify=False)
        last_error = None
        wmts = None
        for attempt in range(3):
            try:
                wmts = WebMapTileService(url, version=settings.WMTS_MAX_VERSION, auth=auth)
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    "Error reading GWC WMTS capabilities for external cached WMS layer %s - %s (attempt %s/3)",
                    layer.id,
                    layer.name,
                    attempt + 1,
                    exc_info=True,
                )
                if attempt < 2:
                    time.sleep(3)
        if wmts is None:
            raise last_error

        wmts_id = layer.name
        if wmts_id not in wmts.contents:
            for k in wmts.contents.keys():
                if k == wmts_id or k.endswith(':' + wmts_id):
                    wmts_id = k
                    break
        if wmts_id not in wmts.contents:
            logger.warning(
                "WMTS capabilities: layer %r not found (have %d layers). Skipping wmts_options.",
                layer.name,
                len(wmts.contents),
            )
            return False
        wmts_options = get_wmts_options(wmts, wmts_id)
        if wmts_options:
            params = json.loads(layer.external_params) if layer.external_params else {}
            params['wmts_options'] = wmts_options
            layer.external_params = json.dumps(params)
            layer.save(update_fields=['external_params'])
            return True
        logger.warning(
            "WMTS capabilities: empty wmts_options for external cached WMS layer %s - %s",
            layer.id,
            layer.name,
        )
        return False
    except Exception as e:
        logger.exception(
            "Error getting GWC wmts_options for external cached WMS layer %s - %s",
            layer.id,
            layer.name,
        )
        return False


@celery_app.task(bind=True)
def update_wmts_layer_info(self, layer_id):
    layer = Layer.objects.select_related('layer_group').get(id=layer_id)
    if layer.external:
        if layer.type == 'WMTS':
            update_external_wmts_layer_options(layer)
        elif layer.type == 'WMS' and layer.cached:
            update_external_cached_wms_wmts_options(layer)
    else:
        update_internal_wmts_layer_options(layer)


@celery_app.task(bind=True)
def regenerate_cache_for_extent_async(self, layer_id, minx, miny, maxx, maxy, source_epsg=4326):
    """
    Regenerate GeoWebCache for the given extent on a cached layer and/or its layer group (async).
    Called after feature create/update/delete. Truncates:
    - The layer cache if layer.cached is True
    - The layer group cache if layer_group.cached is True
    """
    from gvsigol_services.cache_utils import regenerate_cache_for_extent, regenerate_cache_for_extent_group
    from gvsigol_services.models import Layer

    try:
        layer = Layer.objects.select_related('layer_group').get(id=int(layer_id))
    except Layer.DoesNotExist:
        return

    if layer.cached and not layer.external:
        regenerate_cache_for_extent(layer_id, minx, miny, maxx, maxy, source_epsg)
    if layer.layer_group and layer.layer_group.cached:
        regenerate_cache_for_extent_group(layer.layer_group_id, minx, miny, maxx, maxy, source_epsg)
