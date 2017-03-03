from django.conf.urls import url

urlpatterns = [
    url(r'^geocoding/get_conf/$', 'gvsigol_plugin_geocoding.views.get_conf', name='get_conf'),
    url(r'^geocoding/search_candidates/$', 'gvsigol_plugin_geocoding.views.search_candidates', name='search_candidates'),
    url(r'^geocoding/find_candidate/$', 'gvsigol_plugin_geocoding.views.find_candidate', name='find_candidate'),
    url(r'^geocoding/get_location_address/$', 'gvsigol_plugin_geocoding.views.get_location_address', name='get_location_address'),
    url(r'^geocoding/provider_list/$', 'gvsigol_plugin_geocoding.views.provider_list', name='provider_list'),
    url(r'^geocoding/provider_add/$', 'gvsigol_plugin_geocoding.views.provider_add', name='provider_add'),
    url(r'^geocoding/provider_update/(?P<provider_id>[0-9]+)/$', 'gvsigol_plugin_geocoding.views.provider_update', name='provider_update'),
    url(r'^geocoding/provider_update_order/(?P<provider_id>[0-9]+)/(?P<order>[0-9]+)/$', 'gvsigol_plugin_geocoding.views.provider_update_order', name='provider_update_order'),
    url(r'^geocoding/provider_delete/(?P<provider_id>[0-9]+)/$', 'gvsigol_plugin_geocoding.views.provider_delete', name='provider_delete'),
    
    url(r'^geocoding/provider_full_import/(?P<provider_id>[0-9]+)/$', 'gvsigol_plugin_geocoding.views.provider_full_import', name='provider_full_import'),
    url(r'^geocoding/provider_delta_import/(?P<provider_id>[0-9]+)/$', 'gvsigol_plugin_geocoding.views.provider_delta_import', name='provider_delta_import'),
    url(r'^geocoding/provider_import_status/(?P<provider_id>[0-9]+)/$', 'gvsigol_plugin_geocoding.views.provider_import_status', name='provider_import_status'),
    
    url(r'^geocoding/upload_shp_cartociudad/(?P<provider_id>[0-9]+)/$', 'gvsigol_plugin_geocoding.views.upload_shp_cartociudad', name='upload_shp_cartociudad'),
]

