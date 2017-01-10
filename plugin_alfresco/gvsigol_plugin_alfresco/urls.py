from django.conf.urls import url

urlpatterns = [
    url(r'^alfresco/get_repository/$', 'gvsigol_plugin_alfresco.views.get_repository', name='get_repository')
]