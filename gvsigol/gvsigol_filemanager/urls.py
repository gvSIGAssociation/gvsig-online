from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import BrowserView, ExportToDatabaseView, UploadView, UploadFileView, DeleteFileView, DirectoryCreateView, UnzipFileView

app_name="gvsigol_filemanager"
urlpatterns = [
    path('', BrowserView.as_view(), name='browser'),
    #path('pbrowser/', PopupBrowserView.as_view(), name='pbrowser'),
    path('upload/', UploadView.as_view(), name='upload'),
    path('upload/file/', csrf_exempt(UploadFileView.as_view()), name='upload-file'),
    path('delete/file/', csrf_exempt(DeleteFileView.as_view()), name='delete-file'),
    path('unzip/file/', csrf_exempt(UnzipFileView.as_view()), name='unzip-file'),
    path('create/directory/', DirectoryCreateView.as_view(), name='create-directory'),
    path('export_to_database/', ExportToDatabaseView.as_view(), name='export-to-database'),
]
