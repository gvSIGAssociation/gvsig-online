from django.urls import path
from . import views

urlpatterns = [
    path('streetview/get_conf/', views.get_conf, name='get_conf'),
]