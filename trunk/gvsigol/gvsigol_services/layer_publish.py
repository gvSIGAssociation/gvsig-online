import json

from django.db.models import Max, Q
from django.utils.translation import gettext as _

from gvsigol_auth import auth_backend
from gvsigol_core import utils as core_utils
from gvsigol_services import geographic_servers
from gvsigol_services import utils as services_utils
from gvsigol_services.models import Layer, LayerGroupRole


def publish_postgis_resource(user, datastore, layer_group, name, title=None,
                             has_geometry=True, properties=None,
                             read_roles=None, write_roles=None,
                             manage_roles=None, is_public=False):
    """Register a PostGIS resource and, when spatial, publish it in GeoServer."""
    from gvsigol_services.views import (
        _get_default_abstract,
        do_add_layer,
        do_config_layer,
    )

    properties = properties or {}
    name = name.lower()
    title = title or name

    if Layer.objects.filter(datastore=datastore).filter(
            Q(name=name) | Q(source_name=name)).exists():
        raise ValueError(_("A layer or table with this name is already published"))
    if not services_utils.can_use_datastore(user, datastore):
        raise PermissionError(_("You are not allowed to use the selected datastore"))
    if not services_utils.can_use_layergroup(
            user, layer_group,
            permission=LayerGroupRole.PERM_INCLUDEINPROJECTS):
        raise PermissionError(_("You are not allowed to use the selected layer group"))
    if layer_group.server_id != datastore.workspace.server.id:
        raise ValueError(
            _("The selected layer group does not belong to the same server as the datastore."))

    server = geographic_servers.get_instance().get_server_by_id(
        datastore.workspace.server.id)
    queryable = bool(properties.get('queryable', True))
    max_features = int(properties.get('max_features') or 0)
    if has_geometry:
        do_add_layer(
            server, datastore, name, title, queryable,
            {'maxFeatures': max_features},
        )

    requested_format = properties.get('format') or 'image/png'
    vector_tile = requested_format == 'vector-tiles'
    image_format = 'image/png' if vector_tile else requested_format
    external_params = {
        'format': image_format,
        'has_geometry': bool(has_geometry),
    }
    layer = Layer(
        datastore=datastore,
        layer_group=layer_group,
        name=name,
        title=title,
        abstract=properties.get('abstract') or _get_default_abstract(
            datastore.type, title),
        created_by=user.username,
        type=datastore.type,
        visible=bool(properties.get('visible', has_geometry)),
        queryable=queryable,
        allow_download=bool(properties.get('allow_download', False)),
        allow_calculated_fields=bool(
            properties.get('allow_calculated_fields', False)),
        cached=bool(properties.get('cached', False)) if has_geometry else False,
        single_image=bool(properties.get('single_image', False)) if has_geometry else False,
        vector_tile=vector_tile if has_geometry else False,
        source_name=name,
        external=False,
        external_params=json.dumps(external_params),
        native_srs=properties.get('native_srs') or 'EPSG:4326',
    )
    max_order = layer_group.layer_set.aggregate(Max('order')).get('order__max')
    if max_order is not None:
        layer.order = max_order + 1
    layer.save()

    primary_role = auth_backend.get_primary_role(user.username)
    default_roles = [primary_role] if primary_role else []
    services_utils.set_layer_permissions(
        layer,
        bool(is_public),
        default_roles if read_roles is None else read_roles,
        default_roles if write_roles is None else write_roles,
        default_roles if manage_roles is None else manage_roles,
    )

    if has_geometry:
        do_config_layer(server, layer, {'max_features': max_features})
        if vector_tile:
            server.update_vector_tile_format(
                datastore.workspace, layer.name, True)
    else:
        # Non-spatial resources are still part of the project TOC/data model,
        # but must not be advertised to GeoServer as map layers.
        core_utils.toc_add_layer(layer)
    return layer
