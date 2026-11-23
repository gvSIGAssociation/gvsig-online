"""
Centro de documentación: manuales en Markdown dentro de cada paquete.

Hay dos fuentes de manuales:

- la documentación central (repositorio gvsig_doc, la misma que se publica en
  docs.gvsig-services.com): ``<DOCS_ROOT>/manuales.yml`` y las páginas en
  ``<DOCS_ROOT>/docs/<idioma>/<path>/``. Cada manual declara la app a la que pertenece y solo
  aparece si esa app está instalada;
- la carpeta ``docs/`` de cada app (el core, un plugin o una app de proyecto) con su manifiesto
  ``docs.yml`` (convención descrita en ``gvsigol_core/docs/docs.yml``, que no trae manuales), para manuales que no se
  publican (p. ej. plugins de proyectos restringidos).

Si un manual (app + slug) está en las dos, manda el central. Este módulo localiza los manuales,
decide quién puede verlos, elige el idioma y convierte las páginas a HTML limpio con los enlaces
ya resueltos.

No depende de la petición salvo para el usuario y el idioma: las vistas están en ``views_docs``.
Markdown y nh3 se importan al convertir una página: si faltan en la imagen, solo falla el lector,
no las vistas del core que importan este módulo.
"""
import hashlib
import logging
import os
import posixpath
import re
import threading
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

import yaml
from django.apps import apps
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger('gvsigol')

DOCS_DIRNAME = 'docs'
MANIFEST_NAME = 'docs.yml'
CENTRAL_MANIFEST_NAME = 'manuales.yml'
DEFAULT_LANG = 'es'
AUDIENCES = ('public', 'user', 'staff', 'superuser')
FILES_SEGMENT = '_files'

_SLUG_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]*$')
_EXTERNAL_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
_H1_RE = re.compile(r'^#\s+(.+?)\s*#*\s*$')
_RAW_IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")')


# --------------------------------------------------------------------------------------------
# Manifiestos
# --------------------------------------------------------------------------------------------

# Clases normales y no dataclasses: el core también se usa con Python 3.6 (Django 2.2)

class Page:
    def __init__(self, file: str, slug: str, audience: str):
        self.file = file            # nombre del fichero dentro de docs/<idioma>/ (p. ej. proyectos.md)
        self.slug = slug            # nombre sin .md: forma parte de la URL
        self.audience = audience

    def __repr__(self):
        return 'Page(%r)' % self.file


class Manual:
    """Un manual. Sus ficheros se nombran siempre con rutas «<idioma>/<resto>» o «assets/<resto>»
    (las mismas en las URLs _files, en las imágenes subidas desde la web y en las exportaciones);
    resolve() las traduce a la carpeta real según de dónde venga el manual:

    - de un paquete: root es <paquete>/docs y la ruta cuelga de ahí;
    - central: root es <DOCS_ROOT>/docs y la ruta es <idioma>/<path>/<resto> (assets/<path>/<resto>).
    """
    def __init__(self, app: str, slug: str, root: str, title: Dict[str, str], description: Dict[str, str],
                 icon: str, audience: str, order: int, pages: Optional[List[Page]] = None,
                 path: str = '', repo_root: str = ''):
        self.app = app              # nombre de la app (gvsigol_core, gvsigol_plugin_viewer3d…)
        self.slug = slug
        self.root = root            # carpeta docs/ (del paquete o de la documentación central)
        self.path = path            # solo en los centrales: carpeta del manual dentro de docs/<idioma>/
        self.repo_root = repo_root  # raíz del repositorio que contiene root (para exportar y avisos)
        self.title = title
        self.description = description
        self.icon = icon
        self.audience = audience
        self.order = order
        self.pages = pages if pages is not None else []

    def __repr__(self):
        return 'Manual(%r, %r%s)' % (self.app, self.slug, ', central' if self.is_central else '')

    @property
    def is_central(self) -> bool:
        return bool(self.path)

    def resolve(self, rel: Optional[str]) -> Optional[str]:
        """Ruta absoluta de «<idioma>/<resto>» (exista o no), o None si sale de la carpeta."""
        rel = safe_relpath(rel or '')
        if not rel:
            return None
        if self.is_central:
            first, _, rest = rel.partition('/')
            if not rest:
                return None
            rel = posixpath.join(first, self.path, rest)
        root = os.path.realpath(self.root)
        full = os.path.realpath(os.path.join(root, rel))
        return full if full.startswith(root + os.sep) else None

    def langs(self) -> List[str]:
        """Idiomas que tienen carpeta para este manual."""
        try:
            names = os.listdir(self.root)
        except OSError:
            return [DEFAULT_LANG]
        result = []
        for name in names:
            folder = os.path.join(self.root, name, self.path) if self.is_central else os.path.join(self.root, name)
            if name != 'assets' and os.path.isdir(folder):
                result.append(name)
        return sorted(result)

    def repo_path(self, rel: str) -> str:
        """Ruta de un fichero del manual dentro de su repositorio (para el ZIP y los avisos)."""
        full = self.resolve(rel) or ''
        return os.path.relpath(full, self.repo_root).replace(os.sep, '/') if full else rel

    @property
    def is_core(self) -> bool:
        return not (self.app.startswith('gvsigol_plugin_') or self.app.startswith('gvsigol_app_'))

    def page(self, slug: str) -> Optional[Page]:
        return next((p for p in self.pages if p.slug == slug), None)


def _texts(value) -> Dict[str, str]:
    """Un texto del manifiesto: una cadena (es) o un diccionario {idioma: texto}."""
    if isinstance(value, dict):
        return {str(k).lower(): str(v) for k, v in value.items() if v}
    if value:
        return {DEFAULT_LANG: str(value)}
    return {}


def _audience(value, default='staff') -> str:
    value = (value or default)
    if value not in AUDIENCES:
        raise ValueError('audience «%s» no válido (%s)' % (value, ', '.join(AUDIENCES)))
    return value


def _stricter(a: str, b: str) -> str:
    return a if AUDIENCES.index(a) >= AUDIENCES.index(b) else b


def _manual_from(item: dict, app: str, root: str, path: str = '', repo_root: str = '') -> Optional[Manual]:
    slug = str(item.get('slug') or '')
    if not _SLUG_RE.match(slug):
        raise ValueError('slug de manual no válido: «%s»' % slug)
    audience = _audience(item.get('audience'))
    manual = Manual(app=app, slug=slug, root=root, title=_texts(item.get('title')) or {DEFAULT_LANG: slug},
                    description=_texts(item.get('description')), icon=str(item.get('icon') or 'fa-book'),
                    audience=audience, order=int(item.get('order') or 100), path=path, repo_root=repo_root)
    for entry in item.get('pages') or []:
        if isinstance(entry, str):
            entry = {'file': entry}
        name = str(entry.get('file') or '')
        page_slug = name[:-3] if name.endswith('.md') else ''
        if not _SLUG_RE.match(page_slug):
            raise ValueError('página no válida en %s: «%s»' % (slug, name))
        manual.pages.append(Page(file=name, slug=page_slug,
                                 audience=_stricter(_audience(entry.get('audience'), audience), audience)))
    return manual if manual.pages else None


def _parse_manifest(app: str, root: str) -> List[Manual]:
    """docs.yml de un paquete."""
    with open(os.path.join(root, MANIFEST_NAME), encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    manuals = []
    for item in data.get('manuals') or []:
        manual = _manual_from(item, app, root, repo_root=os.path.dirname(os.path.dirname(root)))
        if manual:
            manuals.append(manual)
    return manuals


def _parse_central(docs_root: str) -> List[Manual]:
    """manuales.yml de la documentación central. Un manual con errores se omite (con aviso en el
    log) sin afectar a los demás."""
    with open(os.path.join(docs_root, CENTRAL_MANIFEST_NAME), encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    manuals = []
    for item in data.get('manuals') or []:
        if isinstance(item, dict) and not item.get('app'):
            continue    # sin app: solo se publica en el sitio de documentación (p. ej. gvSIG Mapps)
        try:
            app = str(item.get('app') or '')
            path = safe_relpath(str(item.get('path') or ''))
            if not path:
                raise ValueError('falta path')
            manual = _manual_from(item, app, os.path.join(docs_root, DOCS_DIRNAME), path=path,
                                  repo_root=os.path.dirname(os.path.realpath(docs_root)))
            if manual:
                manuals.append(manual)
        except Exception:
            logger.exception('Manual no válido en %s: %r', os.path.join(docs_root, CENTRAL_MANIFEST_NAME),
                             item.get('slug') if isinstance(item, dict) else item)
    return manuals


def central_root() -> Optional[str]:
    """Carpeta de la documentación central (la que contiene manuales.yml), o None.

    Ajuste DOCS_ROOT: una ruta, u «off» para no usarla. Sin ajuste se busca un checkout o paquete
    de gvsig_doc junto al de gvsigol (<carpeta de gvsigol>/../gvsig_doc/gvSIG): así funciona sin
    configurar en desarrollo y en las imágenes que lo incluyan, y en el resto todo sigue igual."""
    configured = str(getattr(settings, 'DOCS_ROOT', '') or '').strip()
    if configured.lower() in ('off', 'none', 'false', '0'):
        return None
    if configured:
        candidate = configured
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidate = os.path.join(base, 'gvsig_doc', 'gvSIG')
    return candidate if os.path.isfile(os.path.join(candidate, CENTRAL_MANIFEST_NAME)) else None


_cache_lock = threading.Lock()
_manifest_cache = {}  # type: Dict[str, Tuple[float, List[Manual]]]


def _cached(manifest: str, parse) -> List[Manual]:
    """Manuales de un manifiesto, releídos solo si cambia el fichero."""
    try:
        mtime = os.path.getmtime(manifest)
    except OSError:
        return []
    with _cache_lock:
        cached = _manifest_cache.get(manifest)
    if not cached or cached[0] != mtime:
        try:
            cached = (mtime, parse())
        except Exception:
            logger.exception('Manifiesto de documentación no válido: %s', manifest)
            cached = (mtime, [])
        with _cache_lock:
            _manifest_cache[manifest] = cached
    return cached[1]


def all_manuals() -> List[Manual]:
    """Manuales de las apps instaladas: los centrales y los de la carpeta docs/ de cada app. Si un
    manual (app + slug) está en los dos sitios, manda el central."""
    manuals = {}
    for config in apps.get_app_configs():
        if not config.name.startswith('gvsigol'):
            continue
        root = os.path.join(config.path, DOCS_DIRNAME)
        manifest = os.path.join(root, MANIFEST_NAME)
        for manual in _cached(manifest, lambda c=config, r=root: _parse_manifest(c.name, r)):
            manuals[(manual.app, manual.slug)] = manual
    docs_root = central_root()
    if docs_root:
        manifest = os.path.join(docs_root, CENTRAL_MANIFEST_NAME)
        for manual in _cached(manifest, lambda: _parse_central(docs_root)):
            if apps.is_installed(manual.app):
                manuals[(manual.app, manual.slug)] = manual
    return sorted(manuals.values(), key=lambda m: (m.order, m.app, m.slug))


def find_manual(app: str, slug: str) -> Optional[Manual]:
    return next((m for m in all_manuals() if m.app == app and m.slug == slug), None)


_reader_available = None


def available() -> bool:
    """¿Están Markdown y nh3? Sin ellos (p. ej. una instalación con Django 2.2 sin esas librerías)
    no se ofrecen los manuales en línea y cada app sigue mostrando su PDF de siempre."""
    global _reader_available
    if _reader_available is None:
        try:
            import markdown  # noqa: F401
            import nh3  # noqa: F401
            _reader_available = True
        except ImportError:
            logger.warning('Centro de documentación: faltan Markdown o nh3; se muestran solo los PDF')
            _reader_available = False
    return _reader_available


def apps_with_manuals() -> set:
    """Apps cuyos manuales en Markdown sustituyen a su PDF (ninguna si el lector no está disponible)."""
    if not available():
        return set()
    return {m.app for m in all_manuals()}


# --------------------------------------------------------------------------------------------
# Permisos e idioma
# --------------------------------------------------------------------------------------------

def can_edit(user) -> bool:
    """Pueden editar los manuales desde la web el personal y los superusuarios."""
    return bool(getattr(user, 'is_authenticated', False) and user.is_active and (user.is_staff or user.is_superuser))


def can_see(user, audience: str) -> bool:
    if audience == 'public':
        return True
    if not getattr(user, 'is_authenticated', False) or not user.is_active:
        return False
    if audience == 'user':
        return True
    if audience == 'staff':
        return user.is_staff or user.is_superuser
    return user.is_superuser


def visible_manuals(user, allowed_apps=None) -> List[Manual]:
    """Manuales que el usuario puede ver. allowed_apps limita las apps de plugins (p. ej. a las
    del proyecto desde el que se abre la ayuda); el core no se limita."""
    if not available():
        return []
    result = []
    for manual in all_manuals():
        if not can_see(user, manual.audience):
            continue
        if allowed_apps is not None and not manual.is_core and manual.app not in allowed_apps:
            continue
        if any(can_see(user, p.audience) for p in manual.pages):
            result.append(manual)
    return result


def visible_pages(user, manual: Manual) -> List[Page]:
    return [p for p in manual.pages if can_see(user, p.audience)]


def lang_codes(lang: str) -> List[str]:
    codes = []
    normalized = (lang or '').strip().lower().replace('_', '-')
    if normalized:
        codes.append(normalized)
        primary = normalized.split('-')[0]
        if primary not in codes:
            codes.append(primary)
    if DEFAULT_LANG not in codes:
        codes.append(DEFAULT_LANG)
    return codes


def text_for(texts: Dict[str, str], lang: str) -> str:
    for code in lang_codes(lang):
        if code in texts:
            return texts[code]
    return next(iter(texts.values()), '')


def page_file(manual: Manual, page: Page, lang: str) -> Tuple[Optional[str], Optional[str]]:
    """(ruta, idioma) de la página en el idioma pedido o, si no existe, en el de por defecto."""
    for code in lang_codes(lang):
        path = manual.resolve('%s/%s' % (code, page.file))
        if path and os.path.isfile(path):
            return path, code
    return None, None


def is_fallback(used_lang: Optional[str], lang: str) -> bool:
    return bool(used_lang) and used_lang not in lang_codes(lang)[:2]


# --------------------------------------------------------------------------------------------
# Fuente de las páginas: la edición web (DocPageEdit) si existe; si no, el fichero del repositorio
# --------------------------------------------------------------------------------------------

def page_edit(manual: Manual, page: Page, lang_code: str):
    from gvsigol_core.models import DocPageEdit
    return DocPageEdit.objects.filter(app=manual.app, manual=manual.slug, page=page.slug, lang=lang_code).first()


def file_sha1(path: Optional[str]) -> str:
    if not path or not os.path.isfile(path):
        return ''
    with open(path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def repo_file(manual: Manual, page: Page, lang_code: str) -> Optional[str]:
    path = manual.resolve('%s/%s' % (lang_code, page.file))
    return path if path and os.path.isfile(path) else None


def page_source(manual: Manual, page: Page, lang: str) -> Tuple[Optional[str], Optional[str], float]:
    """(texto Markdown, idioma, versión) de una página: en cada idioma, primero la edición web."""
    for code in lang_codes(lang):
        edit = page_edit(manual, page, code)
        if edit:
            return edit.content, code, edit.updated_at.timestamp()
        path = repo_file(manual, page, code)
        if path:
            with open(path, encoding='utf-8') as f:
                return f.read(), code, os.path.getmtime(path)
    return None, None, 0.0


_title_cache: Dict[tuple, str] = {}


def page_title(manual: Manual, page: Page, lang: str) -> str:
    """Título de la página: su primer encabezado «# ...» (sin convertir todo el Markdown)."""
    text, used, version = page_source(manual, page, lang)
    if text is None:
        return page.slug
    key = (manual.app, manual.slug, page.slug, used, version)
    title = _title_cache.get(key)
    if title is None:
        title = page.slug
        for line in text.splitlines():
            match = _H1_RE.match(line)
            if match:
                title = match.group(1)
                break
        if len(_title_cache) > 1000:
            _title_cache.clear()
        _title_cache[key] = title
    return title


def asset(app: str, rel: str):
    """Imagen subida desde la web para esa ruta de docs/, si la hay."""
    from gvsigol_core.models import DocAsset
    return DocAsset.objects.filter(app=app, path=rel).first()


def locate_file(app: str, rel: Optional[str]):
    """Fichero de docs/ de una app: ('asset', DocAsset) si se subió desde la web, ('path', ruta)
    si está en el repositorio, o None. Lo que no existe en el idioma de la página se busca en el
    de por defecto. Lo usan el lector (_files) y el PDF."""
    manuals = [m for m in all_manuals() if m.app == app]
    if not manuals or not rel:
        return None
    first, _, rest = rel.partition('/')
    fallback = DEFAULT_LANG + '/' + rest if rest and first not in (DEFAULT_LANG, 'assets') else None
    # Una imagen subida desde la web sustituye a la del repositorio
    uploaded = asset(app, rel) or (asset(app, fallback) if fallback else None)
    if uploaded is not None:
        return 'asset', uploaded
    for candidate in [rel] + ([fallback] if fallback else []):
        for manual in manuals:
            full = manual.resolve(candidate)
            if full and os.path.isfile(full):
                return 'path', full
    return None


# --------------------------------------------------------------------------------------------
# URLs
# --------------------------------------------------------------------------------------------

def page_url(manual: Manual, page: Page) -> str:
    return reverse('documentation_page', kwargs={'app': manual.app, 'manual': manual.slug, 'page': page.slug})


def file_url(app: str, path: str) -> str:
    return reverse('documentation_file', kwargs={'app': app, 'path': path})


def safe_relpath(path: str) -> Optional[str]:
    """Ruta relativa a docs/ normalizada, o None si intenta salir de la carpeta."""
    normalized = posixpath.normpath(path.replace('\\', '/')).lstrip('/')
    if normalized in ('', '.') or normalized.startswith('..') or '/../' in normalized:
        return None
    return normalized


def _locate_page(app: str, current: Manual, page_slug: str) -> Optional[Tuple[Manual, Page]]:
    """Página por su nombre en una app: primero en el manual actual, luego en los demás."""
    candidates = [current] if current and current.app == app else []
    candidates += [m for m in all_manuals() if m.app == app and m is not current]
    for manual in candidates:
        page = manual.page(page_slug)
        if page:
            return manual, page
    return None


# --------------------------------------------------------------------------------------------
# Markdown → HTML
# --------------------------------------------------------------------------------------------

def _link_extension(manual: Manual, lang_dir: str):
    """Extensión de Markdown que resuelve los enlaces (se crea al convertir: import perezoso)."""
    from markdown.extensions import Extension
    from markdown.treeprocessors import Treeprocessor

    class _LinkResolver(Treeprocessor):
        """Convierte los enlaces del Markdown en URLs del centro de documentación."""

        def __init__(self, md, manual: Manual, lang_dir: str):
            super().__init__(md)
            self.manual = manual
            self.lang_dir = lang_dir

        def run(self, root: ElementTree.Element):
            for el in root.iter():
                if el.tag == 'a' and el.get('href'):
                    self._link(el)
                elif el.tag == 'img' and el.get('src'):
                    el.set('src', self._resource(el.get('src')))
                    el.set('loading', 'lazy')

        def _split(self, target: str) -> Tuple[str, str]:
            path, _, fragment = target.partition('#')
            return path, ('#' + fragment if fragment else '')

        def _broken(self, el, target):
            el.set('href', '#')
            el.set('class', ((el.get('class') or '') + ' doc-broken-link').strip())
            el.set('title', target)

        def _link(self, el):
            href = el.get('href')
            if href.startswith('#'):
                return
            if href.startswith('doc:'):
                path, fragment = self._split(href[4:])
                app, _, rel = path.partition('/')
                found = _locate_page(app, self.manual, posixpath.basename(rel)[:-3]) if rel.endswith('.md') else None
                if found:
                    el.set('href', page_url(*found) + fragment)
                else:
                    self._broken(el, href)
                return
            if _EXTERNAL_RE.match(href):
                el.set('target', '_blank')
                return
            path, fragment = self._split(href)
            if path.endswith('.md'):
                found = _locate_page(self.manual.app, self.manual, posixpath.basename(path)[:-3])
                if found:
                    el.set('href', page_url(*found) + fragment)
                else:
                    self._broken(el, href)
                return
            el.set('href', self._resource(href))

        def _resource(self, target: str) -> str:
            if target.startswith('#') or _EXTERNAL_RE.match(target) or target.startswith('/'):
                return target
            path, fragment = self._split(target)
            rel = safe_relpath(posixpath.join(self.lang_dir, path))
            return file_url(self.manual.app, rel) + fragment if rel else '#'


    from markdown.postprocessors import Postprocessor

    class _RawImageResolver(Postprocessor):
        """Las <img> escritas en HTML (p. ej. dentro de celdas de tabla) no pasan por el árbol:
        se resuelve su src en el HTML final con la misma regla."""

        def __init__(self, md, resolver):
            super().__init__(md)
            self.resolver = resolver

        def run(self, text: str) -> str:
            return _RAW_IMG_SRC_RE.sub(lambda m: m.group(1) + self.resolver._resource(m.group(2)) + m.group(3), text)

    class _LinkExtension(Extension):
        def __init__(self, manual: Manual, lang_dir: str):
            super().__init__()
            self.manual = manual
            self.lang_dir = lang_dir

        def extendMarkdown(self, md):
            resolver = _LinkResolver(md, self.manual, self.lang_dir)
            # Después de los enlaces en línea y antes de serializar
            md.treeprocessors.register(resolver, 'gol_doc_links', 4)
            # Después de reinsertar el HTML en bruto (raw_html, prioridad 30)
            md.postprocessors.register(_RawImageResolver(md, resolver), 'gol_doc_raw_images', 5)

    return _LinkExtension(manual, lang_dir)


_EXTRA_TAGS = {'details', 'summary', 'figure', 'figcaption'}
_ALLOWED_ATTRIBUTES = {
    '*': {'id', 'class', 'title', 'lang'},
    'a': {'href', 'target'},
    'img': {'src', 'alt', 'width', 'height', 'loading'},
    'th': {'align', 'colspan', 'rowspan'},
    'td': {'align', 'colspan', 'rowspan'},
    'ol': {'start'},
    'code': {'class'},
}


def sanitize(html: str) -> str:
    import nh3
    return nh3.clean(html, tags=set(nh3.ALLOWED_TAGS) | _EXTRA_TAGS, attributes=_ALLOWED_ATTRIBUTES,
                     url_schemes={'http', 'https', 'mailto'}, link_rel='noopener noreferrer')


class RenderedPage:
    def __init__(self, html: str, toc: list, title: str, lang: str):
        self.html = html
        self.toc = toc              # [{'id', 'name', 'level', 'children': [...]}] de los h2 y h3
        self.title = title
        self.lang = lang


_render_cache: Dict[tuple, RenderedPage] = {}
_RENDER_CACHE_MAX = 200


def convert(manual: Manual, page: Page, text: str, lang_dir: str) -> RenderedPage:
    """Markdown → HTML limpio con los enlaces resueltos (sin caché: también para la vista previa)."""
    import markdown
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.toc import TocExtension

    md = markdown.Markdown(extensions=[
        'abbr', 'attr_list', 'def_list', 'fenced_code', 'footnotes', 'admonition', 'sane_lists',
        TableExtension(use_align_attribute=True),
        TocExtension(permalink='¶', permalink_title=''),
        _link_extension(manual, lang_dir),
    ], output_format='html')
    html = sanitize(md.convert(text))

    tokens = getattr(md, 'toc_tokens', [])
    title = next((t['name'] for t in tokens if t['level'] == 1), page.slug)
    toc = []
    for token in tokens:
        # El h1 es el título de la página: su índice son los h2 (y sus h3)
        toc.extend(token['children'] if token['level'] == 1 else [token])
    return RenderedPage(html=html, toc=toc, title=title, lang=lang_dir)


def render(manual: Manual, page: Page, lang: str) -> Optional[RenderedPage]:
    text, used_lang, version = page_source(manual, page, lang)
    if text is None:
        return None
    key = (manual.app, manual.slug, page.slug, used_lang, version)
    cached = _render_cache.get(key)
    if cached:
        return cached
    rendered = convert(manual, page, text, used_lang)
    if len(_render_cache) >= _RENDER_CACHE_MAX:
        _render_cache.clear()
    _render_cache[key] = rendered
    return rendered


_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')


def referenced_images(text: str, lang_dir: str) -> List[Tuple[str, str]]:
    """Imágenes locales que usa el Markdown: [(ruta relativa a docs/, texto alternativo)]."""
    found, seen = [], set()
    raw = []        # <img> escritas en HTML (dentro de tablas)
    for match in re.finditer(r'<img\b[^>]*>', text or ''):
        src = re.search(r'\bsrc="([^"]+)"', match.group(0))
        alt = re.search(r'\balt="([^"]*)"', match.group(0))
        if src:
            raw.append((alt.group(1) if alt else '', src.group(1)))
    for alt, target in _IMAGE_RE.findall(text or '') + raw:
        target = target.split('#')[0]
        if not target or _EXTERNAL_RE.match(target) or target.startswith('/'):
            continue
        rel = safe_relpath(posixpath.join(lang_dir, target))
        if rel and rel not in seen:
            seen.add(rel)
            found.append((rel, alt))
    return found
