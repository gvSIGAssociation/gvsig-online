from django.urls import path
from . import views

urlpatterns = [
   path('catalog/get_query/', views.get_query, name='get_query'),
   path('catalog/get_metadata/<str:layer_id>/', views.get_metadata, name='get_metadata'),
   path('catalog/get_metadata_from_uuid/<str:metadata_uuid>/', views.get_metadata_from_uuid, name='get_metadata'),
   path('catalog/get_metadata_id/<str:layer_ws>/<str:layer_name>/', views.get_metadata_id, name='get_metadata_id'),
   path('catalog/create_metadata/<int:layer_id>/', views.create_metadata, name='create_metadata'),
]