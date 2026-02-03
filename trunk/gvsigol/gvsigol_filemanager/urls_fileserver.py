from django.urls import path

from .views import download_file, DownloadFile

app_name="gvsigol_filemanager"
urlpatterns = [
    # fileserver URLs are managed by XSendfile and they are served under the /fileserver
    # prefix to simplify deployments
    path('download/<path:filepath>', download_file, name='fdownload'),

    path('api/v1/download/<path:filepath>/', DownloadFile.as_view(), name='fm_download_file'),
]
