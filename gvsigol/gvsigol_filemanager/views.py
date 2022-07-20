from datetime import datetime
from gvsigol_auth import auth_backend
from gvsigol_services.models import Datastore
from gvsigol_services import geographic_servers
from gvsigol_services.backend_postgis import Introspect
from gvsigol_services.forms_geoserver import PostgisLayerUploadForm
from gvsigol_core import utils as core_utils
from django.views.generic import TemplateView, FormView
from django.shortcuts import HttpResponse, redirect
from django.utils.translation import ugettext as _
from gvsigol.settings import FILEMANAGER_DIRECTORY, INSTALLED_APPS
from django.urls import reverse_lazy
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from gvsigol_services import rest_geoserver
from django.views.generic.base import View
from .forms import DirectoryCreateForm
from django.contrib import messages
from .core import Filemanager
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

logger = logging.getLogger("gvsigol")
ABS_FILEMANAGER_DIRECTORY = os.path.abspath(FILEMANAGER_DIRECTORY)
SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

def can_manage_path(request, path):
    if path is not None:
        full_path = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, path))
        if not full_path.startswith(ABS_FILEMANAGER_DIRECTORY):
            logger.warning("Suspicious path provided: " + path)
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
    raise_exception = True
    def test_func(self):
        return can_browse_path(self.request, self.request.GET.get('path', ''))

    def dispatch(self, request, *args, **kwargs):
        self.popup = self.request.GET.get('popup', 0) == '1'
        return super(BrowserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BrowserView, self).get_context_data(**kwargs)
        
        context['first_level'] = False
        if self.fm.location == FILEMANAGER_DIRECTORY:
            context['first_level'] = True
        context['popup'] = self.popup
        if self.popup:
            context['extends_template'] = 'filemanager_base2.html'
        else:
            context['extends_template'] = 'filemanager_base.html'
        context['files'] = self.fm.directory_list(self.request, context['first_level'])
        context['is_etl_plugin_installed'] = 'gvsigol_plugin_etl' in INSTALLED_APPS
        
        return context
 
class ExportToDatabaseView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, TemplateView):
    template_name = 'browser/export_to_database.html'
    raise_exception = True
    def test_func(self):
        # Note: user permissions in the target datastore are specifically checked in form validation
        if self.request.user.is_superuser or self.request.user.is_staff:
            if self.request.method in SAFE_METHODS:
                return can_manage_path(self.request, self.request.GET.get('path'))
            return can_manage_path(self.request, self.request.POST.get('file'))
        return False

    def get_context_data(self, **kwargs):
        context = super(ExportToDatabaseView, self).get_context_data(**kwargs)
        
        form = PostgisLayerUploadForm(user=self.request.user)
        
        context['form'] = form
        context['file'] = self.fm.file_details()
    
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
        export_md = exports_historical(
            time = "%s-%s-%s %s:%s:%s" % (e.day, e.month, e.year, e.hour, e.minute, e.second),
            file = request.POST.get('file_path'),
            status = 'Running',
            message = 'Running',
            username = request.user.username
        )

        export_md.save()

        postBackground.apply_async(kwargs = {'id': export_md.id, 'post': request.POST, 'files': request.FILES, 'username': request.user.username})

        return redirect('/gvsigonline/filemanager/list_exports/')


def list_exports(request):

    exports_model = exports_historical.objects.order_by('-id')

    exportations = []

    for ex in exports_model:
        export = {}
        export['id'] = ex.id
        export['file'] = ex.file
        export['time'] = ex.time
        export['status'] = ex.status
        export['message'] = ex.message
        export['redirect'] = ex.redirect
        export['username'] = ex.username
        
        if '/' in ex.file:
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
        'label': 'Upload'
    }]

    @method_decorator(login_required(login_url='/gvsigonline/auth/login_user/'))
    @method_decorator(staff_required)
    def dispatch(self, request, *args, **kwargs):
        if not can_manage_path(self.request, self.request.GET.get('path')):
            return render(request, 'illegal_operation.html', {})
        return super(UploadView, self).dispatch(request, *args, **kwargs)

class UploadFileView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, View):
    raise_exception = True
    def test_func(self):
        return can_manage_path(self.request, self.request.POST.get('path'))
    
    def post(self, request, *args, **kwargs):
        if len(request.FILES) != 1:
            return HttpResponseBadRequest("Just a single file please.")
        
        file = request.FILES['files']
        extension = file.name.split(".")[1]
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
        
class DeleteFileView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, View):
    raise_exception = True
    def test_func(self):
        return can_manage_path(self.request, self.request.POST.get('path'))
    
    def post(self, request, *args, **kwargs):
        path = FILEMANAGER_DIRECTORY +'/'+ request.POST.get('path')
        geotiffs = Datastore.objects.filter(type__in=['c_GeoTIFF','c_ImageMosaic'])
        for geotiff in geotiffs:
            params = json.loads(geotiff.connection_params)
            if 'url' in params and params['url'].startswith(path) or (geotiff.type == 'c_ImageMosaic' and path.startswith(params['url'])) :
                return HttpResponse(json.dumps({
                    'success': False,
                    'message': _('Error deleting resource') + ' ' + path + ' ' + _('exists in datastore') + ': ' + geotiff.name 
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
    raise_exception = True
    def test_func(self):
        return can_manage_path(self.request, self.request.POST.get('path'))
    
    def post(self, request, *args, **kwargs):
        path = os.path.join(FILEMANAGER_DIRECTORY, request.POST.get('path'))
        
        try:
            folder = os.path.join(os.path.dirname(path), os.path.basename(path).split(".")[0])
            self.fm.extract_zip(path, folder)

            return HttpResponse(json.dumps({
                'success': True
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
        'label': 'Create directory'
    }]
    raise_exception = True
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
