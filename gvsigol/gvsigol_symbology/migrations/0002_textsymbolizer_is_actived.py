# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-06-02 12:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_symbology', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='textsymbolizer',
            name='is_actived',
            field=models.BooleanField(default=False),
        ),
    ]