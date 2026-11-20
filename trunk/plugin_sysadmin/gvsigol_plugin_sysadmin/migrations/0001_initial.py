# -*- coding: utf-8 -*-

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models

try:
    from django.db.models import JSONField
except ImportError:
    from django_jsonfield_backport.models import JSONField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SysadminTestRun',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('labels', JSONField(default=list, help_text='Django test labels passed to manage.py test')),
                ('filters', JSONField(blank=True, default=dict, help_text='Optional UI filter snapshot when the run was requested')),
                ('status', models.CharField(choices=[('pending', 'pending'), ('running', 'running'), ('success', 'success'), ('failure', 'failure'), ('error', 'error')], db_index=True, default='pending', max_length=16)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('return_code', models.IntegerField(blank=True, null=True)),
                ('stdout', models.TextField(blank=True, default='')),
                ('stderr', models.TextField(blank=True, default='')),
                ('summary', JSONField(blank=True, help_text='Parsed totals: total, passed, failed, errors, skipped', null=True)),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sysadmin_test_runs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-id',),
            },
        ),
    ]
