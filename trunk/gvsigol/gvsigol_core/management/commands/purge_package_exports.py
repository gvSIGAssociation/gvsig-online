# -*- coding: utf-8 -*-
"""
Management command: purge old project-package export ZIPs and activity log rows.

Usage:
    python manage.py purge_package_exports
    python manage.py purge_package_exports --keep 20   # default
    python manage.py purge_package_exports --dry-run
"""
import os

from django.core.management.base import BaseCommand

from gvsigol_core.models import ProjectPackageActivityLog, ProjectPackageExportJob
from gvsigol_core.project_package.activity_log import RECENT_ACTIVITY_LIMIT


class Command(BaseCommand):
    help = 'Delete old package export ZIPs and activity log rows beyond the keep limit.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep', type=int, default=RECENT_ACTIVITY_LIMIT,
            help='Number of most-recent activity log rows to keep (default: %d).' % RECENT_ACTIVITY_LIMIT,
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be deleted without actually deleting.',
        )

    def handle(self, *args, **options):
        keep = options['keep']
        dry = options['dry_run']
        prefix = '[DRY-RUN] ' if dry else ''

        # ── 1. Purge old activity log rows ────────────────────────────────
        all_ids = list(
            ProjectPackageActivityLog.objects
            .order_by('-created_at')
            .values_list('id', flat=True)
        )
        keep_ids = set(all_ids[:keep])
        old_entries = ProjectPackageActivityLog.objects.exclude(pk__in=keep_ids)
        old_count = old_entries.count()

        export_job_ids = []
        for entry in old_entries.filter(operation=ProjectPackageActivityLog.OP_EXPORT):
            ej_id = (entry.summary_json or {}).get('export_job_id')
            if ej_id:
                export_job_ids.append(ej_id)

        if old_count:
            self.stdout.write('%sDeleting %d old activity log row(s).' % (prefix, old_count))
            if not dry:
                old_entries.delete()
        else:
            self.stdout.write('Activity log is within the limit (%d rows, keep=%d).' % (len(all_ids), keep))

        # ── 2. Delete ZIPs and export job rows for purged entries ─────────
        for ej_id in export_job_ids:
            try:
                ej = ProjectPackageExportJob.objects.get(pk=ej_id)
                if ej.zip_path and os.path.isfile(ej.zip_path):
                    self.stdout.write('%sDelete ZIP: %s' % (prefix, ej.zip_path))
                    if not dry:
                        os.remove(ej.zip_path)
                if not dry:
                    ej.delete()
                else:
                    self.stdout.write('[DRY-RUN] Would delete ExportJob %s' % ej_id)
            except ProjectPackageExportJob.DoesNotExist:
                pass

        # ── 3. Orphaned export ZIPs (job rows not in any activity log) ────
        referenced_job_ids = set(
            str(v)
            for v in ProjectPackageActivityLog.objects
            .filter(operation=ProjectPackageActivityLog.OP_EXPORT)
            .values_list('summary_json__export_job_id', flat=True)
            if v
        )
        orphan_jobs = ProjectPackageExportJob.objects.exclude(pk__in=referenced_job_ids)
        for ej in orphan_jobs:
            if ej.zip_path and os.path.isfile(ej.zip_path):
                self.stdout.write('%sDelete orphan ZIP: %s' % (prefix, ej.zip_path))
                if not dry:
                    os.remove(ej.zip_path)
            if not dry:
                ej.delete()
            else:
                self.stdout.write('[DRY-RUN] Would delete orphan ExportJob %s' % ej.pk)

        self.stdout.write(self.style.SUCCESS('%sDone.' % prefix))
