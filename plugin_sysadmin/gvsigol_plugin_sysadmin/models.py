# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

try:
    from django.db.models import JSONField
except ImportError:
    from django_jsonfield_backport.models import JSONField


class SysadminTestRun(models.Model):
    """Record of a sysadmin-triggered `manage.py test` execution (Celery + subprocess)."""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILURE = 'failure'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'pending'),
        (STATUS_RUNNING, 'running'),
        (STATUS_SUCCESS, 'success'),
        (STATUS_FAILURE, 'failure'),
        (STATUS_ERROR, 'error'),
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name='sysadmin_test_runs',
        on_delete=models.SET_NULL,
    )
    labels = JSONField(default=list, help_text='Django test labels passed to manage.py test')
    filters = JSONField(
        default=dict,
        blank=True,
        help_text='Optional UI filter snapshot when the run was requested',
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    return_code = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(blank=True, default='')
    stderr = models.TextField(blank=True, default='')
    summary = JSONField(
        null=True,
        blank=True,
        help_text='Parsed totals: total, passed, failed, errors, skipped',
    )

    class Meta:
        ordering = ('-id',)

    def __str__(self):
        return 'SysadminTestRun(id=%s, status=%s)' % (self.pk, self.status)
