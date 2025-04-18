# Generated by Django 2.2.18 on 2021-04-23 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gvsigol_plugin_geoetl', '0002_auto_20191003_1127'),
    ]

    operations = [
        migrations.CreateModel(
            name='ETLstatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('message', models.CharField(blank=True, max_length=250, null=True)),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ETLworkspaces',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('description', models.CharField(blank=True, max_length=500, null=True)),
                ('workspace', models.TextField()),
            ],
        ),
    ]
