# -*- coding: utf-8 -*-

GEOCODING_PROVIDER = {
    'cartociudad': {
        'candidates_url': 'https://localhost/gc/candidates',
        'find_url': 'https://localhost/gc/find',
        'reverse_url': 'https://localhost/gc/reverseGeocode'
    },
    'nominatim': {
        #'url': 'http://osm.gvsigonline.com/nominatim',
        'url': 'http://nominatim.openstreetmap.org',
        'country_codes': ''
    }
}