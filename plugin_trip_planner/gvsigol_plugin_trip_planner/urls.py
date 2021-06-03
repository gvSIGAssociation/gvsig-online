from django.urls import path
from gvsigol_plugin_trip_planner import views

urlpatterns = [
    path('trip_planner/gtfs_provider_list/', views.gtfs_provider_list, name='gtfs_provider_list'),
    path('trip_planner/gtfs_provider_add/', views.gtfs_provider_add, name='gtfs_provider_add'),
    path('trip_planner/gtfs_provider_update/<int:provider_id>/', views.gtfs_provider_update, name='gtfs_provider_update'),
    path('trip_planner/gtfs_provider_delete/<int:provider_id>/', views.gtfs_provider_delete, name='gtfs_provider_delete'),
    path('trip_planner/gtfs_crontab_update/', views.gtfs_crontab_update, name='gtfs_crontab_update'),

    path('trip_planner/get_app_mobile_config/', views.get_app_mobile_config, name='get_app_mobile_config'),
    path('trip_planner/app_mobile_config_update/', views.app_mobile_config_update, name='app_mobile_config_update'),
]

