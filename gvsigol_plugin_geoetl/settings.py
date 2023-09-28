# -*- coding: utf-8 -*-
ETL_URL = '/etlurl'

URL_GEOCODER = {
    'icv-direct': "http://descargas.icv.gva.es/server_api/geocodificador/solrgeocoderatmvcv.php?limit=1&query=%s&servicio=rtcv+nomenclator&start=0&",
    'icv-reverse': "http://descargas.icv.gva.es/server_api/geocodificador/geocoder.php?&x=%s&y=%s"
}

GEOETL_DB = {
    'host': 'localhost',
    'port': '5432',
    'database': 'gvsigonline',
    'user': 'gvsigonline',
    'password': 'gvsigonline',
    'schema': 'ds_plugin_geoetl'
}