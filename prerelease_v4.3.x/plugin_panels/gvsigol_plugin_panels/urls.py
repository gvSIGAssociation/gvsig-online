from django.urls import path
from gvsigol_plugin_panels import views

urlpatterns = [
    path('panels/', views.dashboard_panels, name='panels_dashboard_list'),
    path('panels/add/', views.dashboard_panel_add, name='panels_dashboard_add'),
    path('panels/<int:panel_id>/update/', views.dashboard_panel_update, name='panels_dashboard_update'),
    path('panels/<int:panel_id>/delete/', views.dashboard_panel_delete, name='panels_dashboard_delete'),
    path('panels/readable/', views.readable_panels, name='panels_readable_list'),
    path('panels/projects/<int:project_id>/panels/', views.project_panels, name='panels_project_list'),
    path('panels/projects/<int:project_id>/layers/', views.project_layers, name='panels_project_layers'),
    path('panels/<int:panel_id>/layers/', views.panel_layers, name='panels_panel_layers'),
    path('panels/<int:panel_id>/layers/<int:layer_id>/fields/', views.panel_layer_fields, name='panels_panel_layer_fields'),
    path('panels/projects/<int:project_id>/layers/<int:layer_id>/fields/', views.layer_fields, name='panels_layer_fields'),
    path('panels/projects/<int:project_id>/datasets/', views.project_datasets, name='panels_project_datasets'),
    path('panels/<int:panel_id>/datasets/', views.panel_datasets, name='panels_panel_datasets'),
    path('panels/datasets/<int:dataset_id>/', views.dataset_detail, name='panels_dataset_detail'),
    path('panels/by-project/<str:project_name>/slug/<slug:slug>/config/', views.panel_project_config, name='panels_project_config'),
    path('panels/by-project/<str:project_name>/slug/<slug:slug>/', views.panel_by_slug, name='panels_by_slug'),
    path('panels/by-slug/<slug:slug>/config/', views.standalone_panel_config, name='panels_standalone_config'),
    path('panels/by-slug/<slug:slug>/', views.standalone_panel_by_slug, name='panels_standalone_by_slug'),
    path('panels/<int:panel_id>/save/', views.panel_save, name='panels_save'),
    path('panels/<int:panel_id>/', views.panel_detail, name='panels_detail'),
]
