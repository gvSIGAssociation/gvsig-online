# Generated by Django 2.2.28 on 2023-06-27 13:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0013_auto_20230608_1122'),
    ]

    operations = [
        migrations.AddField(
            model_name='etlworkspaces',
            name='concat',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
