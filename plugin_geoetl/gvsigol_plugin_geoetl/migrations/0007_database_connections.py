# Generated by Django 2.2.18 on 2022-05-05 13:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0006_auto_20211005_1348'),
    ]

    operations = [
        migrations.CreateModel(
            name='database_connections',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=250)),
                ('name', models.CharField(max_length=250)),
                ('connection_params', models.TextField()),
            ],
        ),
    ]