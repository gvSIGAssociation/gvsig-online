from django.conf.urls import url

urlpatterns = [
    url(r'^alfresco/get_sites/$', 'gvsigol_plugin_alfresco.views.get_sites', name='get_sites'),
    url(r'^alfresco/get_folder_content/$', 'gvsigol_plugin_alfresco.views.get_folder_content', name='get_folder_content'),
    url(r'^alfresco/save_resource/$', 'gvsigol_plugin_alfresco.views.save_resource', name='save_resource'),
    url(r'^alfresco/update_resource/$', 'gvsigol_plugin_alfresco.views.update_resource', name='update_resource'),
    url(r'^alfresco/delete_resource/$', 'gvsigol_plugin_alfresco.views.delete_resource', name='delete_resource'),
]