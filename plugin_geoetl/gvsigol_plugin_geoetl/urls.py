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
    url(r'^etl/etl_workspace_list/$', views.etl_workspace_list, name='etl_workspace_list'),
    url(r'^etl/etl_workspace_add/$', views.etl_workspace_add, name='etl_workspace_add'),
    url(r'^etl/etl_workspace_delete/$', views.etl_workspace_delete, name='etl_workspace_delete'),
    url(r'^etl/etl_workspace_update/$', views.etl_workspace_update, name='etl_workspace_update'),
]