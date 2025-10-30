from django.urls import path
from . import views

urlpatterns = [
    path('simpledownload/config/', views.config_list, name='simpledownload_config_list'),
    path('simpledownload/config/add/', views.config_add, name='simpledownload_config_add'),
    path('simpledownload/config/edit/<int:config_id>/', views.config_edit, name='simpledownload_config_edit'),
    path('simpledownload/config/delete/<int:config_id>/', views.config_delete, name='simpledownload_config_delete'),
    path('simpledownload/api/project-layers/', views.get_project_layers, name='simpledownload_project_layers'),
    path('simpledownload/api/layer-fields/', views.get_layer_fields, name='simpledownload_layer_fields'),
    path('simpledownload/api/config/', views.get_config, name='simpledownload_get_config'),
]
