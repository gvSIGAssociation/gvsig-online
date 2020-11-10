# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def fix_extent(apps, schema_editor):
    try:
        Project = apps.get_model("gvsigol_core", "Project")
        from django.contrib.gis import gdal
        major_version = gdal.gdal_version().split(".")[0]
        if int(major_version) >= 3:
            # fix effect of previous migration on GDAL 3 installations
            try:
                # newer Django versions include AxisOrder settings to manage this issue
                from django.contrib.gis.gdal import AxisOrder # @UnresolvedImport is expected in Diago < 3.1
                # newer Django versions include AxisOrder settings to manage this issue
                # if AxisOrder class exists, the transformation on 0029_fill_project_extent4326
                # should be successful, because AxisOrder.TRADITIONAL is the default behaviour
                return
            except:
                pass
            from django.contrib.gis.gdal import SpatialReference, CoordTransform
            from django.contrib.gis.geos import Point
            crs4326 = SpatialReference("EPSG:4326")
            crs3857 = SpatialReference("EPSG:3857")
            transform = CoordTransform(crs3857, crs4326)
            for project in Project.objects.all():
                extent3857_minx, extent3857_miny, extent3857_maxx, extent3857_maxy =  [ float(f) for f in project.extent.split(',')]
                point = Point(extent3857_minx, extent3857_miny, srid=3857)
                point.transform(transform)
                project.extent4326_miny, project.extent4326_minx  = point.coords
                
                point = Point(extent3857_maxx, extent3857_maxy, srid=3857)
                point.transform(transform)
                project.extent4326_maxy, project.extent4326_maxx  = point.coords
                project.save()
            
    except Exception as error:
        import logging
        logger = logging.getLogger()
        logger.exception("error")
        print str(error)

class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0029_fill_project_extent4326'),
    ]

    operations = [
        migrations.RunPython(fix_extent, reverse_code=migrations.RunPython.noop),
    ]
