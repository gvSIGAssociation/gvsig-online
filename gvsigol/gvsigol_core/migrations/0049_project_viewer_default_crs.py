# Generated by Django 2.2.28 on 2024-04-12 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0048_auto_20240126_0913'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='viewer_default_crs',
            field=models.CharField(blank=True, default='EPSG:3857', max_length=250, null=True),
        ),
    ]