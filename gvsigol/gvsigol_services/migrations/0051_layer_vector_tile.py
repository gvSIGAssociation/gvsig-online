# Generated by Django 2.2.18 on 2021-04-08 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0050_external_layers_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='vector_tile',
            field=models.BooleanField(default=False),
        ),
    ]
