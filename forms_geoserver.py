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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from django import forms
from django.utils.translation import ugettext as _
from models import Workspace, Datastore, LayerGroup
from gvsigol.settings import SUPPORTED_ENCODINGS, SUPPORTED_CRS
import json

supported_encodings = tuple((x,x) for x in SUPPORTED_ENCODINGS)
supported_encodings = supported_encodings + (('autodetect', _('autodetect')),)
supported_srs = tuple((SUPPORTED_CRS[x]['code'],SUPPORTED_CRS[x]['title']) for x in SUPPORTED_CRS)
supported_srs_and_blank = (('', '---------'),) + supported_srs

MODE_CREATE="CR"
MODE_APPEND="AP"
MODE_OVERWRITE="OW"
postgis_modes = ((MODE_CREATE, _('Create')),  (MODE_APPEND, _('Append')), (MODE_OVERWRITE, _('Overwrite')))
geometry_types = (('Point', _('Point')), ('MultiPoint', _('Multipoint')),
                  ('LineString', _('Line')), ('MultiLineString', _('Multiline')),
                  ('Polygon', _('Polygon')), ('MultiPolygon', _('Multipolygon')))

class ImageMosaicUploadForm(forms.Form): 
    workspace = forms.ModelChoiceField(label=_(u'Workspace'), required=True, queryset=Workspace.objects.all())
    file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'validate'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select())
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    date_regex = forms.CharField(label=_(u'Date regex'), required=False, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate', 'placeholder': "(?<=_)[0-9]{8}"}))
    ele_regex = forms.CharField(label=_(u'Elevation regex'), required=False, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate', 'placeholder': "(?<=_)(\\d{4}\\.\\d{3})"}))   

class RasterLayerUploadForm(forms.Form):
    workspace = forms.ModelChoiceField(label=_(u'Workspace'), required=True, queryset=Workspace.objects.all())
    file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'validate'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select())
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))

class VectorLayerUploadForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.all(), widget=forms.Select())
    file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'validate'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'validate'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))


class PostgisLayerUploadForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.filter(type="v_PostGIS"), widget=forms.Select())
    file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    mode = forms.ChoiceField(label=_(u'Mode'), required=True, choices=postgis_modes)
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'validate'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'validate'}))
    encoding = forms.ChoiceField(label=_(u'Encoding'), required=True, choices=supported_encodings)
    srs = forms.ChoiceField(label=_(u'SRS'), required=True, choices=supported_srs_and_blank)
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))

class CreateSqlViewForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.filter(type="v_PostGIS"), widget=forms.Select())
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'validate'}))
    sql_statement = forms.CharField(label=_(u'SQL Statement'), required=True, widget=forms.Textarea(attrs={'class' : 'validate materialize-textarea'}))
    key_column = forms.CharField(label=_(u'Primary key column'), required=True, max_length=512, widget=forms.TextInput(attrs={'class' : 'validate'}))
    geom_column = forms.CharField(label=_(u'Geometry column'), required=True, max_length=512, widget=forms.TextInput(attrs={'class' : 'validate'}))
    geom_type = forms.ChoiceField(label=_(u'Geometry type'), required=True, choices=geometry_types)
    srs = forms.ChoiceField(label=_(u'SRS'), required=True, choices=supported_srs)
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'validate'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))

class CreateFeatureTypeForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.filter(type="v_PostGIS"), widget=forms.Select())
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'validate'}))
    geom_type = forms.ChoiceField(label=_(u'Geometry type'), required=True, choices=geometry_types)
    srs = forms.ChoiceField(label=_(u'SRS'), required=True, choices=supported_srs)
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'validate'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'validate'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    fields = forms.CharField(label=_(u'Fields'), required=True, widget=forms.TextInput(attrs={'class' : 'validate'}))


    def clean(self):
        cleaned_data = super(CreateFeatureTypeForm, self).clean()
        fields = cleaned_data.get("fields")
        
        if fields:
            try:
                cleaned_data['fields'] = json.loads(fields)
            except:
                self.add_error('connection_params', _("Error: Invalid field definition"))
        return cleaned_data
