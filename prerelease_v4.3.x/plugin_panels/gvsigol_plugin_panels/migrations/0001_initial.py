# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion

try:
    from django.db.models import JSONField
except ImportError:
    from django_jsonfield_backport.models import JSONField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gvsigol_core', '0001_initial'),
        ('gvsigol_services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Panel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('description', models.CharField(blank=True, max_length=500, null=True)),
                ('slug', models.SlugField(max_length=160)),
                ('layout', JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('draft', 'draft'), ('published', 'published')], default='draft', max_length=20)),
                ('created_by', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='panels', to='gvsigol_core.project')),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='PanelDataset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('source_type', models.CharField(choices=[('wfs_layer', 'wfs_layer'), ('spreadsheet', 'spreadsheet'), ('rest', 'rest')], default='wfs_layer', max_length=20)),
                ('file', models.FileField(blank=True, null=True, upload_to='panels/datasets')),
                ('column_mapping', JSONField(blank=True, default=dict)),
                ('rows', JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('layer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gvsigol_services.layer')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='panel_datasets', to='gvsigol_core.project')),
            ],
        ),
        migrations.CreateModel(
            name='PanelWidget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('widget_type', models.CharField(choices=[('map', 'map'), ('table', 'table'), ('list', 'list'), ('bar', 'bar'), ('bar_horizontal', 'bar_horizontal'), ('line', 'line'), ('pie', 'pie'), ('kpi', 'kpi')], max_length=30)),
                ('name', models.CharField(blank=True, max_length=150)),
                ('title', models.CharField(blank=True, max_length=150)),
                ('description', models.CharField(blank=True, max_length=500)),
                ('x', models.IntegerField(default=0)),
                ('y', models.IntegerField(default=0)),
                ('w', models.IntegerField(default=6)),
                ('h', models.IntegerField(default=4)),
                ('config', JSONField(blank=True, default=dict)),
                ('filter_mode', models.CharField(choices=[('independent', 'independent'), ('linked', 'linked')], default='linked', max_length=20)),
                ('sort_order', models.IntegerField(default=0)),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gvsigol_plugin_panels.paneldataset')),
                ('panel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='widgets', to='gvsigol_plugin_panels.panel')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='panel',
            unique_together={('project', 'slug')},
        ),
    ]
