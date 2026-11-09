from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0034_etlcanvasdelivery'),
    ]

    operations = [
        migrations.AddField(
            model_name='etlstatus',
            name='celery_task_id',
            field=models.CharField(blank=True, default='', max_length=250, null=True),
        ),
    ]
