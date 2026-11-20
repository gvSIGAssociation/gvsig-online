# -*- coding: utf-8 -*-


from django.db import migrations
import json
from owslib.wmts import WebMapTileService

PIXEL_SIZE_M = 0.00028  # 0.28 mm
def get_wmts_options(
    wmts, # owslib.wmts.WebMapTileService
    layer_id: str
):

    layer = wmts.contents[layer_id]
    request_encoding = "KVP"
    urls = []

    # ResourceURL (REST)
    resource_urls = getattr(layer, "resourceURLs", None) or getattr(layer, "resourceURL", None)
    if resource_urls:
        for r in resource_urls:
            if getattr(r, "resourceType", None) == "tile":
                urls.append(r.template)
        if urls:
            request_encoding = "REST"

    # KVP fallback
    if not urls:
        op = wmts.getOperationByName("GetTile")
        for method in op.methods:
            if method.get("type") == "Get":
                kvp_url = method.get("url")
                if kvp_url:
                    urls = [kvp_url if kvp_url.endswith("?") else (kvp_url + ("&" if "?" in kvp_url else "?"))]

    def _parse_tlc(tlc):
        """Parse TopLeftCorner from various formats"""
        if isinstance(tlc, (list, tuple)) and len(tlc) >= 2:
            return [float(tlc[0]), float(tlc[1])]
        if isinstance(tlc, str):
            parts = tlc.replace(",", " ").split()
            if len(parts) >= 2:
                return [float(parts[0]), float(parts[1])]
        return None

    def _normalize_projection(crs):
        """Normalize CRS to EPSG:xxxx format"""
        if crs and "EPSG" in crs and ":" in crs:
            parts = crs.split(":")
            code = parts[-1]
            if code.isdigit():
                return f"EPSG:{code}"
        return crs

    # TileMatrixSet & tileGrid
    tile_grids = {}
    for current_matrix_set_id in layer.tilematrixsetlinks.keys():
        tms = wmts.tilematrixsets[current_matrix_set_id]
        # como tilematrix es un diccionario, necesitamos ordenar por scaledenominator para mas seguridad
        matrix_ids_with_and_scale = sorted([
            (matrix_id,
                tms.tilematrix[matrix_id].scaledenominator)
                for matrix_id in tms.tilematrix.keys() ], key=lambda x: x[1], reverse=True)
                
        matrices = [tms.tilematrix[matrix_id] for matrix_id, _ in matrix_ids_with_and_scale]

        if not matrices:
            continue

        # matrixIds (identifiers tal cual)
        matrix_ids = [m.identifier for m in matrices]

        # resolutions (m/px) = ScaleDenominator * 0.00028
        resolutions = [m.scaledenominator * PIXEL_SIZE_M for m in matrices]


        #tile_sizes = [[m.tilewidth, m.tileheight] for m in matrices]
        tile_sizes = [m.tilewidth for m in matrices]
        origins = [m.topleftcorner for m in matrices]

            # Obtener (matrix_id, limit_obj, scaledenominator) para cada límite y ordenar por escala
        if hasattr(layer, "tilematrixsetlinks") and layer.tilematrixsetlinks.get(current_matrix_set_id) \
            and getattr(layer.tilematrixsetlinks.get(current_matrix_set_id), "tilematrixlimits"):

            tilematrixlimits_obj = layer.tilematrixsetlinks.get(current_matrix_set_id).tilematrixlimits
            full_tile_ranges = []
            full_tile_ranges_ol4 = []

            for idx, m in enumerate(matrices):
                
                limit_obj = tilematrixlimits_obj.get(m.identifier, None)
                if limit_obj:
                    mintilecol = int(getattr(limit_obj, "mintilecol", getattr(limit_obj, "mincol", 0)))
                    maxtilecol = int(getattr(limit_obj, "maxtilecol", getattr(limit_obj, "maxcol", 0)))
                    mintilerow = int(getattr(limit_obj, "mintilerow", getattr(limit_obj, "minrow", 0)))
                    maxtilerow = int(getattr(limit_obj, "maxtilerow", getattr(limit_obj, "maxrow", 0)))
                    full_tile_ranges.append({
                            "minX": mintilecol,
                            "maxX": maxtilecol,
                            "minY": mintilerow,
                            "maxY": maxtilerow
                        })
                    full_tile_ranges_ol4.append({
                        "minX": mintilecol,
                        "maxX": maxtilecol,
                        "minY": -(mintilerow+1),
                        "maxY": -(maxtilerow+1)
                    })

                    if idx == len(matrices) - 1: # use the most detailed matrix to calculate the extent
                        scale_denominator = tms.tilematrix[m.identifier].scaledenominator
                        res = scale_denominator * PIXEL_SIZE_M
                        origin = _parse_tlc(matrices[idx].topleftcorner)
                        tile_w = int(matrices[idx].tilewidth)
                        tile_h = int(matrices[idx].tileheight)
                        minx = origin[0] + mintilecol * tile_w * res
                        maxx = origin[0] + (maxtilecol + 1) * tile_w * res
                        miny = origin[1] - (maxtilerow + 1) * tile_h * res
                        maxy = origin[1] - mintilerow * tile_h * res
                        extent = [minx, miny, maxx, maxy]
                    
                else:
                    # when no limits are defined, calculate limits and extent from the matrix grid
                    full_tile_ranges.append( {
                        "minX": 0,
                        "maxX": int(matrices[idx].matrixwidth)-1,
                        "minY": 0,
                        "maxY": -(int(matrices[idx].matrixheight)-1),
                    })
                    if idx == len(matrices) - 1: # use the most detailed matrix to calculate the extent
                        mw = int(matrices[idx].matrixwidth)
                        mh = int(matrices[idx].matrixheight)
                        res = resolutions[idx]
                        origin = _parse_tlc(matrices[idx].topleftcorner)
                        tile_w = int(matrices[idx].tilewidth)
                        tile_h = int(matrices[idx].tileheight)
                        maxx = origin[0] + mw * tile_w * res
                        miny = origin[1] - mh * tile_h * res
                        extent = [origin[0], miny, maxx, origin[1]]
                               
        else:
            # Si no hay límites, calcular extent desde el grid completo
            #origins = [m.topleftcorner for m in matrices]
            full_tile_ranges = None
            origin = _parse_tlc(matrices[0].topleftcorner)
            tile_w = int(matrices[0].tilewidth)
            tile_h = int(matrices[0].tileheight)
            mw = int(matrices[0].matrixwidth)
            mh = int(matrices[0].matrixheight)
            res0 = resolutions[0]
            maxx = origin[0] + mw * tile_w * res0
            miny = origin[1] - mh * tile_h * res0
            extent = [origin[0], miny, maxx, origin[1]]

        # Normalizar proyección
        projection = _normalize_projection(getattr(tms, "crs", None))
        tile_grid = {
                "origin": None,
                "origins": origins,
                "minZoom": 0,
                "maxZoom": len(resolutions) - 1,
                "resolutions": resolutions,
                "tileSize": None,
                "tileSizes": tile_sizes,
                "matrixIds": matrix_ids,
            }

        if full_tile_ranges is None:
            tile_grid['extent'] = extent
        else:
            tile_grid['fullTileRanges'] = full_tile_ranges
            tile_grid['fullTileRanges_ol4'] = full_tile_ranges_ol4
            tile_grid['extent'] = extent
        
        tile_grids[current_matrix_set_id] = {
            "matrixSet": current_matrix_set_id,
            "projection": projection,
            "tileGrid": tile_grid
        }

    options = {
        "urls": urls,
        "layer": layer_id,
        "matrixSets": list(layer.tilematrixsetlinks.keys()),
        "formats": layer.formats,
        "requestEncoding": request_encoding,
        "tileGrids": tile_grids,
        "styles": layer.styles,
        "dimensions": {}
    }
    
    # Limpiar valores None
    options = {k: v for k, v in options.items() if v is not None}
    return options


def fill_wmts_options(apps, schema_editor):
    try:
        Layer = apps.get_model("gvsigol_services", "Layer")
        for layer in Layer.objects.filter(external=True):
            try:
                external_params = json.loads(layer.external_params) if layer.external_params else {}
                if external_params.get('capabilities'):
                    wmts = WebMapTileService(None, xml=json.loads(external_params['capabilities']), version="1.0.0")
                    wmts_options = get_wmts_options(wmts, external_params['layers'])
                    if wmts_options:
                        external_params['wmts_options'] = wmts_options
                        layer.external_params = json.dumps(external_params)
                        layer.save()
            except Exception as error:
                import logging
                logger = logging.getLogger()
                logger.exception("error")
                print(str(error))

    except Exception as error:
        import logging
        logger = logging.getLogger()
        logger.exception("error")
        print(str(error))

class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0076_enumeration_order_type'),
    ]

    operations = [
        migrations.RunPython(fill_wmts_options, reverse_code=migrations.RunPython.noop),
    ]
