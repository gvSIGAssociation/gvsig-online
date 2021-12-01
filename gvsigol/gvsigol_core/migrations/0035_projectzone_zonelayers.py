# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2021-11-23 16:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0034_project_labels'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectZone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('levels', models.IntegerField(default=14)),
                ('extent4326_minx', models.FloatField(blank=True, null=True)),
                ('extent4326_miny', models.FloatField(blank=True, null=True)),
                ('extent4326_maxx', models.FloatField(blank=True, null=True)),
                ('extent4326_maxy', models.FloatField(blank=True, null=True)),
                ('project', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_core.Project')),
            ],
        ),
        migrations.CreateModel(
            name='ZoneLayers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('layer', models.IntegerField(default=14)),
                ('levels', models.IntegerField(default=0)),
                ('tilematrixset', models.CharField(max_length=50)),
                ('format', models.CharField(max_length=50)),
                ('extentid', models.CharField(max_length=50)),
                ('version', models.BigIntegerField(blank=True, null=True)),
                ('folder_prj', models.CharField(max_length=1024)),
                ('running', models.BooleanField(default=False)),
                ('bboxes', models.TextField(blank=True, null=True)),
                ('zone', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_core.ProjectZone')),
            ],
        ),
    ]