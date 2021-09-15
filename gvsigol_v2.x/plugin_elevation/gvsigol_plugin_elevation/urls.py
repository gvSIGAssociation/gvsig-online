from django.conf.urls import url
from gvsigol_plugin_elevation import views as print_views

urlpatterns = [
    url(r'^elevation/get_conf/$', print_views.get_conf, name='get_conf'),
]