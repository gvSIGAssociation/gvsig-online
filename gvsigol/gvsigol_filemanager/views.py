from datetime import datetime
from gvsigol_auth import auth_backend
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from gvsigol_services.models import Datastore
from gvsigol_services import geographic_servers
from gvsigol_services.backend_postgis import Introspect
from gvsigol_services.forms_geoserver import PostgisLayerUploadForm
from gvsigol_core import utils as core_utils
from django.views.generic import TemplateView, FormView
from django.shortcuts import HttpResponse, redirect
from django.utils.translation import gettext as _, ngettext
from gvsigol.settings import FILEMANAGER_DIRECTORY, INSTALLED_APPS
from django.urls import reverse_lazy
from django.http import HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.utils.translation import gettext_lazy
from django.conf import settings
from gvsigol_services import rest_geoserver
from django.views.generic.base import View
from .forms import DirectoryCreateForm
from django.contrib import messages
from .core import Filemanager, UnzipError, RESERVED_NAMES
from zipfile import ZipFile
import json
import os
import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django_sendfile import sendfile
from django.contrib.auth.decorators import login_required
from gvsigol_auth.utils import staff_required
from django.utils.decorators import method_decorator
from django.shortcuts import render
from .tasks import postBackground
from .models import exports_historical
from celery.result import AsyncResult
from gvsigol_services.shp2postgis import get_fields_from_shape, get_fields_from_gpkg, list_gpkg_layers
from gvsigol_plugin_baseapi.validation import Validation, HttpException
import re

logger = logging.getLogger("gvsigol")
ABS_FILEMANAGER_DIRECTORY = os.path.abspath(FILEMANAGER_DIRECTORY)
SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']
_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")
_CELERY_RUNNING_STATES = frozenset({
    'PENDING', 'RECEIVED', 'STARTED', 'RETRY', 'PROCESSING', 'PROGRESS',
})
_LEGACY_LOST_MESSAGES = frozenset({
    'Exportation task has been lost',
})


def _export_lost_message():
    return str(_("The export task was lost or the worker did not respond"))


def _resolve_export_progress(ex):
    """
    Resolve Running export status from Celery AsyncResult instead of fragile inspect().
    Returns (status, message, progress, persist_error).
    """
    lost_msg = _export_lost_message()
    if not ex.task_id:
        return 'Error', lost_msg, 0, True

    result = AsyncResult(ex.task_id)
    state = result.state
    info = result.info if isinstance(result.info, dict) else {}
    progress = info.get('progress', 0) or 0
    detail = info.get('status') or ''

    if state in _CELERY_RUNNING_STATES:
        return 'Running', detail or _('Running'), progress, False

    if state == 'SUCCESS':
        ex.refresh_from_db()
        if ex.status == 'Running':
            return 'Running', _('Finalizing...'), max(progress, 95), False
        return ex.status, ex.message, 100, False

    if state in ('FAILURE', 'REVOKED'):
        err = _('Export task failed')
        if isinstance(result.info, Exception):
            err = str(result.info)
        elif isinstance(result.info, dict):
            err = result.info.get('error') or result.info.get('status') or err
        elif result.info:
            err = str(result.info)
        return 'Error', err, 0, True

    # Unknown / expired result backend entry: keep Running if DB says so,
    # only mark lost when previously flagged as lost with no recoverable state.
    if ex.message in _LEGACY_LOST_MESSAGES or ex.message == lost_msg:
        return 'Error', lost_msg, 0, True
    return 'Running', detail or _('Running'), progress, False

def can_manage_path(request, path):
    if path is not None:
        full_path = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, path))
        # Con el separador: sin él, una carpeta hermana como «data_x» pasaría por «data»
        if full_path != ABS_FILEMANAGER_DIRECTORY and not full_path.startswith(ABS_FILEMANAGER_DIRECTORY + os.sep):
            logger.warning("Suspicious path provided: " + path)
            return False
        # La papelera y demás carpetas reservadas solo se manejan desde la API (ver fsops)
        if os.path.relpath(full_path, ABS_FILEMANAGER_DIRECTORY).split(os.sep)[0] in RESERVED_NAMES:
            return False
        if request.user:
            if request.user.is_superuser:
                return True
            if not request.user.is_staff:
                return False
            first_level_path = os.path.relpath(full_path, ABS_FILEMANAGER_DIRECTORY).split("/")[0]
            first_level_abspath = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, first_level_path))
            if os.path.isdir(first_level_abspath):
                for g in auth_backend.get_roles(request):
                    if first_level_path == g:
                        return True
            elif os.path.isfile(first_level_abspath):
                return False
    return False

def can_browse_path(request, path):
    if path == '' and (request.user.is_superuser or request.user.is_staff):
        return True
    return can_manage_path(request, path)

class FilemanagerMixin(object):
    def dispatch(self, request, *args, **kwargs):
        params = dict(request.GET)
        params.update(dict(request.POST))

        self.fm = Filemanager()
        if 'path' in params and len(params['path'][0]) > 0:
            self.fm.update_path(params['path'][0])
        if 'popup' in params:
            self.popup = params['popup']
        
        return super(FilemanagerMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(FilemanagerMixin, self).get_context_data(*args, **kwargs)

        self.fm.patch_context_data(context)

        if hasattr(self, 'popup'):
            context['popup'] = self.popup

        if hasattr(self, 'extra_breadcrumbs') and isinstance(self.extra_breadcrumbs, list):
            context['breadcrumbs'] += self.extra_breadcrumbs

        return context


class BrowserView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, TemplateView):
    template_name = 'browser/filemanager_list.html'
    raise_exception = False
    def test_func(self):
        return can_browse_path(self.request, self.request.GET.get('path', ''))

    def dispatch(self, request, *args, **kwargs):
        self.popup = self.request.GET.get('popup', 0) == '1'
        return super(BrowserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BrowserView, self).get_context_data(**kwargs)
        
        # Una carpeta que no existe (o un fichero) daba un error 500 al listarla
        if not os.path.isdir(self.fm.location):
            raise Http404('Directory not found')

        context['first_level'] = False
        if self.fm.location == FILEMANAGER_DIRECTORY:
            context['first_level'] = True
        context['popup'] = self.popup
        if self.popup:
            context['extends_template'] = 'filemanager_base2.html'
        else:
            context['extends_template'] = 'filemanager_base.html'
        context['is_etl_plugin_installed'] = 'gvsigol_plugin_etl' in INSTALLED_APPS
        if self.use_explorer():
            # La interfaz nueva carga el contenido por la API (api.py)
            context.update(self.explorer_context())
        else:
            context['files'] = self.fm.directory_list(self.request, context['first_level'])

        return context

    def use_explorer(self):
        """
        Interfaz nueva (explorador) o clásica. ?ui=new / ?ui=classic eligen en cada visita; si no,
        manda FILEMANAGER_NEW_UI para la página y FILEMANAGER_NEW_POPUP para el selector (?popup=1),
        que se activan por separado.
        """
        ui = self.request.GET.get('ui')
        session = getattr(self.request, 'session', None)
        if ui in ('new', 'classic'):
            # Se recuerda en la sesión del usuario: así los selectores que abren otras pantallas
            # (que no pasan ?ui=) también salen con la interfaz elegida, solo para él.
            if session is not None and session.get('filemanager_ui') != ui:
                session['filemanager_ui'] = ui
            return ui == 'new'
        if session is not None and session.get('filemanager_ui') in ('new', 'classic'):
            return session.get('filemanager_ui') == 'new'
        setting = 'FILEMANAGER_NEW_POPUP' if self.popup else 'FILEMANAGER_NEW_UI'
        return bool(getattr(settings, setting, False))

    def picker_extensions(self):
        """?ext=tif,tiff: el selector solo muestra (y deja elegir) esos ficheros."""
        raw = self.request.GET.get('ext') or ''
        return sorted({e.strip().lower().lstrip('.') for e in raw.split(',') if e.strip().lstrip('.')})

    def get_template_names(self):
        if self.use_explorer():
            return ['browser/filemanager_explorer.html']
        return super(BrowserView, self).get_template_names()

    def explorer_context(self):
        from . import fsops
        from .ui_strings import ui_strings
        from django.utils import translation
        try:
            transform_url = str(reverse_lazy('transform-to-database')) if 'gvsigol_plugin_etl' in INSTALLED_APPS else None
        except Exception:
            transform_url = None
        browser_url = str(reverse_lazy('filemanager:browser'))
        return {
            'fm_config': {
                'api': browser_url + 'api/',
                'browserUrl': browser_url,
                'keepUiParam': self.request.GET.get('ui') == 'new',
                'downloadUrl': str(reverse_lazy('fsfilemanager:fdownload', args=['x']))[:-1],
                'exportUrl': str(reverse_lazy('filemanager:export-to-database')),
                'transformUrl': transform_url,
                'exportsUrl': str(reverse_lazy('filemanager:list_exports')),
                'path': self.fm.path,
                'trashDays': fsops.retention_days(),
                'language': translation.get_language() or 'es',
                'isSuperuser': self.request.user.is_superuser,
                # Selector: misma respuesta que el clásico, window.opener.filemanagerCallback(ruta)
                'popup': bool(self.popup),
                'extensions': self.picker_extensions() if self.popup else [],
                # ?multiple=1: varios ficheros a la vez (filemanagerMultipleCallback(rutas) si existe,
                # si no, filemanagerCallback(ruta) una vez por fichero)
                'multiple': bool(self.popup) and self.request.GET.get('multiple') in ('1', 'true'),
            },
            'fm_i18n': ui_strings(),
        }
 
class ExportToDatabaseView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, TemplateView):
    template_name = 'browser/export_to_database.html'
    raise_exception = False
    def test_func(self):
        # Note: user permissions in the target datastore are specifically checked in form validation
        if self.request.user.is_superuser or self.request.user.is_staff:
            if self.request.method in SAFE_METHODS:
                return can_manage_path(self.request, self.request.GET.get('path'))
            return can_manage_path(self.request, self.request.POST.get('file'))
        return False

    def get_context_data(self, **kwargs):
        context = super(ExportToDatabaseView, self).get_context_data(**kwargs)

        file_details = self.fm.file_details()
        fileurl = file_details.get('fileurl') or ''
        filepath = file_details.get('filepath') or ''
        is_gpkg = filepath.lower().endswith('.gpkg') or fileurl.lower().endswith('.gpkg')
        column_name_error = None
        gpkg_layers = []
        selected_gpkg_layer = self.request.GET.get('gpkg_layer') or ''
        source_columns = []

        try:
            if is_gpkg:
                gpkg_layers = list_gpkg_layers(fileurl)
                if not gpkg_layers:
                    column_name_error = _("Could not read layers inside the GeoPackage.")
                else:
                    if selected_gpkg_layer not in gpkg_layers:
                        selected_gpkg_layer = gpkg_layers[0]
                    field_defs = get_fields_from_gpkg(fileurl, selected_gpkg_layer)
                    source_columns = [col.name for col in field_defs]
            else:
                field_defs = get_fields_from_shape(fileurl)
                source_columns = [col.name for col in field_defs]

            offending_fields = []
            for name in source_columns:
                if _valid_name_regex.search(name) is None:
                    offending_fields.append(name)
            if len(offending_fields) > 0:
                column_name_error = ngettext(
                        "Field '{}' contains non-ASCII characters in field name and is not suported. Rename this fields and try again. Allowed characters are a-z, A-Z, _ or numbers; the first character can't be a number.",
                        "Fields [{}] contain non-ASCII characters in field name and are not suported. Rename these fields and try again. Allowed characters are a-z, A-Z, _ or numbers; the first character can't be a number.",
                        len(offending_fields)).format(", ".join(offending_fields))
        except UnicodeError:
            source_columns = []
            column_name_error = _("The layer contains non-ASCII characters in field names and it is not suported. Rename the offending fields and try again. Allowed characters are a-z, A-Z, _ or numbers; the first character can't be a number.")
        except Exception as exc:
            logger.exception(exc)
            source_columns = []
            if not column_name_error:
                column_name_error = _("Could not read the file. Review the format and try again.")

        form = PostgisLayerUploadForm(
            user=self.request.user,
            source_columns=source_columns,
            request=self.request,
            gpkg_layers=gpkg_layers,
            selected_gpkg_layer=selected_gpkg_layer,
            is_gpkg=is_gpkg,
        )
        if is_gpkg and selected_gpkg_layer and 'encoding' in form.fields:
            form.fields['encoding'].initial = 'UTF-8'
        context['file'] = file_details
        context['form'] = form
        context['is_gpkg'] = is_gpkg
        context['gpkg_layers'] = gpkg_layers
        context['selected_gpkg_layer'] = selected_gpkg_layer
        context["back_url"] = '%s?path=%s' % (reverse_lazy('filemanager:browser'), file_details.get('directory'))
        if column_name_error:
            context["not_supported_error"] = column_name_error
        return context
    
    def post(self, request, *args, **kwargs):

        exports_model = exports_historical.objects.order_by('id')

        if exports_model.count() >= 20:

            to_remove = exports_model.count() - 19
            i = 0
            for exp in exports_model:
                if i == to_remove:
                    break
                else:
                    exp.delete()
                i+=1

        e = datetime.now()
        file_path = request.POST.get('file_path') or ''
        export_md = exports_historical(
            time = "%s-%s-%s %s:%s:%s" % (e.day, e.month, e.year, e.hour, e.minute, e.second),
            file = file_path,
            status = 'Running',
            message = str(_('Running')),
            username = request.user.username,
            redirect = "/gvsigonline/filemanager/export_to_database/?path=" + file_path
        )

        export_md.save()

        try:
            async_result = postBackground.apply_async(kwargs={
                'id': export_md.id,
                'post': request.POST,
                'files': request.FILES,
                'username': request.user.username,
            })
            export_md.task_id = str(async_result.id)
            export_md.save(update_fields=['task_id'])
            return redirect('/gvsigonline/filemanager/list_exports/')
        
        except Exception as e:

            export_md.status = 'Error'
            export_md.message = str(e)
            export_md.save()

            return redirect('/gvsigonline/filemanager/list_exports/')


@login_required
@staff_required
def list_exports(request):

    exports_model = exports_historical.objects.order_by('-id')

    exportations = []
    lost_msg = _export_lost_message()

    for ex in exports_model:
        export = {
            'id': ex.id,
            'file': ex.file,
            'time': ex.time,
            'redirect': ex.redirect,
            'username': ex.username,
            'progress': 0,
        }

        is_running_like = (
            ex.status == 'Running'
            or ex.message in _LEGACY_LOST_MESSAGES
            or ex.message == lost_msg
        )

        if is_running_like:
            status, message, progress, persist_error = _resolve_export_progress(ex)
            export['status'] = status
            export['message'] = message
            export['progress'] = progress
            if persist_error and (ex.status != 'Error' or ex.message != message):
                ex.status = 'Error'
                ex.message = message
                ex.save(update_fields=['status', 'message'])
            elif status == 'Running' and (
                ex.status != 'Running'
                or ex.message in _LEGACY_LOST_MESSAGES
                or ex.message == lost_msg
            ):
                ex.status = 'Running'
                ex.message = str(_('Running'))
                ex.save(update_fields=['status', 'message'])
        else:
            export['status'] = ex.status
            export['message'] = ex.message
            if ex.status in ('Success', 'Warning'):
                export['progress'] = 100

        if '/' in (ex.file or ''):
            export['back'] = '/'.join(ex.file.split('/')[:-1])
        else:
            export['back'] = ''

        exportations.append(export)

    response = {'exportations': exportations}

    if request.POST:
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    else:

        return render(request, 'filemanager_exports_historical.html', response)



class UploadView(FilemanagerMixin, TemplateView):
    template_name = 'filemanager_upload.html'
    extra_breadcrumbs = [{
        'path': '#',
        'label': gettext_lazy('Upload')
    }]

    @method_decorator(login_required)
    @method_decorator(staff_required)
    def dispatch(self, request, *args, **kwargs):
        if not can_manage_path(self.request, self.request.GET.get('path')):
            return render(request, 'illegal_operation.html', {})
        return super(UploadView, self).dispatch(request, *args, **kwargs)

class UploadFileView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, View):
    raise_exception = False
    def test_func(self):
        return can_manage_path(self.request, self.request.POST.get('path'))
    
    def post(self, request, *args, **kwargs):
        if len(request.FILES) != 1:
            return HttpResponseBadRequest("Just a single file please.")
        
        # Aquí se calculaba la extensión con split(".")[1], que fallaba (500) con ficheros sin ella
        '''
        if extension == "zip":
            folder = file.name.split(".")[0]
            #self.fm.extract_zip(file, folder)
            
        else:
            # TODO: get filepath and validate characters in name, validate mime type and extension
            self.fm.upload_file(filedata = request.FILES['files'])
        '''    
        self.fm.upload_file(filedata = request.FILES['files'])

        return HttpResponse(json.dumps({
            'files': [],
            'path': request.POST.get('path'),
        }))
        
def raster_datastore_paths():
    """
    (nombre, ruta absoluta, es_mosaico) de los almacenes GeoTIFF e ImageMosaic. Guardan la ruta como
    'file:///.../data/...' (el selector antepone file:// y FILEMANAGER_DIRECTORY).
    """
    result = []
    for datastore in Datastore.objects.filter(type__in=['c_GeoTIFF', 'c_ImageMosaic']):
        try:
            url = json.loads(datastore.connection_params).get('url') or ''
        except Exception:
            continue
        if url.startswith('file://'):
            url = url[len('file://'):]
        if url:
            result.append((datastore.name, os.path.abspath(url), datastore.type == 'c_ImageMosaic'))
    return result


def datastore_using_path(abs_path, datastores=None):
    """
    Nombre del almacén raster que depende de esta ruta, o None. Depende si la ruta es su fichero,
    una carpeta que lo contiene o, en un mosaico, algo dentro de su carpeta.
    """
    target = os.path.abspath(abs_path)
    for name, url, is_mosaic in (raster_datastore_paths() if datastores is None else datastores):
        if url == target or url.startswith(target + os.sep):
            return name
        if is_mosaic and target.startswith(url + os.sep):
            return name
    return None


class DeleteFileView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, View):
    raise_exception = False
    def test_func(self):
        return can_manage_path(self.request, self.request.POST.get('path'))

    def post(self, request, *args, **kwargs):
        path = FILEMANAGER_DIRECTORY +'/'+ request.POST.get('path')
        # Antes comparaba sin quitar el 'file://' de la URL del almacén y nunca bloqueaba
        datastore_name = datastore_using_path(path)
        if datastore_name:
                return HttpResponse(json.dumps({
                    'success': False,
                    'message': _('Error deleting resource') + ' ' + path + ' ' + _('exists in datastore') + ': ' + datastore_name
                }))
        
        if self.fm.delete(path):
            return HttpResponse(json.dumps({
                'success': True
            }))
            
        else:
            return HttpResponse(json.dumps({
                'success': False,
                'message': _('Error deleting resource') + ' ' + path
            }))

class UnzipFileView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, View):
    raise_exception = False
    def test_func(self):
        return can_manage_path(self.request, self.request.POST.get('path'))
    
    def post(self, request, *args, **kwargs):
        path = os.path.join(FILEMANAGER_DIRECTORY, request.POST.get('path'))

        try:
            # Descomprime en una carpeta nueva (nombre_1... si ya existe) tras comprobar el tamaño
            self.fm.unzip(path)

            return HttpResponse(json.dumps({
                'success': True
            }))

        except UnzipError as e:
            logger.warning("Error unzipping file %s: %s", path, e)
            return HttpResponse(json.dumps({
                'success': False,
                'message': str(e)
            }))

        except Exception as e:
            logger.exception("Error unzipping file")
            return HttpResponse(json.dumps({
                'success': False,
                'message': _('Error unzipping resource') + ' ' + path
            }))

class DirectoryCreateView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, FormView):
    template_name = 'filemanager_create_directory.html'
    form_class = DirectoryCreateForm
    extra_breadcrumbs = [{
        'path': '#',
        'label': gettext_lazy('Create directory')
    }]
    raise_exception = False
    def test_func(self):
        if self.request.method in SAFE_METHODS:
            return (self.request.user.is_superuser or self.request.user.is_staff)
        return can_manage_path(self.request, self.request.POST.get('path'))

    def get_success_url(self):
        url = '%s?path=%s' % (reverse_lazy('filemanager:browser'), self.fm.path)
        if hasattr(self, 'popup') and self.popup:
            url += '&popup=1'
        return url

    def form_valid(self, form):
        self.fm.create_directory(form.cleaned_data.get('directory_name'))
        return super(DirectoryCreateView, self).form_valid(form)

def download_file(request, filepath):
    """
    Django view to download files from the file manager.
    """
    try:
        print('xsendfile requested file: ' + filepath)
    except:
        logger.exception('xsendfile error')
    abs_path = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, filepath))
    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return HttpResponseBadRequest()
    if not can_manage_path(request, filepath):
        return HttpResponseForbidden()
    try:
        print('xsendfile served file: ' + abs_path)
    except:
        logger.exception('xsendfile error')
    return sendfile(request, abs_path, attachment=True)


class DownloadFile(APIView):
    """
    DRF REST view to download files from the file manager.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='download_filemanager_file',
        operation_summary='Downloads the file from the file manager',
        responses={404: "File not found", 403: "Not allowed"}
    )
    def get(self, request, filepath):
        abs_path = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, filepath))
        if not can_manage_path(request, abs_path):
            return HttpException(403, "Not allowed").get_exception()
        if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            return HttpException(404, "File not found").get_exception()
        try:
            logger.debug(f'REST view: xsendfile served file: {abs_path}')
        except:
            logger.exception('xsendfile error')
        return sendfile(request, abs_path, attachment=True)