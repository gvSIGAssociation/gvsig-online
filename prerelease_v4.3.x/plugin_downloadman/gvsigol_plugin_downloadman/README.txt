DESCRIPTION
==============

When a download request is received in a Django view, it is stored in a Django model (DownloadRequest and related
ResourceLocator(s)) and a Celery task is invoked to process the request.

Celery tasks are executed in a separate process, called Celery worker(s). In order to manage communication between
the Django process and the Celery worker, a message broker is needed. There are several options, such as
RabbitMQ or Redis. In this case, instructions are provided for RabbitMQ.

There are several configuration options in Celery and RAbbitMQ to prioritize tasks and to set the number of workers and
theads per workers. These options can be tweaked to improve the performance of the download manager.

The Celery worker(s) and the RabbitMQ broker may be running on a different server (or a pool of servers).


INSTALLATION
=============

# we need a broker, either RabbitMQ or Redis

sudo apt-get install rabbitmq-server
sudo rabbitmqctl add_user gvsigol 12345678
sudo rabbitmqctl add_vhost gvsigol
# needed?
#sudo rabbitmqctl set_user_tags gvsigol administrator
sudo rabbitmqctl set_permissions -p gvsigol gvsigol ".*" ".*" ".*"

CONFIGURATION
==============

The user name, password and URL for the message broker must be specified on a variable on settings.py (in gvsigol/gvsigol)
For instance:
CELERY_BROKER_URL = 'pyamqp://gvsigol:12345678@localhost:5672/gvsigol'
Some additional variables are required:
CELERY_TASK_ACKS_LATE = True

Email must also be configured to send mail notifications to users. For instance:
EMAIL_HOST = 'youremailhost.com'
EMAIL_HOST_USER = 'youremailuser@youremailhost.com'
EMAIL_HOST_PASSWORD = 'xxxxxxxxx'
EMAIL_PORT = 25
EMAIL_TIMEOUT = 30

Maybe also:
EMAIL_USE_TLS = True

or:
EMAIL_USE_SSL = True



EXECUTION (DEVELOPMENT)
=======================

cd gvsigol
# We need to start at least a celery worker. We define 2 queues (package and notify)
celery -A gvsigol worker -l info -Q package,notify
# if we want debug log level:
celery -A gvsigol worker -l debug -Q package,notify
# We execute a different worker for Celery Beat (scheduler)
celery -A gvsigol beat 

EXECUTION (PRODUCTION)
=======================

In install/celery/ folder contains systemd scripts to execute the workers as services.
By default, it will start a group of nodes (named "package") to process download requests
and another group of nodes for the rest of tasks (mailing/notifying, cleaning periodic
tasks, etc). The config file can be customized to adapt these settings to any workload. 

MONITORING
===========

See https://docs.celeryproject.org/en/latest/userguide/monitoring.html

# Inspect active tasks:
celery -A gvsigol inspect active

# Inspect scheduled tasks (includes to-be-retried tasks):
celery -A gvsigol inspect scheduled

# Inspect prefetched tasks:
celery -A gvsigol inspect reserved

# Show worker statistics:
celery -A gvsigol inspect stats

# Inspect revoked tasks
celery -A gvsigol inspect revoked

# Inspect registered tasks
celery -A gvsigol inspect registered
 
 # purge all tasks:
 celery -A gvsigol purge
 
 # purge all tasks from a specific queue
 celery -A gvsigol purge -Q package
 celery -A gvsigol purge -Q notify
