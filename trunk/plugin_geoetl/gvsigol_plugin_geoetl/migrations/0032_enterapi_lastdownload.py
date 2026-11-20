from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0031_visualizer_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='enterapi_LastDownload',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity', models.CharField(max_length=250)),
                ('epigraph', models.CharField(max_length=250)),
                ('last_download', models.DateTimeField()),
            ],
        ),
        migrations.AddConstraint(
            model_name='enterapi_lastdownload',
            constraint=models.UniqueConstraint(fields=('entity', 'epigraph'), name='unique_enterapi_last_download'),
        ),
    ]
