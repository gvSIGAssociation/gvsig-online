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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from django import forms
from django.utils.translation import ugettext as _
from models import Workspace, Datastore, LayerGroup
from gvsigol.settings import SUPPORTED_ENCODINGS
from gvsigol_core import utils as core_utils
import json

supported_encodings = tuple((x,x) for x in SUPPORTED_ENCODINGS)
supported_encodings = supported_encodings + (('autodetect', _('autodetect')),)
supported_srs = tuple((x['code'],x['code']+' - '+x['title']) for x in core_utils.get_supported_crs_array())
supported_srs_and_blank = (('', '---------'),) + supported_srs

MODE_CREATE="CR"
MODE_APPEND="AP"
MODE_OVERWRITE="OW"
postgis_modes = ((MODE_CREATE, _('Create')),  (MODE_APPEND, _('Append')), (MODE_OVERWRITE, _('Overwrite')))
geometry_types = (('Point', _('Point')), ('MultiPoint', _('Multipoint')),
                  ('LineString', _('Line')), ('MultiLineString', _('Multiline')),
                  ('Polygon', _('Polygon')), ('MultiPolygon', _('Multipolygon')))

class ImageMosaicUploadForm(forms.Form): 
    workspace = forms.ModelChoiceField(label=_(u'Workspace'), required=True, queryset=Workspace.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    #file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    file = forms.CharField(label=_(u'File'), required=True, max_length=500, widget=forms.TextInput(attrs={'id':'selected-file', 'readonly': 'readonly', 'class' : 'form-control'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    date_regex = forms.CharField(label=_(u'Date regex'), required=False, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': "(?<=_)[0-9]{8}"}))
    ele_regex = forms.CharField(label=_(u'Elevation regex'), required=False, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': "(?<=_)(\\d{4}\\.\\d{3})"}))   

class RasterLayerUploadForm(forms.Form):
    workspace = forms.ModelChoiceField(label=_(u'Workspace'), required=True, queryset=Workspace.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    #file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    file = forms.CharField(label=_(u'File'), required=True, max_length=500, widget=forms.TextInput(attrs={'id':'selected-file', 'readonly': 'readonly', 'class' : 'form-control'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))

class VectorLayerUploadForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))


class PostgisLayerUploadForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    #file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    file = forms.CharField(label=_(u'File'), required=True, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    mode = forms.ChoiceField(label=_(u'Mode'), required=True, choices=postgis_modes, widget=forms.Select(attrs={'class':'form-control'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'form-control'}))
    encoding = forms.ChoiceField(label=_(u'Encoding'), required=True, choices=supported_encodings, widget=forms.Select(attrs={'class':'form-control'}))
    srs = forms.ChoiceField(label=_(u'SRS'), required=True, choices=supported_srs_and_blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    #visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    #queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    #cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    #single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        super(PostgisLayerUploadForm, self).__init__(*args, **kwargs)
        if user.is_superuser:
            qs = Datastore.objects.all().order_by('name')
        else:
            qs = Datastore.objects.filter(type="v_PostGIS").filter(created_by__exact=user.username).order_by('name')
            
        self.fields["datastore"] = forms.ModelChoiceField(
            label=_(u'Datastore'), required=True,
            queryset=qs,
            widget=forms.Select(attrs={'class':'form-control js-example-basic-single'})
        )
    
    def clean(self):
        cleaned_data = super(PostgisLayerUploadForm, self).clean()
        return cleaned_data

class CreateSqlViewForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.filter(type="v_PostGIS"), widget=forms.Select(attrs={'class':'form-control'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    sql_statement = forms.CharField(label=_(u'SQL Statement'), required=True, widget=forms.Textarea(attrs={'class' : 'form-control materialize-textarea'}))
    key_column = forms.CharField(label=_(u'Primary key column'), required=True, max_length=512, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    geom_column = forms.CharField(label=_(u'Geometry column'), required=True, max_length=512, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    geom_type = forms.ChoiceField(label=_(u'Geometry type'), required=True, choices=geometry_types)
    srs = forms.ChoiceField(label=_(u'SRS'), required=True, choices=supported_srs)
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'form-control'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))

class CreateFeatureTypeForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    geom_type = forms.ChoiceField(label=_(u'Geometry type'), required=True, choices=geometry_types, widget=forms.Select(attrs={'class' : 'form-control'}))
    srs = forms.ChoiceField(label=_(u'SRS'), required=True, choices=supported_srs_and_blank, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_(u'Layer group'), required=True, initial=1, queryset=LayerGroup.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_(u'Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_(u'Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_(u'Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_(u'Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    fields = forms.CharField(label=_(u'Fields'), required=True, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        super(CreateFeatureTypeForm, self).__init__(*args, **kwargs)
        if user.is_superuser:
            qs = Datastore.objects.all().order_by('name')
            qs_lg = LayerGroup.objects.all().order_by('name')
            
        else:
            qs = Datastore.objects.filter(type="v_PostGIS").filter(created_by__exact=user.username).order_by('name')
            qs_lg = LayerGroup.objects.filter(created_by__exact=user.username).order_by('name')
            
        self.fields["datastore"] = forms.ModelChoiceField(
            label=_(u'Datastore'), required=True,
            queryset=qs,
            widget=forms.Select(attrs={'class':'form-control js-example-basic-single'})
        )
        
        self.fields["layer_group"] = forms.ModelChoiceField(
            label=_(u'Layer group'), required=True,
            queryset=qs_lg,
            widget=forms.Select(attrs={'class':'form-control js-example-basic-single'})
        )

    def clean(self):
        cleaned_data = super(CreateFeatureTypeForm, self).clean()
        fields = cleaned_data.get("fields")
        
        if fields:
            try:
                cleaned_data['fields'] = json.loads(fields)
            except:
                self.add_error('connection_params', _("Error: Invalid field definition"))
        return cleaned_data
