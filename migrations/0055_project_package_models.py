# -*- coding: utf-8 -*-
"""
Register the three ProjectPackage* models under gvsigol_core without touching
any database tables.  The tables already exist from gvsigol_project_package
migrations 0001-0004; the db_table Meta attributes on each model point at those
existing tables so no DDL is needed.

After applying this migration you can safely remove gvsigol_project_package
from INSTALLED_APPS (and keep a compat shim there for re-exports).
"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0054_userhomeorder_user_null_default'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Django state: register the three models so the ORM knows about them
            state_operations=[
                migrations.CreateModel(
                    name='ProjectPackageImportJob',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('created_by', models.CharField(blank=True, max_length=150)),
                        ('status', models.CharField(
                            choices=[
                                ('draft', 'draft'),
                                ('preflight_ok', 'preflight_ok'),
                                ('running', 'running'),
                                ('committed', 'committed'),
                                ('failed', 'failed'),
                            ],
                            default='draft',
                            max_length=32,
                        )),
                        ('celery_task_id', models.CharField(blank=True, max_length=255, null=True)),
                        ('zip_path', models.CharField(help_text='Absolute or MEDIA-relative path', max_length=1024)),
                        ('extract_dir', models.CharField(blank=True, max_length=1024, null=True)),
                        ('manifest_json', models.JSONField(blank=True, null=True)),
                        ('wizard_json', models.JSONField(blank=True, default=dict)),
                        ('report_json', models.JSONField(blank=True, default=list)),
                        ('id_map_json', models.JSONField(blank=True, default=dict)),
                        ('result_project_id', models.IntegerField(blank=True, null=True)),
                        ('summary_json', models.JSONField(blank=True, default=dict)),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'gvsigol_project_package_projectpackageimportjob',
                    },
                ),
                migrations.CreateModel(
                    name='ProjectPackageActivityLog',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('operation', models.CharField(
                            choices=[('import', 'import'), ('export', 'export')],
                            max_length=16,
                        )),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('created_by', models.CharField(blank=True, max_length=150)),
                        ('status', models.CharField(
                            choices=[('ok', 'ok'), ('partial', 'partial'), ('failed', 'failed')],
                            default='ok',
                            max_length=16,
                        )),
                        ('project_id', models.IntegerField(blank=True, null=True)),
                        ('project_name', models.CharField(blank=True, max_length=200)),
                        ('import_job_id', models.UUIDField(blank=True, null=True)),
                        ('summary_json', models.JSONField(blank=True, default=dict)),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'gvsigol_project_package_projectpackageactivitylog',
                    },
                ),
                migrations.CreateModel(
                    name='ProjectPackageExportJob',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('created_by', models.CharField(blank=True, max_length=150)),
                        ('status', models.CharField(
                            choices=[
                                ('pending', 'pending'),
                                ('running', 'running'),
                                ('done', 'done'),
                                ('failed', 'failed'),
                            ],
                            default='pending',
                            max_length=16,
                        )),
                        ('celery_task_id', models.CharField(blank=True, max_length=255, null=True)),
                        ('project_id', models.IntegerField(blank=True, null=True)),
                        ('project_name', models.CharField(blank=True, max_length=200)),
                        ('zip_filename', models.CharField(blank=True, max_length=512)),
                        ('zip_path', models.CharField(blank=True, max_length=1024)),
                        ('export_options_json', models.JSONField(blank=True, default=dict)),
                        ('summary_json', models.JSONField(blank=True, default=dict)),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'gvsigol_project_package_projectpackageexportjob',
                    },
                ),
            ],
            # No DDL — the tables already exist from gvsigol_project_package migrations
            database_operations=[],
        ),
    ]
