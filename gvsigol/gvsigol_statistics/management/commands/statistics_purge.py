# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
Borra eventos de estadísticas antiguos (retención). No se ejecuta solo: lanzarlo
a mano o desde cron, por ejemplo una vez al mes:

    python manage.py statistics_purge --older-than-days 730 --dry-run
    python manage.py statistics_purge --older-than-days 730

Por defecto solo borra los verbos de estadísticas (los del core y los declarados
en STATISTICS por las apps), nunca otras acciones de actstream.
'''

import datetime
import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

MIN_DAYS = 30


class Command(BaseCommand):
    help = 'Delete statistics events (actstream actions) older than the given number of days.'

    def add_arguments(self, parser):
        parser.add_argument('--older-than-days', type=int, required=True,
                            help='Delete events older than this number of days (minimum %d).' % MIN_DAYS)
        parser.add_argument('--verb', action='append', dest='verbs', default=None,
                            help='Only this verb (repeatable). Default: all statistics verbs.')
        parser.add_argument('--batch-size', type=int, default=5000,
                            help='Rows deleted per batch (default 5000), to avoid long locks.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Only count what would be deleted.')

    def handle(self, *args, **options):
        from actstream.models import Action
        from gvsigol_statistics.analytics import get_known_verbs

        days = options['older_than_days']
        if days < MIN_DAYS:
            raise CommandError('--older-than-days must be at least %d' % MIN_DAYS)
        batch_size = options['batch_size']
        if not 100 <= batch_size <= 100000:
            raise CommandError('--batch-size must be between 100 and 100000')

        known = get_known_verbs()
        verbs = options['verbs'] or sorted(known)
        unknown = [v for v in verbs if v not in known]
        if unknown:
            raise CommandError('Not a statistics verb: %s' % ', '.join(unknown))

        cutoff = timezone.now() - datetime.timedelta(days=days)
        queryset = Action.objects.filter(verb__in=verbs, timestamp__lt=cutoff).order_by()
        total = queryset.count()
        self.stdout.write('Events older than %s (%d days) for %s: %d'
                          % (timezone.localtime(cutoff).strftime('%Y-%m-%d %H:%M'), days, ', '.join(verbs), total))
        if options['dry_run'] or not total:
            return

        deleted = 0
        started = time.time()
        while True:
            ids = list(queryset.values_list('id', flat=True)[:batch_size])
            if not ids:
                break
            count, _ = Action.objects.filter(id__in=ids).delete()
            deleted += count
            if options['verbosity'] > 1:
                self.stdout.write('  %d / %d' % (deleted, total))
        self.stdout.write(self.style.SUCCESS('Deleted %d events in %.1f s' % (deleted, time.time() - started)))
