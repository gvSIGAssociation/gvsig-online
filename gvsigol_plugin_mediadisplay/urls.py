from django.urls import path
from . import views

urlpatterns = [
    path('mediadisplay/config/', views.config_list, name='mediadisplay_config_list'),
    path('mediadisplay/config/add/', views.config_add, name='mediadisplay_config_add'),
    path('mediadisplay/config/edit/<int:config_id>/', views.config_edit, name='mediadisplay_config_edit'),
    path('mediadisplay/config/delete/<int:config_id>/', views.config_delete, name='mediadisplay_config_delete'),
    path('mediadisplay/api/project-layers/', views.get_project_layers, name='mediadisplay_project_layers'),
    path('mediadisplay/api/layer-fields/', views.get_layer_fields, name='mediadisplay_layer_fields'),
    path('mediadisplay/api/config/', views.get_config, name='mediadisplay_get_config'),
]
