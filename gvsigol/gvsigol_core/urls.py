from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_core.views.home', name='home'),
    url(r'^project_list/$', 'gvsigol_core.views.project_list', name='project_list'),
    url(r'^project_add/$', 'gvsigol_core.views.project_add', name='project_add'),
    url(r'^project_delete/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_delete', name='project_delete'),
    url(r'^project_update/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_update', name='project_update'),
    url(r'^load/(?P<project_name>.*)/$', 'gvsigol_core.views.load', name='load'),
    url(r'^load_project/(?P<project_name>.*)/$', 'gvsigol_core.views.load_project', name='load_project'),
    url(r'^load_public_project/(?P<project_name>.*)/$', 'gvsigol_core.views.load_public_project', name='load_public_project'),
    url(r'^project_get_conf/$', 'gvsigol_core.views.project_get_conf', name='project_get_conf'),
    url(r'^toc_update/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.toc_update', name='toc_update'),
    url(r'^export/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.export', name='export'),
    url(r'^ogc_services/$', 'gvsigol_core.views.ogc_services', name='ogc_services'),
    url(r'^select_public_project/$', 'gvsigol_core.views.select_public_project', name='select_public_project'),
    url(r'^documentation/$', 'gvsigol_core.views.documentation', name='documentation'),
    url(r'^blank_page/$', 'gvsigol_core.views.blank_page', name='blank_page'),
    url(r'^portable_project_load/(?P<project_name>.*)/$', 'gvsigol_core.views.portable_project_load', name='portable_project_load'),
]