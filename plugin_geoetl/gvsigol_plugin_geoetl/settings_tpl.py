# -*- coding: utf-8 -*-
ETL_URL = '##ETL_URL##'

URL_GEOCODER = {
    'icv-direct': "https://descargas.icv.gva.es/00/buscador/?consulta=%s&limite=1&inicio=0",
    'icv-reverse': "https://descargas.icv.gva.es/00/geoprocesos/geocodificador-inverso/?tema=callejero,municipios,catastro,forestal,espacios-protegidos&epsg=25830&x=%s&y=%s"
}

GEOETL_DB = {
    'host': '##ETL_DB_HOST##',
    'port': '##ETL_DB_PORT##',
    'database': '##ETL_DB_NAME##',
    'user': '##ETL_DB_USER##',
    'password': '##ETL_DB_PASSWD##',
    'schema': 'ds_plugin_geoetl'
}

ETL_EXCEL_MAX_ROWS = 500000
ETL_EXCEL_MAX_COLS = 512
ETL_EXCEL_READ_CHUNKSIZE = 10000
ETL_EXCEL_SQL_CHUNKSIZE = 5000
ETL_CANVAS_MAX_DELIVERIES = 2