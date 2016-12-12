# -*- coding: utf-8 -*-

GEOCODING_PROVIDER = {
    'cartociudad': {
        'candidates_url': '/services/api/geocoder/candidates',
        'find_url': '/services/api/geocoder/find',
        'reverse_url': '/services/api/geocoder/reverseGeocode'
    },
    'nominatim': {
        'url': 'http://osm.gvsigonline.com/nominatim',
        'country_codes': ''
    }
}