# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-06-05 11:58


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0002_workspace_is_public'),
        ('gvsigol_core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectlayergroup',
            name='layer_group',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_services.LayerGroup'),
        ),
        migrations.AddField(
            model_name='projectlayergroup',
            name='project',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_core.Project'),
        ),
        migrations.AlterField(
            model_name='projectusergroup',
            name='project',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_core.Project'),
        ),
        migrations.AlterField(
            model_name='projectusergroup',
            name='user_group',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_auth.UserGroup'),
        ),
    ]
