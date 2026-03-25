from django.urls import path
from . import views

urlpatterns = [
    path('geocoding/get_conf/', views.get_conf, name='get_conf'),
    path('geocoding/search_candidates/', views.search_candidates, name='search_candidates'),
    path('geocoding/find_candidate/', views.find_candidate, name='find_candidate'),
    path('geocoding/find_first_candidate/', views.find_first_candidate, name='find_first_candidate'),
    path('geocoding/get_location_address/', views.get_location_address, name='get_location_address'),
    path('geocoding/provider_list/', views.provider_list, name='provider_list'),
    path('geocoding/provider_add/', views.provider_add, name='provider_add'),
    path('geocoding/provider_update/<int:provider_id>/', views.provider_update, name='provider_update'),
    path('geocoding/provider_update_order/<int:provider_id>/<int:order>/', views.provider_update_order, name='provider_update_order'),
    path('geocoding/provider_delete/<int:provider_id>/', views.provider_delete, name='provider_delete'),
    
    path('geocoding/provider_full_import/<int:provider_id>/', views.provider_full_import, name='provider_full_import'),
    path('geocoding/provider_delta_import/<int:provider_id>/', views.provider_delta_import, name='provider_delta_import'),
    path('geocoding/provider_import_status/<int:provider_id>/', views.provider_import_status, name='provider_import_status'),
    
    path('geocoding/upload_shp_cartociudad/<int:provider_id>/', views.upload_shp_cartociudad, name='upload_shp_cartociudad'),
    
    path('geocoding/get_geocoding_resource_list_available/', views.get_geocoding_resource_list_available, name='get_geocoding_resource_list_available'),
    path('geocoding/get_providers_activated/', views.get_providers_activated, name='get_providers_activated'),
    path('geocoding/get_providers_activated_by_project/<int:project_id>/', views.get_providers_activated_by_project, name='get_providers_activated_by_project'),

]

