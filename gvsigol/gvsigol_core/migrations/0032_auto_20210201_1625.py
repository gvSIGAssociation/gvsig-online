# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2021-02-01 16:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0031_tilingprocessstatus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tilingprocessstatus',
            name='active',
            field=models.CharField(max_length=10),
        ),
        migrations.AlterField(
            model_name='tilingprocessstatus',
            name='stop',
            field=models.CharField(max_length=10),
        ),
    ]