from django.conf.urls import url, include
from gvsigol_core import views as core_views

urlpatterns = [
    url(r'^$', core_views.home, name='home'),
    url(r'^project_list/$', core_views.project_list, name='project_list'),
    url(r'^project_add/$', core_views.project_add, name='project_add'),
    url(r'^project_delete/(?P<pid>[0-9]+)/$', core_views.project_delete, name='project_delete'),
    url(r'^project_update/(?P<pid>[0-9]+)/$', core_views.project_update, name='project_update'),
    url(r'^load/(?P<project_name>.*)/$', core_views.load, name='load'),
    url(r'^load_project/(?P<project_name>.*)/$', core_views.load_project, name='load_project'),
    url(r'^load_public_project/(?P<project_name>.*)/$', core_views.load_public_project, name='load_public_project'),
    url(r'^project_get_conf/$', core_views.project_get_conf, name='project_get_conf'),
    url(r'^toc_update/(?P<pid>[0-9]+)/$', core_views.toc_update, name='toc_update'),
    url(r'^export/(?P<pid>[0-9]+)/$', core_views.export, name='export'),
    url(r'^ogc_services/$', core_views.ogc_services, name='ogc_services'),
    url(r'^select_public_project/$', core_views.select_public_project, name='select_public_project'),
    url(r'^documentation/$', core_views.documentation, name='documentation'),
    url(r'^blank_page/$', core_views.blank_page, name='blank_page'),
    url(r'^portable_project_load/(?P<project_name>.*)/$', core_views.portable_project_load, name='portable_project_load'),
    url(r'^save_shared_view/$', core_views.save_shared_view, name='save_shared_view'),
    url(r'^load_shared_view/(?P<view_name>.*)/$', core_views.load_shared_view, name='load_shared_view'),
    url(r'^shared_view_list/$', core_views.shared_view_list, name='shared_view_list'),
    url(r'^shared_view_delete/(?P<svid>[0-9]+)/$', core_views.shared_view_delete, name='shared_view_delete'),
    url(r'^not_found_sharedview/$', core_views.not_found_sharedview, name='not_found_sharedview'),
    # keep compatibility with old project URLs:
    url(r'^public_project_load/(?P<project_name>.*)/$', core_views.load_public_project, name='public_project_load'),
    url(r'^project_load/(?P<project_name>.*)/$', core_views.load_project, name='project_load'),
    url(r'^project_clone/(?P<pid>[0-9]+)/$', core_views.project_clone, name='project_clone'),
]