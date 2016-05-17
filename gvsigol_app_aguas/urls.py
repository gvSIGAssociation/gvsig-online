from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_app_aguas.views.index', name='index'), 
]