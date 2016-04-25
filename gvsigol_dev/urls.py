from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'gvsigol_dev.views.index', name='index'), 
]