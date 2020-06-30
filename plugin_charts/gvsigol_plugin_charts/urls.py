from django.conf.urls import url
from gvsigol_plugin_charts import views

urlpatterns = [
    url(r'^charts/get_conf/$', views.get_conf, name='get_conf'),
    url(r'^charts/chart_list/$', views.chart_list, name='chart_list'),
    url(r'^charts/select_chart_type/(?P<layer_id>[0-9]+)/$', views.select_chart_type, name='select_chart_type'),
    url(r'^charts/barchart_add/(?P<layer_id>[0-9]+)/$', views.barchart_add, name='barchart_add'),
    url(r'^charts/linechart_add/(?P<layer_id>[0-9]+)/$', views.linechart_add, name='linechart_add'),
    url(r'^charts/piechart_add/(?P<layer_id>[0-9]+)/$', views.piechart_add, name='piechart_add'),
    url(r'^charts/chart_update/(?P<layer_id>[0-9]+)/(?P<chart_id>[0-9]+)/$$', views.chart_update, name='chart_update'),
    url(r'^charts/barchart_update/(?P<layer_id>[0-9]+)/(?P<chart_id>[0-9]+)/$$', views.barchart_update, name='barchart_update'),
    url(r'^charts/linechart_update/(?P<layer_id>[0-9]+)/(?P<chart_id>[0-9]+)/$$', views.linechart_update, name='linechart_update'),
    url(r'^charts/piechart_update/(?P<layer_id>[0-9]+)/(?P<chart_id>[0-9]+)/$$', views.piechart_update, name='piechart_update'),
    url(r'^charts/chart_delete/(?P<chart_id>[0-9]+)/$', views.chart_delete, name='chart_delete'),
    url(r'^charts/dashboard/(?P<layer_id>[0-9]+)/$', views.dashboard, name='dashboard'),
]