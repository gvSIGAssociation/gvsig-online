# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2020-01-09 12:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_downloadman', '0019_auto_20191211_1704'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resourcelocator',
            name='download_link',
        ),
        migrations.AddField(
            model_name='downloadlink',
            name='is_auxiliary',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='downloadlink',
            name='name',
            field=models.TextField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='resourcelocator',
            name='download_links',
            field=models.ManyToManyField(to='gvsigol_plugin_downloadman.DownloadLink'),
        ),
    ]