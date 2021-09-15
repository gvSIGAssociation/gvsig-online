from django.conf.urls import url
from gvsigol_plugin_catastro import views

urlpatterns = [
    url(r'^catastro/get_conf/$', views.get_conf, name='get_conf'),

    url(r'^catastro/get_provincias/$', views.get_provincias, name='get_provincias'),
    url(r'^catastro/get_municipios/$', views.get_municipios, name='get_municipios'),
    url(r'^catastro/get_vias/$', views.get_vias, name='get_vias'),

    url(r'^catastro/get_referencia_catastral/$', views.get_referencia_catastral, name='get_referencia_catastral'),
    url(r'^catastro/get_referencia_catastral_polygon/$', views.get_referencia_catastral_polygon, name='get_referencia_catastral_polygon'),
    url(r'^catastro/get_rc_info/$', views.get_rc_info, name='get_rc_info'),
    url(r'^catastro/get_rc_by_coords/$', views.get_rc_by_coords, name='get_rc_by_coords')
]
