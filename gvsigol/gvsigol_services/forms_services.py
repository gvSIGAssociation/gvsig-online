# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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
from django.utils.translation import ugettext as _
from backend_mapservice import backend
from django import forms
import json

class WorkspaceForm(forms.Form):   
    name = forms.CharField(required=True, max_length=250, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
    description = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '2'}))
    uri = forms.CharField(required=True, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    wms_endpoint = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '4'}))
    wfs_endpoint = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '5'}))
    wcs_endpoint = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '6'}))
    cache_endpoint = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '7'}))

class DatastoreForm(forms.Form):
    workspace = forms.ModelChoiceField(required=True, queryset=Workspace.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    type = forms.ChoiceField(choices=backend.getSupportedTypes(), required=True, widget=forms.Select(attrs={'class':'form-control'}))  
    name = forms.CharField(required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    description = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    connection_params = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))

    def __init__(self, session, *args, **kwargs):
        self.session = session
        super(DatastoreForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(DatastoreForm, self).clean()
        workspace = cleaned_data.get("workspace")
        name = cleaned_data.get("name")
        connection_params = cleaned_data.get("connection_params")

        if name and workspace:
            if backend.datastore_exists(workspace.name, name, self.session):
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
    type = forms.CharField(required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))
    name = forms.CharField(required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))   
    description = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class':'form-control', 'tabindex': '1'}))
    connection_params = forms.CharField(required=True, widget=forms.Textarea(attrs={'class':'form-control', 'tabindex': '2'}))
    
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
    datastore = forms.ModelChoiceField(required=True, queryset=Datastore.objects.all(), widget=forms.Select(attrs={'class' : 'form-control'}))
    name = forms.CharField(required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
    title = forms.CharField(required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'form-control'}))
    #visible = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #queryable = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))

class LayerUpdateForm(forms.ModelForm):
    class Meta:
        model = Layer
        fields = ['datastore', 'name', 'title', 'layer_group', 'visible', 'queryable']
    datastore = forms.ModelChoiceField(required=True, queryset=Datastore.objects.all(), widget=forms.Select(attrs={'class' : 'validate', 'readonly': 'true'}))
    name = forms.CharField(required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'validate', 'readonly': 'true'}))
    title = forms.CharField(required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    layer_group = forms.ModelChoiceField(required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'validate'}))
    #visible = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #queryable = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #cached = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))

class LayerUploadTypeForm(forms.ModelForm):
    class Meta:
        model = Datastore
        fields = ['type']
    type = forms.ModelChoiceField(required=True, queryset=Workspace.objects.all())
