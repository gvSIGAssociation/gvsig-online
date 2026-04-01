import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
import tempfile

from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import Building3DJob
from .tasks import process_building3d_job_async


def _jobs_storage_dir() -> Path:
    """
    Usamos MEDIA_ROOT/data para aprovechar el mismo esquema/permisos que otros exports (ej: _tmp_exports).
    Evita PermissionError al crear carpetas directamente en MEDIA_ROOT.
    """
    base = getattr(settings, "MEDIA_ROOT", None) or getattr(settings, "BASE_DIR", ".")
    return Path(base) / "data" / "_tmp_building3d_jobs"

def _get_tmp_folder() -> Path:
    """
    Sigue el patrón de gvsigol_services: usa FILEMANAGER_DIRECTORY o MEDIA_ROOT/data,
    crea _tmp_exports si es posible; si falla, cae a /tmp/_tmp_exports.
    Devuelve un subdirectorio único.
    """
    fileman_dir = getattr(settings, "FILEMANAGER_DIRECTORY", None)
    if not fileman_dir:
        fileman_dir = os.path.join(getattr(settings, "MEDIA_ROOT", "/tmp"), "data")
    base_tmp = os.path.join(fileman_dir, "_tmp_exports")
    try:
        os.makedirs(base_tmp, exist_ok=True)
    except Exception:
        base_tmp = os.path.join(tempfile.gettempdir(), "_tmp_exports")
        os.makedirs(base_tmp, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="exp_", dir=base_tmp))

def upload_page(request):
    return render(request, "building3d_lidar/upload.html", {})


@csrf_exempt
@require_POST
def api_start(request):
    lidar_file = request.FILES.get("lidar_file")
    buildings_zip = request.FILES.get("buildings_zip")

    if lidar_file is None or buildings_zip is None:
        return JsonResponse({"error": "Se requieren 'lidar_file' y 'buildings_zip'."}, status=400)

    # Basic validations
    lidar_name = lidar_file.name.lower()
    if not (lidar_name.endswith(".las") or lidar_name.endswith(".laz")):
        return JsonResponse({"error": "El archivo LiDAR debe ser .las o .laz."}, status=400)

    zip_name = buildings_zip.name.lower()
    if not zip_name.endswith(".zip"):
        return JsonResponse({"error": "El archivo de edificios debe ser un .zip (Shapefile)."}, status=400)

    job = Building3DJob.objects.create(status="pending", progress=0, message="Creado")
    # Carpeta temporal segura (FILEMANAGER_DIRECTORY/_tmp_exports o /tmp/_tmp_exports)
    tmp_dir = _get_tmp_folder() / str(job.id)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    # Guardar LiDAR
    lidar_path = tmp_dir / lidar_file.name
    with open(lidar_path, "wb") as f:
        for chunk in lidar_file.chunks():
            f.write(chunk)
    # Guardar ZIP
    zip_path = tmp_dir / buildings_zip.name
    with open(zip_path, "wb") as f:
        for chunk in buildings_zip.chunks():
            f.write(chunk)

    job.lidar_file_path = str(lidar_path)      # rutas absolutas en FS
    job.buildings_zip_path = str(zip_path)
    job.save(update_fields=["lidar_file_path", "buildings_zip_path"])

    # Enqueue async task (fallback to sync if broker not configured)
    process_building3d_job_async(job.id)

    return JsonResponse(
        {
            "job_id": str(job.id),
            "status": job.status,
            "progress": job.progress,
        }
    )


@require_GET
def api_progress(request, job_id: uuid.UUID):
    try:
        job = Building3DJob.objects.get(id=job_id)
    except Building3DJob.DoesNotExist:
        raise Http404("Job no encontrado")

    data = {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "message": job.message or "",
    }
    if job.status == "finished":
        # Asegurar prefijo absoluto /gvsigonline
        prefix = getattr(settings, "GVSIGOL_PATH", "/gvsigonline") or "/gvsigonline"
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        data.update(
            {
                "features_count": job.result_features_count,
                "center": job.result_center,
                "download_url": request.build_absolute_uri(
                    f"{prefix}/building3d-lidar/api/download/{job.id}/"
                ),
                "download_name": job.download_name,
                "geojson": json.loads(job.result_geojson) if job.result_geojson else None,
            }
        )
    return JsonResponse(data)


@require_GET
def api_download(request, job_id: uuid.UUID):
    try:
        job = Building3DJob.objects.get(id=job_id)
    except Building3DJob.DoesNotExist:
        raise Http404("Job no encontrado")

    if job.status != "finished" or not job.download_path:
        raise Http404("Archivo no disponible")

    file_path = Path(job.download_path)
    if not file_path.exists():
        raise Http404("Archivo no disponible")
    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=job.download_name or file_path.name)
