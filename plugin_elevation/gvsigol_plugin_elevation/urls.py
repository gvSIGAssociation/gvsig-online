from django.urls import path
from gvsigol_plugin_elevation import views as print_views

urlpatterns = [
    path('elevation/get_conf/', print_views.get_conf, name='get_conf'),
]