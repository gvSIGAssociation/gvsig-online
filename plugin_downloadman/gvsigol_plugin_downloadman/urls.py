from django.conf.urls import url
from gvsigol_plugin_downloadman import views as downman_views

#from views import BrowserView, ExportToDatabaseView, UploadView, UploadFileView, DeleteFileView, DirectoryCreateView


urlpatterns = [
    #url(r'^$', BrowserView.as_view(), name='browser'),
    url(r'^downloadmanager/layer/(?P<layer_id>[\-a-zA-Z0-9]+)/$', downman_views.getLayerDownloadResources, name='get_download_resources'),
    url(r'^downloadmanager/layer/(?P<workspace_name>[|_\-a-zA-Z0-9]+)/(?P<layer_name>[\_\-a-zA-Z0-9]+)/$', downman_views.getWsLayerDownloadResources, name='get_download_resources_layer_name'),
    url(r'^downloadmanager/$', downman_views.requestDownload, name='download_manager_base'),
    url(r'^downloadmanager/request/$', downman_views.requestDownload, name='request_download'),
    url(r'^downloadmanager/request/(?P<uuid>[\-a-zA-Z0-9]+)/status/$', downman_views.requestTracking, name='download-request-tracking'),
    url(r'^downloadmanager/request/(?P<uuid>[\-a-zA-Z0-9]+)/resource/(?P<resuuid>[\-a-zA-Z0-9]+)$', downman_views.downloadResource, name='downman-download-resource'),
    url(r'^downloadmanager/dashboard/index/$', downman_views.dashboard_index, name='downman-dashboard-index'),
    url(r'^downloadmanager/dashboard/update/(?P<request_id>[\-a-zA-Z0-9]+)/$', downman_views.update_request, name='downman-update-request'),
    url(r'^downloadmanager/dashboard/settings-update/$', downman_views.settings_store, name='downman-settings-store'),
    #url(r'^downloadmanager/request/(?P<uuid>[\-a-zA-Z0-9]+)/$', downman_views.downloadLink, name='download-link'),
    #url(r'^upload/$', UploadView.as_view(), name='upload'),
    #url(r'^upload/file/$', csrf_exempt(UploadFileView.as_view()), name='upload-file'),
    #url(r'^delete/file/$', csrf_exempt(DeleteFileView.as_view()), name='delete-file'),
    #url(r'^create/directory/$', DirectoryCreateView.as_view(), name='create-directory'),
    #url(r'^export_to_database/$', ExportToDatabaseView.as_view(), name='export-to-database'),
]
