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
@author: José Badía <jbadia@scolab.es>
'''
from gvsigol_services.models import Workspace, Datastore
from models import Provider
from django.utils.translation import ugettext as _
from django import forms
import json
import settings


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['type', 'workspace', 'datastore', 'resource', 'params']
    
    type = forms.ChoiceField(label=_(u'Type'), choices=settings.GEOCODING_SUPPORTED_TYPES, required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
   
    workspace = forms.ModelChoiceField(label=_(u'Workspace'), required=False, queryset=Workspace.objects.all(), widget=forms.Select(attrs={'class' : 'form-control'}))
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
    resource = forms.ModelChoiceField(label=_(u'Resource'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))

    id_field = forms.ModelChoiceField(label=_(u'Id'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
    text_field = forms.ModelChoiceField(label=_(u'Text'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
    geom_field = forms.ModelChoiceField(label=_(u'Geom'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))

    category = forms.CharField(label=_(u'Category'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    
    params = forms.CharField(label=_(u'Parameters'), required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))


class ProviderUpdateForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['type', 'workspace', 'datastore', 'resource', 'params']
        
    type = forms.ChoiceField(label=_(u'Type'), choices=settings.GEOCODING_SUPPORTED_TYPES, disabled=True, required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
       
    workspace = forms.CharField(label=_(u'Workspace'), disabled=True, required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))  
    datastore = forms.CharField(label=_(u'Datastore'), disabled=True, required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))  
    resource = forms.ModelChoiceField(label=_(u'Resource'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))

    id_field = forms.ModelChoiceField(label=_(u'Id'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
    text_field = forms.ModelChoiceField(label=_(u'Text'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
    geom_field = forms.ModelChoiceField(label=_(u'Geom'), required=False, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class' : 'form-control'}))
 
    category = forms.CharField(label=_(u'Category'),  required=True, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    
    params = forms.CharField(label=_(u'Parameters'), required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))

    