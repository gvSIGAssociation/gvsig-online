# Generated by Django 2.2.18 on 2021-02-23 11:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_survey', '0008_auto_20180119_0936'),
    ]

    operations = [
        migrations.AlterField(
            model_name='survey',
            name='layer_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gvsigol_services.LayerGroup'),
        ),
    ]