# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-05-17 16:40


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0009_project_tools'),
    ]

    operations = [
        migrations.CreateModel(
            name='SharedView',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=10, unique=True)),
                ('project_id', models.IntegerField()),
                ('description', models.CharField(blank=True, max_length=250, null=True)),
                ('state', models.TextField(blank=True, null=True)),
                ('creation_date', models.DateField(auto_now=True)),
                ('expiration_date', models.DateField()),
                ('created_by', models.CharField(max_length=100)),
            ],
        ),
    ]
