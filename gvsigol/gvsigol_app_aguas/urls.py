from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_app_aguas.views.index', name='index'), 
    url(r'^create_project_wizard/$', 'gvsigol_app_aguas.views.create_project_wizard', name='create_project_wizard'),
]