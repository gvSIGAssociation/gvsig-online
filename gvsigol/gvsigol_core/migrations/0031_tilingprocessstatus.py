# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2021-02-01 16:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0030_fill_project_extent4327_gdal3'),
    ]

    operations = [
        migrations.CreateModel(
            name='TilingProcessStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('layer', models.IntegerField(default=0)),
                ('format_processed', models.CharField(max_length=50)),
                ('processed_tiles', models.IntegerField(default=0)),
                ('total_tiles', models.IntegerField(default=0)),
                ('version', models.BigIntegerField(blank=True, null=True)),
                ('time', models.CharField(max_length=150)),
                ('active', models.BooleanField(default=True)),
                ('stop', models.BooleanField(default=False)),
                ('extent_processed', models.CharField(max_length=150)),
                ('zoom_levels_processed', models.IntegerField(default=0)),
            ],
        ),
    ]