from django.conf.urls import url
from gvsigol_plugin_alfresco import views

urlpatterns = [
    url(r'^alfresco/get_sites/$', views.get_sites, name='get_sites'),
    url(r'^alfresco/get_folder_content/$', views.get_folder_content, name='get_folder_content'),
    url(r'^alfresco/save_resource/$', views.save_resource, name='save_resource'),
    url(r'^alfresco/update_resource/$', views.update_resource, name='update_resource'),
    url(r'^alfresco/delete_resource/$', views.delete_resource, name='delete_resource'),
]
