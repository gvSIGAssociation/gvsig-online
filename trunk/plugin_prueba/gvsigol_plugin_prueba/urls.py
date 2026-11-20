from django.urls import path
from . import api

urlpatterns = [
    path('prueba/data/', api.DataView.as_view(), name='get_pois'),
]