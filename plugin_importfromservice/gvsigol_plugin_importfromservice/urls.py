from django.urls import path
from gvsigol_plugin_importfromservice import views

urlpatterns = [
    path('importfromservice/get_conf/', views.get_conf, name='plugin_importfromservice_get_conf'),
]
