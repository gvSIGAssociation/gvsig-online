# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2018-01-12 16:18


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0009_auto_20171002_1116'),
        ('gvsigol_plugin_survey', '0005_auto_20180112_1052'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='layer_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_services.LayerGroup'),
        ),
    ]
