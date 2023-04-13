from django.conf.urls import url
from . import api

from gvsigol_plugin_prueba import views

urlpatterns = [
    url(r'^prueba/test/', api.TestView.as_view(), name='get_test'),
    url(r'^prueba/test/', api.TestView.as_view(), name='post_test'),
]