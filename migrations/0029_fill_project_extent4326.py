# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def fix_extent(apps, schema_editor):
    try:
        Project = apps.get_model("gvsigol_core", "Project")
        from django.contrib.gis.gdal import SpatialReference, CoordTransform
        from django.contrib.gis.geos import Point
        crs4326 = SpatialReference("EPSG:4326")
        crs3857 = SpatialReference("EPSG:3857")
        transform = CoordTransform(crs3857, crs4326)
        for project in Project.objects.all():
            if not project.extent4326_minx or not project.extent4326_miny or not project.extent4326_maxx or not project.extent4326_maxy:
                extent4326_minx, extent4326_miny, extent4326_maxx, extent4326_maxy =  [ float(f) for f in project.extent.split(',')]
                point = Point(extent4326_minx, extent4326_miny, srid=3857)
                point.transform(transform)
                project.extent4326_minx, project.extent4326_miny  = point.coords
                
                point = Point(extent4326_maxx, extent4326_maxy, srid=3857)
                point.transform(transform)
                project.extent4326_maxx, project.extent4326_maxy  = point.coords
                project.save()
            
    except Exception as error:
        import logging
        logger = logging.getLogger()
        logger.exception("error")
        print str(error)

class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0028_auto_20201030_1347'),
    ]

    operations = [
        migrations.RunPython(fix_extent, reverse_code=migrations.RunPython.noop),
    ]
