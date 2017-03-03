# -*- coding: utf-8 -*-

GEOCODING_PROVIDER = {
    'cartociudad': {
        'candidates_url': '/geocoder/api/geocoder/candidates',
        'find_url': '/geocoder/api/geocoder/find',
        'reverse_url': '/geocoder/api/geocoder/reverseGeocode'
    },
    'nominatim': {
        'url': 'http://osm.gvsigonline.com/nominatim',
        'country_codes': ''
    }
}