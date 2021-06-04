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

logger = logging.getLogger("gvsigol")
ABS_FILEMANAGER_DIRECTORY = os.path.abspath(FILEMANAGER_DIRECTORY)
SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

def can_manage_path(user, path):
    if path is not None:
        full_path = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, path))
        if not full_path.startswith(ABS_FILEMANAGER_DIRECTORY):
            logger.warning("Suspicious path provided: " + path)
            return False
        if user:
            if user.is_superuser:
                return True
            if not user.is_staff:
                return False
            first_level_path = os.path.relpath(full_path, ABS_FILEMANAGER_DIRECTORY).split("/")[0]
            first_level_abspath = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, first_level_path))
            if os.path.isdir(first_level_abspath):
                for g in core_utils.get_group_names_by_user(user):
                    if first_level_path == g:
                        return True
            elif os.path.isfile(first_level_abspath):
                return False
    return False

def can_browse_path(user, path):
    if path == '' and (user.is_superuser or user.is_staff):
        return True
    return can_manage_path(user, path)

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
        return can_browse_path(self.request.user, self.request.GET.get('path', ''))

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
                return can_manage_path(self.request.user, self.request.GET.get('path'))
            return can_manage_path(self.request.user, self.request.POST.get('file'))
        return False

    def get_context_data(self, **kwargs):
        context = super(ExportToDatabaseView, self).get_context_data(**kwargs)
        
        form = PostgisLayerUploadForm(user=self.request.user)
        
        context['form'] = form
        context['file'] = self.fm.file_details()
    
        return context
    
    def post(self, request, *args, **kwargs):
        form = PostgisLayerUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                gs = geographic_servers.get_instance().get_server_by_id(form.cleaned_data['datastore'].workspace.server.id)
                if gs.exportShpToPostgis(form.cleaned_data):
                    #request.session.message = _('Export process done successfully')
                    messages.add_message(request, messages.INFO, _('Export process done successfully'))
                    return redirect("/gvsigonline/filemanager/?path=" + request.POST.get('directory_path'))
            except rest_geoserver.RequestWarning as e:
                    msg = _('Export process completed with warnings:') + ' ' + str(e)
                    messages.add_message(request, messages.INFO, msg)
                    return redirect("/gvsigonline/filemanager/?path=" + request.POST.get('directory_path'))
            except rest_geoserver.RequestError as e:
                message = e.server_message
                #request.session['message'] = str(message)
                messages.add_message(request, messages.ERROR, str(message))
                """
                if e.status_code == -1:
                    name = form.data['name']
                    datastore_id = form.data['datastore']
                    datastore = Datastore.objects.get(id=datastore_id)
                    params = json.loads(datastore.connection_params)
                    host = params['host']
                    port = params['port']
                    dbname = params['database']
                    user = params['user']
                    passwd = params['passwd']
                    schema = params.get('schema', 'public')
                    i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                    i.delete_table(schema, name)
                    i.close()
                """
                return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))
                
            except Exception as exc:
                #request.session['message'] = _('Server error') +  ":" + str(exc)
                messages.add_message(request, messages.ERROR, _('Server error') +  ":" + str(exc))
                return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))
        else:
            #request.session['message'] = _('You must fill in all fields')
            messages.add_message(request, messages.ERROR, _('You must fill in all fields'))
            return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))

class UploadView(FilemanagerMixin, TemplateView):
    template_name = 'filemanager_upload.html'
    extra_breadcrumbs = [{
        'path': '#',
        'label': 'Upload'
    }]

    @method_decorator(login_required(login_url='/gvsigonline/auth/login_user/'))
    @method_decorator(staff_required)
    def dispatch(self, request, *args, **kwargs):
        if not can_manage_path(self.request.user, self.request.GET.get('path')):
            return render(request, 'illegal_operation.html', {})
        return super(UploadView, self).dispatch(request, *args, **kwargs)

class UploadFileView(LoginRequiredMixin, UserPassesTestMixin, FilemanagerMixin, View):
    raise_exception = True
    def test_func(self):
        return can_manage_path(self.request.user, self.request.POST.get('path'))
    
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
        return can_manage_path(self.request.user, self.request.POST.get('path'))
    
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
        return can_manage_path(self.request.user, self.request.POST.get('path'))
    
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
        return can_manage_path(self.request.user, self.request.POST.get('path'))

    def get_success_url(self):
        url = '%s?path=%s' % (reverse_lazy('filemanager:browser'), self.fm.path)
        if hasattr(self, 'popup') and self.popup:
            url += '&popup=1'
        return url

    def form_valid(self, form):
        self.fm.create_directory(form.cleaned_data.get('directory_name'))
        return super(DirectoryCreateView, self).form_valid(form)

def download_file(request, filepath):
    abs_path = os.path.abspath(os.path.join(ABS_FILEMANAGER_DIRECTORY, filepath))
    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return HttpResponseBadRequest()
    if not can_manage_path(request.user, filepath):
        return HttpResponseForbidden()
    return sendfile(request, abs_path, attachment=True)
