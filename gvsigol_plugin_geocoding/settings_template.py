# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 Scolab Software Colaborativo S.L.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
@author: José Badía <jbadia@scolab.es>
'''
from django.utils.translation import ugettext_lazy as _
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GEOCODING_PROVIDER_NAME='nominatim'

GEOCODING_SUPPORTED_TYPES = (
                ('googlemaps', _('Servicios de Google Maps')),
                ('nominatim', _('Servicios de Nominatim')),
                ('cartociudad', _('Cartografía de CartoCiudad')),
                ('user', _('Otras fuentes de datos')),
            )

GEOCODING_PROVIDER = {
    'cartociudad': {
        'configuration_url': '##GEOCODER_URL##/api/geocoder/configureSourceJsonp',
        'candidates_url': '##GEOCODER_URL##/api/geocoder/candidatesJsonp',
        'find_url': '##GEOCODER_URL##/api/geocoder/findJsonp',
        'reverse_url': '##GEOCODER_URL##/api/geocoder/reverseGeocode',
        'country_codes': 'es',
        'autocancel': True,
        'max_results': 10
    },
    'nominatim': {
        #'url': 'http://osm.gvsigonline.com/nominatim',
        'url': 'http://nominatim.openstreetmap.org',
        'country_codes': ''
    },
    'googlemaps': {
        'candidates_url': 'https://maps.googleapis.com/maps/api/place/autocomplete/json',
        'find_url': 'https://maps.googleapis.com/maps/api/geocode/json',
        'reverse_url': 'https://maps.googleapis.com/maps/api/geocode/json',
        'key': 'AIzaSyDRJwLAQS6t8LP-rnv0IBhkp6fT4lHjV1w'
    },
    'user':{
        'candidates_url': '##GEOCODER_URL##/api/geocoder/candidatesJsonp',
        'find_url': '##GEOCODER_URL##/api/geocoder/findJsonp',
        'reverse_url': '##GEOCODER_URL##/api/geocoder/reverseGeocode',
        'country_codes': 'es',
        'autocancel': True,
        'max_results': 10
    }
}

STATIC_URL = '/gvsigonline/static/'

LAST_MODIFIED_FIELD_NAME="last_modified"

URL_SOLR="##SOLR_URL##"
DIR_SOLR_CONFIG="/var/solr/data/gvsigonline/conf/"
FILE_DATE_CONFIG="data-config.xml"
FILE_SOLR_CONFIG="solrconfig.xml"
SOLR_CORE_NAME="gvsigonline"

CARTOCIUDAD_SHP_CODIGO_POSTAL="CODIGO_POSTAL.shp"
CARTOCIUDAD_DB_CODIGO_POSTAL="codigo_postal"

CARTOCIUDAD_SHP_TRAMO_VIAL="TRAMO_VIAL.shp"
CARTOCIUDAD_DB_TRAMO_VIAL="tramo_vial"

CARTOCIUDAD_SHP_PORTAL_PK="PORTAL_PK.shp"
CARTOCIUDAD_DB_PORTAL_PK="portal_pk"

CARTOCIUDAD_SHP_TOPONIMO="TOPONIMO.shp"
CARTOCIUDAD_DB_TOPONIMO="toponimo"

CARTOCIUDAD_SHP_MANZANA="MANZANA.shp"
CARTOCIUDAD_DB_MANZANA="manzana"

CARTOCIUDAD_SHP_LINEA_AUXILIAR="LINEA_AUXILIAR.shp"
CARTOCIUDAD_DB_LINEA_AUXILIAR="linea_auxiliar"

CARTOCIUDAD_DBF_MUNICIPIO_VIAL="MUNICIPIO_VIAL.dbf"
CARTOCIUDAD_DB_MUNICIPIO_VIAL="municipio_vial"

CARTOCIUDAD_SHP_MUNICIPIO="recintos_municipales_inspire_peninbal_etrs89.shp"
CARTOCIUDAD_DB_MUNICIPIO="municipio"

CARTOCIUDAD_SHP_PROVINCIA="recintos_provinciales_inspire_peninbal_etrs89.shp"
CARTOCIUDAD_DB_PROVINCIA="provincia"

CARTOCIUDAD_INE_MUN_FILTER="##CARTOCIUDAD_INE_MUN##"  

SQL_SOUNDEXESP_FILE_NAME="soundexesp2.sql"
   