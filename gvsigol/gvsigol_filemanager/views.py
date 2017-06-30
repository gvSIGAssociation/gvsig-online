from gvsigol_services.models import Datastore
from gvsigol_services.backend_mapservice import backend as mapservice
from gvsigol_services.backend_postgis import Introspect
from gvsigol_services.forms_geoserver import PostgisLayerUploadForm
from django.views.generic import TemplateView, FormView
from django.shortcuts import HttpResponse, redirect
from django.utils.translation import ugettext as _
from gvsigol.settings import FILEMANAGER_DIRECTORY
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseBadRequest
from gvsigol_services import rest_geoserver
from django.views.generic.base import View
from forms import DirectoryCreateForm
from core import Filemanager
import json

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


class BrowserView(FilemanagerMixin, TemplateView):
    template_name = 'browser/filemanager_list.html'

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

        return context


class ExportToDatabaseView(FilemanagerMixin, TemplateView):
    template_name = 'browser/export_to_database.html'

    def get_context_data(self, **kwargs):
        context = super(ExportToDatabaseView, self).get_context_data(**kwargs)
        
        form = mapservice.getUploadForm('v_PostGIS', self.request.user)
        context['form'] = form
        if 'message' in self.request.session:
            if self.request.session['message'] != '':
                context['message'] = self.request.session['message']
                self.request.session['message'] = ''
        context['file'] = self.fm.file_details()
        
        return context
    
    def post(self, request, *args, **kwargs):
        form = PostgisLayerUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                if mapservice.exportShpToPostgis(form.cleaned_data):
                    return redirect("/gvsigonline/filemanager/?path=" + request.POST.get('directory_path'))
                
            except rest_geoserver.RequestError as e:
                message = e.server_message
                request.session['message'] = message
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
                return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))
                
            except Exception as exc:
                request.session['message'] = _('Server error')
                return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))
        else:
            request.session['message'] = _('You must fill in all fields')
            return redirect("/gvsigonline/filemanager/export_to_database/?path=" + request.POST.get('file_path'))

class UploadView(FilemanagerMixin, TemplateView):
    template_name = 'filemanager_upload.html'
    extra_breadcrumbs = [{
        'path': '#',
        'label': 'Upload'
    }]


class UploadFileView(FilemanagerMixin, View):
    def post(self, request, *args, **kwargs):
        if len(request.FILES) != 1:
            return HttpResponseBadRequest("Just a single file please.")
        
        file = request.FILES['files']
        extension = file.name.split(".")[1]
        
        if extension == "zip":
            folder = file.name.split(".")[0]
            self.fm.extract_zip(file, folder)
            
        else:
            # TODO: get filepath and validate characters in name, validate mime type and extension
            self.fm.upload_file(filedata = request.FILES['files'])

        return HttpResponse(json.dumps({
            'files': [],
            'path': request.POST.get('path'),
        }))
        
class DeleteFileView(FilemanagerMixin, View):
    def post(self, request, *args, **kwargs):
        if self.fm.delete(request.POST.get('path')):
            return HttpResponse(json.dumps({
                'success': True
            }))
            
        else:
            return HttpResponse(json.dumps({
                'success': False
            }))


class DirectoryCreateView(FilemanagerMixin, FormView):
    template_name = 'filemanager_create_directory.html'
    form_class = DirectoryCreateForm
    extra_breadcrumbs = [{
        'path': '#',
        'label': 'Create directory'
    }]

    def get_success_url(self):
        url = '%s?path=%s' % (reverse_lazy('filemanager:browser'), self.fm.path)
        if hasattr(self, 'popup') and self.popup:
            url += '&popup=1'
        return url

    def form_valid(self, form):
        self.fm.create_directory(form.cleaned_data.get('directory_name'))
        return super(DirectoryCreateView, self).form_valid(form)