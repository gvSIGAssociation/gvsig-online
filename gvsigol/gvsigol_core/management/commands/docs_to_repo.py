"""
Pasa al repositorio lo editado desde la web en el centro de documentación (solo en desarrollo,
donde el código del repositorio está montado en el contenedor).

Escribe las páginas editadas y las imágenes subidas en la carpeta docs/ de su paquete y después
borra esas ediciones de la base de datos (el historial de revisiones se conserva), de modo que la
página vuelve a salir del fichero. No ejecuta svn: al terminar indica qué ficheros son nuevos.

Uso (en el contenedor, como root para poder dejar los ficheros a nombre del dueño del repositorio):

    python manage.py docs_to_repo                 # todas las apps con cambios web
    python manage.py docs_to_repo --app gvsigol_core
    python manage.py docs_to_repo --dry-run       # solo muestra lo que haría
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gvsigol_core import docs_center as dc
from gvsigol_core import docs_sync


class Command(BaseCommand):
    help = 'Escribe en la carpeta docs/ de cada paquete las páginas editadas y las imágenes subidas desde la web'

    def add_arguments(self, parser):
        parser.add_argument('--app', help='Solo esta app (p. ej. gvsigol_core)')
        parser.add_argument('--dry-run', action='store_true', help='Mostrar lo que se haría sin escribir nada')
        parser.add_argument('--force', action='store_true',
                            help='Sobrescribir también las páginas cuyo fichero cambió en el repositorio '
                                 'después de editarlas en la web')
        parser.add_argument('--keep', action='store_true',
                            help='No borrar las ediciones de la base de datos después de escribirlas')

    def handle(self, *args, **options):
        from gvsigol_core.models import DocAsset, DocPageEdit

        apps = sorted(set(DocPageEdit.objects.values_list('app', flat=True))
                      | set(DocAsset.objects.values_list('app', flat=True)))
        if options['app']:
            if options['app'] not in dc.apps_with_manuals():
                raise CommandError('La app %s no tiene manuales (docs/docs.yml)' % options['app'])
            apps = [a for a in apps if a == options['app']]
        if not apps:
            self.stdout.write('No hay cambios web pendientes.')
            return

        for app in apps:
            changes = docs_sync.collect(app)
            if changes is None:
                self.stdout.write(self.style.WARNING('%s: la app ya no está instalada o no tiene docs.yml; se omite' % app))
                continue
            self._apply(changes, options)

    def _apply(self, changes, options):
        root = os.path.realpath(changes.root)
        if not options['dry_run'] and not os.access(root, os.W_OK):
            raise CommandError('No se puede escribir en %s. Ejecute el comando como root '
                               '(docker exec -u root ...).' % root)
        owner = os.stat(root)
        self.stdout.write(self.style.MIGRATE_HEADING('%s → %s' % (changes.app, root)))

        written, new_files, skipped = [], [], []
        for change in changes.pages + changes.images:
            if change.base_changed and not options['force']:
                skipped.append(change)
                continue
            target = os.path.realpath(os.path.join(root, change.rel))
            if not target.startswith(root + os.sep):
                skipped.append(change)
                continue
            data = change.read()
            exists = os.path.isfile(target)
            if exists:
                with open(target, 'rb') as f:
                    if f.read() == data:
                        written.append((change, 'sin cambios'))
                        continue
            written.append((change, 'modificado' if exists else 'nuevo'))
            if not exists:
                new_files.append(target)
            if options['dry_run']:
                continue
            self._write(target, data, root, owner)

        for change, state in written:
            self.stdout.write('  %-11s %s' % (state, change.rel))
        for change in skipped:
            self.stdout.write(self.style.WARNING(
                '  OMITIDO    %s: el fichero del repositorio cambió después de editarlo en la web. '
                'Revíselo en el editor o use --force.' % change.rel))
        for change in changes.unused_images:
            self.stdout.write(self.style.WARNING(
                '  sin usar   %s: subida desde la web, pero ninguna página la usa; se deja en la base de datos'
                % change.rel))

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE('  (simulación: no se ha escrito nada)'))
            return

        if not options['keep']:
            # Lo escrito ya está en el repositorio: la página vuelve a salir del fichero
            with transaction.atomic():
                for change, _state in written:
                    if change.kind == 'image':
                        storage, name = change.obj.file.storage, change.obj.file.name
                        change.obj.delete()
                        transaction.on_commit(lambda s=storage, n=name: s.delete(n))
                    else:
                        change.obj.delete()
            dc._render_cache.clear()

        if new_files:
            package_parent = os.path.dirname(os.path.dirname(root))
            rels = ' '.join(os.path.relpath(p, package_parent) for p in new_files)
            self.stdout.write('  Ficheros nuevos; desde %s:\n    svn add --parents %s' % (package_parent, rels))
        self.stdout.write(self.style.SUCCESS('  %d escritos, %d omitidos.' % (
            sum(1 for _c, s in written if s != 'sin cambios'), len(skipped))))

    def _write(self, target, data, root, owner):
        """Escribe el fichero y deja a nombre del dueño de docs/ lo que se cree (si se es root)."""
        created_dirs = []
        parent = os.path.dirname(target)
        while not os.path.isdir(parent):
            created_dirs.append(parent)
            parent = os.path.dirname(parent)
        for directory in reversed(created_dirs):
            os.mkdir(directory, 0o755)
        tmp = target + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
        if os.geteuid() == 0:
            for path in created_dirs + [target]:
                os.chown(path, owner.st_uid, owner.st_gid)
