from .models import SharedView
from django.utils import timezone
from gvsigol.celery import app as celery_app
from django_celery_beat.models import CrontabSchedule, PeriodicTask

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    my_task_name = 'gvsigol_core.tasks.clean_shared_views'
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='01',
        hour='0',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*'
    )
    PeriodicTask.objects.get_or_create(
        name=my_task_name,
        task=my_task_name,
        defaults={'crontab': schedule}
    )

@celery_app.task(bind=True)
def clean_shared_views(self):
    now = timezone.now()
    SharedView.objects.filter(expiration_date__lt=now).delete()