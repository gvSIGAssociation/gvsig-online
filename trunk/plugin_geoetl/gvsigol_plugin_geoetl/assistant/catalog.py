# -*- coding: utf-8 -*-
"""Carga las fichas YAML de assistant/nodes."""

import os

import yaml

NODES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodes')


def load_catalog(directory=None):
    directory = directory or NODES_DIR
    catalog = {}
    if not os.path.isdir(directory):
        return catalog
    for name in sorted(os.listdir(directory)):
        if not name.endswith('.yaml'):
            continue
        path = os.path.join(directory, name)
        with open(path, 'r', encoding='utf-8') as handle:
            spec = yaml.safe_load(handle) or {}
        type_name = spec.get('type') or name[:-5]
        spec['type'] = type_name
        spec.setdefault('parameters', [])
        spec.setdefault('ports', [])
        spec.setdefault('connection_types', [])
        spec.setdefault('sql_parameters', [])
        catalog[type_name] = spec
    return catalog


def port_count(spec, direction):
    return sum(1 for port in spec.get('ports') or [] if port.get('direction') == direction)


def port_kind(spec, direction, index):
    """Tipo de dato (table, raster o model) del puerto `index` de una dirección; table por defecto."""
    ports = [port for port in spec.get('ports') or [] if port.get('direction') == direction]
    if 0 <= index < len(ports):
        return ports[index].get('kind') or 'table'
    return 'table'


def first_sentence(text, limit=160):
    """Primera frase de un resumen, para el índice del prompt (la ficha completa va en get_node_specs)."""
    text = ' '.join((text or '').split())
    cut = text.find('. ')
    if cut != -1:
        text = text[:cut + 1]
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + '…'
    return text


def index_lines(catalog):
    """Índice corto para el prompt: tipo, nombre visible y la primera frase del resumen."""
    lines = []
    for type_name in sorted(catalog):
        spec = catalog[type_name]
        label = spec.get('label') or type_name
        lines.append('%s (%s): %s' % (type_name, label, first_sentence(spec.get('summary'))))
    return lines


def public_specs(catalog, type_names):
    """Fichas que puede ver el modelo, sin campos internos."""
    found = []
    missing = []
    for type_name in type_names:
        spec = catalog.get(type_name)
        if not spec:
            missing.append(type_name)
            continue
        found.append({
            'type': spec['type'],
            'label': spec.get('label') or spec['type'],
            'family': spec.get('family') or '',
            'summary': spec.get('summary') or '',
            'parameters': spec.get('parameters') or [],
            'ports': spec.get('ports') or [],
            'connection_parameter': spec.get('connection_parameter'),
            'connection_types': spec.get('connection_types') or [],
            'sql_parameters': spec.get('sql_parameters') or [],
        })
    return found, missing
