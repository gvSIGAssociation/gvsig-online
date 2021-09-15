from django.conf.urls import url
from gvsigol_plugin_importfromservice import views

urlpatterns = [
    url(r'^importfromservice/get_conf/$', views.get_conf, name='get_conf'),
]