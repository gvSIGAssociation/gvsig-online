# -*- coding: utf-8 -*-

from django.db import migrations

def fix_duplicate_layer_roles(apps, schema_editor):
    try:
        LayerReadRole = apps.get_model("gvsigol_services", "LayerReadRole")
        for lrr in LayerReadRole.objects.all().reverse():
            if LayerReadRole.objects.filter(layer=lrr.layer, role=lrr.role).count() > 1:
                lrr.delete()
        
        LayerWriteRole = apps.get_model("gvsigol_services", "LayerWriteRole")
        for lwr in LayerWriteRole.objects.all().reverse():
            if LayerWriteRole.objects.filter(layer=lwr.layer, role=lwr.role).count() > 1:
                lwr.delete()

    except Exception as error:
        import logging
        logger = logging.getLogger()
        #logging.basicConfig()
        logger.exception(str(error))
        print(error)
        
class Migration(migrations.Migration):
    dependencies = [
        ('gvsigol_services', '0064_auto_20231110_1450'),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_layer_roles, reverse_code=migrations.RunPython.noop),
    ]
