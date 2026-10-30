# -*- coding: utf-8 -*-
"""Genera fichas YAML a partir de TableShape.js.

El comando de manage.py es un envoltorio. Los tests llaman a estas funciones.
"""

import os

import yaml

from .shapes import parse_all, parse_node, read_tableshape, node_block

NODES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodes')

SUMMARIES = {
    'input_Csv': 'Lee un fichero CSV o TXT. El esquema lo completa el usuario al aceptar el modal.',
    'input_Excel': 'Lee una hoja de un fichero Excel. El esquema lo completa el usuario al aceptar.',
    'input_Json': 'Lee un fichero JSON o responde a una URL.',
    'input_Xml': 'Lee un XML a partir de una etiqueta.',
    'input_Shp': 'Lee un shapefile con su codificación y EPSG.',
    'input_Kml': 'Lee un KML o KMZ.',
    'input_Postgis': 'Lee una tabla o una consulta de una conexión PostgreSQL o PostGIS.',
    'input_Oracle': 'Lee una tabla o una consulta de Oracle.',
    'input_SqlServer': 'Lee una tabla o una consulta de SQL Server.',
    'input_Sharepoint': 'Lee ficheros Excel de una biblioteca de SharePoint.',
    'input_Indenova': 'Lee expedientes de InDenova entre dos fechas.',
    'input_Segex': 'Lee trámites de SEGEX.',
    'input_EnterApi': 'Lee datos de EnterApi (epígrafe, por ejemplo inmuebles).',
    'input_PadronAlbacete': 'Lee el padrón de Albacete (servicio PRO o PRE).',
    'input_PadronAtm': 'Lee el padrón ATM a través de su conexión.',
    'crea_Grid': 'Crea una malla de celdas rectangulares a partir de un origen, tamaño y EPSG.',
    'trans_Calculator': 'Crea o rellena un atributo con una expresión.',
    'trans_ChangeAttrType': 'Cambia el tipo de un atributo.',
    'trans_CompareRows': 'Compara filas de dos entradas por un atributo. Tiene dos entradas y varias salidas.',
    'trans_ConcatAttr': 'Concatena atributos en uno nuevo.',
    'trans_Counter': 'Numera filas, opcionalmente dentro de grupos.',
    'trans_CorrectSpelling': 'Corrige la ortografía de un atributo de texto.',
    'trans_CurrentDate': 'Escribe la fecha actual en un atributo.',
    'trans_CreateAttr': 'Añade un atributo con un valor constante.',
    'trans_ExposeAttr': 'Expone atributos anidados.',
    'trans_Filter': 'Filtra filas. La salida 0 son las que cumplen y la 1 las que no.',
    'trans_FilterDupli': 'Separa duplicados. La salida 0 son las filas únicas.',
    'trans_Join': 'Cruza dos tablas por atributos. Entrada 0 es la principal y la 1 la secundaria.',
    'trans_KeepAttr': 'Conserva solo los atributos indicados.',
    'trans_ModifyValue': 'Sustituye el valor de un atributo.',
    'trans_PadAttr': 'Rellena un texto hasta una longitud por la izquierda o la derecha.',
    'trans_RemoveAttr': 'Elimina atributos.',
    'trans_RenameAttr': 'Renombra un atributo.',
    'trans_Stats': 'Calcula estadísticas de un atributo, opcionalmente por grupos.',
    'trans_Buffer': 'Calcula un área de influencia. El radio puede ser fijo o un atributo.',
    'trans_CadastralGeom': 'Obtiene la geometría catastral a partir de la referencia catastral.',
    'trans_CalcArea': 'Calcula el área y la guarda en un atributo.',
    'trans_CalcLength': 'Añade la longitud de la geometría en el atributo _length.',
    'trans_Difference': 'Diferencia geométrica. La entrada 0 es la geometría de la que se resta la 1.',
    'trans_ExplodeGeom': 'Separa las partes de una geometría múltiple.',
    'trans_FilterGeom': 'Clasifica la geometría en seis salidas: punto, multipunto, línea, multilínea, polígono y multipolígono.',
    'trans_Geocoder': 'Geocodifica una dirección o hace geocodificación inversa.',
    'trans_Intersection': 'Intersección geométrica de dos entradas.',
    'trans_LineEndPoints': 'Añade las coordenadas de los extremos de una línea.',
    'trans_MGRS': 'Convierte entre coordenada MGRS y longitud/latitud.',
    'trans_NearestNeighbor': 'Asigna a cada fila de la entrada 0 el vecino más cercano de la entrada 1.',
    'trans_RemoveGeom': 'Quita la geometría y deja solo los atributos.',
    'trans_Reproject': 'Reproyecta la geometría de un EPSG a otro.',
    'trans_SimpGeom': 'Comprueba que la geometría es simple. stop detiene el flujo si no lo es.',
    'trans_SpatialRel': 'Filtra la entrada 0 según una relación espacial con la entrada 1.',
    'trans_TextToPoint': 'Crea un punto a partir de columnas de longitud y latitud.',
    'trans_Union': 'Une geometrías, opcionalmente agrupando por un atributo.',
    'trans_ValGeom': 'Valida la geometría. stop detiene el flujo si no es válida.',
    'trans_WktGeom': 'Convierte un atributo WKT en geometría.',
    'trans_Cluster': 'Agrupa puntos con DBSCAN o K-means.',
    'trans_IDW': 'Interpolación IDW. El resultado es una rejilla.',
    'trans_Kriging': 'Interpolación kriging. El resultado es una rejilla.',
    'trans_Voronoi': 'Construye el diagrama de Voronoi de los puntos.',
    'trans_ExplodeList': 'Expande un atributo que contiene una lista en varias filas.',
    'trans_SplitAttr': 'Parte un texto en varios atributos.',
    'trans_ExecuteSQL': 'Ejecuta SQL contra una conexión. Puede leer y escribir; en edición restringida no se puede cambiar.',
    'output_Postgis': 'Escribe el resultado en una tabla PostgreSQL o PostGIS.',
    'output_Visualizer': 'Publica el resultado en el visualizador con un nombre de capa y un grupo.',
}

EXTRA_CHOICES = {
    ('output_Postgis', 'operation'): [
        'CREATE', 'DROPANDCREATE', 'APPEND', 'OVERWRITE', 'UPDATE', 'DELETE',
    ],
    ('trans_MGRS', 'select'): ['mgrstolatlon', 'latlontomgrs'],
    ('input_Sharepoint', 'format'): ['excel'],
    ('input_Csv', 'schema-option'): ['has-schema', 'no-schema'],
    ('input_Kml', 'reading'): ['single', 'multiple'],
}


def _apply_copy(spec):
    spec = dict(spec)
    spec['summary'] = SUMMARIES.get(spec['type'], spec.get('summary') or '')
    parameters = []
    for item in spec.get('parameters') or []:
        item = dict(item)
        extra = EXTRA_CHOICES.get((spec['type'], item['name']))
        if extra and not item.get('choices'):
            item['choices'] = list(extra)
        parameters.append(item)
    spec['parameters'] = parameters
    return spec


def draft_for(type_name, source=None):
    source = source if source is not None else read_tableshape()
    block = node_block(source, type_name)
    from .shapes import palette_labels
    label = palette_labels().get(type_name, type_name)
    return _apply_copy(parse_node(type_name, block, label))


def drafts_for_all(source=None, html=None):
    return [_apply_copy(spec) for spec in parse_all(source, html)]


def dump_yaml(spec):
    return yaml.safe_dump(
        spec,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


class ScaffoldUsageError(Exception):
    """Argumentos incompatibles del comando. manage.py lo convierte en CommandError."""


def selected_types(tipo, write_all):
    if not tipo and not write_all:
        raise ScaffoldUsageError('Indica un tipo de nodo o --all.')
    if tipo and write_all:
        raise ScaffoldUsageError('Usa un tipo o --all, no los dos.')
    return [tipo] if tipo else None


def write_drafts(directory=None, types=None, overwrite=False):
    """Escribe fichas. Con overwrite False no pisa una ficha ya existente."""
    directory = directory or NODES_DIR
    os.makedirs(directory, exist_ok=True)
    written = []
    skipped = []
    for spec in drafts_for_all():
        if types and spec['type'] not in types:
            continue
        path = os.path.join(directory, spec['type'] + '.yaml')
        if os.path.exists(path) and not overwrite:
            skipped.append(spec['type'])
            continue
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(dump_yaml(spec))
        written.append(spec['type'])
    return written, skipped
