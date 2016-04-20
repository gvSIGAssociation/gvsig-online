from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_core.views.home', name='home'), 
    url(r'^project_list/$', 'gvsigol_core.views.project_list', name='project_list'),
    url(r'^project_add/$', 'gvsigol_core.views.project_add', name='project_add'),
    url(r'^project_delete/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_delete', name='project_delete'),
    #url(r'^project_update/(?P<pid>[0-9]+)/$', 'gvsigol_core.views.project_update', name='project_update'),
]