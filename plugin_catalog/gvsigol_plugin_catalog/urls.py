from django.conf.urls import url

urlpatterns = [
   url(r'^catalog/get_query/$', 'gvsigol_plugin_catalog.views.get_query', name='get_query'),
   url(r'^catalog/get_metadata/(?P<metadata_uuid>.+)/$', 'gvsigol_plugin_catalog.views.get_metadata', name='get_metadata'),
   url(r'^catalog/get_metadata_id/(?P<layer_ws>.+)/(?P<layer_name>.+)/$', 'gvsigol_plugin_catalog.views.get_metadata_id', name='get_metadata_id'),
   url(r'^catalog/create_metadata/(?P<layer_id>[0-9]+)/$', 'gvsigol_plugin_catalog.views.create_metadata', name='create_metadata'),
]