from django.urls import path
from gvsigol_plugin_staticdownloads import views

urlpatterns = [
    path('staticdownloads/get_conf/', views.get_conf, name='get_conf'),
]