# -*- coding: utf-8 -*-
"""Carga las fichas YAML de assistant/nodes."""

import os

import yaml

NODES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodes')


def _geocoder_engine_choices():
    """ICV (integrado) + motores del plugin de geocodificación, como en el diálogo del nodo."""
    choices = ['ICV']
    try:
        from gvsigol_plugin_geocoding.models import Provider
        for provider in Provider.objects.all():
            engine = getattr(provider, 'type', None)
            if engine and engine not in choices:
                choices.append(engine)
    except Exception:
        pass
    return choices


def _enrich_geocoder_spec(spec):
    if (spec.get('type') or '') != 'trans_Geocoder':
        return
    for item in spec.get('parameters') or []:
        if item.get('name') != 'engine-option':
            continue
        item['choices'] = _geocoder_engine_choices()
        item.setdefault('default', 'ICV')
        break


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
        _enrich_geocoder_spec(spec)
        catalog[type_name] = spec
    return catalog


AI_NODES = ('trans_AIText', 'trans_AIAction')


def available(catalog):
    """El catálogo sin los nodos IA que la instalación tiene apagados."""
    from gvsigol_plugin_geoetl.etl_ai import feature_enabled
    if feature_enabled():
        return catalog
    return {name: spec for name, spec in catalog.items() if name not in AI_NODES}


def port_count(spec, direction):
    return sum(1 for port in spec.get('ports') or [] if port.get('direction') == direction)


def port_kind(spec, direction, index):
    """Tipo de dato (table, raster o model) del puerto `index` de una dirección; table por defecto."""
    ports = [port for port in spec.get('ports') or [] if port.get('direction') == direction]
    if 0 <= index < len(ports):
        return ports[index].get('kind') or 'table'
    return 'table'


def _matches(params, condition):
    return all(str(params.get(name) or '').strip().lower() == str(value or '').strip().lower()
               for name, value in condition.items())


def is_required(item, params):
    """Obligatorio según la ficha: required, y si los hay, required_when / required_unless {parámetro: valor}."""
    if not item.get('required'):
        return False
    params = params or {}
    when = item.get('required_when')
    if isinstance(when, dict) and not _matches(params, when):
        return False
    unless = item.get('required_unless')
    if isinstance(unless, dict) and _matches(params, unless):
        return False
    return True


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
