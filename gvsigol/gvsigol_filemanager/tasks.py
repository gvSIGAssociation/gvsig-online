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


def _set_progress(task, progress, status):
    try:
        task.update_state(state='PROCESSING', meta={'status': status, 'progress': progress})
    except Exception:
        logger.exception('Could not update export task progress')


def _is_gpkg_export(post):
    file_path = (post.get('file_path') or post.get('file') or '').lower()
    return file_path.endswith('.gpkg') or bool(post.get('gpkg_layer'))


@celery_app.task(bind=True)
def postBackground(self, **kwargs):

    _id = kwargs['id']
    post = kwargs['post']
    files = kwargs['files']
    username = kwargs['username']

    task_id = self.request.id

    export = exports_historical.objects.get(id=_id)

    if not export.task_id:
        export.task_id = str(task_id)
        export.save(update_fields=['task_id'])

    _set_progress(self, 5, _('Validating export parameters'))

    user = User.objects.get(username=username)
    source_columns = [post.get('pk_column', '')] if post.get('pk_column') else []
    is_gpkg = _is_gpkg_export(post)
    gpkg_layers = []
    selected_gpkg_layer = post.get('gpkg_layer') or ''
    if is_gpkg:
        from gvsigol_services.shp2postgis import list_gpkg_layers, get_fields_from_gpkg
        try:
            gpkg_layers = list_gpkg_layers(post.get('file'))
            if selected_gpkg_layer and selected_gpkg_layer in gpkg_layers:
                source_columns = [col.name for col in get_fields_from_gpkg(post.get('file'), selected_gpkg_layer)]
            elif gpkg_layers:
                selected_gpkg_layer = gpkg_layers[0]
                source_columns = [col.name for col in get_fields_from_gpkg(post.get('file'), selected_gpkg_layer)]
        except Exception:
            logger.exception('Could not load GeoPackage layers for form validation')
    form = PostgisLayerUploadForm(
        post, files, user=user, source_columns=source_columns,
        gpkg_layers=gpkg_layers, selected_gpkg_layer=selected_gpkg_layer, is_gpkg=is_gpkg,
    )
    if form.is_valid():
        publish_requested = bool(form.cleaned_data.get('publish'))
        try:
            _set_progress(self, 20, _('Connecting to geographic server'))
            gs = geographic_servers.get_instance().get_server_by_id(
                form.cleaned_data['datastore'].workspace.server.id
            )
            _set_progress(self, 40, _('Exporting data to PostGIS'))
            if _is_gpkg_export(post):
                ok = gs.exportGpkgToPostgis(form.cleaned_data)
            else:
                ok = gs.exportShpToPostgis(form.cleaned_data)
            if ok:
                if publish_requested:
                    _set_progress(self, 85, _('Publishing layer'))
                else:
                    _set_progress(self, 90, _('Finalizing export'))
                _finalize_export_status(
                    export, post,
                    _('Export process done successfully'),
                    publish_requested, user, form.cleaned_data,
                    had_export_warning=False
                )
                _set_progress(self, 100, _('Done'))

        except rest_geoserver.RequestWarning as e:
            logger.exception(e)
            msg = _('Export process completed with warnings: ') + str(e)
            if publish_requested:
                _set_progress(self, 85, _('Publishing layer'))
            _finalize_export_status(
                export, post, msg,
                publish_requested, user, form.cleaned_data,
                had_export_warning=True
            )
            _set_progress(self, 100, _('Done with warnings'))

        except rest_geoserver.RequestError as e:
            logger.exception(e)
            try:
                from ast import literal_eval as make_tuple

                msg = make_tuple(e.server_message.replace('\n', ""))
                export.message = msg[1].decode("utf-8")
            except Exception:
                msg = e.server_message
                export.message = msg

            export.status = 'Error'
            export.redirect = "/gvsigonline/filemanager/export_to_database/?path=" + (post.get('file_path') or '')
            export.save()

        except Exception as exc:
            logger.exception(exc)
            export.status = 'Error'
            export.message = 'Server error' + ": " + str(exc)
            export.redirect = "/gvsigonline/filemanager/export_to_database/?path=" + (post.get('file_path') or '')
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
        export.redirect = "/gvsigonline/filemanager/export_to_database/?path=" + (post.get('file_path') or '')
        export.save()
