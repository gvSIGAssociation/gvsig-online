# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.db.utils import ProgrammingError, OperationalError
import logging

LOGGER = logging.getLogger('gvsigol')

class GvsigolSentiloConfig(AppConfig):
    name = 'gvsigol_plugin_sentilo'
    verbose_name = "Plugin de la integración Sentilo"
    label = "gvsigol_plugin_sentilo"

    def ready(self):
        # Register a daily Celery Beat task at 02:00 if not exists
        try:
            from django_celery_beat.models import CrontabSchedule, PeriodicTask
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute='0', hour='2', day_of_week='*', day_of_month='*', month_of_year='*'
            )
            PeriodicTask.objects.get_or_create(
                crontab=schedule,
                name='gvsigol_plugin_sentilo.sentilo_daily_cleanup_task',
                task='gvsigol_plugin_sentilo.tasks.sentilo_daily_cleanup_task',
            )
        except (ProgrammingError, OperationalError) as e:
            # Likely during migrate or DB not ready
            LOGGER.warning("[Sentilo Cleanup] Beat schedule not created yet: %s", str(e))
        except Exception as e:
            LOGGER.error("[Sentilo Cleanup] Unexpected error creating beat schedule: %s", str(e))