# -*- coding: utf-8 -*-
ETL_URL = '/etlurl'

URL_GEOCODER = {
    'icv-direct': "http://descargas.icv.gva.es/server_api/geocodificador/solrgeocoderatmvcv.php?limit=1&query=%s&servicio=rtcv+nomenclator&start=0&",
    'icv-reverse': "http://descargas.icv.gva.es/server_api/geocodificador/geocoder.php?&x=%s&y=%s"
}

try:
    from gvsigol import settings_passwords
    USER = settings_passwords.DB_USER_DEVEL
    PASS = settings_passwords.DB_PW_DEVEL
except:
    USER = 'postgres'
    PASS = 'postgres'



GEOETL_DB = {
    'host': 'localhost',
    'port': '5432',
    'database': 'gvsigonline',
    'user': USER,
    'password': PASS,
    'schema': 'ds_plugin_geoetl'
}