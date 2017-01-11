from django.conf.urls import url

urlpatterns = [
    url(r'^alfresco/get_sites/$', 'gvsigol_plugin_alfresco.views.get_sites', name='get_sites'),
    url(r'^alfresco/get_folder_content/$', 'gvsigol_plugin_alfresco.views.get_folder_content', name='get_folder_content')
]