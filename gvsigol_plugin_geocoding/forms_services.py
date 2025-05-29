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
@author: José Badía <jbadia@scolab.es>
'''
from gvsigol_services.models import Workspace, Datastore
from .models import Provider
from django.utils.translation import ugettext as _
from django import forms
import json
from . import settings
from gvsigol_core.models import Project


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['type', 'workspace', 'datastore', 'resource', 'params', 'projects']
    
    type = forms.ChoiceField(label=_('Type'), choices=settings.GEOCODING_SUPPORTED_TYPES, required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
   
    workspace = forms.ModelChoiceField(label=_('Workspace'), required=False, queryset=Workspace.objects.all(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    resource = forms.ModelChoiceField(label=_('Resource'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))

    id_field = forms.ModelChoiceField(label=_('Id'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    text_field = forms.ModelChoiceField(label=_('Text'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    geom_field = forms.ModelChoiceField(label=_('Geom'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))

    category = forms.CharField(label=_('Category'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    
    params = forms.CharField(label=_('Parameters'), required=False, disabled=False, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))

    candidates_url = forms.CharField(label=_('Candidates URL'), required=False, max_length=1024, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    find_url = forms.CharField(label=_('Find URL'), required=False, max_length=1024, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    reverse_url = forms.CharField(label=_('Reverse URL'), required=False, max_length=1024, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    max_results = forms.CharField(label=_('Limit'), required=False, max_length=3, widget=forms.TextInput(attrs={'class' : 'form-control'}))

    projects = forms.ChoiceField(
        label=_('Projects'),
        choices=[(p.id, f"{p.name} - {p.description}") for p in Project.objects.all()],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class ProviderUpdateForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['type', 'workspace', 'datastore', 'resource', 'params', 'projects']
        
    type = forms.ChoiceField(label=_('Type'), choices=settings.GEOCODING_SUPPORTED_TYPES, disabled=True, required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
       
    workspace = forms.CharField(label=_('Workspace'), disabled=True, required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))  
    datastore = forms.CharField(label=_('Datastore'), disabled=True, required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))  
    resource = forms.ModelChoiceField(label=_('Resource'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))

    id_field = forms.ModelChoiceField(label=_('Id'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
    text_field = forms.ModelChoiceField(label=_('Text'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
    geom_field = forms.ModelChoiceField(label=_('Geom'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
 
    category = forms.CharField(label=_('Category'),  required=True, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    
    params = forms.CharField(label=_('Parameters'), required=True, disabled=False, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))

    candidates_url = forms.CharField(label=_('Candidates URL'), required=False, max_length=1024, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    find_url = forms.CharField(label=_('Find URL'), required=False, max_length=1024, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    reverse_url = forms.CharField(label=_('Reverse URL'), required=False, max_length=1024, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    max_results = forms.CharField(label=_('Limit'), required=False, max_length=3, widget=forms.TextInput(attrs={'class' : 'form-control'}))

    projects = forms.ChoiceField(
        label=_('Projects'),
        choices=[(p.id, f"{p.name} - {p.description}") for p in Project.objects.all()],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    