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
import json

from django import forms
from django.utils.translation import gettext_lazy as _

from django.utils import timezone

from gvsigol_plugin_trip_planner import gtfs_files
from gvsigol_plugin_trip_planner.models import GTFSProvider, APPMobileConfig


class GtfsProviderForm(forms.ModelForm):
    class Meta:
        model = GTFSProvider
        fields = ['name', 'description', 'source_type', 'url', 'is_active']

    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control'}))
    source_type = forms.ChoiceField(label=_('Source'), choices=GTFSProvider.SOURCE_CHOICES, initial=GTFSProvider.SOURCE_URL, widget=forms.RadioSelect)
    url = forms.URLField(label=_('Url'), required=False, max_length=400, widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}))
    gtfs_file = forms.FileField(label=_('GTFS file'), required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.zip,application/zip'}))
    is_active = forms.BooleanField(label=_('Active'), required=False)

    def clean_gtfs_file(self):
        f = self.cleaned_data.get('gtfs_file')
        if f:
            if not f.name.lower().endswith('.zip'):
                raise forms.ValidationError(_('The GTFS file must be a .zip file.'))
            try:
                gtfs_files.validate_gtfs_zip(f)
            except ValueError as e:
                raise forms.ValidationError(str(e))
        return f

    def clean(self):
        cleaned = super().clean()
        source = cleaned.get('source_type')
        if source == GTFSProvider.SOURCE_URL:
            if not cleaned.get('url') and 'url' not in self.errors:
                self.add_error('url', _('The URL is required for a downloaded feed.'))
        elif source == GTFSProvider.SOURCE_FILE:
            has_file = self.instance.pk and gtfs_files.has_source(self.instance.pk)
            if not cleaned.get('gtfs_file') and not has_file and 'gtfs_file' not in self.errors:
                self.add_error('gtfs_file', _('Upload a GTFS .zip file.'))
            cleaned['url'] = ''
        return cleaned

    def save(self, commit=True):
        type_changed = bool(self.instance.pk) and 'source_type' in self.changed_data
        provider = super().save(commit=commit)
        if commit and type_changed:
            # the previous source (download or upload) no longer applies
            gtfs_files.delete_source(provider.pk)
        f = self.cleaned_data.get('gtfs_file')
        if commit and f and provider.is_file:
            gtfs_files.save_uploaded(provider.pk, f)
            provider.last_update = timezone.now()
            provider.save(update_fields=['last_update'])
        return provider


# Kept as an alias for backwards compatibility.
GtfsProviderUpdateForm = GtfsProviderForm


class APPMobileConfigUpdateForm(forms.ModelForm):
    class Meta:
        model = APPMobileConfig
        fields = ['name', 'description', 'params']

    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control'}))
    params = forms.CharField(label=_('Config'), required=False, widget=forms.HiddenInput(attrs={'class': 'form-control'}))

    def clean_params(self):
        params = self.cleaned_data.get('params')
        if not params:
            return params
        try:
            value = json.loads(params)
        except ValueError:
            raise forms.ValidationError(_('Invalid JSON configuration'))
        if not isinstance(value, dict):
            raise forms.ValidationError(_('Invalid JSON configuration'))
        return params
