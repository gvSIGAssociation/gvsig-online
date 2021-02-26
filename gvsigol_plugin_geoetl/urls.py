from django.urls import path
from django.views.i18n import JavaScriptCatalog
from gvsigol_plugin_geoetl import views

urlpatterns = [
    path('etl/get_conf/', views.get_conf, name='get_conf'),
    path('etl/etl_canvas/', views.etl_canvas, name='etl_canvas'),
    path('etl/etl_read_canvas/', views.etl_read_canvas, name='etl_read_canvas'),
    path('etl/etl_sheet_excel/', views.etl_sheet_excel, name='etl_sheet_excel'),
    path('etl/etl_schema_excel/', views.etl_schema_excel, name='etl_schema_excel'),
    path('etl/etl_schema_shape/', views.etl_schema_shape, name='etl_schema_shape'),
    path('etl/test_postgres_conexion/', views.test_postgres_conexion, name='test_postgres_conexion'),
    path('etl/etl_schema_csv/', views.etl_schema_csv, name='etl_schema_csv'),
    path('etl/etl_workspace_list/', views.etl_workspace_list, name='etl_workspace_list'),
    path('etl/etl_workspace_add/', views.etl_workspace_add, name='etl_workspace_add'),
    path('etl/etl_workspace_delete/', views.etl_workspace_delete, name='etl_workspace_delete'),
    path('etl/etl_workspace_update/', views.etl_workspace_update, name='etl_workspace_update'),
]