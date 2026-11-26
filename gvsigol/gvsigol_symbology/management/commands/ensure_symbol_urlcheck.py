# -*- coding: utf-8 -*-
"""
Añade a cada GeoServer la regla de URL checks que permite los iconos de las bibliotecas de
símbolos (ver gvsigol_symbology/geoserver_urlchecks.py). Si ya hay una regla que lo permite,
no cambia nada. Con --dry-run solo informa.
"""
from django.core.management.base import BaseCommand

from gvsigol_services import geographic_servers
from gvsigol_services.models import Server
from gvsigol_symbology import geoserver_urlchecks


class Command(BaseCommand):
    help = 'Permite en GeoServer (URL checks) los iconos de las bibliotecas de símbolos.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo comprueba, sin crear la regla.')

    def handle(self, *args, **opts):
        self.stdout.write('Regla: %s' % geoserver_urlchecks.library_regex())
        for server in Server.objects.all():
            gs = geographic_servers.get_instance().get_server_by_id(server.id)
            if gs is None:
                continue
            if opts['dry_run']:
                result = geoserver_urlchecks.check_symbol_library_urlcheck(gs)
            else:
                result = geoserver_urlchecks.ensure_symbol_library_urlcheck(gs)
            labels = {'exists': 'ya permitido', 'created': 'regla creada', 'missing': 'falta la regla (no se crea: --dry-run)',
                      'error': 'no se pudo comprobar o crear (ver log)'}
            self.stdout.write('%s: %s' % (server.name, labels.get(result, result)))
