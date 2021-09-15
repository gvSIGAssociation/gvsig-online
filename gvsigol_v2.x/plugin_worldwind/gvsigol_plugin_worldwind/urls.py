from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^ww_providers_list/$', views.list, name='list'),
    url(r'^ww_provider_add/$', views.add, name='add'),
    url(r'^ww_provider_delete/(?P<id>[0-9]+)/$', views.delete, name='delete'),
    url(r'^ww_provider_conf/(?P<id>[0-9]+)/$', views.conf, name='conf')
]