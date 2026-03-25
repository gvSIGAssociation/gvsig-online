from django.urls import path, re_path
from gvsigol_plugin_sync import views as sync_views
urlpatterns = [
    path('sync/layerinfo/', sync_views.get_layerinfo, name='get_layerinfo'),
    re_path(r'^sync/layerinfo/([^/]+)/$', sync_views.get_layerinfo, name='get_layerinfo_by_project'),
    path('sync/download/', sync_views.sync_download, name='sync_download'),
    path('sync/upload/', sync_views.sync_upload, name='sync_upload'),
    path('sync/commit/', sync_views.sync_commit, name='sync_commit'),
]
