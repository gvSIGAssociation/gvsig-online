"""
PDF de un manual del centro de documentación (WeasyPrint).

Junta en un documento las páginas del manual que ve el usuario, en su idioma y con las ediciones
web aplicadas: portada, índice con números de página, un capítulo por página y los enlaces entre
páginas del manual convertidos en enlaces internos del PDF.

- WeasyPrint no hace peticiones de red: las imágenes se leen del repositorio o de las capturas
  subidas desde la web (docs_center.locate_file) y cualquier otra URL se rechaza.
- El PDF se guarda en MEDIA_ROOT/restricted/docs/_pdf y solo se regenera cuando cambia algo de lo
  que lleva (texto, ediciones web, imágenes, páginas visibles o las plantillas).
- La maquetación está en las plantillas documentation_pdf.html (portada, índice y capítulos) y
  documentation_pdf.css (estilos, cabecera y pie).
- WeasyPrint se importa al generar: sin él (o sin Pango en la imagen), available() es False y el
  lector se queda con «Imprimir».
"""
import glob
import hashlib
import html
import logging
import mimetypes
import os
import re
import threading
from datetime import datetime, timezone as dt_timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.template.loader import get_template, render_to_string
from django.utils import formats, timezone
from django.utils.text import slugify

from gvsigol_core import docs_center as dc

logger = logging.getLogger('gvsigol')

# Plantillas de la maquetación (gvsigol_core/templates; una app de proyecto puede sobrescribirlas)
HTML_TEMPLATE = 'documentation_pdf.html'
CSS_TEMPLATE = 'documentation_pdf.css'

# Los cambios en las plantillas regeneran el PDF solos. Subir solo si cambia cómo se prepara el
# HTML en este módulo (id, enlaces…).
LAYOUT_VERSION = '2'

_available: Optional[bool] = None
_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

_ID_RE = re.compile(r'\sid="([^"]+)"')
_HREF_RE = re.compile(r'\shref="([^"]*)"')
_HEADERLINK_RE = re.compile(r'<a\b[^>]*class="headerlink"[^>]*>.*?</a>', re.S)


def available() -> bool:
    """¿Se puede generar el PDF? (WeasyPrint y Pango instalados)."""
    global _available
    if _available is None:
        try:
            import weasyprint  # noqa: F401  (falla con OSError si falta Pango)
            _available = True
        except Exception:
            logger.info('WeasyPrint no disponible: los manuales no se pueden descargar en PDF')
            _available = False
    return _available


def _pdf_dir() -> str:
    return os.path.join(settings.MEDIA_ROOT, 'restricted', 'docs', '_pdf')


def _lock(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


# --------------------------------------------------------------------------------------------
# Qué lleva el PDF y su huella (para la caché)
# --------------------------------------------------------------------------------------------

def _chapters(manual: dc.Manual, pages: List[dc.Page], lang: str):
    """[(página, RenderedPage, versión)] de las páginas que existen en algún idioma."""
    chapters = []
    for page in pages:
        text, used_lang, version = dc.page_source(manual, page, lang)
        if text is None:
            continue
        rendered = dc.render(manual, page, lang)
        if rendered is None:
            continue
        images = []
        for rel, _alt in dc.referenced_images(text, used_lang):
            located = dc.locate_file(manual.app, rel)
            if located is None:
                images.append((rel, 0))
            elif located[0] == 'asset':
                images.append((rel, located[1].uploaded_at.timestamp()))
            else:
                images.append((rel, os.path.getmtime(located[1])))
        chapters.append((page, rendered, (page.slug, used_lang, version, tuple(images))))
    return chapters


def _fingerprint(manual: dc.Manual, lang: str, base_url: str, labels: Dict[str, str], chapters) -> str:
    data = repr((LAYOUT_VERSION, _templates_version(), manual.app, manual.slug, lang, base_url, sorted(labels.items()),
                 dc.text_for(manual.title, lang), dc.text_for(manual.description, lang),
                 [c[2] for c in chapters]))
    return hashlib.sha1(data.encode('utf-8')).hexdigest()[:16]


# --------------------------------------------------------------------------------------------
# HTML del documento
# --------------------------------------------------------------------------------------------

def _anchor(slug: str, fragment: str = '') -> str:
    return 'p-%s--%s' % (slug, fragment) if fragment else 'p-%s' % slug


def _chapter_html(page: dc.Page, rendered: dc.RenderedPage, page_urls: Dict[str, str], site_root: str) -> str:
    """HTML de una página con los id prefijados (únicos en todo el PDF) y los enlaces resueltos:
    a otra página del manual → enlace interno; a otra dirección del sitio → URL absoluta."""
    body = _HEADERLINK_RE.sub('', rendered.html)
    body = _ID_RE.sub(lambda m: ' id="%s"' % _anchor(page.slug, m.group(1)), body)

    def link(match):
        href = html.unescape(match.group(1))
        if href == '#':
            target = href
        elif href.startswith('#'):
            target = '#' + _anchor(page.slug, href[1:])
        else:
            path, _, fragment = href.partition('#')
            if path in page_urls:
                target = '#' + _anchor(page_urls[path], fragment)
            elif path.startswith('/'):
                target = site_root + href
            else:
                target = href
        return ' href="%s"' % html.escape(target, quote=True)

    return _HREF_RE.sub(link, body)


def _document_html(manual: dc.Manual, lang: str, site_root: str, labels: Dict[str, str], chapters) -> str:
    page_urls = {dc.page_url(manual, page): page.slug for page, _r, _v in chapters}
    return render_to_string(HTML_TEMPLATE, {
        'lang': lang,
        'title': dc.text_for(manual.title, lang),
        'description': dc.text_for(manual.description, lang),
        'site': labels['site'],
        'updated': labels['updated'],
        'contents_label': labels['contents'],
        'chapters': [{
            'anchor': _anchor(page.slug),
            'lang': rendered.lang,
            'title': rendered.title,
            'html': _chapter_html(page, rendered, page_urls, site_root),
            'sections': [{'anchor': _anchor(page.slug, t['id']), 'name': t['name']}
                         for t in rendered.toc if t.get('level') == 2],
        } for page, rendered, _v in chapters],
    })


def _stylesheet(lang: str) -> str:
    return render_to_string(CSS_TEMPLATE, {'lang': lang})


def _templates_version() -> tuple:
    """Ruta y fecha de las plantillas en uso: si se editan (o una app las sobrescribe), cambia la
    huella y el PDF guardado se regenera."""
    version = []
    for name in (HTML_TEMPLATE, CSS_TEMPLATE):
        origin = get_template(name).origin.name
        try:
            version.append((origin, os.path.getmtime(origin)))
        except (OSError, TypeError):
            version.append((str(origin), 0))
    return tuple(version)


# --------------------------------------------------------------------------------------------
# Recursos: solo ficheros de docs/ de la app del manual, nunca la red
# --------------------------------------------------------------------------------------------

def _url_fetcher(manual: dc.Manual):
    prefix = dc.file_url(manual.app, 'x')[:-1]

    def fetch(url, timeout=10, ssl_context=None, http_headers=None):
        path = unquote(urlsplit(url).path)
        if not path.startswith(prefix):
            raise ValueError('recurso no permitido en el PDF: %s' % url)
        located = dc.locate_file(manual.app, dc.safe_relpath(path[len(prefix):]))
        if located is None:
            raise ValueError('recurso no encontrado: %s' % url)
        kind, item = located
        if kind == 'asset':
            with item.file.open('rb') as f:
                data, name = f.read(), item.file.name
        else:
            with open(item, 'rb') as f:
                data, name = f.read(), item
        return {'string': data, 'mime_type': mimetypes.guess_type(name)[0], 'redirected_url': url}

    return fetch


# --------------------------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------------------------

def manual_pdf(manual: dc.Manual, pages: List[dc.Page], lang: str, site_root: str,
               labels: Dict[str, str]) -> Optional[Tuple[str, str]]:
    """(ruta del PDF, nombre para descargarlo) o None si el manual no tiene páginas.

    site_root: raíz absoluta del sitio (https://host), para las imágenes y los enlaces.
    labels: textos ya traducidos: 'contents', 'site' y 'updated' (con {date}).
    """
    site_root = site_root.rstrip('/')
    chapters = _chapters(manual, pages, lang)
    if not chapters:
        return None
    newest = max(max([c[2][2]] + [ts for _rel, ts in c[2][3]]) for c in chapters)
    labels = dict(labels, updated=labels['updated'].format(
        date=formats.date_format(datetime.fromtimestamp(newest), 'DATE_FORMAT')))
    digest = _fingerprint(manual, lang, site_root, labels, chapters)

    # Cada combinación de páginas visibles (según el rol) tiene su propio PDF
    scope = hashlib.sha1(','.join(c[0].slug for c in chapters).encode('utf-8')).hexdigest()[:6]
    prefix = '%s-%s-%s-%s-' % (manual.app, manual.slug, slugify(lang), scope)
    path = os.path.join(_pdf_dir(), prefix + digest + '.pdf')
    # La fecha y hora del último cambio en el nombre: dos descargas de versiones distintas no se
    # confunden en la carpeta de descargas
    stamp = timezone.localtime(datetime.fromtimestamp(newest, tz=dt_timezone.utc)).strftime('%Y%m%d-%H%M')
    filename = '%s-%s.pdf' % (slugify(dc.text_for(manual.title, lang)) or manual.slug, stamp)
    if os.path.isfile(path):
        return path, filename

    with _lock(prefix):
        if os.path.isfile(path):
            return path, filename
        from weasyprint import CSS, HTML
        os.makedirs(_pdf_dir(), exist_ok=True)
        document = _document_html(manual, lang, site_root, labels, chapters)
        tmp = path + '.tmp'
        HTML(string=document, base_url=site_root + '/', url_fetcher=_url_fetcher(manual)).write_pdf(
            tmp, stylesheets=[CSS(string=_stylesheet(lang))])
        os.replace(tmp, path)
        # Versiones anteriores de ese manual e idioma
        for old in glob.glob(os.path.join(_pdf_dir(), glob.escape(prefix) + '*.pdf')):
            if old != path:
                try:
                    os.remove(old)
                except OSError:
                    pass
    return path, filename
