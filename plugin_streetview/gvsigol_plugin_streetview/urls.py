from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^streetview/get_conf/$', views.get_conf, name='get_conf'),
]