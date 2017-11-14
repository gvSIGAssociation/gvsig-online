from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_core.views.home', name='home'),
    url(r'^project_list/$', 'gvsigol_core.views.project_list', name='project_list'),
    url(r'^project_add/$', 'gvsigol_core.views.project_add', name='project_add'),
    url(r'^project_delete/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_delete', name='project_delete'),
    url(r'^project_update/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_update', name='project_update'),
    #url(r'^project_load/(?P<project_name>\w+)/$', 'gvsigol_core.views.project_load', name='project_load'),
    url(ur'^project_load/(?P<project_name>.*)/$', 'gvsigol_core.views.project_load', name='project_load'),
    url(r'^project_get_conf/$', 'gvsigol_core.views.project_get_conf', name='project_get_conf'),
    url(r'^toc_update/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.toc_update', name='toc_update'),
    url(r'^export/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.export', name='export'),
    url(r'^ogc_services/$', 'gvsigol_core.views.ogc_services', name='ogc_services'),
    url(r'^select_public_project/$', 'gvsigol_core.views.select_public_project', name='select_public_project'),
    #url(r'^public_project_load/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.public_project_load', name='public_project_load'),
    url(ur'^public_project_load/(?P<project_name>.*)/$', 'gvsigol_core.views.public_project_load', name='public_project_load'),
    url(r'^public_viewer_get_conf/$', 'gvsigol_core.views.public_viewer_get_conf', name='public_viewer_get_conf'),
    url(r'^documentation/$', 'gvsigol_core.views.documentation', name='documentation'),
]