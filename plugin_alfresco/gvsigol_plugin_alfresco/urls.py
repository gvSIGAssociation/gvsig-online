from django.urls import path
from gvsigol_plugin_alfresco import views

urlpatterns = [
    path('alfresco/get_sites/', views.get_sites, name='alfresco_get_sites'),
    path('alfresco/get_folder_content/', views.get_folder_content, name='alfresco_get_folder_content'),
    path('alfresco/save_resource/', views.save_resource, name='alfresco_save_resource'),
    path('alfresco/update_resource/', views.update_resource, name='alfresco_update_resource'),
    path('alfresco/delete_resource/', views.delete_resource, name='alfresco_delete_resource'),
]
