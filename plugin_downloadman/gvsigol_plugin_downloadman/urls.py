from django.conf.urls import url
from gvsigol_plugin_downloadman import views as downman_views


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
    url(r'^downloadmanager/request/(?P<request_id>[\-a-zA-Z0-9]+)/cancel/$', downman_views.cancel_request, name='download-request-cancel'),
    url(r'^downloadmanager/link/(?P<link_id>[\-a-zA-Z0-9]+)/cancel/$', downman_views.cancel_link, name='download-link-cancel'),
    url(r'^downloadmanager/resource/(?P<resource_id>[\-a-zA-Z0-9]+)/cancel/$', downman_views.cancel_locator, name='download-resource-cancel'),
    url(r'^downloadmanager/resource-authorization/(?P<resource_id>[\-a-zA-Z0-9]+)/accept/$', downman_views.accept_resource_authorization, name='resource-authorization-accept'),
    url(r'^downloadmanager/resource-authorization/(?P<resource_id>[\-a-zA-Z0-9]+)/reject/$', downman_views.reject_resource_authorization, name='resource-authorization-reject'),
    url(r'^downloadmanager/generic-request/(?P<request_id>[\-a-zA-Z0-9]+)/completed/$', downman_views.complete_generic_request, name='generic-request-completed'),
    url(r'^downloadmanager/generic-request/(?P<request_id>[\-a-zA-Z0-9]+)/rejected/$', downman_views.reject_generic_request, name='generic-request-rejected'),
    url(r'^downloadmanager/get_conf/$', downman_views.get_conf, name='download_manager_getconf'),
]
