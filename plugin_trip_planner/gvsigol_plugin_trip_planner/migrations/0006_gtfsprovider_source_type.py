from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_trip_planner', '0005_gtfsstatus_message_updated'),
    ]

    operations = [
        migrations.AddField(
            model_name='gtfsprovider',
            name='source_type',
            field=models.CharField(choices=[('url', 'URL'), ('file', 'File')], default='url', max_length=10),
        ),
        migrations.AlterField(
            model_name='gtfsprovider',
            name='url',
            field=models.URLField(blank=True, default='', max_length=400),
        ),
        migrations.AddField(
            model_name='gtfsstatus',
            name='last_build_signature',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
