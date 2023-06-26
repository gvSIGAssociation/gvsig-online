from django.conf.urls import url
from gvsigol_plugin_sampledashboard import views

urlpatterns = [
    path('sampledashboard/get_conf/', views.get_conf, name='get_conf'),
    path('sampledashboard/sampledashboard_list/', views.sampledashboard_list, name='sampledashboard_list'),
    path('sampledashboard/sampledashboard_add/', views.sampledashboard_add, name='sampledashboard_add'),
    path('sampledashboard/sampledashboard_delete/', views.sampledashboard_delete, name='sampledashboard_delete'),
    path('sampledashboard/sampledashboard_update/', views.sampledashboard_update, name='sampledashboard_update'),
    path('sampledashboard/sampledashboard_update/<int:lgid>/', views.sampledashboard_update, name='sampledashboard_update'),
]
