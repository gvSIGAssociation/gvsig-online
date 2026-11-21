# -*- coding: utf-8 -*-
'''
Estadísticas de SOLO LECTURA sobre los simbolizadores de punto, línea y polígono.
Sirve para dimensionar en producción la mejora de simbolizadores (tramas, guiones,
marcas a lo largo de líneas...). No modifica nada.

    python manage.py symbology_symbolizer_stats
'''
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count

from gvsigol_symbology.models import (Style, Rule, Symbolizer, MarkSymbolizer, LineSymbolizer,
                                      PolygonSymbolizer, ExternalGraphicSymbolizer, LibraryRule,
                                      MapboxStyleCache)

# Construcciones de SLD que hoy solo pueden aparecer en estilos personalizados (SLD libre)
SLD_MARKERS = (
    ('GraphicFill (tramas / texturas)', 'GraphicFill'),
    ('GraphicStroke (marcas a lo largo de líneas)', 'GraphicStroke'),
    ('PerpendicularOffset (desplazamiento lateral)', 'PerpendicularOffset'),
    ('stroke-linecap', 'stroke-linecap'),
    ('stroke-linejoin', 'stroke-linejoin'),
    ('stroke-dashoffset', 'stroke-dashoffset'),
    ('shape:// (marcas de trama)', 'shape://'),
    ('extshape://', 'extshape://'),
    ('qgis://', 'qgis://'),
    ('ttf:// (fuentes)', 'ttf://'),
    ('Displacement', 'Displacement'),
    ('startPoint / endPoint (flechas)', 'Point"'),  # ogc:Function name="startPoint"/"endPoint"
    ('vertices', '"vertices"'),
    ('VendorOption random (relleno aleatorio)', 'name="random"'),
)


class Command(BaseCommand):
    help = 'Estadísticas de solo lectura de los simbolizadores de punto, línea y polígono.'

    def line(self, label, value):
        self.stdout.write('  %-52s %s' % (label, value))

    def _common(self, objs, with_fill):
        objs = list(objs)
        self.line('total', len(objs))
        self.line('en estilos temporales (__tmp)', sum(1 for o in objs if o.rule.style.name.endswith('__tmp')))
        self.line('en biblioteca', sum(1 for o in objs if o.rule_id in self.library_rules))
        self.line('patrón de guiones', Counter(o.stroke_dash_array for o in objs).most_common(12))
        self.line('grosor de borde', Counter(o.stroke_width for o in objs).most_common(12))
        self.line('opacidad de borde', Counter(o.stroke_opacity for o in objs).most_common(8))
        if with_fill:
            self.line('opacidad de relleno', Counter(o.fill_opacity for o in objs).most_common(8))
        self.line('colores que no son #rrggbb',
                  Counter(c for o in objs for c in ([o.stroke] + ([o.fill] if with_fill else []))
                          if not (isinstance(c, str) and len(c) == 7 and c.startswith('#'))).most_common(8))
        return objs

    def handle(self, *args, **opts):
        self.library_rules = set(LibraryRule.objects.values_list('rule_id', flat=True))

        self.stdout.write('MARCAS (MarkSymbolizer)')
        marks = self._common(MarkSymbolizer.objects.select_related('rule__style'), True)
        self.line('forma (well_known_name)', Counter(m.well_known_name for m in marks).most_common())
        self.line('tamaño', Counter(m.size for m in marks).most_common(10))
        self.line('rotación distinta de 0', sum(1 for m in marks if m.rotation))
        self.line('opacidad global', Counter(m.opacity for m in marks).most_common(5))

        self.stdout.write('LÍNEAS (LineSymbolizer)')
        self._common(LineSymbolizer.objects.select_related('rule__style'), False)

        self.stdout.write('POLÍGONOS (PolygonSymbolizer)')
        self._common(PolygonSymbolizer.objects.select_related('rule__style'), True)

        self.stdout.write('IMÁGENES (ExternalGraphicSymbolizer)')
        egs = list(ExternalGraphicSymbolizer.objects.all())
        self.line('total', len(egs))
        self.line('formato', Counter(e.format for e in egs).most_common())

        self.stdout.write('REGLAS')
        per_rule = Counter(
            Symbolizer.objects.exclude(textsymbolizer__isnull=False).values('rule_id')
            .annotate(n=Count('id')).values_list('n', flat=True))
        self.line('simbolizadores (sin etiquetas) por regla', sorted(per_rule.items()))
        self.line('reglas totales', Rule.objects.count())
        self.line('estilos por tipo de leyenda', dict(Counter(Style.objects.values_list('type', flat=True))))

        custom = [s.sld or '' for s in Style.objects.filter(type__in=('CS', 'MC')).exclude(sld__isnull=True)]
        imported = [s.sld or '' for s in Style.objects.exclude(type__in=('CS', 'MC')).exclude(sld__isnull=True)
                    .exclude(sld='')]
        self.stdout.write('SLD GUARDADO (personalizados CS/MC: %d; otros con SLD guardado: %d)'
                          % (len(custom), len(imported)))
        for label, marker in SLD_MARKERS:
            self.line(label, '%d / %d' % (sum(1 for s in custom if marker in s), sum(1 for s in imported if marker in s)))
        self.line('cachés de estilo Mapbox guardadas', MapboxStyleCache.objects.count())
