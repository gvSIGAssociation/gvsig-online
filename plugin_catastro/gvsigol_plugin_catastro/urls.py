from django.urls import path
from gvsigol_plugin_catastro import views

urlpatterns = [
    path('catastro/get_conf/', views.get_conf, name='get_conf'),

    path('catastro/get_provincias/', views.get_provincias, name='get_provincias'),
    path('catastro/get_municipios/', views.get_municipios, name='get_municipios'),
    path('catastro/get_vias/', views.get_vias, name='get_vias'),

    path('catastro/get_referencia_catastral/', views.get_referencia_catastral, name='get_referencia_catastral'),
    path('catastro/get_referencia_catastral_polygon/', views.get_referencia_catastral_polygon, name='get_referencia_catastral_polygon'),
    path('catastro/get_rc_info/', views.get_rc_info, name='get_rc_info'),
    path('catastro/get_rc_public_data/', views.get_rc_public_data, name='get_rc_public_data'),
    path('catastro/get_rc_parcel_public_data/', views.get_rc_parcel_public_data, name='get_rc_parce_public_data'),
    path('catastro/get_rc_by_coords/', views.get_rc_by_coords, name='get_rc_by_coords')
]
