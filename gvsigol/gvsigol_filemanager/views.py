import json

from django.views.generic import TemplateView, FormView
from django.views.generic.base import View
from django.shortcuts import HttpResponse
from django.http import HttpResponseBadRequest
from django.core.urlresolvers import reverse_lazy
from gvsigol.settings import FILEMANAGER_DIRECTORY
from forms import DirectoryCreateForm
from core import Filemanager


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
        context['files'] = self.fm.directory_list()

        return context


class DetailView(FilemanagerMixin, TemplateView):
    template_name = 'browser/filemanager_detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)

        context['file'] = self.fm.file_details()

        return context


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

        # TODO: get filepath and validate characters in name, validate mime type and extension
        filename = self.fm.upload_file(filedata = request.FILES['files'])

        return HttpResponse(json.dumps({
            'files': [{'name': filename}],
            'path': request.POST.get('path'),
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
