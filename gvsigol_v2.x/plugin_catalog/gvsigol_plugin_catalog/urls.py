from django.conf.urls import url
from . import views

urlpatterns = [
   url(r'^catalog/get_query/$', views.get_query, name='get_query'),
   url(r'^catalog/get_metadata/(?P<layer_id>.+)/$', views.get_metadata, name='get_metadata'),
   url(r'^catalog/get_metadata_from_uuid/(?P<metadata_uuid>.+)/$', views.get_metadata_from_uuid, name='get_metadata'),
   url(r'^catalog/get_metadata_id/(?P<layer_ws>.+)/(?P<layer_name>.+)/$', views.get_metadata_id, name='get_metadata_id'),
   url(r'^catalog/create_metadata/(?P<layer_id>[0-9]+)/$', views.create_metadata, name='create_metadata'),
]