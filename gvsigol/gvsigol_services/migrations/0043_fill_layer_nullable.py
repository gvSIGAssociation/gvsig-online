# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
import ast

def fill_layer_nullable(apps, schema_editor):
    try:
        Layer = apps.get_model("gvsigol_services", "Layer")
        for layer in Layer.objects.all():
            try:
                conf = ast.literal_eval(layer.conf)
                fields = conf.get('fields', [])
                fields_fixed = []
                for f in fields:
                    if not 'nullable' in f:
                        mandatory = f.get('mandatory', False)
                        f['nullable'] = (not mandatory)
                    fields_fixed.append(f)
                conf['fields'] = fields
                layer.conf = conf
                layer.save()
            except:
                pass
    except Exception as error:
        import logging
        logger = logging.getLogger()
        logger.exception("error")
        print str(error)

class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0042_golfunc_geocoder_inv_cartociudad_v3'),
    ]

    operations = [
        migrations.RunPython(fill_layer_nullable, reverse_code=migrations.RunPython.noop),
    ]
