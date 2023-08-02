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
from gvsigol_plugin_trip_planner.models import GTFSProvider, APPMobileConfig
'''
@author: José Badía <jbadia@scolab.es>
'''
from django.utils.translation import ugettext as _
from django import forms
import json
from . import settings


class GtfsProviderForm(forms.ModelForm):
    class Meta:
        model = GTFSProvider
        fields = ['name', 'description', 'url', 'is_active', 'last_update']

    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    url = forms.URLField(label=_('Url'), required=True, max_length=400, widget=forms.URLInput(attrs={'class' : 'form-control'}))
    is_active = forms.BooleanField(label=_('Active'), required = False)



class GtfsProviderUpdateForm(forms.ModelForm):
    class Meta:
        model = GTFSProvider
        fields = ['name', 'description', 'url', 'is_active', 'last_update']

    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    url = forms.URLField(label=_('Url'), required=True, max_length=400, widget=forms.URLInput(attrs={'class' : 'form-control'}))
    is_active = forms.BooleanField(label=_('Active'), required = False)

class GtfsCrontabForm(forms.ModelForm):
    class Meta:
        fields = ['cron_hour', 'cron_minutes']

    cron_hour = forms.CharField(label=_('Hour'), required=True, max_length=10, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    cron_minutes = forms.CharField(label=_('Minutes'), required=True, max_length=10, widget=forms.TextInput(attrs={'class' : 'form-control'}))



class APPMobileConfigUpdateForm(forms.ModelForm):
    class Meta:
        model = APPMobileConfig
        fields = ['name', 'description', 'params']

    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=1000, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    params = forms.CharField(label=_('Config'), required=False, widget=forms.HiddenInput(attrs={'class' : 'form-control'}))
