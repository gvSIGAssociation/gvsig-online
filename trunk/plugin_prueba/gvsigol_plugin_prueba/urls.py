from django.conf.urls import url
from . import api

urlpatterns = [
    url(r'^prueba/data/', api.DataView.as_view(), name='get_pois'),
    url(r'^prueba/data/', api.DataView.as_view(), name='save_pois'),
]