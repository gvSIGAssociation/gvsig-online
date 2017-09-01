# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
@author: César Martinez <cmartinez@scolab.es>
'''
from models import Workspace, Datastore, Layer, LayerGroup
from gvsigol_core.models import BaseLayer
from django.utils.translation import ugettext as _
from backend_mapservice import backend
from django import forms
import json
from gvsigol.settings import BASELAYER_SUPPORTED_TYPES


supported_types = tuple((x,x) for x in BASELAYER_SUPPORTED_TYPES)
layers = (('---', _('No se han podido obtener las capas')), ('1.3.0', 'version 1.3.0'))
version = (('1.1.1', _('version 1.1.1')), ('1.3.0', _('version 1.3.0')), ('1.0.0', _('version 1.0.0')))
blank = (('', '---------'),)

class WorkspaceForm(forms.Form):   
    name = forms.CharField(label=_(u'Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
    description = forms.CharField(label=_(u'Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '2'}))
    uri = forms.CharField(required=True, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    wms_endpoint = forms.CharField(label=_(u'WMS URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '4'}))
    wfs_endpoint = forms.CharField(label=_(u'WFS URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '5'}))
    wcs_endpoint = forms.CharField(label=_(u'WCS URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '6'}))
    cache_endpoint = forms.CharField(label=_(u'Cache URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '7'}))
    is_public = forms.BooleanField(label=_(u'Is public?'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'style' : 'margin-left: 10px'}))
    
class DatastoreForm(forms.Form):
    workspace = forms.ModelChoiceField(label=_(u'Workspace'), required=True, queryset=Workspace.objects.all().order_by('name'), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    type = forms.ChoiceField(label=_(u'Type'), choices=backend.getSupportedTypes(), required=True, widget=forms.Select(attrs={'class':'form-control'}))
    file = forms.CharField(label=_(u'File'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))  
    name = forms.CharField(label=_(u'Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    description = forms.CharField(label=_(u'Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    connection_params = forms.CharField(label=_(u'Connection params'), required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))

    def __init__(self, *args, **kwargs):
        super(DatastoreForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(DatastoreForm, self).clean()
        workspace = cleaned_data.get("workspace")
        name = cleaned_data.get("name")
        connection_params = cleaned_data.get("connection_params")

        if name and workspace:
            if backend.datastore_exists(workspace.name, name):
                self.add_error('name', _("Datastore already exists")) 
        
        if connection_params:
            try:
                json.loads(connection_params) 
            except:
                self.add_error('connection_params', _("Error: Invalid JSON format"))
        return cleaned_data

class DatastoreUpdateForm(forms.ModelForm):
    class Meta:
        model = Datastore
        fields = ['type', 'name', 'description', 'connection_params']
    type = forms.CharField(label=_(u'Type'), required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))   
    description = forms.CharField(label=_(u'Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class':'form-control', 'tabindex': '1'}))
    connection_params = forms.CharField(label=_(u'Connection params'), required=True, widget=forms.Textarea(attrs={'class':'form-control', 'tabindex': '2'}))
    
    def clean(self):
        cleaned_data = super(DatastoreUpdateForm, self).clean()
        connection_params = cleaned_data.get("connection_params") 
        
        if connection_params:
            try:
                cleaned_data['connection_params_json'] = json.loads(connection_params) 
            except:
                self.add_error('connection_params', _("Error: Invalid JSON format"))
        return cleaned_data


class LayerForm(forms.ModelForm):
    class Meta:
        model = Layer
        fields = ['datastore', 'name', 'title', 'layer_group', 'visible', 'queryable']
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    name = forms.CharField(label=_(u'Name'), required=True, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    #visible = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #queryable = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    
class LayerUpdateForm(forms.ModelForm):
    class Meta:
        model = Layer
        fields = ['datastore', 'name', 'title', 'layer_group', 'visible', 'queryable']
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single', 'readonly': 'true'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control', 'readonly': 'true'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    #visible = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #queryable = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #cached = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
 
class LayerUploadTypeForm(forms.ModelForm):
    class Meta:
        model = Datastore
        fields = ['type']
    type = forms.ModelChoiceField(required=True, queryset=Workspace.objects.all())

class BaseLayerForm(forms.ModelForm):
    class Meta:
        model = BaseLayer
        fields = ['name', 'title', 'type', 'version', 'url', 'layers', 'format', 'key']
        
    name = forms.CharField(label=_(u'Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    
    type = forms.ChoiceField(label=_(u'Type'), choices=supported_types, required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
    version = forms.ChoiceField(label=_(u'Version'), required=False, choices=version, widget=forms.Select(attrs={'class':'form-control'}))
   
    url = forms.CharField(label=_(u'URL'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    layers = forms.CharField(label=_(u'Layers'), required=False, disabled=False,  max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'list':'id_layer_list'}))

    format = forms.CharField(label=_(u'Format'), required=False, disabled=False, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'list':'id_format_list'}))
    key = forms.CharField(label=_(u'Apikey'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    
