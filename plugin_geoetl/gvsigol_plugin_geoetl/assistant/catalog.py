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


def index_lines(catalog):
    """Índice corto para el prompt: tipo y una línea."""
    lines = []
    for type_name in sorted(catalog):
        spec = catalog[type_name]
        summary = (spec.get('summary') or '').replace('\n', ' ')
        lines.append('%s: %s' % (type_name, summary))
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
