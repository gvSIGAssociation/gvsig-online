# -*- coding: utf-8 -*-

# wfs inspire URL_CATASTRO = 'https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx'

# inspire layers URL_CATASTRO = 'http://ovc.catastro.meh.es/cartografia/INSPIRE/spadgcwms.aspx'
# Vieja, ya no funciona
# URL_API_CATASTRO = 'https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC'
# Nueva API JSON
# URL_API_CATASTRO = 'https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/json/'
# Nueva API REST (xml, es más parecida al servicio viejo)
#URL_API_CATASTRO = 'https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero'


import environ

print('INFO: Loading plugin catastro.')

env_catastro = environ.Env(
    URL_CATASTRO=(str,'http://ovc.catastro.meh.es/Cartografia/WMS/ServidorWMS.aspx'),
    URL_API_CATASTRO=(str,'https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero'),
    URL_CATASTRO_INSPIRE=(str,'https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx')
)
URL_CATASTRO=env_catastro('URL_CATASTRO')
URL_API_CATASTRO=env_catastro('URL_API_CATASTRO')
URL_CATASTRO_INSPIRE=env_catastro('URL_CATASTRO_INSPIRE')