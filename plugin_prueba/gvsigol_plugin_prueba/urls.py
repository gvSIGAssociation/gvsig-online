from django.conf.urls import url
from . import api

urlpatterns = [
    url(r'^prueba/pois/', api.PoiView.as_view(), name='get_pois'),
    url(r'^prueba/pois/', api.PoiView.as_view(), name='save_pois'),
]