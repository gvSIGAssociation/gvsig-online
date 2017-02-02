from django.conf.urls import url

urlpatterns = [
    url(r'^sync/layerinfo/$', 'gvsigol_plugin_sync.views.get_layerinfo', name='get_layerinfo'),
    url(r'^sync/layerinfo/([^/]+)/$', 'gvsigol_plugin_sync.views.get_layerinfo', name='get_layerinfo_by_project'),
    url(r'^sync/download/$', 'gvsigol_plugin_sync.views.sync_download', name='sync_download'),
    url(r'^sync/upload/$', 'gvsigol_plugin_sync.views.sync_upload', name='sync_upload'),
    url(r'^sync/commit/$', 'gvsigol_plugin_sync.views.sync_commit', name='sync_commit'),
]
