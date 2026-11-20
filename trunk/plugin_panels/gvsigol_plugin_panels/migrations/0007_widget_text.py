# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_panels', '0006_panel_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='panelwidget',
            name='widget_type',
            field=models.CharField(
                choices=[
                    ('map', 'map'),
                    ('table', 'table'),
                    ('list', 'list'),
                    ('bar', 'bar'),
                    ('bar_horizontal', 'bar_horizontal'),
                    ('line', 'line'),
                    ('pie', 'pie'),
                    ('kpi', 'kpi'),
                    ('text', 'text'),
                ],
                max_length=30,
            ),
        ),
    ]
