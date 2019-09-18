from django.conf.urls import url
from gvsigol_plugin_trip_planner import views

urlpatterns = [
    url(r'^trip_planner/gtfs_provider_list/$', views.gtfs_provider_list, name='gtfs_provider_list'),
    url(r'^trip_planner/gtfs_provider_add/$', views.gtfs_provider_add, name='gtfs_provider_add'),
    url(r'^trip_planner/gtfs_provider_update/(?P<provider_id>[0-9]+)/$', views.gtfs_provider_update, name='gtfs_provider_update'),
    url(r'^trip_planner/gtfs_provider_delete/(?P<provider_id>[0-9]+)/$', views.gtfs_provider_delete, name='gtfs_provider_delete'),
    url(r'^trip_planner/gtfs_crontab_update/$', views.gtfs_crontab_update, name='gtfs_crontab_update'),

    url(r'^trip_planner/get_app_mobile_config/$', views.get_app_mobile_config, name='get_app_mobile_config'),
    url(r'^trip_planner/app_mobile_config_update/$', views.app_mobile_config_update, name='app_mobile_config_update'),
]

