"""
Llevar al repositorio lo editado desde la web en el centro de documentación.

Las ediciones web (DocPageEdit) y las imágenes subidas (DocAsset) viven en la base de datos y en
MEDIA_ROOT de cada despliegue; para que lleguen a los demás tienen que pasar por SVN. Este módulo
reúne esos cambios de una app y los entrega:

- como ZIP con las rutas del paquete (vista «Exportar cambios web» del lector, cualquier despliegue);
- escritos directamente en la carpeta docs/ del paquete (comando ``docs_to_repo``, en desarrollo,
  donde el código del repositorio está montado en el contenedor).
"""
import io
import os
import zipfile
from typing import List, Optional

from gvsigol_core import docs_center as dc


# Clases normales y no dataclasses: el core también se usa con Python 3.6 (Django 2.2)

class Change:
    def __init__(self, rel: str, kind: str, obj, base_changed: bool = False):
        self.rel = rel                   # ruta dentro de docs/ (es/usuarios.md, es/img/x.png)
        self.kind = kind                 # 'page' | 'image'
        self.obj = obj                   # DocPageEdit o DocAsset
        self.base_changed = base_changed  # la página del repositorio cambió después de la edición web

    def read(self) -> bytes:
        if self.kind == 'page':
            return self.obj.content.encode('utf-8')
        with self.obj.file.open('rb') as f:
            return f.read()


class Changes:
    def __init__(self, app: str, root: str):
        self.app = app
        self.root = root                         # carpeta docs/ del paquete
        self.pages = []                          # type: List[Change]
        self.images = []                         # type: List[Change]
        self.unused_images = []                  # type: List[Change]  subidas que ya no usa ninguna página

    @property
    def count(self) -> int:
        return len(self.pages) + len(self.images)


def collect(app: str, user=None) -> Optional[Changes]:
    """Cambios web de una app. Con user, solo las páginas que ese usuario puede ver."""
    from gvsigol_core.models import DocAsset, DocPageEdit

    manuals = [m for m in dc.all_manuals() if m.app == app]
    if not manuals:
        return None
    result = Changes(app=app, root=manuals[0].root)

    for edit in DocPageEdit.objects.filter(app=app).order_by('manual', 'page', 'lang'):
        manual = next((m for m in manuals if m.slug == edit.manual), None)
        page = manual.page(edit.page) if manual else None
        if not page:
            continue    # la página ya no está en docs.yml
        if user is not None and not (dc.can_see(user, manual.audience) and dc.can_see(user, page.audience)):
            continue
        repo_path = os.path.join(manual.root, edit.lang, page.file)
        result.pages.append(Change(
            rel='%s/%s' % (edit.lang, page.file), kind='page', obj=edit,
            base_changed=os.path.isfile(repo_path) and edit.base_hash != dc.file_sha1(repo_path)))

    # Imágenes que usa alguna página, tal como quedará en el repositorio (edición web o fichero)
    used = set()
    for manual in manuals:
        for page in manual.pages:
            for code in _langs(manual):
                text, used_lang, _v = dc.page_source(manual, page, code)
                if text is not None and used_lang == code:
                    used.update(rel for rel, _alt in dc.referenced_images(text, code))
    for item in DocAsset.objects.filter(app=app).order_by('path'):
        rel = dc.safe_relpath(item.path)
        if not rel:
            continue
        change = Change(rel=rel, kind='image', obj=item)
        (result.images if rel in used else result.unused_images).append(change)
    return result


def _langs(manual) -> List[str]:
    try:
        return sorted(d for d in os.listdir(manual.root)
                      if os.path.isdir(os.path.join(manual.root, d)) and d != 'assets')
    except OSError:
        return [dc.DEFAULT_LANG]


def zip_bytes(changes: Changes) -> bytes:
    """ZIP con las rutas del paquete: <app>/docs/<ruta>. Se descomprime en la carpeta del
    repositorio que contiene el paquete (gvsigol/ para el core, plugin_x/ para un plugin)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for change in changes.pages + changes.images:
            zf.writestr('%s/%s/%s' % (changes.app, dc.DOCS_DIRNAME, change.rel), change.read())
    return buffer.getvalue()
