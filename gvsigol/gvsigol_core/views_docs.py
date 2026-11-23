"""Vistas del lector de documentación en Markdown (ver docs_center)."""
import io
from functools import wraps
import logging
import mimetypes
import os
import re
import zipfile

from django.contrib.auth.views import redirect_to_login
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import pgettext
from django.views.decorators.http import require_POST, require_safe

from django.conf import settings

from gvsigol_core import docs_center as dc
from gvsigol_core import docs_pdf
from gvsigol_core import docs_sync
from gvsigol_core.models import DocAsset, DocPageEdit, DocPageRevision

logger = logging.getLogger('gvsigol')

# Imágenes que se pueden subir desde el editor (sin SVG: podría llevar código)
_UPLOAD_TYPES = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
_UPLOAD_MAX_BYTES = 10 * 1024 * 1024

# Ficheros que se pueden servir desde docs/: imágenes y recursos descargables
_INLINE_TYPES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
_DOWNLOAD_TYPES = {'.sld', '.xml', '.json', '.geojson', '.csv', '.txt', '.pdf', '.zip', '.qml', '.qgs'}


def _requires_reader(view):
    """Sin Markdown o nh3 no hay lector: las direcciones de los manuales llevan a la página de
    documentación, que muestra los PDF."""
    @wraps(view)
    def wrap(request, *args, **kwargs):
        if not dc.available():
            return redirect('documentation')
        return view(request, *args, **kwargs)
    return wrap


def _deny(request):
    """Sin sesión se pide iniciarla; con sesión, el manual no existe para este usuario."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    raise Http404()


def _lang(request):
    return getattr(request, 'LANGUAGE_CODE', None) or dc.DEFAULT_LANG


def _navigation(request, current_manual, current_page):
    """Índice lateral: los manuales visibles con sus páginas."""
    lang = _lang(request)
    nav = []
    for manual in dc.visible_manuals(request.user):
        pages = [{
            'title': dc.page_title(manual, page, lang),
            'url': dc.page_url(manual, page),
            'current': manual is current_manual and page is current_page,
        } for page in dc.visible_pages(request.user, manual)]
        nav.append({
            'title': dc.text_for(manual.title, lang),
            'icon': manual.icon,
            'current': manual is current_manual,
            'url': pages[0]['url'] if pages else '#',
            'pages': pages,
        })
    return nav


@_requires_reader
@require_safe
def documentation_manual(request, app, manual):
    """La dirección de un manual lleva a su primera página visible."""
    found = dc.find_manual(app, manual)
    if not found or not dc.can_see(request.user, found.audience):
        return _deny(request)
    pages = dc.visible_pages(request.user, found)
    if not pages:
        return _deny(request)
    return redirect(dc.page_url(found, pages[0]))


@_requires_reader
@require_safe
def documentation_page(request, app, manual, page):
    found = dc.find_manual(app, manual)
    current = found.page(page) if found else None
    if not found or not current or not dc.can_see(request.user, found.audience) \
            or not dc.can_see(request.user, current.audience):
        return _deny(request)

    lang = _lang(request)
    rendered = dc.render(found, current, lang)
    if rendered is None:
        raise Http404()

    pages = dc.visible_pages(request.user, found)
    index = pages.index(current)
    neighbour = lambda p: {'title': dc.page_title(found, p, lang), 'url': dc.page_url(found, p)} if p else None

    can_edit = dc.can_edit(request.user)
    edit = dc.page_edit(found, current, rendered.lang) if can_edit else None
    # Cambios web del paquete pendientes de llevar al repositorio (para «Exportar cambios web»)
    web_changes = (DocPageEdit.objects.filter(app=found.app).count()
                   + DocAsset.objects.filter(app=found.app).count()) if can_edit else 0
    return render(request, 'documentation_page.html', {
        'can_edit': can_edit,
        'edit_url': dc.page_url(found, current) + 'edit/' if can_edit else None,
        'web_edit': edit,
        'web_changes': web_changes,
        'export_all_url': reverse('documentation_export_all', kwargs={'app': found.app, 'manual': found.slug})
                          if web_changes else None,
        'base_changed': bool(edit and edit.base_hash != dc.file_sha1(dc.repo_file(found, current, edit.lang))),
        'manual_title': dc.text_for(found.title, lang),
        'manual_url': dc.page_url(found, pages[0]),
        'pdf_url': reverse('documentation_pdf', kwargs={'app': found.app, 'manual': found.slug})
                   if docs_pdf.available() else None,
        'page': rendered,
        'fallback_lang': rendered.lang if dc.is_fallback(rendered.lang, lang) else None,
        'nav': _navigation(request, found, current),
        'previous': neighbour(pages[index - 1] if index > 0 else None),
        'next': neighbour(pages[index + 1] if index + 1 < len(pages) else None),
    })


@_requires_reader
@require_safe
def documentation_pdf(request, app, manual):
    """El manual entero en PDF, con las páginas que ve el usuario y en su idioma."""
    found = dc.find_manual(app, manual)
    if not found or not dc.can_see(request.user, found.audience):
        return _deny(request)
    pages = dc.visible_pages(request.user, found)
    if not pages:
        return _deny(request)
    if not docs_pdf.available():
        raise Http404()
    labels = {
        'contents': pgettext('documentation', 'Contents'),
        'site': getattr(settings, 'GVSIGOL_NAME', '') or 'gvSIG Online',
        # {date} lo rellena docs_pdf con la fecha del último cambio del manual
        'updated': pgettext('documentation', 'Updated on {date}'),
    }
    try:
        result = docs_pdf.manual_pdf(found, pages, _lang(request), request.build_absolute_uri('/'), labels)
    except Exception:
        logger.exception('Error al generar el PDF del manual %s/%s', app, manual)
        return HttpResponse(pgettext('documentation', 'The PDF could not be generated. Use Print instead.'),
                            status=500, content_type='text/plain; charset=utf-8')
    if result is None:
        raise Http404()
    path, filename = result
    response = FileResponse(open(path, 'rb'), content_type='application/pdf', as_attachment=True, filename=filename)
    response['X-Content-Type-Options'] = 'nosniff'
    # Sin copia en el navegador: cada descarga pide la versión actual del manual
    response['Cache-Control'] = 'no-store'
    return response


@_requires_reader
@require_safe
def documentation_export_all(request, app, manual):
    """ZIP con todas las páginas editadas y las imágenes subidas desde la web del paquete, con
    sus rutas en el repositorio. En desarrollo se puede usar el comando docs_to_repo."""
    found = dc.find_manual(app, manual)
    if not found or not dc.can_see(request.user, found.audience):
        return _deny(request)
    if not dc.can_edit(request.user):
        return HttpResponseForbidden()
    changes = docs_sync.collect(found.app, request.user)
    if changes is None or not changes.count:
        return redirect(dc.page_url(found, dc.visible_pages(request.user, found)[0]))
    stamp = timezone.localtime().strftime('%Y%m%d-%H%M')
    response = HttpResponse(docs_sync.zip_bytes(changes), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s-docs-web-%s.zip"' % (found.app, stamp)
    response['Cache-Control'] = 'no-store'
    return response


@require_safe
def documentation_file(request, app, path):
    """Imágenes y recursos de la carpeta docs/ de una app."""
    manuals = [m for m in dc.all_manuals() if m.app == app]
    if not manuals:
        raise Http404()
    if not any(dc.can_see(request.user, m.audience) for m in manuals):
        return _deny(request)

    rel = dc.safe_relpath(path)
    ext = os.path.splitext(rel or '')[1].lower()
    if not rel or ext not in _INLINE_TYPES | _DOWNLOAD_TYPES:
        raise Http404()

    located = dc.locate_file(app, rel)
    if located is None:
        raise Http404()
    kind, item = located
    if kind == 'asset':
        return _file_response(item.file.open('rb'), item.file.name, ext in _DOWNLOAD_TYPES, private_cache=True)
    return _file_response(open(item, 'rb'), item, ext in _DOWNLOAD_TYPES)


def _file_response(handle, name, as_attachment, private_cache=False):
    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    response = FileResponse(handle, content_type=content_type, as_attachment=as_attachment,
                            filename=os.path.basename(name))
    response['X-Content-Type-Options'] = 'nosniff'
    # Un SVG no puede ejecutar código aunque se abra directamente
    response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    # Las imágenes subidas se pueden reemplazar con el mismo nombre: sin caché larga
    response['Cache-Control'] = 'private, no-cache' if private_cache else 'private, max-age=300'
    return response


# --------------------------------------------------------------------------------------------
# Edición desde la web (personal y superusuarios)
# --------------------------------------------------------------------------------------------

def _editable(request, app, manual, page):
    """(manual, página, idioma que se edita) o None si no existe o no se puede editar."""
    if not dc.can_edit(request.user):
        return None
    found = dc.find_manual(app, manual)
    current = found.page(page) if found else None
    if not current or not dc.can_see(request.user, current.audience):
        return None
    _text, used_lang, _v = dc.page_source(found, current, _lang(request))
    if used_lang is None:
        return None
    return found, current, used_lang


def _repo_text(manual, page, lang_code):
    path = dc.repo_file(manual, page, lang_code)
    if not path:
        return None
    with open(path, encoding='utf-8') as f:
        return f.read()


def _edit_version(edit):
    return '%.6f' % edit.updated_at.timestamp() if edit else ''


def _images(manual, text, lang_code):
    """Imágenes que usa la página, con su origen (subida, repositorio o ninguna)."""
    images = []
    for rel, alt in dc.referenced_images(text, lang_code):
        uploaded = dc.asset(manual.app, rel)
        in_repo = bool(manual.resolve(rel)) and os.path.isfile(manual.resolve(rel))
        images.append({
            'path': rel,
            'name': rel.rsplit('/', 1)[-1],
            'alt': alt,
            'url': dc.file_url(manual.app, rel),
            'source': 'web' if uploaded else ('repo' if in_repo else 'missing'),
            'uploaded_by': uploaded.uploaded_by if uploaded else '',
            'uploaded_at': uploaded.uploaded_at if uploaded else None,
        })
    return images


@_requires_reader
def documentation_edit(request, app, manual, page):
    target = _editable(request, app, manual, page)
    if target is None:
        return _deny(request) if not request.user.is_authenticated else HttpResponseForbidden()
    found, current, lang_code = target
    edit = dc.page_edit(found, current, lang_code)
    repo_text = _repo_text(found, current, lang_code)
    error = None

    if request.method == 'POST':
        content = request.POST.get('content', '').replace('\r\n', '\n')
        comment = request.POST.get('comment', '').strip()[:250]
        if request.POST.get('edit_version', '') != _edit_version(edit):
            error = pgettext('documentation', 'Someone else saved this page while you were editing it. '
                                              'Copy your changes, reload and apply them again.')
        elif not content.strip():
            error = pgettext('documentation', 'The page cannot be empty.')
        else:
            with transaction.atomic():
                if repo_text is not None and content == repo_text:
                    # Igual que la del repositorio: no hace falta la edición
                    DocPageEdit.objects.filter(pk=edit.pk if edit else None).delete()
                else:
                    edit = edit or DocPageEdit(app=found.app, manual=found.slug, page=current.slug, lang=lang_code)
                    edit.content = content
                    edit.base_hash = request.POST.get('base_hash', '')[:40]
                    edit.updated_by = request.user.username
                    edit.save()
                DocPageRevision.objects.create(app=found.app, manual=found.slug, page=current.slug, lang=lang_code,
                                               content=content, comment=comment, created_by=request.user.username)
            return redirect(dc.page_url(found, current))
    else:
        content = edit.content if edit else (repo_text or '')

    revisions = DocPageRevision.objects.filter(app=found.app, manual=found.slug, page=current.slug,
                                               lang=lang_code)[:20]
    page_url = dc.page_url(found, current)
    return render(request, 'documentation_edit.html', {
        'manual_title': dc.text_for(found.title, _lang(request)),
        'page_title': dc.page_title(found, current, _lang(request)),
        'page_url': page_url,
        'lang_code': lang_code,
        'file_label': '%s/docs/%s/%s' % (found.app, lang_code, current.file),
        'content': content,
        'error': error,
        'edit': edit,
        'edit_version': _edit_version(edit),
        # La edición se hace sobre esta versión del fichero del repositorio
        'base_hash': edit.base_hash if edit else dc.file_sha1(dc.repo_file(found, current, lang_code)),
        'base_changed': bool(edit and edit.base_hash != dc.file_sha1(dc.repo_file(found, current, lang_code))),
        'has_repo_file': repo_text is not None,
        'images': _images(found, content, lang_code),
        'revisions': revisions,
        'revisions_json': [{'id': r.id, 'content': r.content} for r in revisions],
        'preview_url': page_url + 'preview/',
        'upload_url': page_url + 'upload/',
        'restore_url': page_url + 'restore/',
        'export_url': page_url + 'export/',
    })


@_requires_reader
@require_POST
def documentation_preview(request, app, manual, page):
    target = _editable(request, app, manual, page)
    if target is None:
        return HttpResponseForbidden()
    found, current, lang_code = target
    content = request.POST.get('content', '')
    rendered = dc.convert(found, current, content, lang_code)
    return JsonResponse({'html': rendered.html, 'images': [
        {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in img.items()}
        for img in _images(found, content, lang_code)]})


_NAME_RE = re.compile(r'[^a-z0-9._-]+')


def _clean_name(name, ext):
    base = _NAME_RE.sub('-', os.path.splitext(os.path.basename(name or ''))[0].lower()).strip('-.') or 'imagen'
    return base[:80] + ext


@_requires_reader
@require_POST
def documentation_upload(request, app, manual, page):
    """Sube una imagen. Con «path» (ruta relativa a docs/) la sustituye; si no, la guarda en
    <idioma>/img/ con el nombre del fichero. Devuelve la ruta y el Markdown para insertarla."""
    target = _editable(request, app, manual, page)
    if target is None:
        return HttpResponseForbidden()
    found, current, lang_code = target
    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'error': pgettext('documentation', 'No file was received.')}, status=400)
    ext = os.path.splitext(upload.name)[1].lower()
    if ext == '.jpeg':
        ext = '.jpg'
    if ext not in _UPLOAD_TYPES:
        return JsonResponse({'error': pgettext('documentation', 'Only PNG, JPG, GIF or WEBP images can be uploaded.')}, status=400)
    if upload.size > _UPLOAD_MAX_BYTES:
        return JsonResponse({'error': pgettext('documentation', 'The image is larger than 10 MB.')}, status=400)
    data = upload.read()
    try:
        from PIL import Image
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        return JsonResponse({'error': pgettext('documentation', 'The file is not a valid image.')}, status=400)

    wanted = request.POST.get('path', '').strip()
    if wanted:
        rel = dc.safe_relpath(wanted)
        # Solo se sustituyen imágenes de la carpeta del idioma o de assets/
        if not rel or not (rel.startswith(lang_code + '/') or rel.startswith('assets/')) \
                or os.path.splitext(rel)[1].lower() not in _UPLOAD_TYPES | {'.jpeg'}:
            return JsonResponse({'error': pgettext('documentation', 'Invalid image path.')}, status=400)
    else:
        name = _clean_name(request.POST.get('name') or upload.name, ext)
        rel = '%s/img/%s' % (lang_code, name)
        # Una imagen nueva no pisa otra con el mismo nombre
        stem, n = rel[:-len(ext)], 2
        while dc.asset(found.app, rel) or os.path.exists(found.resolve(rel) or ''):
            rel = '%s-%d%s' % (stem, n, ext)
            n += 1

    with transaction.atomic():
        item = DocAsset.objects.select_for_update().filter(app=found.app, path=rel).first() \
            or DocAsset(app=found.app, path=rel)
        if item.pk and item.file:
            item.file.delete(save=False)
        item.uploaded_by = request.user.username
        item.file.save(rel.replace('/', '_'), ContentFile(data), save=False)
        item.save()

    rel_to_page = rel[len(lang_code) + 1:] if rel.startswith(lang_code + '/') else '../' + rel
    return JsonResponse({
        'path': rel,
        'url': dc.file_url(found.app, rel) + '?v=%d' % int(timezone.now().timestamp()),
        'markdown': '![%s](%s)' % (os.path.splitext(rel.rsplit('/', 1)[-1])[0], rel_to_page),
    })


@_requires_reader
@require_POST
def documentation_restore(request, app, manual, page):
    """Descarta la edición web: la página vuelve a la versión del repositorio (el historial se
    conserva y las imágenes subidas también)."""
    target = _editable(request, app, manual, page)
    if target is None:
        return HttpResponseForbidden()
    found, current, lang_code = target
    DocPageEdit.objects.filter(app=found.app, manual=found.slug, page=current.slug, lang=lang_code).delete()
    return redirect(dc.page_url(found, current))


@_requires_reader
@require_safe
def documentation_export(request, app, manual, page):
    """ZIP con la página tal como se ve (edición web o repositorio) y las imágenes subidas de la
    app, con sus rutas en el repositorio del manual: se descomprime en la raíz de ese repositorio
    (gvsigol/, plugin_x/ o gvsig_doc/)."""
    target = _editable(request, app, manual, page)
    if target is None:
        return HttpResponseForbidden()
    found, current, lang_code = target
    text, used_lang, _v = dc.page_source(found, current, lang_code)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Rutas dentro del repositorio del manual: <paquete>/docs/... o gvSIG/docs/<idioma>/<path>/...
        zf.writestr(found.repo_path('%s/%s' % (used_lang, current.file)), text or '')
        for item in DocAsset.objects.filter(app=found.app):
            with item.file.open('rb') as f:
                zf.writestr(found.repo_path(item.path), f.read())
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s-%s-%s.zip"' % (found.app, current.slug, used_lang)
    return response
