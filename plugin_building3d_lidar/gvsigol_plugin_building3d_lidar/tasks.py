import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Optional

# IMPORTANT:
# This project runs Django 2.2; we must avoid importing heavy geo libs at import-time.
# If something like geopandas isn't installed yet, we prefer the server to boot and
# fail only when executing the job, with a clear message.

try:
    from celery import shared_task
except Exception:  # pragma: no cover
    shared_task = None

from django.conf import settings
import logging
from django.core.files.storage import default_storage

from .models import Building3DJob


def _safe_update(job: Building3DJob, **fields):
    for k, v in fields.items():
        setattr(job, k, v)
    job.save(update_fields=list(fields.keys()))

logger = logging.getLogger(__name__)

def _extract_first_shp(shp_zip_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(shp_zip_path, "r") as zf:
        zf.extractall(dest_dir)
    shp_files = sorted(dest_dir.glob("*.shp"))
    if not shp_files:
        raise RuntimeError("El ZIP no contiene un .shp válido.")
    return shp_files[0]


def _run_pdal_dem(lidar_path: Path, out_raster: Path, ground_only: bool, resolution: float = 1.0) -> None:
    try:
        import pdal  # type: ignore
    except Exception:
        raise RuntimeError("PDAL (python bindings) no está instalado/disponible en el entorno.")
    # CRS de entrada del LAS si está configurado (alineado con MiniGis)
    lidar_in_srs = getattr(settings, "LIDAR_IN_SRS", None)
    # Pipeline: lee LAS/LAZ, clasifica suelo (SMRF) y rasteriza
    # Para DSM usamos el máximo; para DTM filtramos a suelo y usamos mínimo/medio.
    readers = [
        {"type": "readers.las", "filename": str(lidar_path)},
    ]
    filters = []
    if ground_only:
        filters.append({"type": "filters.smrf"})  # clasifica ground
        # Filtro de rango a ground
        filters.append({"type": "filters.range", "limits": "Classification[2:2]"})
        writers = [
            {
                "type": "writers.gdal",
                "filename": str(out_raster),
                "resolution": resolution,
                "radius": 1.5,
                "output_type": "min",  # terreno bajo
                "gdaldriver": "GTiff",
                "data_type": "float32",
                "nodata": -9999,
                **({"override_srs": lidar_in_srs} if lidar_in_srs else {}),
            }
        ]
    else:
        # DSM: no filtramos ground; tomamos el valor máximo
        writers = [
            {
                "type": "writers.gdal",
                "filename": str(out_raster),
                "resolution": resolution,
                "radius": 1.5,
                "output_type": "max",
                "gdaldriver": "GTiff",
                "data_type": "float32",
                "nodata": -9999,
                **({"override_srs": lidar_in_srs} if lidar_in_srs else {}),
            }
        ]
    pipeline = {"pipeline": readers + filters + writers}
    p = pdal.Pipeline(json.dumps(pipeline))
    p.execute()


def _raster_math_subtract(a_path: Path, b_path: Path, out_path: Path) -> None:
    try:
        import numpy as np  # noqa
        import rasterio  # noqa
    except ModuleNotFoundError as e:
        raise RuntimeError(f"Falta dependencia para raster (rasterio/numpy): {e}")

    with rasterio.open(a_path) as ra, rasterio.open(b_path) as rb:
        if ra.crs != rb.crs or ra.transform != rb.transform or ra.width != rb.width or ra.height != rb.height:
            raise RuntimeError("Los rasters DSM y DTM no están alineados.")
        data_a = ra.read(1).astype("float32")
        data_b = rb.read(1).astype("float32")
        nd = -9999.0
        mask = (data_a == ra.nodata) | (data_b == rb.nodata)
        ndsm = np.where(mask, nd, data_a - data_b)
        meta = ra.meta.copy()
        meta.update(dtype="float32", nodata=nd)
        with rasterio.open(out_path, "w", **meta) as dst:
            dst.write(ndsm, 1)


def _percentile_90_positive(values) -> Optional[float]:
    # Import lazy para no cargar dependencias geo pesadas al arrancar Django.
    import numpy as np

    if values.size == 0:
        return None
    vals = values[np.isfinite(values)]
    vals = vals[vals > 0.0]
    if vals.size == 0:
        # Fallback: si no hay positivos, calcula p90 de todos los finitos
        vals_all = values[np.isfinite(values)]
        if vals_all.size == 0:
            return 0.0
        return float(np.percentile(vals_all, 90))
    return float(np.percentile(vals, 90))


def _compute_pipeline(job: Building3DJob, job_dir: Path, lidar_path: Path, shp_zip_path: Path) -> Tuple[str, int, Dict[str, float], Path, str]:
    try:
        import numpy as np
        import geopandas as gpd
        from shapely.geometry import mapping
        import rasterio
        from rasterio import mask as rio_mask
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Faltan dependencias geo en el contenedor. Instala geopandas, rasterio, fiona, shapely y sus libs nativas. "
            f"Detalle: {e}"
        )

    work_dir = job_dir / "work"
    out_dir = job_dir / "output"
    shp_dir = work_dir / "shp"
    rasters_dir = work_dir / "rasters"
    for d in (work_dir, out_dir, shp_dir, rasters_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1) Extraer primer shapefile
    _safe_update(job, progress=15, message="Extrayendo Shapefile")
    shp_path = _extract_first_shp(shp_zip_path, shp_dir)

    # 2) Generar DTM y DSM con PDAL
    _safe_update(job, progress=25, message="Generando DTM y DSM con PDAL")
    dtm_path = rasters_dir / "dtm.tif"
    dsm_path = rasters_dir / "dsm.tif"
    _run_pdal_dem(lidar_path, dtm_path, ground_only=True, resolution=1.0)
    _run_pdal_dem(lidar_path, dsm_path, ground_only=False, resolution=1.0)

    # 3) nDSM = DSM - DTM
    _safe_update(job, progress=40, message="Calculando nDSM")
    ndsm_path = rasters_dir / "ndsm.tif"
    _raster_math_subtract(dsm_path, dtm_path, ndsm_path)

    # 4) Leer shapefile, calcular p90 positiva por polígono desde nDSM
    _safe_update(job, progress=55, message="Calculando alturas por edificio")
    gdf = gpd.read_file(str(shp_path))
    features_count = len(gdf)
    alturas: list[Optional[float]] = []
    with rasterio.open(ndsm_path) as src:
        if gdf.crs is None:
            assumed_crs = src.crs or getattr(settings, "LIDAR_IN_SRS", None)
            if assumed_crs is None:
                raise RuntimeError(
                    "El shapefile no tiene CRS y no se pudo inferir uno desde el raster LiDAR."
                )
            gdf = gdf.set_crs(assumed_crs, allow_override=True)

        # Reproyectar polígonos al CRS del raster antes de recortar
        try:
            if gdf.crs is not None and src.crs is not None and gdf.crs != src.crs:
                gdf = gdf.to_crs(src.crs)
        except Exception:
            # Si falla reproyección, continuar con CRS original (podría dar alturas vacías)
            pass
        # Tamaño de píxel para amortiguar polígonos muy pequeños
        try:
            pixel_size = max(abs(src.transform.a), abs(src.transform.e))
        except Exception:
            pixel_size = None
        # Depuración: log de raster y CRS
        try:
            logger.debug("[LiDAR] nDSM crs=%s transform=%s width=%s height=%s nodata=%s",
                         getattr(src, "crs", None), src.transform, src.width, src.height, src.nodata)
            logger.debug("[LiDAR] Footprints crs=%s pixel_size=%s", getattr(gdf, "crs", None), pixel_size)
        except Exception:
            pass
        empty_overlaps = 0
        computed = 0
        for idx, geom in enumerate(gdf.geometry):
            if geom is None or geom.is_empty:
                alturas.append(None)
            else:
                try:
                    # Arreglar geometrías inválidas y amortiguar si son muy pequeñas
                    if not geom.is_valid:
                        geom = geom.buffer(0)
                    if pixel_size:
                        # amortiguar un píxel para asegurar que al menos una celda caiga dentro
                        geom_for_mask = geom.buffer(pixel_size)
                    else:
                        geom_for_mask = geom
                    out_img, out_transform = rio_mask.mask(src, [mapping(geom_for_mask)], crop=True)
                    arr = out_img[0].astype("float32")  # banda única
                    nd = src.nodata
                    if nd is not None:
                        arr = np.where(arr == nd, np.nan, arr)
                    altura = _percentile_90_positive(arr)
                    # Depuración: primeras 3 features imprimimos métricas
                    if computed < 3:
                        try:
                            total = arr.size
                            finite = int(np.isfinite(arr).sum())
                            pos = int(np.nansum(arr > 0))
                            logger.debug("[LiDAR] geom#%s area=%.2f m2, raster cells total=%s finite=%s >0=%s p90=%s",
                                         idx, geom.area if hasattr(geom, "area") else -1, total, finite, pos, altura)
                        except Exception:
                            pass
                    if altura is not None:
                        computed += 1
                    alturas.append(altura)
                except Exception as e:
                    empty_overlaps += 1
                    try:
                        logger.warning("[LiDAR] Error procesando geom#%s: %s", idx, e)
                    except Exception:
                        pass
                    alturas.append(None)
            if features_count:
                step = 15.0 / max(1, features_count)
                new_prog = min(85, int(55 + (idx + 1) * step))
                if new_prog > job.progress:
                    _safe_update(job, progress=new_prog)
        # Resumen de depuración
        try:
            logger.debug("[LiDAR] alturas computed=%s empty_overlaps=%s of %s", computed, empty_overlaps, features_count)
            _safe_update(job, message=f"Alturas calc: {computed}/{features_count}")
        except Exception:
            pass

    if "Altura" not in gdf.columns:
        gdf["Altura"] = alturas
    else:
        gdf["Altura"] = alturas

    # 5) GeoJSON reproyectado a EPSG:4326
    _safe_update(job, progress=88, message="Generando GeoJSON y Shapefile de salida")
    gdf4326 = gdf.to_crs(epsg=4326)
    geojson_str = gdf4326.to_json()

    # Centro de bbox en 4326
    if features_count == 0:
        center = {"lat": 0.0, "lng": 0.0}
    else:
        minx, miny, maxx, maxy = gdf4326.total_bounds
        center = {"lat": float((miny + maxy) / 2.0), "lng": float((minx + maxx) / 2.0)}

    # 6) Shapefile salida conservando CRS original
    shp_out_dir = out_dir / "shp_out"
    shp_out_dir.mkdir(exist_ok=True)
    out_shp = shp_out_dir / "buildings_altura.shp"
    gdf.to_file(out_shp)

    # 7) ZIP
    zip_path = out_dir / "buildings_altura.zip"
    from shutil import make_archive
    make_archive(str(zip_path.with_suffix("")), "zip", shp_out_dir)

    return geojson_str, features_count, center, zip_path, "buildings_altura.zip"


def process_building3d_job(job_id):
    job = Building3DJob.objects.get(id=job_id)
    _safe_update(job, status="running", progress=5, message="Iniciando procesamiento")

    # Resolver rutas reales: aceptar absolutas o relativas al storage
    def _resolve(p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else Path(default_storage.path(p))
    lidar_fs_path = _resolve(job.lidar_file_path)
    zip_fs_path = _resolve(job.buildings_zip_path)
    job_dir = lidar_fs_path.parent
    try:
        _safe_update(job, progress=10, message="Preparando datos")
        geojson_str, features_count, center, zip_path, download_name = _compute_pipeline(
            job=job,
            job_dir=job_dir,
            lidar_path=lidar_fs_path,
            shp_zip_path=zip_fs_path,
        )

        _safe_update(job, progress=95, message="Finalizando resultados")
        _safe_update(
            job,
            result_geojson=geojson_str,
            result_features_count=features_count,
            result_center=center,
            download_path=str(zip_path),
            download_name=download_name,
        )
        _safe_update(job, status="finished", progress=100, message="Listo", finished_at=datetime.utcnow())
    except Exception as exc:
        _safe_update(job, status="failed", message=str(exc), finished_at=datetime.utcnow())
        raise


if shared_task:
    @shared_task(name="gvsigol_plugin_building3d_lidar.process", bind=True)
    def building3d_process_task(self, job_uuid_str: str):
        process_building3d_job(job_uuid_str)


def process_building3d_job_async(job_id):
    # Usa Celery si está disponible, si no ejecuta síncrono
    if shared_task:
        building3d_process_task.delay(str(job_id))  # type: ignore[name-defined]
    else:
        process_building3d_job(job_id)
