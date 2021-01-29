"""
 Defines the django instance to use
 See https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#django-first-steps
"""


import os
from celery import Celery
import sys, re

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gvsigol.settings')

app = Celery('gvsigol')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
"""
app.conf['broker_connection_max_retries'] = 1
app.conf['broker_transport_options'] = {
    'max_retries': 1,
    'interval_start': 0,
    'interval_step': 0.5,
    'interval_max': 1,
}
app.conf['task_publish_retry_policy'] = {
    'max_retries': 1,
    'interval_start': 0,
    'interval_step': 0.5,
    'interval_max': 1,
}
"""
app.conf['task_acks_late'] = True

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(('Request: {0!r}'.format(self.request)))
    

def is_celery_process():
    cmd = " ".join(sys.argv)
    return (re.match(".*celery.*worker", cmd) is not None)