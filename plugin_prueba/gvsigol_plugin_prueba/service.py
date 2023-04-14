# -*- coding: utf-8 -*-

from gvsigol_plugin_prueba.models import Poi
from django.contrib.gis.geos import GEOSGeometry

def save_pois(pois):
    try:
        Poi.objects.all().delete()
        for p in pois:
            geom_4326 = GEOSGeometry(p['wkt'], srid=4326)
            poi = Poi(
                name = p['name'],
                description = p['description'],
                geometry = geom_4326
            )
            poi.save()

        return True

    except Exception as e:
        print('EXCEPTION IN METHOD: save_pois')
        print(str(e))
        return False