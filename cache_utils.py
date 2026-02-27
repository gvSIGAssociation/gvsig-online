# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    Utilities for cache regeneration after feature edits.
    Regenerates only the affected extent (with buffer) for cached layers.
'''

import logging
from gvsigol import settings
from gvsigol_services.models import Layer, LayerGroup, Server
from gvsigol_services import geographic_servers
from gvsigol_services import rest_geowebcache as geowebcache
from gvsigol_services.rest_geowebcache import FailedRequestError

logger = logging.getLogger('gvsigol')

# Buffer: 1% of extent on each side
# EPSG:3857 (meters): minimum 50m for points/very small features
# EPSG:4326 (degrees): ~0.0005° ≈ 55m at equator
BUFFER_PCT = 0.01
MIN_BUFFER_METERS = 50
MIN_BUFFER_DEGREES = 0.0005


def get_geojson_geometry_extent(geom):
    """
    Extract (minx, miny, maxx, maxy) from a GeoJSON geometry.
    Returns None if geometry is empty or invalid.
    """
    if not geom or geom == 'null' or (isinstance(geom, dict) and geom.get('type') == 'null'):
        return None

    coords = []

    def extract_coords(g):
        gtype = g.get('type')
        gcoords = g.get('coordinates')
        if not gcoords:
            return
        if gtype == 'Point':
            coords.append(gcoords)
        elif gtype == 'LineString':
            coords.extend(gcoords)
        elif gtype == 'MultiPoint':
            coords.extend(gcoords)
        elif gtype == 'Polygon':
            for ring in gcoords:
                coords.extend(ring)
        elif gtype == 'MultiLineString':
            for line in gcoords:
                coords.extend(line)
        elif gtype == 'MultiPolygon':
            for poly in gcoords:
                for ring in poly:
                    coords.extend(ring)
        elif gtype == 'GeometryCollection':
            for child in g.get('geometries', []):
                extract_coords(child)

    try:
        extract_coords(geom)
        if not coords:
            return None

        xs = []
        ys = []
        for c in coords:
            if isinstance(c, (list, tuple)):
                if len(c) >= 2:
                    xs.append(float(c[0]))
                    ys.append(float(c[1]))
                elif len(c) == 1 and isinstance(c[0], (list, tuple)) and len(c[0]) >= 2:
                    xs.append(float(c[0][0]))
                    ys.append(float(c[0][1]))
            else:
                return None

        if not xs or not ys:
            return None

        return (min(xs), min(ys), max(xs), max(ys))
    except (TypeError, ValueError, KeyError) as e:
        logger.warning("Could not extract extent from geometry: %s", e)
        return None


def _transform_extent(minx, miny, maxx, maxy, source_epsg, target_epsg):
    """Transform extent from source_epsg to target_epsg."""
    if source_epsg == target_epsg:
        return (minx, miny, maxx, maxy)

    try:
        try:
            from pyproj import Transformer
            transformer = Transformer.from_crs(
                "EPSG:{}".format(source_epsg),
                "EPSG:{}".format(target_epsg),
                always_xy=True
            )
            x1, y1 = transformer.transform(minx, miny)
            x2, y2 = transformer.transform(maxx, maxy)
        except ImportError:
            from pyproj import Proj, transform
            src = Proj("EPSG:{}".format(source_epsg))
            dst = Proj("EPSG:{}".format(target_epsg))
            x1, y1 = transform(src, dst, minx, miny)
            x2, y2 = transform(src, dst, maxx, maxy)
        return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    except Exception as e:
        logger.warning("Could not transform extent from EPSG:%s to EPSG:%s: %s",
                       source_epsg, target_epsg, e)
        return None


def _apply_buffer_to_extent(minx, miny, maxx, maxy, buffer_pct, min_buffer):
    """
    Apply buffer to extent. min_buffer units match the extent CRS
    (meters for projected e.g. EPSG:3857, degrees for geographic e.g. EPSG:4326).
    """
    width = maxx - minx
    height = maxy - miny

    buf_x = max(width * buffer_pct, min_buffer)
    buf_y = max(height * buffer_pct, min_buffer)

    if width < 1e-10:
        buf_x = min_buffer
    if height < 1e-10:
        buf_y = min_buffer

    return (
        minx - buf_x,
        miny - buf_y,
        maxx + buf_x,
        maxy + buf_y
    )


def _parse_epsg_from_grid_set(grid_set):
    """Extract EPSG code from grid set string (e.g. 'EPSG:3857' -> 3857)."""
    try:
        return int(grid_set.split(':')[1])
    except (IndexError, ValueError):
        return 3857


def _get_min_buffer_for_epsg(target_epsg):
    """
    Return minimum buffer value (meters or degrees) for the given EPSG.
    Uses crs_definitions.json 'units' field for robust handling of any CRS.
    """
    crs_def = getattr(settings, 'crs_definitions_json', None)
    if not crs_def:
        try:
            import json
            import os
            path = os.path.join(os.path.dirname(settings.__file__), 'crs_definitions.json')
            with open(path, 'r') as f:
                crs_def = json.load(f)
        except Exception as e:
            logger.warning("Could not load crs_definitions.json for buffer units: %s", e)
            return MIN_BUFFER_DEGREES  # safe fallback for geographic

    srid_str = str(target_epsg)
    entry = crs_def.get(srid_str) if crs_def else None
    if not entry:
        logger.warning("EPSG:%s not in crs_definitions.json, using degrees buffer", target_epsg)
        return MIN_BUFFER_DEGREES

    units = entry.get('units', '').lower()
    if units == 'meters':
        return MIN_BUFFER_METERS
    return MIN_BUFFER_DEGREES


def _effective_grid_subsets(grid_subsets):
    """
    GWC configs vary: some use EPSG:3857, some EPSG:900913 for Web Mercator.
    When 3857 is requested, also try 900913 so truncate works regardless of GWC config.
    """
    effective = list(grid_subsets)
    if 'EPSG:3857' in effective and 'EPSG:900913' not in effective:
        effective.append('EPSG:900913')
    return effective


def _truncate_extent_by_grid_sets(server, minx, miny, maxx, maxy, source_epsg, execute_fn, target_name):
    """
    Common truncate loop: for each grid set, transform extent, apply buffer, call execute_fn.
    execute_fn(node_url, minx_b, miny_b, maxx_b, maxy_b, gwc_grid_set, format_, zoom_start,
               zoom_stop, op_type, truncate_thread_count) performs the GWC truncate.
    target_name is used in log messages (e.g. "layer 123" or "group mygroup").
    """
    format_ = settings.CACHE_OPTIONS['FORMATS'][0]
    grid_subsets = settings.CACHE_OPTIONS['GRID_SUBSETS']
    effective_subsets = _effective_grid_subsets(grid_subsets)
    zoom_start = '0'
    zoom_stop = str(settings.MAX_ZOOM_LEVEL)
    op_type = 'truncate'
    truncate_thread_count = '1'

    if settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ONLY_MASTER':
        master_node = geographic_servers.get_instance().get_master_node(server.id)
        node_urls = [master_node.getUrl()]
    elif settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ALL_NODES':
        all_nodes = geographic_servers.get_instance().get_all_nodes(server.id)
        node_urls = [n.getUrl() for n in all_nodes]
    else:
        return False

    for grid_set in effective_subsets:
        target_epsg = _parse_epsg_from_grid_set(grid_set)
        extent = _transform_extent(minx, miny, maxx, maxy, source_epsg, target_epsg)
        if not extent:
            logger.warning("Skipping grid set %s: could not transform extent", grid_set)
            continue

        min_buffer = _get_min_buffer_for_epsg(target_epsg)
        minx_b, miny_b, maxx_b, maxy_b = _apply_buffer_to_extent(
            *extent, BUFFER_PCT, min_buffer
        )

        try:
            for node_url in node_urls:
                execute_fn(node_url, str(minx_b), str(miny_b), str(maxx_b), str(maxy_b),
                          grid_set, format_, zoom_start, zoom_stop, op_type, truncate_thread_count)
        except FailedRequestError as e:
            msg = e.server_message.decode('utf-8', 'replace') if isinstance(e.server_message, bytes) else str(e.server_message)
            if 'Unknown grid set' in msg:
                logger.warning("Skipping grid set %s (%s): not configured in GeoWebCache (%s)",
                              grid_set, target_name, msg.strip())
            else:
                raise

    logger.info("Cache truncate (extent only) triggered for %s (grid sets: %s)",
                target_name, ', '.join(effective_subsets))
    return True


def regenerate_cache_for_extent(layer_id, minx, miny, maxx, maxy, source_epsg=4326):
    """
    Regenerate GeoWebCache for the given extent on a cached layer.
    Only runs if layer.cached is True.
    Extent is in source_epsg (by default 4326).
    For each grid set, bounds are transformed to that grid set's CRS before truncating.
    """
    try:
        layer = Layer.objects.select_related('datastore__workspace', 'layer_group').get(id=int(layer_id))
    except Layer.DoesNotExist:
        logger.warning("Layer %s not found for cache regeneration", layer_id)
        return False

    if not layer.cached:
        return False

    if layer.external:
        return False

    try:
        layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
        server = Server.objects.get(id=layer_group.server_id)
    except (LayerGroup.DoesNotExist, Server.DoesNotExist) as e:
        logger.warning("Server/layergroup not found for layer %s: %s", layer_id, e)
        return False

    ws = layer.datastore.workspace.name if layer.datastore and layer.datastore.workspace else None

    def execute_layer_truncate(node_url, minx_b, miny_b, maxx_b, maxy_b, gwc_grid_set,
                               format_, zoom_start, zoom_stop, op_type, truncate_thread_count):
        geowebcache.get_instance().execute_cache_operation(
            ws, layer, server, node_url,
            minx_b, miny_b, maxx_b, maxy_b,
            gwc_grid_set, zoom_start, zoom_stop, format_, op_type, truncate_thread_count
        )

    try:
        return _truncate_extent_by_grid_sets(
            server, minx, miny, maxx, maxy, source_epsg,
            execute_layer_truncate, "layer %s" % layer_id
        )
    except Exception as e:
        logger.exception("Error regenerating cache for layer %s: %s", layer_id, e)
        return False


def regenerate_cache_for_extent_group(layer_group_id, minx, miny, maxx, maxy, source_epsg=4326):
    """
    Truncate GeoWebCache for the given extent on a cached layer group.
    Only runs if layer_group.cached is True.
    Used when a feature is edited in a layer belonging to a cached group.
    """
    try:
        layer_group = LayerGroup.objects.get(id=int(layer_group_id))
    except LayerGroup.DoesNotExist:
        logger.warning("LayerGroup %s not found for cache regeneration", layer_group_id)
        return False

    if not layer_group.cached:
        return False

    try:
        server = Server.objects.get(id=layer_group.server_id)
    except Server.DoesNotExist as e:
        logger.warning("Server not found for layer group %s: %s", layer_group_id, e)
        return False

    def execute_group_truncate(node_url, minx_b, miny_b, maxx_b, maxy_b, gwc_grid_set,
                               format_, zoom_start, zoom_stop, op_type, truncate_thread_count):
        geowebcache.get_instance().execute_group_cache_operation(
            layer_group, server, node_url,
            minx_b, miny_b, maxx_b, maxy_b,
            gwc_grid_set, zoom_start, zoom_stop, format_, op_type, truncate_thread_count
        )

    try:
        return _truncate_extent_by_grid_sets(
            server, minx, miny, maxx, maxy, source_epsg,
            execute_group_truncate, "layer group %s" % layer_group.name
        )
    except Exception as e:
        logger.exception("Error regenerating cache for layer group %s: %s", layer_group_id, e)
        return False
