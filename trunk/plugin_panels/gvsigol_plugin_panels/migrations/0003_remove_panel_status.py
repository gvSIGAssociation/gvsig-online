# -*- coding: utf-8 -*-
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_panels', '0002_panel_permissions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='panel',
            name='status',
        ),
    ]
