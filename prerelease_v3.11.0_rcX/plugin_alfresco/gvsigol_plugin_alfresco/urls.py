from django.urls import path
from gvsigol_plugin_alfresco import views

urlpatterns = [
    path('alfresco/get_sites/', views.get_sites, name='get_sites'),
    path('alfresco/get_folder_content/', views.get_folder_content, name='get_folder_content'),
    path('alfresco/save_resource/', views.save_resource, name='save_resource'),
    path('alfresco/update_resource/', views.update_resource, name='update_resource'),
    path('alfresco/delete_resource/', views.delete_resource, name='delete_resource'),
]
