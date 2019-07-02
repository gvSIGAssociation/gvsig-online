from django.conf.urls import url

urlpatterns = [
    url(r'^catastro/get_conf/$', 'gvsigol_plugin_catastro.views.get_conf', name='get_conf'),

    url(r'^catastro/get_provincias/$', 'gvsigol_plugin_catastro.views.get_provincias', name='get_provincias'),
    url(r'^catastro/get_municipios/$', 'gvsigol_plugin_catastro.views.get_municipios', name='get_municipios'),
    url(r'^catastro/get_vias/$', 'gvsigol_plugin_catastro.views.get_vias', name='get_vias'),

    url(r'^catastro/get_referencia_catastral/$', 'gvsigol_plugin_catastro.views.get_referencia_catastral', name='get_referencia_catastral'),
    url(r'^catastro/get_referencia_catastral_polygon/$', 'gvsigol_plugin_catastro.views.get_referencia_catastral_polygon', name='get_referencia_catastral_polygon'),
    url(r'^catastro/get_rc_info/$', 'gvsigol_plugin_catastro.views.get_rc_info', name='get_rc_info'),
    url(r'^catastro/get_rc_by_coords/$', 'gvsigol_plugin_catastro.views.get_rc_by_coords', name='get_rc_by_coords')
]