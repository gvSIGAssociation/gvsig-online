from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt

from views import BrowserView, ExportToDatabaseView, UploadView, UploadFileView, DeleteFileView, DirectoryCreateView, UnzipFileView


urlpatterns = [
    url(r'^$', BrowserView.as_view(), name='browser'),
    #url(r'^pbrowser/$', PopupBrowserView.as_view(), name='pbrowser'),
    url(r'^upload/$', UploadView.as_view(), name='upload'),
    url(r'^upload/file/$', csrf_exempt(UploadFileView.as_view()), name='upload-file'),
    url(r'^delete/file/$', csrf_exempt(DeleteFileView.as_view()), name='delete-file'),
    url(r'^unzip/file/$', csrf_exempt(UnzipFileView.as_view()), name='unzip-file'),
    url(r'^create/directory/$', DirectoryCreateView.as_view(), name='create-directory'),
    url(r'^export_to_database/$', ExportToDatabaseView.as_view(), name='export-to-database'),
]
