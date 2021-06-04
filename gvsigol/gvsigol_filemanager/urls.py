from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import BrowserView, ExportToDatabaseView, UploadView, UploadFileView, DeleteFileView, DirectoryCreateView, UnzipFileView, download_file

app_name="gvsigol_filemanager"
urlpatterns = [
    path('', BrowserView.as_view(), name='browser'),
    #path('pbrowser/', PopupBrowserView.as_view(), name='pbrowser'),
    path('upload/', UploadView.as_view(), name='upload'),
    path('upload/file/', UploadFileView.as_view(), name='upload-file'),
    path('delete/file/', DeleteFileView.as_view(), name='delete-file'),
    path('unzip/file/', UnzipFileView.as_view(), name='unzip-file'),
    path('create/directory/', DirectoryCreateView.as_view(), name='create-directory'),
    path('export_to_database/', ExportToDatabaseView.as_view(), name='export-to-database'),
    path('download/<path:filepath>', download_file, name='fdownload'),
]
