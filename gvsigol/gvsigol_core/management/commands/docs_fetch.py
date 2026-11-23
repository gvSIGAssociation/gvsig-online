"""
Instala o actualiza la documentación central (los manuales de gvsig_doc) en un despliegue.

Descarga el paquete que publica el sitio de documentación (o usa un fichero ya descargado, para
instalaciones sin salida a Internet) y lo deja en la carpeta que lee el centro de documentación:
DOCS_ROOT o, si no está configurado, <carpeta de gvsigol>/../gvsig_doc/gvSIG. La sustitución es
atómica: si algo falla, se conserva la documentación que hubiera.

Uso:
    python manage.py docs_fetch                       # descarga DOCS_BUNDLE_URL
    python manage.py docs_fetch --file manuales.tar.gz
    python manage.py docs_fetch --url https://.../paquete/manuales.tar.gz

Las imágenes Docker ya llevan el paquete (docker/gvsigol-back/build.sh): este comando es para
las instalaciones sin Docker o para actualizar la documentación sin reconstruir la imagen.
"""
import os
import shutil
import tarfile
import tempfile
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from gvsigol_core import docs_center as dc

DEFAULT_URL = 'https://docs.gvsig-services.com/paquete/manuales.tar.gz'
MAX_BYTES = 1024 ** 3          # 1 GB: el paquete pesa unos pocos MB
TOP = 'gvSIG'


def default_destination():
    configured = str(getattr(settings, 'DOCS_ROOT', '') or '').strip()
    if configured.lower() in ('off', 'none', 'false', '0'):
        raise CommandError('DOCS_ROOT=%s: la documentación central está desactivada en esta instalación.' % configured)
    if configured:
        return configured
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(dc.__file__))))
    return os.path.join(base, 'gvsig_doc', TOP)


class Command(BaseCommand):
    help = 'Instala o actualiza la documentación central (paquete de manuales de gvsig_doc)'

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group()
        source.add_argument('--url', help='URL del paquete (por defecto DOCS_BUNDLE_URL o %s)' % DEFAULT_URL)
        source.add_argument('--file', help='Paquete .tar.gz ya descargado')
        parser.add_argument('--dest', help='Carpeta de destino (por defecto DOCS_ROOT o ../gvsig_doc/gvSIG)')

    def handle(self, *args, **options):
        dest = os.path.abspath(options['dest'] or default_destination())
        if os.path.basename(dest) != TOP:
            raise CommandError('El destino debe ser una carpeta llamada %s (es la que contiene manuales.yml): %s'
                               % (TOP, dest))
        if os.path.exists(os.path.join(os.path.dirname(dest), '.git')):
            raise CommandError('%s es un checkout de gvsig_doc: actualícelo con git, no con este comando.' % dest)

        parent = os.path.dirname(dest)
        os.makedirs(parent, exist_ok=True)
        work = tempfile.mkdtemp(prefix='.docs_fetch-', dir=parent)
        try:
            archive = options['file'] or self._download(options['url'] or getattr(settings, 'DOCS_BUNDLE_URL', '')
                                                        or DEFAULT_URL, work)
            staged = self._extract(archive, work)
            self._swap(staged, dest)
        finally:
            shutil.rmtree(work, ignore_errors=True)

        version = os.path.join(dest, 'VERSION')
        detail = open(version, encoding='utf-8').read().strip().replace('\n', ', ') if os.path.isfile(version) else ''
        manuals = [m for m in dc.all_manuals() if m.is_central]
        self.stdout.write(self.style.SUCCESS('Documentación instalada en %s (%s). Manuales centrales visibles: %s'
                                             % (dest, detail, ', '.join('%s/%s' % (m.app, m.slug) for m in manuals)
                                                or 'ninguno (¿DOCS_ROOT apunta a otra carpeta?)')))

    def _download(self, url, work):
        if not url.startswith(('https://', 'http://')):
            raise CommandError('URL no válida: %s' % url)
        target = os.path.join(work, 'manuales.tar.gz')
        self.stdout.write('Descargando %s …' % url)
        try:
            with urllib.request.urlopen(url, timeout=60) as response, open(target, 'wb') as out:
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise CommandError('El paquete supera %d MB' % (MAX_BYTES // 1024 ** 2))
                    out.write(chunk)
        except CommandError:
            raise
        except Exception as e:
            raise CommandError('No se ha podido descargar el paquete: %s' % e)
        return target

    def _extract(self, archive, work):
        """Descomprime en una carpeta temporal admitiendo solo ficheros y carpetas bajo gvSIG/."""
        staged = os.path.join(work, 'nuevo')
        os.makedirs(staged)
        try:
            with tarfile.open(archive, 'r:gz') as tar:
                members = tar.getmembers()
                for member in members:
                    name = member.name
                    parts = name.split('/')
                    if not (member.isfile() or member.isdir()) or name.startswith('/') or '..' in parts \
                            or parts[0] != TOP:
                        raise CommandError('Paquete no válido: entrada no permitida «%s»' % name)
                for member in members:
                    target = os.path.join(staged, *member.name.split('/'))
                    if member.isdir():
                        os.makedirs(target, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with tar.extractfile(member) as src, open(target, 'wb') as out:
                        shutil.copyfileobj(src, out)
                    os.chmod(target, 0o644)
        except (tarfile.TarError, OSError) as e:
            raise CommandError('No se ha podido leer el paquete: %s' % e)
        root = os.path.join(staged, TOP)
        if not os.path.isfile(os.path.join(root, dc.CENTRAL_MANIFEST_NAME)):
            raise CommandError('El paquete no contiene %s/%s' % (TOP, dc.CENTRAL_MANIFEST_NAME))
        for folder, dirs, _files in os.walk(root):
            for d in dirs:
                os.chmod(os.path.join(folder, d), 0o755)
        os.chmod(root, 0o755)
        return root

    def _swap(self, staged, dest):
        """Sustituye la carpeta de destino por la nueva con dos renombrados (la carpeta falta solo un instante)."""
        old = None
        if os.path.exists(dest):
            old = dest + '.anterior'
            shutil.rmtree(old, ignore_errors=True)
            os.rename(dest, old)
        os.rename(staged, dest)
        if old:
            shutil.rmtree(old, ignore_errors=True)
