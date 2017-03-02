from django.conf.urls import url

urlpatterns = [
    url(r'^catastro/get_conf/$', 'gvsigol_plugin_catastro.views.get_conf', name='get_conf')
]