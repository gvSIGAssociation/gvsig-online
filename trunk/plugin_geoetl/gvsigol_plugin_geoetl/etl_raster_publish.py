# -*- coding: utf-8 -*-
"""
Nodo de salida que publica un ráster de geoetl como capa de gvSIG Online.

El GeoTIFF se SUBE a GeoServer por REST (no se le pasa una ruta), porque el backend y
GeoServer no tienen por qué compartir volúmenes. Después se registran el Datastore
(c_GeoTIFF) y la Layer en gvSIG, con permisos y un estilo de clases.

Los imports de Django/gvsigol_services son perezosos para poder importar el módulo
(y usar las utilidades puras: class_palette, safe_layer_name) sin Django cargado.
"""

import colorsys
import json
import logging
import os
import re

from .etl_raster import read_meta, REGRESSION_NODATA

LOG = logging.getLogger('gvsigol')

# Paleta categórica apta para daltonismo (Okabe-Ito); si hay más clases se generan tonos extra.
BASE_PALETTE = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7', '#999999']
RAMP_COLORS = ('#FFFFFF', '#00441B')  # regresión: de claro a oscuro


def class_palette(n):
    """n colores hexadecimales distinguibles."""
    colors = list(BASE_PALETTE[:n])
    i = 0
    while len(colors) < n:
        r, g, b = colorsys.hsv_to_rgb((i * 0.61803398875) % 1.0, 0.65, 0.85)
        colors.append('#%02X%02X%02X' % (int(r * 255), int(g * 255), int(b * 255)))
        i += 1
    return colors


def safe_layer_name(text):
    """Nombre de capa/almacén válido en GeoServer: minúsculas, dígitos y guion bajo."""
    import unicodedata
    text = unicodedata.normalize('NFKD', str(text or '')).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^0-9a-zA-Z_]+', '_', text).strip('_').lower()
    if not text:
        raise ValueError('Indica un nombre para la capa.')
    if text[0].isdigit():
        text = 'l_' + text
    return text[:60]


def assign_class_colors(labels, previous=None):
    """
    Un color por clase. Las clases que ya tenían color (previous: etiqueta -> color) lo conservan,
    así una clase no cambia de color cuando aparecen o desaparecen otras entre ejecuciones; las
    nuevas toman los siguientes colores de la paleta que no estén en uso.
    """
    previous = previous or {}
    used = {previous[l].upper() for l in labels if l in previous}
    pool = [c for c in class_palette(len(labels) + len(previous) + 8) if c.upper() not in used]
    pool = iter(pool)
    return [previous[l] if l in previous else next(pool) for l in labels]


def style_entries(raster_path, previous_colors=None, ramp_range=None):
    """
    Entradas del mapa de colores del ráster. Clasificación: una por clase (colores estables).
    Resto: rampa entre mínimo y máximo (o ramp_range=(mínimo, máximo) si se indica; la confianza
    usa siempre 0-1). Devuelve (lista de entradas, tipo de mapa: 'values' o 'ramp').
    """
    import numpy as np
    import rasterio

    meta = read_meta(raster_path)
    class_map = meta.get('class_map') or {}
    entries = []
    if class_map:
        codes = sorted(int(c) for c in class_map)
        labels = [str(class_map[str(code)])[:100] for code in codes]
        colors = assign_class_colors(labels, previous_colors)
        for order, (code, label, color) in enumerate(zip(codes, labels, colors)):
            entries.append({'order': order, 'color': color, 'quantity': code, 'label': label, 'opacity': 1.0})
        return entries, 'values'

    if ramp_range is not None and ramp_range[0] is not None and ramp_range[1] is not None:
        lo, hi = float(ramp_range[0]), float(ramp_range[1])
    elif meta.get('kind') == 'confidence':
        lo, hi = 0.0, 1.0       # probabilidad: siempre la escala completa, para que 0,9 se vea igual en todas las capas
    else:
        with rasterio.open(raster_path) as src:
            band = src.read(1, masked=True)
        valid = band.compressed()
        valid = valid[valid != REGRESSION_NODATA]
        lo, hi = (float(np.min(valid)), float(np.max(valid))) if valid.size else (0.0, 1.0)
    if hi <= lo:
        hi = lo + 1.0
    entries = [{'order': 0, 'color': RAMP_COLORS[0], 'quantity': lo, 'label': '%.4g' % lo, 'opacity': 1.0},
               {'order': 1, 'color': RAMP_COLORS[1], 'quantity': hi, 'label': '%.4g' % hi, 'opacity': 1.0}]
    return entries, 'ramp'


def build_style_json(style_name, title, raster_path, previous_colors=None, ramp_range=None):
    """
    Datos del estilo en el formato de gvsigol_symbology.services_color_table.create_style.
    Clasificación -> una entrada por clase; regresión -> rampa entre mínimo y máximo.
    Devuelve (json_data, colormap_type).
    """
    entries, cmap_type = style_entries(raster_path, previous_colors, ramp_range)
    json_data = {
        'name': style_name, 'title': title, 'is_default': True,
        'rule': {'name': 'rule_1', 'title': title, 'filter': [], 'minscale': -1, 'maxscale': -1, 'order': 0},
        'entries': [{'json': json.dumps(e)} for e in entries],
    }
    return json_data, cmap_type


# --------------------------------------------------------------------------
# Resolución de entidades y permisos
# --------------------------------------------------------------------------

def _resolve(model, value, what):
    """Busca por nombre (portable entre instalaciones) y, si no, por id numérico."""
    text = str(value).strip() if value not in (None, '') else ''
    obj = model.objects.filter(name=text).first() if text else None
    if obj is None and text.isdigit():
        obj = model.objects.filter(pk=int(text)).first()
    if obj is None:
        raise ValueError('No se encuentra %s "%s".' % (what, value))
    return obj


def _can_use_workspace(user, workspace):
    from gvsigol_services.models import Datastore
    from gvsigol_services import utils as services_utils
    if user.is_superuser or workspace.created_by == user.username:
        return True
    return any(services_utils.can_use_datastore(user, ds)
               for ds in Datastore.objects.filter(workspace=workspace))


# --------------------------------------------------------------------------
# Publicación
# --------------------------------------------------------------------------

def publish_raster_layer(user, raster_path, workspace, layer_group, name, title=None,
                         abstract=None, replace=True, public=False, update_style='auto', ramp_range=None):
    """
    Publica (o reemplaza) el ráster como capa. Devuelve (layer, created: bool).
    Si algo falla al crear, se deshace lo creado en GeoServer y en la BD de gvSIG.
    update_style: qué hacer con el estilo al reemplazar una capa existente ('auto', 'yes' o 'no').
    """
    import rasterio
    from django.db.models import Max
    from gvsigol_auth import auth_backend
    from gvsigol_services import geographic_servers, utils as services_utils
    from gvsigol_services.authorization import can_use_layergroup
    from gvsigol_services.models import Datastore, Layer, LayerGroupRole

    if not raster_path or not os.path.isfile(raster_path):
        raise ValueError('No hay ráster que publicar.')
    name = safe_layer_name(name)
    title = (title or name)[:150]

    if layer_group.server_id != workspace.server_id:
        raise ValueError('El grupo de capas y el workspace pertenecen a servidores distintos.')
    if not _can_use_workspace(user, workspace):
        raise PermissionError('No tienes permiso para publicar en el workspace "%s".' % workspace.name)
    if not can_use_layergroup(user, layer_group, permission=LayerGroupRole.PERM_INCLUDEINPROJECTS):
        raise PermissionError('No tienes permiso para añadir capas al grupo "%s".' % layer_group.name)

    gs = geographic_servers.get_instance().get_server_by_id(workspace.server_id)
    catalog = gs.getGsconfig()

    existing = Layer.objects.filter(datastore__workspace=workspace, name=name).first()
    if existing:
        if not replace:
            raise ValueError('Ya existe la capa "%s" en el workspace "%s".' % (name, workspace.name))
        if not services_utils.can_manage_layer(user, existing):
            raise PermissionError('No tienes permiso para modificar la capa "%s".' % name)
        if existing.datastore.type != 'c_GeoTIFF':
            raise ValueError('La capa "%s" existe pero no es un ráster GeoTIFF; no se puede reemplazar.' % name)
        # Sustituye el fichero de la capa existente; se conservan permisos, grupo y estilo
        catalog.create_coveragestore(existing.datastore.name, workspace=workspace.name, path=raster_path,
                                     type='GeoTIFF', create_layer=False, upload_data=True, overwrite=True)
        _refresh_extent(gs, existing)
        if abstract:
            existing.abstract = abstract
            existing.save()
        # El ráster ya está reemplazado: un fallo al actualizar el estilo no debe tirar la publicación
        try:
            outcome = update_class_style(gs, existing, workspace, raster_path, update_style, ramp_range)
            if outcome in ('updated', 'created'):
                print('Estilo de la capa %s %s.' % (name, 'actualizado' if outcome == 'updated' else 'creado'))
        except Exception:
            LOG.exception('No se pudo actualizar el estilo de la capa %s', name)
            print('AVISO: el ráster se ha reemplazado, pero no se ha podido actualizar el estilo de la capa %s; '
                  'revísalo en el gestor de simbología.' % name)
        gs.reload_nodes()
        LOG.info('Ráster de la capa %s reemplazado desde geoetl', name)
        return existing, False

    if Datastore.objects.filter(workspace=workspace, name=name).exists():
        raise ValueError('Ya existe un almacén de datos "%s" en el workspace "%s".' % (name, workspace.name))

    with rasterio.open(raster_path) as src:
        srs = ('EPSG:%d' % src.crs.to_epsg()) if src.crs and src.crs.to_epsg() else None

    created = {'store': False, 'store_name': name, 'datastore': None, 'layer': None, 'coverage': False}
    try:
        catalog.create_coveragestore(name, workspace=workspace.name, path=raster_path, type='GeoTIFF',
                                     create_layer=False, upload_data=True, overwrite=False)
        created['store'] = True
        store = catalog.get_store(name, workspace=workspace.name)
        datastore = Datastore(
            workspace=workspace, type='c_GeoTIFF', name=name, description=title,
            connection_params=json.dumps({'url': getattr(store, 'url', '') or ''}),
            created_by=user.username, connection=None, schema=None, legacy_mode=True)
        datastore.save()
        created['datastore'] = datastore

        # Al subir el fichero GeoServer ya crea la cobertura con el nombre del almacén
        if not gs.resource_exists(workspace.name, name):
            gs.createCoverage(workspace, datastore, name, title)
        else:
            try:
                gs.rest_catalog.update_coverage(workspace.name, name, name, {'coverage': {'title': title}},
                                                user=gs.user, password=gs.password)
            except Exception:
                LOG.warning('No se pudo fijar el título de la cobertura %s', name)
        created['coverage'] = True

        layer = Layer(
            external=False, datastore=datastore, layer_group=layer_group, name=name, title=title,
            abstract=abstract or title, type='c_GeoTIFF', public=bool(public), visible=True,
            queryable=False, cached=False, single_image=False, vector_tile=False,
            allow_download=False, created_by=user.username, native_srs=srs or 'EPSG:4326')
        max_order = layer_group.layer_set.aggregate(Max('order')).get('order__max')
        if max_order is not None:
            layer.order = max_order + 1
        layer.save()
        created['layer'] = layer

        _refresh_extent(gs, layer)

        primary_role = auth_backend.get_primary_role(user.username)
        roles = [primary_role] if primary_role else []
        services_utils.set_layer_permissions(layer, bool(public), roles, roles, roles)

        _create_class_style(gs, layer, workspace, raster_path, ramp_range)
        gs.createOrUpdateGeoserverLayerGroup(layer_group)
        gs.reload_nodes()
    except Exception:
        LOG.exception('Falló la publicación del ráster %s; se deshace lo creado', name)
        _rollback(gs, workspace, created)
        raise
    return layer, True


def _refresh_extent(gs, layer):
    from gvsigol_services.utils import set_layer_extent
    try:
        ds_type, info = gs.getResourceInfo(layer.datastore.workspace.name, layer.datastore, layer.name, 'json')
        if info:
            set_layer_extent(layer, ds_type, info, gs)
            layer.save()
    except Exception:
        LOG.exception('No se pudo actualizar la extensión de la capa %s', layer.name)


def _own_style_name(workspace, layer):
    return '%s_%s_classes' % (workspace.name, layer.name)


def _create_class_style(gs, layer, workspace, raster_path, ramp_range=None):
    """Estilo de clases (o rampa) registrado en simbología y publicado en GeoServer."""
    from gvsigol_symbology import sld_builder, utils as sym_utils
    from gvsigol_symbology.models import ColorMap
    from gvsigol_symbology.services_color_table import create_style

    style_name = _own_style_name(workspace, layer)
    json_data, cmap_type = build_style_json(style_name, layer.title, raster_path, ramp_range=ramp_range)
    style = create_style(None, json_data, layer, gs)
    if style is None:
        LOG.warning('No se pudo crear el estilo de la capa %s; queda con el estilo por defecto', layer.name)
        return None
    if cmap_type != 'ramp':
        # create_style genera siempre una rampa; las clases discretas necesitan 'values'
        cmap = ColorMap.objects.get(rastersymbolizer__rule__style=style)
        cmap.type = cmap_type
        cmap.save()
        sym_utils.publish_style(gs, layer, style, sld_builder.build_sld(layer, style), overwrite=True)
    return style


def _entries_signature(entries):
    return [(round(float(e['quantity']), 6), str(e['label']), str(e['color']).upper()) for e in entries]


def update_class_style(gs, layer, workspace, raster_path, mode='auto', ramp_range=None):
    """
    Pone al día el estilo que generó este nodo cuando se reemplaza el ráster de una capa.

    mode: 'auto' (solo si cambian las clases o el rango), 'yes' (siempre) o 'no' (nunca). Solo toca
    el estilo propio (<workspace>_<capa>_classes): si el usuario lo cambió de nombre o lo borró, no se
    inventa otro salvo con 'yes'. Las clases que ya existían conservan su color.
    Devuelve 'skipped', 'unchanged', 'updated' o 'created'. Es atómico: si falla la publicación del
    SLD en GeoServer, la base de datos queda como estaba.
    """
    from django.db import transaction
    from gvsigol_symbology import sld_builder
    from gvsigol_symbology.models import ColorMap, ColorMapEntry, Style, StyleLayer

    if mode == 'no':
        return 'skipped'
    style = Style.objects.filter(name=_own_style_name(workspace, layer),
                                 pk__in=StyleLayer.objects.filter(layer=layer).values('style')).first()
    if style is None:
        if mode == 'yes':
            return 'created' if _create_class_style(gs, layer, workspace, raster_path, ramp_range) else 'skipped'
        return 'skipped'

    cmap = ColorMap.objects.filter(rastersymbolizer__rule__style=style).first()
    if cmap is None:
        return 'skipped'
    old = list(ColorMapEntry.objects.filter(color_map=cmap).order_by('order'))
    entries, cmap_type = style_entries(raster_path, {e.label: e.color for e in old}, ramp_range)
    old_signature = [(round(float(e.quantity), 6), e.label, e.color.upper()) for e in old]
    if mode == 'auto' and old_signature == _entries_signature(entries) and cmap.type == cmap_type:
        return 'unchanged'

    with transaction.atomic():
        ColorMapEntry.objects.filter(color_map=cmap).delete()
        for order, e in enumerate(sorted(entries, key=lambda x: float(x['quantity']))):
            ColorMapEntry(color_map=cmap, order=order, color=e['color'], quantity=e['quantity'],
                          label=e['label'], opacity=e['opacity']).save()
        cmap.type = cmap_type
        cmap.save()
        created = gs.createOverwrittenStyle(style.name, sld_builder.build_sld(layer, style), True)
        if not created:
            raise RuntimeError('GeoServer no aceptó el estilo actualizado.')
    return 'updated'


def _rollback(gs, workspace, created):
    """Deshace lo creado en una publicación a medias, ignorando errores secundarios."""
    from gvsigol_services.models import Layer
    try:
        layer = created.get('layer')
        datastore = created.get('datastore')
        if layer is not None:
            try:
                gs.deleteLayerStyles(layer)
            except Exception:
                pass
            try:
                gs.deleteLayerRules(layer)
            except Exception:
                pass
            Layer.objects.filter(pk=layer.pk).delete()
        if created.get('coverage') and datastore is not None and layer is not None:
            try:
                gs.deleteResource(workspace, datastore, layer)
            except Exception:
                pass
        if created.get('store'):
            catalog = gs.getGsconfig()
            store = catalog.get_store(created['store_name'], workspace=workspace.name)
            if store is not None:
                catalog.delete(store, recurse=True, purge='all')
        if datastore is not None:
            datastore.delete()
    except Exception:
        LOG.exception('Error durante el rollback de la publicación ráster')


def publish_targets(user):
    """Workspaces y grupos de capas donde el usuario puede publicar (para el diálogo del nodo)."""
    from gvsigol_services.authorization import can_use_layergroup
    from gvsigol_services.models import LayerGroup, LayerGroupRole, Workspace

    workspaces = [{'id': w.id, 'name': w.name, 'server_id': w.server_id}
                  for w in Workspace.objects.all().order_by('name') if _can_use_workspace(user, w)]
    groups = [{'id': g.id, 'name': g.name, 'title': g.title or g.name, 'server_id': g.server_id}
              for g in LayerGroup.objects.exclude(name='__default_baselayergroup__').order_by('name')
              if can_use_layergroup(user, g, permission=LayerGroupRole.PERM_INCLUDEINPROJECTS)]
    return {'workspaces': workspaces, 'layer_groups': groups}


# --------------------------------------------------------------------------
# Nodo
# --------------------------------------------------------------------------

def _truthy(value):
    return str(value).strip().lower() in ('1', 'true', 'yes', 'si', 'sí', 'on')


def output_RasterPublish(dicc):
    """Publica el ráster de entrada como capa de gvSIG Online. No tiene salidas."""
    from django.contrib.auth import get_user_model
    from gvsigol_services.models import LayerGroup, Workspace
    from .etl_raster import is_raster_ref, extract_band, new_artifact_path, remove_artifact

    raster = next((d for d in dicc.get('data', []) if is_raster_ref(d)), None)
    if not raster:
        raise Exception('Conecta un ráster para publicar.')
    username = dicc.get('_username')
    if not username:
        raise Exception('No se conoce el usuario que ejecuta el ETL.')
    user = get_user_model().objects.get(username=username)

    workspace = _resolve(Workspace, dicc.get('workspace'), 'el workspace')
    layer_group = _resolve(LayerGroup, dicc.get('layer-group'), 'el grupo de capas')

    update_style = (dicc.get('update-style') or 'auto')
    if update_style not in ('auto', 'yes', 'no'):
        raise Exception('Opción de estilo desconocida: %s.' % update_style)
    ramp_range = (_float_or_none(dicc.get('ramp-min')), _float_or_none(dicc.get('ramp-max')))
    if None in ramp_range:
        ramp_range = None
    elif ramp_range[1] <= ramp_range[0]:
        raise Exception('El máximo de la rampa de color debe ser mayor que el mínimo.')

    # Un ráster multibanda se publica entero salvo que se pida una banda concreta
    to_publish, temporary = raster, None
    band = (dicc.get('band') or '').strip()
    if band:
        temporary = new_artifact_path(dicc['id'] + '_band', '.tif')
        extract_band(raster, band, temporary)
        to_publish = temporary
    try:
        layer, created = publish_raster_layer(
            user, to_publish, workspace, layer_group,
            name=dicc.get('layer-name'), title=dicc.get('title'), abstract=(dicc.get('abstract') or None),
            replace=not dicc.get('on-existing') == 'fail',
            public=_truthy(dicc.get('public', False)), update_style=update_style, ramp_range=ramp_range)
    finally:
        if temporary:
            remove_artifact(temporary)
    print('Capa %s %s en %s/%s' % (layer.name, 'publicada' if created else 'actualizada',
                                  workspace.name, layer_group.name))
    return []


def _float_or_none(value):
    try:
        if value is None or str(value).strip() == '':
            return None
        return float(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        raise Exception('"%s" no es un número válido para la rampa de color.' % value)
