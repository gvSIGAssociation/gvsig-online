# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2020-10-22 10:57


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0039_golfunc_geocoder_inv_cartociudad'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='layerfieldenumeration',
            index=models.Index(fields=['layer', 'field'], name='gvsigol_ser_layer_i_ce273c_idx'),
        ),
        migrations.AddIndex(
            model_name='trigger',
            index=models.Index(fields=['layer', 'field'], name='gvsigol_ser_layer_i_a65867_idx'),
        ),
    ]
