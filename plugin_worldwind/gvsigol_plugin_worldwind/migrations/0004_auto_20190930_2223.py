# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-09-30 20:23


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_worldwind', '0003_auto_20190925_1207'),
    ]

    operations = [
        migrations.AlterField(
            model_name='worldwindprovider',
            name='path',
            field=models.CharField(blank=True, default='', max_length=250, null=True),
        ),
    ]
