"""
 Defines the django instance to use
 See https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#django-first-steps
"""


import os
from celery import Celery
import sys, re
from celery.signals import after_setup_logger
import logging

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gvsigol.settings')

@after_setup_logger.connect
def add_custom_logger(logger, **kwargs):
    formatter = logging.Formatter(
        fmt='[%(asctime)s]%(levelname)s:%(name)s_celery: %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S'
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    gvsigol_logger = logging.getLogger('gvsigol')    
    try:
        from gvsigol import settings
        gvsigol_logger.setLevel(settings.env('LOG_LEVEL', 'DEBUG'))
    except Exception as e:
        print(e)
        gvsigol_logger.setLevel(logging.INFO)
    gvsigol_logger.handlers = []
    gvsigol_logger.addHandler(console_handler)
    gvsigol_logger.propagate = False

app = Celery('gvsigol')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
"""
app.conf['broker_connection_max_retries'] = 1
# set timeout and retry options from workers to broker
app.conf['task_publish_retry_policy'] = {
    'max_retries': 1,
    'interval_start': 0,
    'interval_step': 0.5,
    'interval_max': 1,
}
"""

app.conf['task_acks_late'] = True
# set timeout and retry options from producer to broker
app.conf['broker_transport_options'] = {
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 1,
    'interval_max': 3,
}

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(('Request: {0!r}'.format(self.request)))
    logging.debug('Request: {0!r}'.format(self.request))

@app.task(bind=True)
def debug_loggers(self):
    print('Test gvsigol print from task')
    logging.getLogger('gvsigol').info('Test gvsigol logger')
    from celery.utils.log import get_task_logger
    get_task_logger(__name__).info('Test Celery task logger')

@app.task(bind=True)
def debug_environment(self):
    from celery.utils.log import get_task_logger
    logger = get_task_logger(__name__)
    import os
    for key, value in os.environ.items():
        logger.info(f"{key}: {value}")



def is_celery_process():
    cmd = " ".join(sys.argv)
    return (re.match(".*celery.*worker", cmd) is not None)