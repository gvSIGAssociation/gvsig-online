# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-03-25 10:54


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gvsigol_core', '0008_auto_20171117_1128'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorldwindProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(default='', max_length=250)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_core.Project')),
            ],
        ),
    ]
