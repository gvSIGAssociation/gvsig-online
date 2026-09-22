from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0033_enterapi_lastdownload_id_ws'),
    ]

    operations = [
        migrations.CreateModel(
            name='ETLCanvasDelivery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('deliveries', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'ETL canvas Celery delivery',
                'verbose_name_plural': 'ETL canvas Celery deliveries',
            },
        ),
    ]
