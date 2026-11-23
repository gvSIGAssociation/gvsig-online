"""
Llevar al repositorio lo editado desde la web en el centro de documentación.

Las ediciones web (DocPageEdit) y las imágenes subidas (DocAsset) viven en la base de datos y en
MEDIA_ROOT de cada despliegue; para que lleguen a los demás tienen que pasar por el repositorio
del manual: la documentación central (gvsig_doc, Git) o la carpeta docs/ del paquete (SVN). Este
módulo reúne esos cambios de una app y los entrega:

- como ZIP con las rutas dentro del repositorio de cada manual (vista «Exportar cambios web» del
  lector, cualquier despliegue);
- escritos directamente en su sitio (comando ``docs_to_repo``, en desarrollo, donde los
  repositorios están montados en el contenedor).
"""
import io
import os
import zipfile
from typing import List, Optional

from gvsigol_core import docs_center as dc


# Clases normales y no dataclasses: el core también se usa con Python 3.6 (Django 2.2)

class Change:
    def __init__(self, rel: str, kind: str, obj, manual, base_changed: bool = False):
        self.rel = rel                   # ruta del manual: es/usuarios.md, es/img/x.png
        self.kind = kind                 # 'page' | 'image'
        self.obj = obj                   # DocPageEdit o DocAsset
        self.manual = manual             # manual al que pertenece (decide dónde se escribe)
        self.base_changed = base_changed  # la página del repositorio cambió después de la edición web

    @property
    def target(self) -> Optional[str]:
        """Ruta absoluta donde se escribe."""
        return self.manual.resolve(self.rel)

    @property
    def repo_rel(self) -> str:
        """Ruta dentro del repositorio del manual (ZIP y avisos)."""
        return self.manual.repo_path(self.rel)

    def read(self) -> bytes:
        if self.kind == 'page':
            return self.obj.content.encode('utf-8')
        with self.obj.file.open('rb') as f:
            return f.read()


class Changes:
    def __init__(self, app: str):
        self.app = app
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
    result = Changes(app=app)

    for edit in DocPageEdit.objects.filter(app=app).order_by('manual', 'page', 'lang'):
        manual = next((m for m in manuals if m.slug == edit.manual), None)
        page = manual.page(edit.page) if manual else None
        if not page:
            continue    # la página ya no está en el manifiesto
        if user is not None and not (dc.can_see(user, manual.audience) and dc.can_see(user, page.audience)):
            continue
        repo_path = dc.repo_file(manual, page, edit.lang)
        result.pages.append(Change(
            rel='%s/%s' % (edit.lang, page.file), kind='page', obj=edit, manual=manual,
            base_changed=bool(repo_path) and edit.base_hash != dc.file_sha1(repo_path)))

    # Imágenes que usa alguna página, tal como quedará en el repositorio (edición web o fichero):
    # cada una va al manual que la usa
    used = {}
    for manual in manuals:
        for page in manual.pages:
            for code in manual.langs():
                text, used_lang, _v = dc.page_source(manual, page, code)
                if text is not None and used_lang == code:
                    for rel, _alt in dc.referenced_images(text, code):
                        used.setdefault(rel, manual)
    for item in DocAsset.objects.filter(app=app).order_by('path'):
        rel = dc.safe_relpath(item.path)
        if not rel:
            continue
        change = Change(rel=rel, kind='image', obj=item, manual=used.get(rel, manuals[0]))
        (result.images if rel in used else result.unused_images).append(change)
    return result


def zip_bytes(changes: Changes) -> bytes:
    """ZIP con las rutas dentro del repositorio de cada manual: <paquete>/docs/<ruta> para los de
    un paquete, gvSIG/docs/<idioma>/<path>/<resto> para los centrales. Se descomprime en la raíz
    de ese repositorio (gvsigol/, plugin_x/ o gvsig_doc/)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for change in changes.pages + changes.images:
            zf.writestr(change.repo_rel, change.read())
    return buffer.getvalue()
