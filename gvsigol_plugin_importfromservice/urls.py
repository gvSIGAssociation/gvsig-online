from django.urls import path
from gvsigol_plugin_importfromservice import views
from . import api

urlpatterns = [
    path('importfromservice/get_conf/', views.get_conf, name='plugin_importfromservice_get_conf'),
    path('importfromservice/services/', api.ServicesView.as_view(), name='get_services'),

]
