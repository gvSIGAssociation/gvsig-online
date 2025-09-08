from django.urls import path
from . import views

urlpatterns = [
    path(r'mediadisplay/layers/$', views.get_layers, name='get_layers'),
]