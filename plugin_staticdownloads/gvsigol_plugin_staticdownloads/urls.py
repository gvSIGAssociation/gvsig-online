from django.conf.urls import url
from gvsigol_plugin_staticdownloads import views

urlpatterns = [
    url(r'^staticdownloads/get_conf/$', views.get_conf, name='get_conf'),
]