from django.urls import path
from gvsigol_plugin_charts import views

urlpatterns = [
    path('charts/get_conf/', views.get_conf, name='charts_get_conf'),
    path('charts/chart_list/', views.chart_list, name='chart_list'),
    path('charts/select_chart_type/<int:layer_id>/', views.select_chart_type, name='select_chart_type'),
    path('charts/barchart_add/<int:layer_id>/', views.barchart_add, name='barchart_add'),
    path('charts/linechart_add/<int:layer_id>/', views.linechart_add, name='linechart_add'),
    path('charts/piechart_add/<int:layer_id>/', views.piechart_add, name='piechart_add'),
    path('charts/chart_update/<int:layer_id>/<int:chart_id>/', views.chart_update, name='chart_update'),
    path('charts/barchart_update/<int:layer_id>/<int:chart_id>/', views.barchart_update, name='barchart_update'),
    path('charts/linechart_update/<int:layer_id>/<int:chart_id>/', views.linechart_update, name='linechart_update'),
    path('charts/piechart_update/<int:layer_id>/<int:chart_id>/', views.piechart_update, name='piechart_update'),
    path('charts/chart_delete/', views.chart_delete, name='chart_delete'),
    path('charts/view/', views.view, name='view'),
    path('charts/single_chart/', views.single_chart, name='single_chart'),
]