from django.urls import path
from . import views

app_name = "gvsigol_plugin_building3d_lidar"

urlpatterns = [
    # Importante: usar prefijo para evitar colisión con /gvsigonline/
    path("building3d-lidar/", views.upload_page, name="upload_page"),
    path("building3d-lidar/api/start/", views.api_start, name="api_start"),
    path("building3d-lidar/api/progress/<uuid:job_id>/", views.api_progress, name="api_progress"),
    path("building3d-lidar/api/download/<uuid:job_id>/", views.api_download, name="api_download"),
]
