from django.urls import path
from .views import catastrord_admin

app_name = 'gvsigol_plugin_catastrord_admin'

urlpatterns = [
    # Vista HTML principal con pestañas
    path('catastrord/admin/', catastrord_admin, name='catastrord_admin'),
]