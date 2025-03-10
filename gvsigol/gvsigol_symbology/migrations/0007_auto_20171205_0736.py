# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-12-05 07:36


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_symbology', '0006_auto_20171128_0822'),
    ]

    operations = [
        migrations.CreateModel(
            name='ColorRampFolder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=500, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ColorRampLibrary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=500, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='colorrampfolder',
            name='color_ramp_library',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.ColorRampLibrary'),
        ),
        migrations.AddField(
            model_name='colorramp',
            name='color_ramp_folder',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.ColorRampFolder'),
            preserve_default=False,
        ),
    ]
