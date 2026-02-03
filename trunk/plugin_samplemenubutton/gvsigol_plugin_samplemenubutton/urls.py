from django.conf.urls import url
from gvsigol_plugin_samplemenubutton import views

urlpatterns = [
    url(r'^samplemenubutton/get_conf/$', views.get_conf, name='get_conf'),
]