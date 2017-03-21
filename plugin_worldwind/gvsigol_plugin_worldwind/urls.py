from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_plugin_worldwind.views.index', name='index'),
    url(r'^ww_providers_list/$', 'gvsigol_plugin_worldwind.views.list', name='list'),
    url(r'^ww_provider_add/$', 'gvsigol_plugin_worldwind.views.add', name='add'),
    url(r'^ww_provider_delete/(?P<id>[0-9]+)/$', 'gvsigol_plugin_worldwind.views.delete', name='delete'),
    url(r'^ww_provider_conf/(?P<id>[0-9]+)/$', 'gvsigol_plugin_worldwind.views.conf', name='conf')
]