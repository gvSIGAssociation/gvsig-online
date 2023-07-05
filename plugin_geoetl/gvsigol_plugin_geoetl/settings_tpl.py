# -*- coding: utf-8 -*-
ETL_URL = '##ETL_URL##'

URL_GEOCODER = {
    'icv-direct': "http://descargas.icv.gva.es/server_api/geocodificador/solrgeocoderatmvcv.php?limit=1&query=%s&servicio=rtcv+nomenclator&start=0&",
    'icv-reverse': "http://descargas.icv.gva.es/server_api/geocodificador/geocoder.php?&x=%s&y=%s"
}

GEOETL_DB = {
    'host': '##ETL_DB_HOST##',
    'port': '##ETL_DB_PORT##',
    'database': '##ETL_DB_NAME##',
    'user': '##ETL_DB_USER##',
    'password': '##ETL_DB_PASSWD##',
    'schema': 'ds_plugin_geoetl'
}