from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_core.views.home', name='home'), 
    url(r'^project_list/$', 'gvsigol_core.views.project_list', name='project_list'),
    url(r'^project_add/$', 'gvsigol_core.views.project_add', name='project_add'),
    url(r'^project_delete/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_delete', name='project_delete'),
    url(r'^project_update/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_update', name='project_update'),
    url(r'^project_load/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_load', name='project_load'),
    url(r'^project_get_conf/$', 'gvsigol_core.views.project_get_conf', name='project_get_conf'),
    url(r'^search_candidates/$', 'gvsigol_core.views.search_candidates', name='search_candidates'),
    url(r'^get_location_address/$', 'gvsigol_core.views.get_location_address', name='get_location_address'),
    url(r'^export/$', 'gvsigol_core.views.export', name='export'),
]