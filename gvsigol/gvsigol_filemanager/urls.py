from django.conf.urls import url, patterns
from django.views.decorators.csrf import csrf_exempt

from views import BrowserView, DetailView, UploadView, UploadFileView, DeleteFileView, DirectoryCreateView


urlpatterns = patterns('',
    url(r'^$', BrowserView.as_view(), name='browser'),
    url(r'^detail/$', DetailView.as_view(), name='detail'),
    url(r'^upload/$', UploadView.as_view(), name='upload'),
    url(r'^upload/file/$', csrf_exempt(UploadFileView.as_view()), name='upload-file'),
    url(r'^delete/file/$', csrf_exempt(DeleteFileView.as_view()), name='delete-file'),
    url(r'^create/directory/$', DirectoryCreateView.as_view(), name='create-directory'),
)
