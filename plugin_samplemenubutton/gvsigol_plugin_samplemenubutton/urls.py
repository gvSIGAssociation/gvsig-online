from django.urls import path
from gvsigol_plugin_samplemenubutton import views

urlpatterns = [
    path('samplemenubutton/get_conf/', views.get_conf, name='get_conf'),
]