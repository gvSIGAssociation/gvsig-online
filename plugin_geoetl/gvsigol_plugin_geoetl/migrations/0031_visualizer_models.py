import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0030_delete_database_connections'),
    ]

    operations = [
        # ETLstatus: nuevo campo visualizer_session_id
        migrations.AddField(
            model_name='etlstatus',
            name='visualizer_session_id',
            field=models.UUIDField(blank=True, null=True),
        ),

        # ETLVisualizerSession
        migrations.CreateModel(
            name='ETLVisualizerSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('run_key', models.CharField(max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
            ],
            options={
                'verbose_name': 'Sesión Visualizador ETL',
                'verbose_name_plural': 'Sesiones Visualizador ETL',
            },
        ),

        # ETLVisualizerLayer
        migrations.CreateModel(
            name='ETLVisualizerLayer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='layers',
                    to='gvsigol_plugin_geoetl.ETLVisualizerSession',
                )),
                ('name', models.CharField(max_length=250)),
                ('layer_group', models.CharField(default='Visualizer', max_length=250)),
                ('color', models.CharField(max_length=20)),
                ('has_geometry', models.BooleanField(default=False)),
                ('feature_count', models.IntegerField(default=0)),
                ('table_name', models.CharField(max_length=250)),
                ('extent_3857', models.CharField(blank=True, max_length=200, null=True)),
                ('truncated', models.BooleanField(default=False)),
                ('layer_order', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Capa Visualizador ETL',
                'verbose_name_plural': 'Capas Visualizador ETL',
                'ordering': ['layer_order'],
            },
        ),
    ]
