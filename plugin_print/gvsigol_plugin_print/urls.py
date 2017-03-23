from django.conf.urls import url

urlpatterns = [
    url(r'^print/get_conf/$', 'gvsigol_plugin_print.views.get_conf', name='get_conf'),
]