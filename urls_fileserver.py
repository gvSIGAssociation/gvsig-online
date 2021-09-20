from django.urls import path
from gvsigol_services import views as services_views

urlpatterns =  [
    # fileserver URLs are managed by XSendfile and they are served under the /fileserver
    # prefix to simplify deployments
    path('layer_resource/<int:resource_id>/', services_views.get_resource, name='layer_resource'),
]