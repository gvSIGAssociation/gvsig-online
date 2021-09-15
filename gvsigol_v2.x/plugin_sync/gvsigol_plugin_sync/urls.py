from django.conf.urls import url
from gvsigol_plugin_sync import views as sync_views
urlpatterns = [
    url(r'^sync/layerinfo/$', sync_views.get_layerinfo, name='get_layerinfo'),
    url(r'^sync/layerinfo/([^/]+)/$', sync_views.get_layerinfo, name='get_layerinfo_by_project'),
    url(r'^sync/download/$', sync_views.sync_download, name='sync_download'),
    url(r'^sync/upload/$', sync_views.sync_upload, name='sync_upload'),
    url(r'^sync/commit/$', sync_views.sync_commit, name='sync_commit'),
]
