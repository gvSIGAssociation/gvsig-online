from django.conf.urls import url

urlpatterns = [
    url(r'^layerinfo/$', 'gvsigol_app_sync.views.get_layerinfo', name='get_layerinfo'),
    url(r'^layerinfo/([^/]+)/$', 'gvsigol_app_sync.views.get_layerinfo', name='get_layerinfo_by_project'),
    url(r'^download/$', 'gvsigol_app_sync.views.sync_download', name='sync_download'),
    url(r'^upload/$', 'gvsigol_app_sync.views.sync_upload', name='sync_upload'),
    
]
