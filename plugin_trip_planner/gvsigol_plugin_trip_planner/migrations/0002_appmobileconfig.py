# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-02-25 11:52


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_trip_planner', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='APPMobileConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=250, null=True)),
                ('params', models.TextField()),
            ],
        ),
    ]
