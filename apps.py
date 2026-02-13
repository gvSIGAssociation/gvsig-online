

from django.apps import AppConfig
import logging

from gvsigol.celery import app as celery_app

LOGGER = 'gvsigol'

class GvsigolAuthConfig(AppConfig):
    name = 'gvsigol_auth'

    def setup_update_user_cache(self):
        try:
            from gvsigol_auth import settings
            from django_celery_beat.models import PeriodicTask, IntervalSchedule
            if settings.USE_USER_CACHE and settings.USER_CACHE_UPDATE_INTERVAL > 0:
                task_name = 'gvsigol_auth.tasks.update_user_cache'
                schedule = IntervalSchedule.objects.filter(
                    every=settings.USER_CACHE_UPDATE_INTERVAL,
                    period=IntervalSchedule.SECONDS,
                ).first()
                if not schedule:
                    schedule, created = IntervalSchedule.objects.get_or_create(
                        every=settings.USER_CACHE_UPDATE_INTERVAL,
                        period=IntervalSchedule.SECONDS,
                    )
                task = PeriodicTask.objects.filter(name=task_name).first()
                if task:
                    task.interval = schedule
                    task.save()
                else:
                    task, created = PeriodicTask.objects.get_or_create(
                        name=task_name,
                        task = task_name,
                        interval = schedule
                    )
            else:
                PeriodicTask.objects.filter(name=task_name).delete()
                IntervalSchedule.objects.filter(periodictask__isnull=True).delete()
        except Exception as e:
            logging.getLogger(LOGGER).exception(f'GvsigolAuthConfig: setup_update_user_cache error')
            

    def ready(self):
        from actstream import registry
        from django.contrib.auth import get_user_model
        registry.register(get_user_model())
        try:
            # ensure we have a proper environment
            from gvsigol_auth.utils import ensure_admin_group
            ensure_admin_group()
            self.setup_update_user_cache()
        except Exception as e:
            # Don't fail when we are migrating applications!!
            logging.getLogger(LOGGER).exception(f'GvsigolAuthConfig, problems with auth backend. {str(e)} ')
            pass
