from django.urls import path
from gvsigol_plugin_print import views as print_views

urlpatterns = [
    path('print/get_conf/', print_views.get_conf, name='print_get_conf'),
]