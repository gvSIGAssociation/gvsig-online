# -*- coding: utf-8 -*-
'''
Regenera en GeoServer el SLD de estilos de simbología a partir de la BD.

Uso típico tras corregir el operador "menor que" (antes se publicaba como
PropertyIsGreaterThan en filtros de una sola condición):

    python manage.py regenerate_symbology_sld --less-than            # solo lista (dry-run)
    python manage.py regenerate_symbology_sld --less-than --apply    # publica

Otras opciones: --style-id N (repetible) para estilos concretos, --all para todos.
Los estilos de SLD guardado (CS, MC) y los temporales (__tmp) nunca se tocan: su
SLD no se construye desde las reglas. No modifica la BD de gvSIG.
'''
import json
import logging

from django.core.management.base import BaseCommand, CommandError

from gvsigol_symbology.models import Style, StyleLayer, Rule
from gvsigol_symbology import sld_builder
from gvsigol_symbology.services import SLD_STORED_TYPES

logger = logging.getLogger('gvsigol')


def _single_condition_ops(filter_text):
    '''Operaciones de los filtros de una sola condición (los que usan get_operation_symbol).'''
    if not filter_text:
        return []
    try:
        f = json.loads(filter_text)
    except (TypeError, ValueError):
        return []
    if isinstance(f, list):
        return [f[0].get('operation')] if len(f) == 1 and isinstance(f[0], dict) else []
    if isinstance(f, dict):
        return [f.get('operation')]
    return []


def style_uses_single_less_than(style):
    for filter_text in Rule.objects.filter(style=style).values_list('filter', flat=True):
        if 'is_less_than' in _single_condition_ops(filter_text):
            return True
    return False


class Command(BaseCommand):
    help = 'Regenera en GeoServer el SLD de estilos de simbología a partir de la BD (dry-run por defecto).'

    def add_arguments(self, parser):
        parser.add_argument('--less-than', action='store_true',
                            help='Estilos con filtros de una condición "is_less_than" (corrección del operador).')
        parser.add_argument('--style-id', type=int, action='append', default=[],
                            help='Id de estilo concreto (repetible).')
        parser.add_argument('--all', action='store_true', help='Todos los estilos construidos desde reglas.')
        parser.add_argument('--apply', action='store_true', help='Publicar en GeoServer (sin esto solo lista).')

    def handle(self, *args, **opts):
        if not (opts['less_than'] or opts['style_id'] or opts['all']):
            raise CommandError('Indica --less-than, --style-id o --all')
        from gvsigol_services import geographic_servers
        from gvsigol_services.tasks import do_layer_cache_clear

        styles = Style.objects.exclude(type__in=SLD_STORED_TYPES).exclude(name__endswith='__tmp')
        if opts['style_id']:
            styles = styles.filter(id__in=opts['style_id'])
        selected = [s for s in styles.order_by('id')
                    if not opts['less_than'] or style_uses_single_less_than(s)]

        mode = 'APLICANDO' if opts['apply'] else 'DRY-RUN (usa --apply para publicar)'
        self.stdout.write('%s: %d estilo(s)' % (mode, len(selected)))
        servers_to_reload = {}
        ok = errors = 0
        for style in selected:
            style_layers = list(StyleLayer.objects.filter(style=style).select_related(
                'layer__datastore__workspace__server'))
            if not style_layers:
                self.stdout.write('  - %s (id %d, %s): sin capa, se omite' % (style.name, style.id, style.type))
                continue
            layer = style_layers[0].layer
            self.stdout.write('  - %s (id %d, %s) capa %s' % (style.name, style.id, style.type, layer.name))
            if not opts['apply']:
                continue
            try:
                gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
                sld_body = sld_builder.build_sld(layer, style)
                if not gs.createOverwrittenStyle(style.name, sld_body, True):
                    raise Exception(getattr(gs, 'last_style_error', None) or 'createOverwrittenStyle devolvió False')
                servers_to_reload[gs.id] = gs
                for sl in style_layers:
                    if getattr(sl.layer, 'cached', False):
                        try:
                            do_layer_cache_clear(sl.layer, gs)
                        except Exception:
                            logger.exception('Error limpiando caché de %s', sl.layer.name)
                ok += 1
            except Exception as e:
                errors += 1
                logger.exception('Error regenerando el estilo %s', style.name)
                self.stderr.write('    ERROR: %s' % e)
        for gs in servers_to_reload.values():
            gs.reload_nodes()
        if opts['apply']:
            self.stdout.write('Regenerados: %d, errores: %d' % (ok, errors))
