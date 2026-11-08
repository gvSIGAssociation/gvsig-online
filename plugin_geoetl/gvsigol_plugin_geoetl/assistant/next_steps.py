# -*- coding: utf-8 -*-
"""Siguiente paso sugerido tras cada respuesta (usabilidad, fase 5: ETL_ASSISTANT_NEXT_STEPS).

Son reglas sobre cómo queda el flujo: gratis y previsibles, sin llamar al
modelo. El servidor devuelve solo códigos; el texto del botón y el mensaje que
envía los pone el panel, que los traduce como el resto de la interfaz.
"""

import logging

from .review import ERROR, check_graph, graph_after

LOGGER = logging.getLogger('gvsigol')

ADD_OUTPUT = 'add_output'
EXPLAIN = 'explain'
REVIEW = 'review'

MAX_STEPS = 3

# Con estos problemas lo primero es arreglarlos: el panel ya ofrece Arreglar
_BLOCKERS = ('unconnected_input', 'duplicated_input', 'cycle', 'kind_mismatch', 'bad_port', 'source', 'target')


def next_steps_enabled():
    try:
        from gvsigol_plugin_geoetl import settings as geoetl_settings
        return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_NEXT_STEPS', False))
    except Exception:
        return False


def compute_steps(nodes, issues, restricted=False):
    """Códigos de las sugerencias para un flujo y sus problemas."""
    if not nodes:
        return []
    codes = {issue.get('code') for issue in issues}
    if codes.intersection(_BLOCKERS):
        return []
    steps = []
    if 'no_output' in codes and not restricted:      # la edición restringida no añade salidas
        steps.append(ADD_OUTPUT)
    if any(issue.get('level') == ERROR for issue in issues):
        steps.append(REVIEW)
    else:
        steps.extend([EXPLAIN, REVIEW])
    return steps[:MAX_STEPS]


def attach_next_steps(payload, holder, canvas, catalog, context):
    """Añade 'next_steps' a la respuesta. Sin el interruptor no cambia nada; un fallo tampoco."""
    if not next_steps_enabled() or payload.get('error') or payload.get('needs_confirmation') or payload.get('questions'):
        return payload
    try:
        nodes, edges = graph_after(holder[-1]['proposal'] if holder else None, canvas)
        issues = check_graph(nodes, edges, catalog, context.connections)
        steps = compute_steps(nodes, issues, context.restricted)
        if steps:
            payload['next_steps'] = [{'code': code} for code in steps]
    except Exception:
        LOGGER.exception('etl_assistant: no se pudieron calcular las sugerencias')
    return payload
