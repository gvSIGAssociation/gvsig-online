from django.urls import path

from .views import download_file

app_name="gvsigol_filemanager"
urlpatterns = [
    # fileserver URLs are managed by XSendfile and they are served under the /fileserver
    # prefix to simplify deployments
    path('download/<path:filepath>', download_file, name='fdownload'),
]
