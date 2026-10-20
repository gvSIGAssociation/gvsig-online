# -*- coding: utf-8 -*-


from django.db import migrations
import ast

def fix_val_title(apps, schema_editor):
    try:
        Layer = apps.get_model("gvsigol_services", "Layer")
        for layer in Layer.objects.filter(external=False, type__startswith='v_'):
            try:
                conf = ast.literal_eval(layer.conf) if layer.conf else {}
                fields = conf.get('fields', [])
                for f in fields:
                    if not 'title-ca-es-valencia' in f:
                        if 'title-ca-es@valencia' in f:
                            f['title-ca-es-valencia'] = f.get('title-ca-es@valencia')
                        elif 'title-va' in f:
                            f['title-ca-es-valencia'] = f.get('title-va')
                    try:
                        del f['title-ca-es@valencia']
                    except:
                        pass
                    try:
                        del f['title-va']
                    except:
                        pass
                layer.conf = conf
                layer.save()
            except:
                pass
    except Exception as error:
        import logging
        logger = logging.getLogger()
        logger.exception("error")
        print(str(error))

class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0067_layer_featureapi_endpoint'),
    ]

    operations = [
        migrations.RunPython(fix_val_title, reverse_code=migrations.RunPython.noop),
    ]
