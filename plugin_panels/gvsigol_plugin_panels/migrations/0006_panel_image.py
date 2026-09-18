# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_panels', '0005_panel_slug_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='panel',
            name='image',
            field=models.ImageField(
                blank=True,
                default='',
                null=True,
                upload_to='images',
            ),
        ),
    ]
