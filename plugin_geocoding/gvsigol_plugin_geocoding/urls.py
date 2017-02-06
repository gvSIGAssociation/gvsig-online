from django.conf.urls import url

urlpatterns = [
    url(r'^geocoding/get_conf/$', 'gvsigol_plugin_geocoding.views.get_conf', name='get_conf'),
    url(r'^geocoding/search_candidates/$', 'gvsigol_plugin_geocoding.views.search_candidates', name='search_candidates'),
    url(r'^geocoding/get_location_address/$', 'gvsigol_plugin_geocoding.views.get_location_address', name='get_location_address'),
]