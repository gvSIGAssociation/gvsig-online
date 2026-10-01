from gvsigol.celery import app as celery_app
from gvsigol_services.forms_geoserver import PostgisLayerUploadForm
from gvsigol_services import geographic_servers
from gvsigol_services import rest_geoserver
from gvsigol_services.models import Layer, LayerGroupRole
from gvsigol_services import utils as services_utils
from gvsigol_auth import auth_backend

from django.contrib.auth.models import User
from django.db.models import Max, Q
from django.utils.translation import gettext as _
from .models import exports_historical
import json

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def _publish_exported_layer(user, cleaned_data):
    """
    Publish a PostGIS table as a gvsigol layer after export.
    Returns 'published' or 'skipped' (layer already exists).
    """
    from gvsigol_services.views import do_add_layer, do_config_layer, _get_default_abstract

    datastore = cleaned_data['datastore']
    name = cleaned_data['name'].lower()
    title = cleaned_data.get('title') or name
    layer_group = cleaned_data['layer_group']

    if Layer.objects.filter(datastore=datastore).filter(Q(name=name) | Q(source_name=name)).exists():
        return 'skipped'

    if not services_utils.can_use_datastore(user, datastore):
        raise ValueError(_("You are not allowed to use the selected datastore"))
    if not services_utils.can_use_layergroup(user, layer_group, permission=LayerGroupRole.PERM_INCLUDEINPROJECTS):
        raise ValueError(_("You are not allowed to manage the selected layergroup"))
    if layer_group.server_id != datastore.workspace.server.id:
        raise ValueError(_("The selected layer group does not belong to the same server as the datastore."))

    server = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server.id)
    do_add_layer(server, datastore, name, title, True, {'maxFeatures': 0})

    new_record = Layer(
        datastore=datastore,
        layer_group=layer_group,
        name=name,
        title=title,
        abstract=_get_default_abstract(datastore.type, title),
        created_by=user.username,
        type=datastore.type,
        visible=False,
        queryable=True,
        allow_download=False,
        allow_calculated_fields=False,
        cached=False,
        single_image=False,
        source_name=name,
        external=False,
        external_params=json.dumps({'format': 'image/png'}),
    )
    max_order = layer_group.layer_set.aggregate(Max('order')).get('order__max')
    if max_order is not None:
        new_record.order = max_order + 1
    new_record.save()

    primary_role = auth_backend.get_primary_role(user.username)
    roles = [primary_role] if primary_role else []
    services_utils.set_layer_permissions(new_record, False, roles, roles, roles)
    do_config_layer(server, new_record, {'max_features': 0})
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
