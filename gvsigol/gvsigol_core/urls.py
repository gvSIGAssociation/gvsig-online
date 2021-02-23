from django.urls import path
from gvsigol_core import views as core_views

urlpatterns = [
    path('', core_views.home, name='home'),
    path('project_list/', core_views.project_list, name='project_list'),
    path('project_add/', core_views.project_add, name='project_add'),
    path('project_delete/<int:pid>/', core_views.project_delete, name='project_delete'),
    path('project_update/<int:pid>/', core_views.project_update, name='project_update'),
    path('load/<project_name>/', core_views.load, name='load'),
    path('load_project/<project_name>/', core_views.load_project, name='load_project'),
    path('load_public_project/<project_name>/', core_views.load_public_project, name='load_public_project'),
    path('project_get_conf/', core_views.project_get_conf, name='project_get_conf'),
    path('toc_update/<int:pid>/', core_views.toc_update, name='toc_update'),
    path('export/<int:pid>/', core_views.export, name='export'),
    path('ogc_services/', core_views.ogc_services, name='ogc_services'),
    path('select_public_project/', core_views.select_public_project, name='select_public_project'),
    path('documentation/', core_views.documentation, name='documentation'),
    path('blank_page/', core_views.blank_page, name='blank_page'),
    path('portable_project_load/<project_name>/', core_views.portable_project_load, name='portable_project_load'),
    path('save_shared_view/', core_views.save_shared_view, name='save_shared_view'),
    path('load_shared_view/<view_name>/', core_views.load_shared_view, name='load_shared_view'),
    path('shared_view_list/', core_views.shared_view_list, name='shared_view_list'),
    path('shared_view_delete/<int:svid>/', core_views.shared_view_delete, name='shared_view_delete'),
    path('not_found_sharedview/', core_views.not_found_sharedview, name='not_found_sharedview'),
    # keep compatibility with old project URLs:
    path('public_project_load/<project_name>/', core_views.load_public_project, name='public_project_load'),
    path('project_load/<project_name>/', core_views.load_project, name='project_load'),
    path('project_clone/<int:pid>/', core_views.project_clone, name='project_clone'),
    path('project_permissions_to_layers/<int:pid>/', core_views.project_permissions_to_layer, name='project_permissions_to_layers'),
    path('extend_permissions_to_layer/', core_views.extend_permissions_to_layer, name='extend_permissions_to_layer'),
]