from gvsigol.celery import app as celery_app
from celery.schedules import crontab
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from django.http import HttpResponse
from .models import GTFSProvider, GTFSstatus
from .utils import *
from gvsigol import settings
from gvsigol_plugin_trip_planner.settings import GTFS_SCRIPT
from datetime import datetime
import os
import logging
import json

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    my_task_name = 'gvsigol_plugin_trip_planner.trip_planner_refresh'
    if not PeriodicTask.objects.filter(name=my_task_name).exists():
        
        # si no se ha programado la tarea, la programamos para ejecutarse todos los días a las 00:01
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='01',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*'
        )
        PeriodicTask.objects.create(
            crontab=schedule,
            name=my_task_name,
            args=[0],
            task='gvsigol_plugin_trip_planner.tasks.cron_trip_planner_refresh',
        )



# This method will download the GTFS files, stop the server, calculate Graph and start again.
@celery_app.task
def cron_trip_planner_refresh(id):
    
    statusModel  = GTFSstatus.objects.get(name = 'update')
    statusModel.message = 'Running'
    statusModel.status = 'Running'
    statusModel.save()

    print(('############################    '+datetime.now().strftime("%Y-%m-%d %H:%M") + ' -> Actualizando Trip-Planner: '))

    try:
        providers = GTFSProvider.objects.order_by('name')
        bChange = False
        for p in providers:
            path = 'data/GTFS/{0}{1}'.format(p.id, '.zip')
            url = p.url
            dstFile = os.path.join(settings.MEDIA_ROOT, path)
            try:
                if os.path.exists(dstFile):
                    aux = download_file_if_newer(url, dstFile)
                    if (aux):
                        bChange = True
                else:
                    download_file(url, dstFile)
                    bChange = True
            except:
                #Do logging
                msg = 'File:{0} url:{1}'.format(dstFile, url)
                logging.exception(msg)

        if bChange:
            os.system(GTFS_SCRIPT)

        response = {
            'refresh': True
        }

        statusModel  = GTFSstatus.objects.get(name = 'update')
        statusModel.message = 'Success'
        statusModel.status = 'Success'
        statusModel.save() 
        
        return HttpResponse(json.dumps(response, indent=4), content_type='project/json')
    
    except Exception as e:
        
        statusModel  = GTFSstatus.objects.get(name = 'update')
        statusModel.message = str(e)[:250]
        statusModel.status = 'Error'
        statusModel.save() 