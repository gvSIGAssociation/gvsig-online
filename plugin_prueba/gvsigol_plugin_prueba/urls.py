from django.conf.urls import url
from . import api

urlpatterns = [
    url(r'^prueba/pois/', api.PoiView.as_view(), name='get_pois'),
    url(r'^prueba/pois/', api.PoiView.as_view(), name='save_pois'),
    url(r'^prueba/pois/<int:pk>/', api.PoiView.as_view(), name='update_pois'),
    url(r'^prueba/search_pois', api.SearchPoiView.as_view(), name='search_pois'),
    url(r'^prueba/delete_pois/<int:pk>/', api.PoiView.as_view(), name='delete_pois'),
]