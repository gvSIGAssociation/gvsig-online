from gvsigol.celery import app as celery_app
from gvsigol_services.forms_geoserver import PostgisLayerUploadForm
from gvsigol_services import geographic_servers
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.shortcuts import HttpResponse, redirect
from gvsigol_services import rest_geoserver

from django.contrib.auth.models import User
from .models import exports_historical

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

@celery_app.task
def postBackground(**kwargs):

    _id = kwargs['id']
    post = kwargs['post']
    files = kwargs['files']
    username = kwargs['username']

    export = exports_historical.objects.get(id = _id)

    user = User.objects.get(username = username)

    form = PostgisLayerUploadForm(post, files, user=user)
    if form.is_valid():
        try:
            gs = geographic_servers.get_instance().get_server_by_id(form.cleaned_data['datastore'].workspace.server.id)
            if gs.exportShpToPostgis(form.cleaned_data):

                export.status = 'Success'
                export.message = 'Export process done successfully'
                export.redirect = "/gvsigonline/filemanager/?path=" + post.get('directory_path')
                export.save()
               
        except rest_geoserver.RequestWarning as e:
            logger.exception(e)
            msg = 'Export process completed with warnings: ' + str(e)

            export.status = 'Warning'
            export.message = msg
            export.redirect = "/gvsigonline/filemanager/?path=" + post.get('directory_path')
            export.save()
                
        except rest_geoserver.RequestError as e:
            logger.exception(e)
            try:
                from ast import literal_eval as make_tuple
                
                msg = make_tuple(e.server_message.replace('\n', ""))
                export.message = msg[1].decode("utf-8")
            except:
                msg = e.server_message
                export.message = msg

            export.status = 'Error'
            export.redirect = "/gvsigonline/filemanager/export_to_database/?path=" + post.get('file_path')
            export.save()
            
        except Exception as exc:
            logger.exception(exc)
            export.status = 'Error'
            export.message = 'Server error'+  ": " + str(exc)
            export.redirect = "/gvsigonline/filemanager/export_to_database/?path=" + post.get('file_path')
            export.save()
            
    else:

        export.status = 'Error'
        export.message = 'You must fill in all fields'
        export.redirect = "/gvsigonline/filemanager/export_to_database/?path=" + post.get('file_path')
        export.save()