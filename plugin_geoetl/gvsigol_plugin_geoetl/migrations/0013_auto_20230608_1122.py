# Generated by Django 2.2.28 on 2023-06-08 11:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0012_cadastral_requests'),
    ]

    operations = [
        migrations.AlterField(
            model_name='etlstatus',
            name='message',
            field=models.TextField(blank=True, null=True),
        ),
    ]