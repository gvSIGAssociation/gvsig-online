# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-07-10 11:17


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0014_configure_projects'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='baselayerproject',
            name='baselayer',
        ),
        migrations.RemoveField(
            model_name='baselayerproject',
            name='project',
        ),
        migrations.DeleteModel(
            name='BaseLayer',
        ),
        migrations.DeleteModel(
            name='BaseLayerProject',
        ),
    ]
