from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0032_enterapi_lastdownload'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='enterapi_lastdownload',
            name='unique_enterapi_last_download',
        ),
        migrations.AddField(
            model_name='enterapi_lastdownload',
            name='id_ws',
            field=models.IntegerField(),
        ),
        migrations.AddConstraint(
            model_name='enterapi_lastdownload',
            constraint=models.UniqueConstraint(
                fields=('id_ws', 'entity', 'epigraph'),
                name='unique_enterapi_last_download',
            ),
        ),
    ]
