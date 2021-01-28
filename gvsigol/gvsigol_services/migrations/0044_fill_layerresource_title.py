# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
import os

def fill_layerresource_title(apps, schema_editor):
    try:
        LayerResource = apps.get_model("gvsigol_services", "LayerResource")
        for layer_res in LayerResource.objects.filter(title=''):
            try:
                layer_res.title = os.path.basename(layer_res.path)
                layer_res.save()
            except:
                pass
    except Exception as error:
        import logging
        logger = logging.getLogger()
        logger.exception("error")
        print str(error)

class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0043_fill_layer_nullable'),
    ]

    operations = [
        migrations.RunPython(fill_layerresource_title, reverse_code=migrations.RunPython.noop),
    ]
