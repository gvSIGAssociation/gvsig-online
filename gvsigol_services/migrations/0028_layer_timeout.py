# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-11-15 11:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0027_inserts_in_layerfieldenumeration'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='timeout',
            field=models.IntegerField(default=30000, null=True),
        ),
    ]