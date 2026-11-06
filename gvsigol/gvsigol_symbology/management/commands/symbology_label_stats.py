# -*- coding: utf-8 -*-
'''
Estadísticas de SOLO LECTURA sobre las etiquetas (TextSymbolizer) y las escalas de las reglas.
Sirve para dimensionar en producción el impacto de la mejora del etiquetado. No modifica nada.

    python manage.py symbology_label_stats
    python manage.py symbology_label_stats --geometry     # además, tipo de geometría de cada capa (consulta PostGIS)
'''
from collections import Counter

from django.core.management.base import BaseCommand

from gvsigol_symbology.models import Style, StyleLayer, Rule, TextSymbolizer, MapboxStyleCache


class Command(BaseCommand):
    help = 'Estadísticas de solo lectura de etiquetas y escalas de la simbología.'

    def add_arguments(self, parser):
        parser.add_argument('--geometry', action='store_true',
                            help='Incluir el tipo de geometría de las capas etiquetadas (abre una conexión a PostGIS por capa).')

    def line(self, label, value):
        self.stdout.write('  %-48s %s' % (label, value))

    def handle(self, *args, **opts):
        texts = list(TextSymbolizer.objects.select_related('rule__style'))
        styles_with_labels = {t.rule.style_id for t in texts}

        self.stdout.write('ETIQUETAS (TextSymbolizer)')
        self.line('total', len(texts))
        self.line('estilos con etiquetas', len(styles_with_labels))
        self.line('por tipo de leyenda', dict(Counter(t.rule.style.type for t in texts)))
        self.line('activadas (is_actived)', dict(Counter(bool(t.is_actived) for t in texts)))
        self.line('en estilos temporales (__tmp)', sum(1 for t in texts if t.rule.style.name.endswith('__tmp')))
        self.line('anclaje (x, y) más frecuentes', Counter((t.anchor_point_x, t.anchor_point_y) for t in texts).most_common(5))
        self.line('estilo de letra', dict(Counter(t.font_style for t in texts)))
        self.line('grosor de letra', dict(Counter(t.font_weight for t in texts)))
        self.line('opacidad de texto < 1', sum(1 for t in texts if (t.fill_opacity if t.fill_opacity is not None else 1) < 1))
        self.line('opacidad de halo < 1', sum(1 for t in texts if (t.halo_fill_opacity if t.halo_fill_opacity is not None else 1) < 1))
        self.line('sin halo (radio 0 o sin color)', sum(1 for t in texts if not t.halo_radius or not t.halo_fill))
        self.line('sin campo de etiqueta', sum(1 for t in texts if not t.label))
        self.line('reglas de etiqueta con filtro', sum(1 for t in texts if t.rule.filter))

        custom = Style.objects.filter(type__in=('CS', 'MC')).exclude(sld__isnull=True)
        self.stdout.write('ESTILOS PERSONALIZADOS (SLD guardado)')
        self.line('con TextSymbolizer en el SLD', sum(1 for s in custom if 'TextSymbolizer' in (s.sld or '')))
        self.line('con etiquetas compuestas (Concatenate)', sum(1 for s in custom if 'TextSymbolizer' in (s.sld or '')
                                                                 and 'oncatenate' in (s.sld or '')))

        rules = Rule.objects.exclude(style__name__endswith='__tmp')
        with_scale = rules.filter(minscale__gt=0) | rules.filter(maxscale__gt=0)
        self.stdout.write('ESCALAS (afectadas por la conversión escala->zoom del SPA)')
        self.line('reglas totales', rules.count())
        self.line('reglas con escala mínima o máxima', with_scale.distinct().count())
        self.line('estilos con alguna regla con escala', with_scale.values('style_id').distinct().count())
        self.line('estilos con escala propia (Style.min/maxscale)',
                  (Style.objects.filter(minscale__gt=0) | Style.objects.filter(maxscale__gt=0)).distinct().count())
        self.line('cachés de estilo Mapbox guardadas', MapboxStyleCache.objects.count())

        if opts['geometry']:
            from gvsigol_symbology import utils
            geoms = Counter()
            for sid in styles_with_labels:
                sl = StyleLayer.objects.filter(style_id=sid).select_related('layer').first()
                if not sl:
                    geoms['sin capa'] += 1
                    continue
                try:
                    g = utils.get_geometry_field(sl.layer)
                    geoms[g['field_type'] if g else 'no PostGIS (%s)' % sl.layer.type] += 1
                except Exception as e:
                    geoms['error: %s' % type(e).__name__] += 1
            self.stdout.write('GEOMETRÍA DE LAS CAPAS ETIQUETADAS')
            self.line('por tipo', dict(geoms))
