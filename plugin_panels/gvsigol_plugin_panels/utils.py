# -*- coding: utf-8 -*-
import json
import logging
import math
from urllib.parse import urlparse

from django.db.models import Q
from django.utils.text import slugify
from gvsigol_core.models import ProjectLayerGroup
from gvsigol_services import geographic_servers
from gvsigol_services import utils as services_utils
from gvsigol_services.models import Datastore, Layer, Workspace

logger = logging.getLogger(__name__)


def unique_slug(title, exclude_id=None):
    base = slugify(title) or 'panel'
    slug = base
    n = 2
    from .models import Panel
    qs = Panel.objects.all()
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    while qs.filter(slug=slug).exists():
        slug = '%s-%s' % (base, n)
        n += 1
    return slug[:160]


def parse_json_body(request):
    if request.content_type and 'application/json' in request.content_type:
        if not request.body:
            return {}
        try:
            data = json.loads(request.body.decode('utf-8'))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return request.POST.dict() if request.POST else {}


def get_browser_wfs_url(layer):
    if not layer or not layer.datastore_id:
        return None
    workspace = layer.datastore.workspace
    server = getattr(workspace, 'server', None)
    if server is not None:
        endpoint = server.getWfsEndpoint(workspace.name, relative=True)
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            path = urlparse(endpoint).path
            if path:
                return path
        return endpoint
    if workspace.wfs_endpoint:
        endpoint = workspace.wfs_endpoint
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            path = urlparse(endpoint).path
            if path:
                return path
        return endpoint
    return '/geoserver/%s/wfs' % workspace.name


def get_browser_wms_url(layer):
    if not layer or not layer.datastore_id:
        return None
    workspace = layer.datastore.workspace
    server = getattr(workspace, 'server', None)
    if server is not None:
        endpoint = server.getWmsEndpoint(relative=True)
        if endpoint.startswith(('http://', 'https://')):
            return urlparse(endpoint).path or endpoint
        return endpoint
    return '/geoserver/%s/wms' % workspace.name


def layer_in_project(project, layer):
    return ProjectLayerGroup.objects.filter(
        project=project,
        layer_group_id=layer.layer_group_id,
        baselayer_group=False,
    ).exists()


def is_vector_layer(layer):
    """Los paneles sólo usan capas vectoriales: las ráster no tienen atributos
    consultables ni geometrías que un mapa, una tabla o una gráfica puedan
    leer. En gvSIG Online las vectoriales se marcan con el prefijo `v_`."""
    layer_type = getattr(layer, 'type', None) or ''
    if str(layer_type).startswith('v_'):
        return True
    try:
        datastore_type = layer.datastore.type or ''
    except Exception:
        datastore_type = ''
    return str(datastore_type).startswith('v_')


def vector_layers(qs):
    return qs.filter(
        Q(type__startswith='v_') | Q(datastore__type__startswith='v_')
    )


def project_operational_layers(project):
    group_ids = ProjectLayerGroup.objects.filter(
        project=project,
        baselayer_group=False,
    ).values_list('layer_group_id', flat=True)
    return vector_layers(Layer.objects.filter(
        layer_group_id__in=group_ids,
        external=False,
        queryable=True,
    )).select_related('datastore__workspace')


def global_operational_layers(request):
    return vector_layers(services_utils.get_layerread_by_user(request).filter(
        external=False,
        queryable=True,
    )).select_related('datastore__workspace').distinct()


def serialize_layer(layer):
    workspace = None
    try:
        workspace = layer.datastore.workspace.name
    except Exception:
        workspace = None
    styles = []
    try:
        from gvsigol_symbology.models import StyleLayer
        styles = [
            {
                'name': relation.style.name,
                'title': relation.style.title or relation.style.name,
                'is_default': relation.style.is_default,
            }
            for relation in StyleLayer.objects.filter(
                layer=layer).select_related('style').order_by('style__order')
        ]
    except Exception:
        logger.debug('Unable to serialize styles for layer %s', layer.id, exc_info=True)
    return {
        'id': layer.id,
        'name': layer.name,
        'title': layer.title,
        'workspace': workspace,
        'typename': ('%s:%s' % (workspace, layer.name)) if workspace else layer.name,
        'wfs_url': get_browser_wfs_url(layer),
        'wms_url': get_browser_wms_url(layer),
        'native_srs': getattr(layer, 'native_srs', None) or getattr(layer, 'source_srs', None) or '',
        'native_extent': getattr(layer, 'native_extent', '') or '',
        'latlong_extent': getattr(layer, 'latlong_extent', '') or '',
        'public': bool(getattr(layer, 'public', False)),
        'visible': bool(getattr(layer, 'visible', True)),
        'queryable': bool(getattr(layer, 'queryable', True)),
        'styles': styles,
        'format': 'image/png',
        'type': layer.type,
        'is_vector': is_vector_layer(layer),
    }


def panel_layer_ids(panel):
    from django.db.models import Q
    from .models import PanelDataset
    widget_ids = panel.widgets.exclude(layer_id=None).values_list('layer_id', flat=True)
    dataset_ids = PanelDataset.objects.filter(
        Q(panel=panel) | Q(panelwidget__panel=panel),
        layer_id__isnull=False,
    ).values_list('layer_id', flat=True)
    return set(widget_ids) | set(dataset_ids)


def _parse_extent(value):
    try:
        parts = [float(item) for item in str(value or '').split(',')]
        if len(parts) == 4 and all(math.isfinite(item) for item in parts):
            return parts
    except (TypeError, ValueError):
        pass
    return None


def _mercator(lon, lat):
    lat = max(-85.05112878, min(85.05112878, lat))
    radius = 6378137.0
    return [
        radius * math.radians(lon),
        radius * math.log(math.tan((math.pi / 4.0) + (math.radians(lat) / 2.0))),
    ]


DEFAULT_BASELAYER_GROUP = '__default_baselayergroup__'
# El mapa del panel trabaja en Mercator, como el visor por defecto.
PANEL_MAP_CRS = 'EPSG:3857'


def serialize_base_layer(layer, default_id=None):
    """Capa base lista para OpenLayers, sea OSM, XYZ, WMS o WMTS."""
    try:
        params = json.loads(layer.external_params) if layer.external_params else {}
    except Exception:
        params = {}
    params.pop('capabilities', None)
    if params.get('wmts_options'):
        try:
            params['wmts_options'] = services_utils.wmts_options_for_openlayers(
                params['wmts_options'],
                params.get('format'),
                projection=PANEL_MAP_CRS,
            )
        except Exception:
            logger.debug('Unusable wmts_options for base layer %s', layer.id, exc_info=True)
            params.pop('wmts_options', None)
    return {
        'id': layer.id,
        'title': layer.title or layer.name,
        'type': layer.type,
        'external_url': params.get('url') or '',
        'external_layers': params.get('layers') or '',
        'external_params': params,
        'format': params.get('format') or 'image/png',
        'cached': bool(layer.cached),
        'order': layer.order,
        'default': default_id is not None and layer.id == default_id,
    }


def base_layers_config(panel):
    """Capas base que puede usar el panel.

    Con proyecto son las suyas, que es lo que el usuario ve en el visor; sin
    proyecto, las del grupo base de la instalación.
    """
    from gvsigol_services.models import LayerGroup
    group_ids = []
    default_id = None
    if panel.project_id:
        for relation in ProjectLayerGroup.objects.filter(
            project_id=panel.project_id,
            baselayer_group=True,
        ):
            group_ids.append(relation.layer_group_id)
            default_id = default_id or relation.default_baselayer
    if not group_ids:
        group_ids = list(LayerGroup.objects.filter(
            name=DEFAULT_BASELAYER_GROUP).values_list('id', flat=True))
    layers = Layer.objects.filter(
        layer_group_id__in=group_ids,
        external=True,
    ).order_by('order', 'id')
    return [serialize_base_layer(layer, default_id) for layer in layers]


def synthetic_panel_config(panel, layers):
    from gvsigol_core.utils import get_supported_crs
    serialized = [serialize_layer(layer) for layer in layers]
    extents = [_parse_extent(item.get('latlong_extent')) for item in serialized]
    extents = [item for item in extents if item]
    if extents:
        west = min(item[0] for item in extents)
        south = min(item[1] for item in extents)
        east = max(item[2] for item in extents)
        north = max(item[3] for item in extents)
    else:
        west, south, east, north = -180.0, -70.0, 180.0, 70.0
    lower = _mercator(west, south)
    upper = _mercator(east, north)
    return {
        'id': None,
        'name': 'panel-%s' % panel.id,
        'title': panel.title,
        'center_lon': (west + east) / 2.0,
        'center_lat': (south + north) / 2.0,
        'zoom': 4,
        'extent_array': [lower[0], lower[1], upper[0], upper[1]],
        'supported_crs': get_supported_crs(),
        'plugins': ['gvsigol_plugin_panels'],
        'layer_groups': [{
            'id': 'panel-layers',
            'name': 'panel-layers',
            'title': panel.title,
            'layers': serialized,
        }],
        'base_layers': base_layers_config(panel),
    }


def load_layer_fields(layer):
    empty = {'fields': [], 'numeric_fields': [], 'alpha_numeric_fields': [], 'geom_fields': []}
    try:
        datastore = Datastore.objects.get(id=layer.datastore_id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        _ds_type, resource = gs.getResourceInfo(workspace.name, datastore, layer.name, 'json')
        feature_type = (resource or {}).get('featureType') or {}
        attributes = feature_type.get('attributes') or {}
        raw = attributes.get('attribute')
        if raw is None:
            fields = []
        elif isinstance(raw, list):
            fields = raw
        else:
            fields = [raw]
        numeric = []
        alpha = []
        geom = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            binding = field.get('binding') or ''
            if binding.startswith('org.locationtech.jts.geom') or 'jts.geom' in binding:
                geom.append(field)
            else:
                alpha.append(field)
                if (
                    binding.startswith('java.math')
                    or binding in (
                        'java.lang.Number', 'java.lang.Byte', 'java.lang.Float',
                        'java.lang.Integer', 'java.lang.Long', 'java.lang.Short',
                        'java.lang.Double',
                    )
                ):
                    numeric.append(field)
        return {
            'fields': fields,
            'numeric_fields': numeric,
            'alpha_numeric_fields': alpha,
            'geom_fields': geom,
        }
    except Exception:
        logger.exception('plugin_panels: unable to load fields for layer_id=%s', getattr(layer, 'id', None))
        return empty


def serialize_dataset(dataset):
    return {
        'id': dataset.id,
        'name': dataset.name,
        'source_type': dataset.source_type,
        'layer_id': dataset.layer_id,
        'column_mapping': dataset.column_mapping or {},
        'row_count': len(dataset.rows or []),
        'columns': list((dataset.column_mapping or {}).keys()) or (
            list((dataset.rows or [{}])[0].keys()) if dataset.rows else []
        ),
        'created_at': dataset.created_at.isoformat() if dataset.created_at else None,
    }


def serialize_widget(widget):
    return {
        'id': widget.id,
        'widget_type': widget.widget_type,
        'name': widget.name,
        'title': widget.title,
        'description': widget.description,
        'x': widget.x,
        'y': widget.y,
        'w': widget.w,
        'h': widget.h,
        'config': widget.config or {},
        'filter_mode': widget.filter_mode,
        'dataset_id': widget.dataset_id,
        'sort_order': widget.sort_order,
    }


def serialize_panel(panel, include_widgets=True):
    project_name = panel.project.name if panel.project_id else None
    # El proyecto sólo decide desde dónde se llega al panel, no su dirección.
    public_path = '/panel/%s/' % panel.slug
    edit_path = '/panel/%s/edit/' % panel.slug
    data = {
        'id': panel.id,
        'project_id': panel.project_id,
        'project_name': project_name,
        'name': panel.name or panel.slug,
        'title': panel.title,
        'description': panel.description or '',
        'image': panel.image_url,
        'slug': panel.slug,
        'layout': panel.layout or {},
        'is_public': panel.is_public,
        'created_by': panel.created_by,
        'created_at': panel.created_at.isoformat() if panel.created_at else None,
        'updated_at': panel.updated_at.isoformat() if panel.updated_at else None,
        'public_path': public_path,
        'edit_path': edit_path,
    }
    if include_widgets:
        data['widgets'] = [serialize_widget(w) for w in panel.widgets.all()]
    else:
        data['widget_count'] = panel.widgets.count()
    return data


def home_panel_items(request):
    """Tarjetas de los paneles que el usuario puede leer, para las portadas.

    Un usuario anónimo sólo obtiene los paneles públicos, así que la misma
    lista sirve para la página de bienvenida y para el escritorio.
    """
    from .models import Panel
    items = []
    for panel in Panel.objects.select_related('project').order_by('title'):
        if not panel.can_read(request):
            continue
        items.append({
            'id': panel.id,
            'name': panel.name or panel.slug,
            'title': panel.title,
            'description': panel.description or '',
            'image': panel.image_url,
            'url': '/spa/panel/%s/' % panel.slug,
            'item_type': 'panel',
            'is_public': panel.is_public,
        })
    return items


def apply_widget_payload(widget, payload, index=0):
    allowed_types = {c[0] for c in widget.TYPE_CHOICES}
    widget_type = payload.get('widget_type') or widget.widget_type
    if widget_type not in allowed_types:
        widget_type = 'bar'
    widget.widget_type = widget_type
    widget.name = payload.get('name') or widget.name or ''
    widget.title = payload.get('title') or ''
    widget.description = payload.get('description') or ''
    widget.x = int(payload.get('x') if payload.get('x') is not None else widget.x or 0)
    widget.y = int(payload.get('y') if payload.get('y') is not None else widget.y or 0)
    widget.w = int(payload.get('w') if payload.get('w') is not None else widget.w or 6)
    widget.h = int(payload.get('h') if payload.get('h') is not None else widget.h or 4)
    config = payload.get('config')
    widget.config = config if isinstance(config, dict) else (widget.config or {})
    try:
        widget.layer_id = int(widget.config.get('layer_id')) if widget.config.get('layer_id') else None
    except (TypeError, ValueError):
        widget.layer_id = None
    filter_mode = payload.get('filter_mode') or widget.filter_mode
    if filter_mode not in ('independent', 'linked'):
        filter_mode = 'linked'
    widget.filter_mode = filter_mode
    dataset_id = payload.get('dataset_id')
    if dataset_id in (None, '', 0, '0'):
        widget.dataset_id = None
    else:
        widget.dataset_id = int(dataset_id)
    widget.sort_order = int(payload.get('sort_order') if payload.get('sort_order') is not None else index)


def normalize_rows(rows, limit=10000):
    if not isinstance(rows, list):
        return []
    clean = []
    for row in rows[:limit]:
        if isinstance(row, dict):
            item = {}
            for key, value in row.items():
                if key is None:
                    continue
                item[str(key)] = value
            clean.append(item)
    return clean
