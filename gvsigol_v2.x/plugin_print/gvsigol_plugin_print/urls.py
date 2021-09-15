from django.conf.urls import url
from gvsigol_plugin_print import views as print_views

urlpatterns = [
    url(r'^print/get_conf/$', print_views.get_conf, name='get_conf'),
]