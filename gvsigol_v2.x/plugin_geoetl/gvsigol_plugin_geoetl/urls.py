from django.conf.urls import url
from gvsigol_plugin_geoetl import views

urlpatterns = [
    url(r'^etl/get_conf/$', views.get_conf, name='get_conf'),
    url(r'^etl/etl_canvas/$', views.etl_canvas, name='etl_canvas'),
    url(r'^etl/etl_read_canvas/$', views.etl_read_canvas, name='etl_read_canvas'),
    url(r'^etl/etl_sheet_excel/$', views.etl_sheet_excel, name='etl_sheet_excel'),
    url(r'^etl/etl_schema_excel/$', views.etl_schema_excel, name='etl_schema_excel'),
    url(r'^etl/etl_schema_shape/$', views.etl_schema_shape, name='etl_schema_shape'),
    url(r'^etl/test_postgres_conexion/$', views.test_postgres_conexion, name='test_postgres_conexion'),
    url(r'^etl/etl_schema_csv/$', views.etl_schema_csv, name='etl_schema_csv'),
#    url(r'^sampledashboard/sampledashboard_update/(?P<lgid>[0-9]+)/$', views.sampledashboard_update, name='sampledashboard_update'),
]