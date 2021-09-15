from django.conf.urls import url
from gvsigol_plugin_sampledashboard import views

urlpatterns = [
    url(r'^sampledashboard/get_conf/$', views.get_conf, name='get_conf'),
    url(r'^sampledashboard/sampledashboard_list/$', views.sampledashboard_list, name='sampledashboard_list'),
    url(r'^sampledashboard/sampledashboard_add/$', views.sampledashboard_add, name='sampledashboard_add'),
    url(r'^sampledashboard/sampledashboard_delete/$', views.sampledashboard_delete, name='sampledashboard_delete'),
    url(r'^sampledashboard/sampledashboard_update/$', views.sampledashboard_update, name='sampledashboard_update'),
    url(r'^sampledashboard/sampledashboard_update/(?P<lgid>[0-9]+)/$', views.sampledashboard_update, name='sampledashboard_update'),
]