# -*- coding: utf-8 -*-
"""Genera fichas del asistente ETL a partir de TableShape.js.

    python manage.py etl_assistant_scaffold input_Csv
    python manage.py etl_assistant_scaffold --all
    python manage.py etl_assistant_scaffold --all --force
"""

from django.core.management.base import BaseCommand, CommandError

from gvsigol_plugin_geoetl.assistant.scaffold import ScaffoldUsageError, selected_types, write_drafts


class Command(BaseCommand):
    help = 'Genera el borrador YAML de uno o todos los nodos del asistente ETL.'

    def add_arguments(self, parser):
        parser.add_argument('tipo', nargs='?', help='Tipo de nodo, por ejemplo input_Csv.')
        parser.add_argument('--all', action='store_true', help='Genera las fichas que falten.')
        parser.add_argument('--force', action='store_true', help='Sobrescribe fichas existentes.')

    def handle(self, *args, **options):
        tipo = options.get('tipo')
        write_all = options['all']
        try:
            types = selected_types(tipo, write_all)
        except ScaffoldUsageError as exc:
            raise CommandError(str(exc))
        written, skipped = write_drafts(
            types=types,
            overwrite=bool(options['force'] or tipo),
        )
        if tipo and not written and not skipped:
            raise CommandError('No existe el nodo %s en TableShape.js.' % tipo)
        if written:
            self.stdout.write('Fichas escritas: %s' % ', '.join(written))
        if skipped:
            self.stdout.write('Sin cambios: %s' % ', '.join(skipped))
