from gvsigol.celery import app as celery_app
from gvsigol_services.forms_geoserver import PostgisLayerUploadForm
from gvsigol_services import geographic_servers
from gvsigol_services import rest_geoserver
from gvsigol_services.models import Layer

from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from .models import exports_historical

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def _publish_exported_layer(user, cleaned_data):
    """
    Publish a PostGIS table as a gvsigol layer after export.
    Returns 'published' or 'skipped' (layer already exists).
    """
    from gvsigol_services.layer_publish import publish_postgis_resource

    datastore = cleaned_data['datastore']
    name = cleaned_data['name'].lower()
    if Layer.objects.filter(datastore=datastore).filter(name=name).exists():
        return 'skipped'
    publish_postgis_resource(
        user=user,
        datastore=datastore,
        layer_group=cleaned_data['layer_group'],
        name=name,
        title=cleaned_data.get('title') or name,
        properties={'visible': False, 'queryable': True},
    )
    return 'published'


def _finalize_export_status(export, post, export_message, publish_requested, user, cleaned_data, had_export_warning=False):
    redirect = "/gvsigonline/filemanager/?path=" + (post.get('directory_path') or '')
    if not publish_requested:
        export.status = 'Warning' if had_export_warning else 'Success'
        export.message = export_message
        export.redirect = redirect
        export.save()
        return

    try:
        result = _publish_exported_layer(user, cleaned_data)
        if result == 'skipped':
            msg = _('Export process done successfully. Layer was already published.')
            if had_export_warning:
                msg = export_message + ' ' + _('Layer was already published.')
            export.status = 'Warning' if had_export_warning else 'Success'
            export.message = msg
        else:
            msg = _('Export and publish completed successfully')
            if had_export_warning:
                msg = export_message + ' ' + _('Layer published successfully.')
            export.status = 'Warning' if had_export_warning else 'Success'
            export.message = msg
        export.redirect = redirect
        export.save()
    except Exception as exc:
        logger.exception(exc)
        export.status = 'Warning'
        export.message = _(
            'Export process done successfully, but the layer could not be published: %(error)s'
        ) % {'error': str(exc)}
        export.redirect = redirect
        export.save()


@celery_app.task
def postBackground(**kwargs):

    _id = kwargs['id']
    post = kwargs['post']
    files = kwargs['files']
    username = kwargs['username']

    task_id = postBackground.request.id

    export = exports_historical.objects.get(id = _id)

    export.task_id = str(task_id)
    export.save()

    user = User.objects.get(username = username)
    form = PostgisLayerUploadForm(post, files, user=user, source_columns=[post.get('pk_column', '')])
    if form.is_valid():
        publish_requested = bool(form.cleaned_data.get('publish'))
        try:
            gs = geographic_servers.get_instance().get_server_by_id(form.cleaned_data['datastore'].workspace.server.id)
            if gs.exportShpToPostgis(form.cleaned_data):
                _finalize_export_status(
                    export, post,
                    _('Export process done successfully'),
                    publish_requested, user, form.cleaned_data,
                    had_export_warning=False
                )
               
        except rest_geoserver.RequestWarning as e:
            logger.exception(e)
            msg = _('Export process completed with warnings: ') + str(e)
            _finalize_export_status(
                export, post, msg,
                publish_requested, user, form.cleaned_data,
                had_export_warning=True
            )
                
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
        errors = []
        for field, field_errors in form.errors.items():
            for err in field_errors:
                if field == '__all__':
                    errors.append(str(err))
                else:
                    errors.append('%s: %s' % (field, err))
        export.message = '; '.join(errors) if errors else _('You must fill in all fields')
        export.redirect = "/gvsigonline/filemanager/export_to_database/?path=" + post.get('file_path')
        export.save()
