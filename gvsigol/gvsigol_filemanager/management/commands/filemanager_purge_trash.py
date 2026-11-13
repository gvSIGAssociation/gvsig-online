from django.core.management.base import BaseCommand

from gvsigol_filemanager import fsops, uploads


class Command(BaseCommand):
    help = ('Limpieza del gestor de ficheros: borra de la papelera lo que lleva más días de los '
            'indicados en FILEMANAGER_TRASH_RETENTION_DAYS (30 por defecto) y las subidas por trozos '
            'abandonadas (sin actividad en 24 horas). Pensado para ejecutarlo a diario.')

    def handle(self, *args, **options):
        purged = fsops.purge_expired()
        stale = uploads.purge_stale()
        self.stdout.write('Elementos purgados de la papelera: %d' % purged)
        self.stdout.write('Subidas abandonadas borradas: %d' % stale)
