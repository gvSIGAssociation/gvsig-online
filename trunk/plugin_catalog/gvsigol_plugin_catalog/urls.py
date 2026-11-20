from django.urls import path
from . import views

urlpatterns = [
   path('catalog/config/', views.get_catalog_config, name='get_catalog_config'),
   path('catalog/get_query/', views.get_query, name='get_query'),
   path('catalog/get_metadata/<str:layer_id>/', views.get_metadata, name='get_metadata'),
   path('catalog/get_metadata_from_uuid/<str:metadata_uuid>/', views.get_metadata_from_uuid, name='get_metadata_from_uuid'),
   path('catalog/get_metadata_id/<str:layer_ws>/<str:layer_name>/', views.get_metadata_id, name='get_metadata_id'),
   path('catalog/get_extent_image/<str:metadata_uuid>/', views.get_extent_image, name='get_extent_image'),
   path('catalog/get_thumbnail/<str:metadata_uuid>/', views.get_thumbnail, name='get_thumbnail'),
   path('catalog/create_metadata/<int:layer_id>/', views.create_metadata, name='create_metadata'),
]