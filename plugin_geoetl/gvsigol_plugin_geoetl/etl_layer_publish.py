# -*- coding: utf-8 -*-
"""
Nodo de salida que publica una tabla de geoetl como capa de gvSIG Online.

La tabla se escribe en un almacén PostGIS con output_Postgis y se publica con
publish_postgis_resource, el servicio del núcleo que usa la importación de
capas: registra la capa, sus permisos y el estilo por defecto.

Las tablas intermedias del ETL suelen tener una columna de geometría sin tipo,
y GeoServer y el estilo por defecto necesitan uno concreto: se escribe una copia
con la columna tipada. Si la tabla mezcla puntos, líneas o polígonos no se
publica, porque un único estilo no puede representarla.

Los imports de Django/gvsigol_services son perezosos, como en etl_raster_publish.
"""

import json
import logging

import psycopg2
from psycopg2 import sql

from .etl_raster_publish import _refresh_extent, _resolve, _truthy, safe_layer_name
from .settings import GEOETL_DB

LOG = logging.getLogger('gvsigol')

GEOMETRY_COLUMN = 'wkb_geometry'
_FAMILIES = {
    'POINT': 'Point', 'MULTIPOINT': 'Point',
    'LINESTRING': 'LineString', 'MULTILINESTRING': 'LineString',
    'POLYGON': 'Polygon', 'MULTIPOLYGON': 'Polygon',
}
_GENERIC = ('GEOMETRY', '')


def target_geometry_type(kinds):
    """Tipo de la columna a partir de los tipos de geometría que hay en la tabla. Lanza si se mezclan."""
    names = [str(kind).upper() for kind in kinds]
    unknown = [name for name in names if name not in _FAMILIES]
    if unknown:
        raise ValueError('La tabla tiene geometrías de tipo %s y no se puede publicar como capa.' % ', '.join(unknown))
    families = {_FAMILIES[name] for name in names}
    if len(families) != 1:
        raise ValueError('La tabla mezcla tipos de geometría (%s) y no se puede publicar con un único estilo. '
                         'Sepárala antes por tipo de geometría.' % ', '.join(sorted(families)))
    family = families.pop()
    if family == 'Point' and 'MULTIPOINT' not in names:
        return 'Point'
    return 'Multi' + family


def _geoetl_connection():
    return psycopg2.connect(user=GEOETL_DB['user'], password=GEOETL_DB['password'], host=GEOETL_DB['host'],
                            port=GEOETL_DB['port'], database=GEOETL_DB['database'])


def _target_connection(datastore):
    params = json.loads(datastore.connection.connection_params)
    return psycopg2.connect(user=params['user'], password=params['passwd'], host=params['host'],
                            port=params['port'], database=params['database'])


def _columns(cur, schema, table):
    cur.execute('SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s',
                [schema, table])
    return [row[0] for row in cur.fetchall()]


def source_geometry(table):
    """(tipos de geometría, srid) de la tabla de entrada; ([], None) si no tiene filas con geometría."""
    conn = _geoetl_connection()
    try:
        cur = conn.cursor()
        if GEOMETRY_COLUMN not in _columns(cur, GEOETL_DB['schema'], table):
            raise ValueError('La tabla de entrada no tiene geometría. Para guardarla sin publicarla como capa, '
                             'usa la salida PostGIS.')
        cur.execute(sql.SQL('SELECT DISTINCT upper(GeometryType({g})), ST_SRID({g}) FROM {s}.{t} WHERE {g} IS NOT NULL')
                    .format(g=sql.Identifier(GEOMETRY_COLUMN), s=sql.Identifier(GEOETL_DB['schema']), t=sql.Identifier(table)))
        rows = cur.fetchall()
    finally:
        conn.close()
    srids = {row[1] for row in rows}
    if len(srids) > 1:
        raise ValueError('La tabla mezcla sistemas de referencia (%s). Reproyéctala antes de publicarla.'
                         % ', '.join(str(srid) for srid in sorted(srids)))
    return [row[0] for row in rows], (srids.pop() if srids else None)


def copy_typed(table, copy_name, geometry_type, srid):
    """Copia la tabla de entrada con la columna de geometría tipada, sin tocar el original."""
    conn = _geoetl_connection()
    try:
        cur = conn.cursor()
        identifiers = {'s': sql.Identifier(GEOETL_DB['schema']), 'c': sql.Identifier(copy_name),
                       'o': sql.Identifier(table), 'g': sql.Identifier(GEOMETRY_COLUMN)}
        cur.execute(sql.SQL('DROP TABLE IF EXISTS {s}.{c}').format(**identifiers))
        cur.execute(sql.SQL('CREATE TABLE {s}.{c} AS SELECT * FROM {s}.{o}').format(**identifiers))
        value = 'ST_Multi({g})' if geometry_type.startswith('Multi') else '{g}'
        cur.execute(sql.SQL('ALTER TABLE {s}.{c} ALTER COLUMN {g} TYPE geometry(%s, %s) USING ' % (geometry_type, int(srid))
                            + value).format(**identifiers))
        conn.commit()
    finally:
        conn.close()


def drop_copy(copy_name):
    conn = _geoetl_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql.SQL('DROP TABLE IF EXISTS {s}.{c}').format(s=sql.Identifier(GEOETL_DB['schema']),
                                                                   c=sql.Identifier(copy_name)))
        conn.commit()
    finally:
        conn.close()


def table_exists(datastore, name):
    conn = _target_connection(datastore)
    try:
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s',
                    [datastore.schema, name])
        return cur.fetchone() is not None
    finally:
        conn.close()


def drop_target(datastore, name):
    conn = _target_connection(datastore)
    try:
        cur = conn.cursor()
        cur.execute(sql.SQL('DROP TABLE IF EXISTS {s}.{t}').format(s=sql.Identifier(datastore.schema), t=sql.Identifier(name)))
        conn.commit()
    finally:
        conn.close()


def check_replace(datastore, name, source_table, geometry_type, srid):
    """Comprueba que los datos nuevos caben en la tabla publicada ANTES de vaciarla."""
    source = _geoetl_connection()
    target = _target_connection(datastore)
    try:
        wanted = _columns(source.cursor(), GEOETL_DB['schema'], source_table)
        cur = target.cursor()
        existing = _columns(cur, datastore.schema, name)
        if not existing:
            raise ValueError('La capa "%s" existe, pero no se encuentra su tabla en el almacén.' % name)
        missing = [column for column in wanted if column not in existing]
        if missing:
            raise ValueError('La capa "%s" no tiene las columnas %s, así que no se pueden reemplazar sus datos. '
                             'No se ha cambiado nada: quita esas columnas del flujo o publica con otro nombre.'
                             % (name, ', '.join(missing)))
        cur.execute('SELECT type, srid FROM geometry_columns WHERE f_table_schema = %s AND f_table_name = %s AND '
                    'f_geometry_column = %s', [datastore.schema, name, GEOMETRY_COLUMN])
        row = cur.fetchone()
    finally:
        source.close()
        target.close()
    if row and geometry_type and (
            (str(row[0]).upper() not in _GENERIC and str(row[0]).upper() != geometry_type.upper()) or (srid and row[1] and row[1] != srid)):
        raise ValueError('La capa "%s" es de tipo %s (EPSG:%s) y los datos nuevos son %s (EPSG:%s). No se ha cambiado '
                         'nada: reproyecta los datos o publica con otro nombre.' % (name, row[0], row[1], geometry_type, srid))


def find_datastore(value):
    """El almacén se guarda como workspace/nombre, para que el flujo sea portable entre instalaciones."""
    from gvsigol_services.models import Datastore

    workspace, _, name = str(value or '').partition('/')
    datastore = Datastore.objects.filter(workspace__name=workspace, name=name).select_related('connection', 'workspace').first()
    if datastore is None:
        raise ValueError('No se encuentra el almacén "%s".' % value)
    if datastore.type != 'v_PostGIS' or datastore.connection is None or not datastore.schema:
        raise ValueError('El almacén "%s" no se puede usar para publicar: no es un PostGIS con conexión y esquema.' % value)
    return datastore


def check_datastore_allowed(user, datastore):
    """Mismo criterio que el diálogo: usar el almacén y usar su conexión en ETL."""
    from types import SimpleNamespace

    from .assistant.context import usable_datastores
    from .views import get_etl_connections_list

    connections = get_etl_connections_list(SimpleNamespace(user=user))
    if not any(item['name'] == datastore.name and item['workspace'] == datastore.workspace.name
               for item in usable_datastores(user, connections, [datastore])):
        raise PermissionError('No tienes permiso para publicar en el almacén "%s".' % datastore.name)


def _write(table, datastore, name, operation, node_id):
    from . import etl_tasks
    etl_tasks.output_Postgis({
        'id': node_id, 'data': [table], 'db-option': datastore.connection.name, 'schema-name-option': datastore.schema,
        'tablename': name, 'operation': operation, 'match': '', 'create-gvsigol-fields': operation == 'CREATE',
    })


def _rollback(datastore, name):
    """Deja las cosas como estaban si falla una publicación nueva. Cada paso es independiente."""
    from gvsigol_core import utils as core_utils
    from gvsigol_services import geographic_servers
    from gvsigol_services.models import Layer

    gs = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server_id)
    layer = Layer.objects.filter(datastore=datastore, name=name).first()
    steps = []
    if layer is not None:
        steps = [lambda: gs.deleteLayerStyles(layer), lambda: gs.deleteLayerRules(layer),
                 lambda: core_utils.toc_remove_layer(layer), lambda: gs.deleteResource(datastore.workspace, datastore, layer),
                 lambda: Layer.objects.filter(pk=layer.pk).delete()]
    else:
        # El recurso de GeoServer se crea antes que la capa de gvSIG
        from types import SimpleNamespace
        steps.append(lambda: gs.deleteResource(datastore.workspace, datastore, SimpleNamespace(name=name)))
    steps.append(lambda: drop_target(datastore, name))
    for step in steps:
        try:
            step()
        except Exception:
            LOG.exception('Error al deshacer la publicación de la capa %s', name)


def _publish_new(user, datastore, layer_group, name, title, abstract, public, source, geometry_type, srid, node_id):
    from gvsigol_services.layer_publish import publish_postgis_resource

    if not geometry_type:
        raise ValueError('La tabla de entrada no tiene filas con geometría: no se puede publicar una capa nueva.')
    if not srid:
        raise ValueError('La geometría de la tabla no tiene sistema de referencia. Asígnaselo antes de publicarla.')
    if table_exists(datastore, name):
        raise ValueError('Ya existe la tabla "%s" en el almacén y no está publicada como capa. Usa otro nombre.' % name)
    _write(source, datastore, name, 'CREATE', node_id)
    try:
        properties = {'native_srs': 'EPSG:%d' % srid}
        if abstract:
            properties['abstract'] = abstract
        return publish_postgis_resource(user=user, datastore=datastore, layer_group=layer_group, name=name, title=title,
                                        has_geometry=True, properties=properties, is_public=public)
    except Exception:
        LOG.exception('Falló la publicación de la capa %s; se deshace lo creado', name)
        _rollback(datastore, name)
        raise


def _replace_data(user, datastore, existing, source, geometry_type, srid, node_id):
    from gvsigol_services import geographic_servers, utils as services_utils

    if not services_utils.can_manage_layer(user, existing):
        raise PermissionError('No tienes permiso para modificar la capa "%s".' % existing.name)
    check_replace(datastore, existing.name, source, geometry_type, srid)
    _write(source, datastore, existing.name, 'OVERWRITE', node_id)
    # Los datos ya están reemplazados: un fallo aquí no debe dar por fallida la publicación
    try:
        gs = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server_id)
        gs.updateBoundingBoxFromData(existing)
        _refresh_extent(gs, existing)
        gs.clearCache(datastore.workspace.name, existing)
        gs.updateThumbnail(existing, 'update')
        gs.reload_nodes()
    except Exception:
        LOG.exception('No se pudo actualizar GeoServer tras reemplazar la capa %s', existing.name)
        print('AVISO: los datos de la capa %s se han reemplazado, pero no se ha podido actualizar su extensión o '
              'su caché en GeoServer.' % existing.name)


def output_LayerPublish(dicc):
    """Publica la tabla de entrada como capa de gvSIG Online. No tiene salidas."""
    from django.contrib.auth import get_user_model
    from gvsigol_services.models import Layer, LayerGroup

    data = dicc.get('data') or []
    if not data:
        raise Exception('Conecta una tabla para publicar.')
    username = dicc.get('_username')
    if not username:
        raise Exception('No se conoce el usuario que ejecuta el ETL.')
    user = get_user_model().objects.get(username=username)
    name = safe_layer_name(dicc.get('layer-name') or dicc.get('title'))
    if not name:
        raise Exception('Indica un nombre para la capa.')
    title = (dicc.get('title') or name)[:150]

    datastore = find_datastore(dicc.get('datastore'))
    layer_group = _resolve(LayerGroup, dicc.get('layer-group'), 'el grupo de capas')
    check_datastore_allowed(user, datastore)

    existing = Layer.objects.filter(datastore=datastore, name=name).first()
    if existing and dicc.get('on-existing') == 'fail':
        raise Exception('Ya existe la capa "%s" en el almacén.' % name)

    kinds, srid = source_geometry(data[0])
    geometry_type = target_geometry_type(kinds) if kinds else None
    source, copy_name = data[0], None
    if geometry_type:
        copy_name = dicc['id'] + '_publish'
        copy_typed(data[0], copy_name, geometry_type, srid)
        source = copy_name
    try:
        if existing:
            _replace_data(user, datastore, existing, source, geometry_type, srid, dicc['id'])
            print('Datos de la capa %s reemplazados en %s' % (name, datastore.name))
        else:
            _publish_new(user, datastore, layer_group, name, title, dicc.get('abstract') or None,
                         _truthy(dicc.get('public', False)), source, geometry_type, srid, dicc['id'])
            print('Capa %s publicada en %s/%s' % (name, datastore.workspace.name, layer_group.name))
    finally:
        if copy_name:
            drop_copy(copy_name)
    return []
