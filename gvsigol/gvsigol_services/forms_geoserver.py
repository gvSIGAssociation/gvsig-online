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
from .models import Workspace, Datastore, LayerGroup
from gvsigol.settings import SUPPORTED_ENCODINGS
from gvsigol_core import utils as core_utils
import json
from gvsigol_services.utils import get_user_layergroups
from .shp2postgis import MODE_APPEND, MODE_CREATE, MODE_OVERWRITE

supported_encodings = tuple((x,x) for x in SUPPORTED_ENCODINGS)
supported_encodings = (('autodetect', _('autodetect')),) + supported_encodings
supported_srs = tuple((x['code'],x['code']+' - '+x['title']) for x in core_utils.get_supported_crs_array())
supported_srs_and_blank = (('', '---------'),) + supported_srs

postgis_modes = ((MODE_CREATE, _('Create')),  (MODE_APPEND, _('Append')), (MODE_OVERWRITE, _('Overwrite')))
geometry_types = (('Point', _('Point')), ('MultiPoint', _('Multipoint')),
                  ('LineString', _('Line')), ('MultiLineString', _('Multiline')),
                  ('Polygon', _('Polygon')), ('MultiPolygon', _('Multipolygon')))

PRESERVE_PK = 'preserve_pk'
DO_NOT_PRESERVE_PK = 'do_not_preserve_pk'
preserve_pk_choices = ((PRESERVE_PK, _('Preserve primary key values')), (DO_NOT_PRESERVE_PK, _('Do not preserve primary key values')))

PRESERVE_TABLE_NOT_APPLIC = "not_applic"
PRESERVE_TABLE = "ow_trunc"
DO_NOT_PRESERVE_TABLE = "ow_no_trunc"

preserve_table_choices = ((PRESERVE_TABLE_NOT_APPLIC, _('Not applicable')),(PRESERVE_TABLE, _('Preserve table structure (truncate mode)')),  (DO_NOT_PRESERVE_TABLE, _('Delete and recreate table')))


time_presentation_op = (('CONTINUOUS_INTERVAL', _('continuous interval')),)
#time_presentation_op = (('CONTINUOUS_INTERVAL', _('continuous interval')), ('DISCRETE_INTERVAL', _('interval and resolution')), ('LIST', _('list')))
time_default_value_mode_op = (('MINIMUM', _('smallest domain value')), ('MAXIMUM', _('biggest domain value')), ('NEAREST', _('nearest to the reference value')), ('FIXED', _('reference value')))
#time_default_value_mode_op = (('MINIMUM', _('smallest domain value')), ('MAXIMUM', _('biggest domain value')))

class ImageMosaicUploadForm(forms.Form): 
    workspace = forms.ModelChoiceField(label=_('Workspace'), required=True, queryset=Workspace.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    #file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    file = forms.CharField(label=_('File'), required=True, max_length=500, widget=forms.TextInput(attrs={'id':'selected-file', 'readonly': 'readonly', 'class' : 'form-control'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_('Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_('Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_('Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_('Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    date_regex = forms.CharField(label=_('Date regex'), required=False, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': "(?<=_)[0-9]{8}"}))
    ele_regex = forms.CharField(label=_('Elevation regex'), required=False, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': "(?<=_)(\\d{4}\\.\\d{3})"}))   

class RasterLayerUploadForm(forms.Form):
    workspace = forms.ModelChoiceField(label=_('Workspace'), required=True, queryset=Workspace.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    #file = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    file = forms.CharField(label=_('File'), required=True, max_length=500, widget=forms.TextInput(attrs={'id':'selected-file', 'readonly': 'readonly', 'class' : 'form-control'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_('Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_('Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_('Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_('Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))

class VectorLayerUploadForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=True, queryset=Datastore.objects.all(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    file = forms.FileField(label=_('File'), required=True, widget=forms.FileInput(attrs={'accept': 'application/zip'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    #style = forms.CharField(label=_(u'Name'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_('Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_('Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_('Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_('Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))


class PostgisLayerUploadForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=True, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    file = forms.CharField(label=_('File'), required=True, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    mode = forms.ChoiceField(label=_('Mode'), required=True, choices=postgis_modes, widget=forms.Select(attrs={'class':'form-control'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    encoding = forms.ChoiceField(label=_('Encoding'), required=True, choices=supported_encodings, widget=forms.Select(attrs={'class':'form-control'}))
    srs = forms.ChoiceField(label=_('SRS'), required=True, choices=supported_srs_and_blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    preserve_pk = forms.ChoiceField(label=_('Preserve primary key'), required=True, choices=preserve_pk_choices, initial=PRESERVE_PK, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    pk_column = forms.ChoiceField(label=_('Primary key column'), required=False, choices=[], widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    truncate = forms.ChoiceField(label=_('Preserve table structure'), required=False, choices=preserve_table_choices, initial=PRESERVE_TABLE_NOT_APPLIC, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        source_columns = kwargs.pop('source_columns', [])
        if 'ogc_fid' in source_columns:
            pk_column = 'ogc_fid'
        else:
            pk_column = ''
            source_columns.insert(0, pk_column)
        pk_column_choices = [(col, col) for col in source_columns]
        super(PostgisLayerUploadForm, self).__init__(*args, **kwargs)
        if user.is_superuser:
            qs = Datastore.objects.filter(type="v_PostGIS").order_by('name')
        else:
            qs = (Datastore.objects.filter(type="v_PostGIS", created_by=user.username) |
                  Datastore.objects.filter(type="v_PostGIS", defaultuserdatastore__username=user.username)).order_by('name').distinct()
            
        self.fields["datastore"] = forms.ModelChoiceField(
            label=_('Datastore'), required=True,
            queryset=qs,
            widget=forms.Select(attrs={'class':'form-control js-example-basic-single'})
        )
        self.fields["pk_column"] = forms.ChoiceField(
            label=_('Primary key column'), required=False,
            choices = pk_column_choices,
            initial = pk_column,
            widget=forms.Select(attrs={'class':'form-control js-example-basic-single'})
        )
    
    def clean(self):
        cleaned_data = super(PostgisLayerUploadForm, self).clean()
        return cleaned_data

class CreateSqlViewForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=True, queryset=Datastore.objects.filter(type="v_PostGIS"), widget=forms.Select(attrs={'class':'form-control'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    sql_statement = forms.CharField(label=_('SQL Statement'), required=True, widget=forms.Textarea(attrs={'class' : 'form-control materialize-textarea'}))
    key_column = forms.CharField(label=_('Primary key column'), required=True, max_length=512, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    geom_column = forms.CharField(label=_('Geometry column'), required=True, max_length=512, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    geom_type = forms.ChoiceField(label=_('Geometry type'), required=True, choices=geometry_types)
    srs = forms.ChoiceField(label=_('SRS'), required=True, choices=supported_srs)
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.all(), widget=forms.Select(attrs={'class' : 'form-control'}))
    visible = forms.BooleanField(label=_('Visible'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_('Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_('Cached'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_('Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))

class CreateFeatureTypeForm(forms.Form):
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=True, queryset=Datastore.objects.none(), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    geom_type = forms.ChoiceField(label=_('Geometry type'), required=True, choices=geometry_types, widget=forms.Select(attrs={'class' : 'form-control'}))
    srs = forms.ChoiceField(label=_('SRS'), required=True, choices=supported_srs_and_blank, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, initial=1, queryset=LayerGroup.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    visible = forms.BooleanField(label=_('Visible'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    queryable = forms.BooleanField(label=_('Queryable'), required=False, initial=True, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    cached = forms.BooleanField(label=_('Cached'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    single_image = forms.BooleanField(label=_('Single image'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    allow_download = forms.BooleanField(label=_('Allow downloads'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'class' : 'form-control'}))
    fields = forms.CharField(label=_('Fields'), required=True, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    time_enabled_field = forms.CharField(label=_('Field'), required=False, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_enabled_endfield = forms.CharField(label=_('End field'), required=False, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_presentation = forms.ChoiceField(label=_('Presentation'), required=False, choices=time_presentation_op, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_resolution_year = forms.IntegerField(label=_('Resolution year'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_month = forms.IntegerField(label=_('Resolution month'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_week = forms.IntegerField(label=_('Resolution week'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_day = forms.IntegerField(label=_('Resolution day'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_hour = forms.IntegerField(label=_('Resolution hour'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_minute = forms.IntegerField(label=_('Resolution minute'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_second = forms.IntegerField(label=_('Resolution second'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_default_value_mode = forms.ChoiceField(label=_('Default mode'), required=False, choices=time_default_value_mode_op, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_default_value = forms.CharField(label=_('Default value'), required=False, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        layergroup_id = kwargs.pop('layergroup_id', None)
        super(CreateFeatureTypeForm, self).__init__(*args, **kwargs)

        if request.user.is_superuser:
            qs = Datastore.objects.filter(type="v_PostGIS").order_by('name')
            
        else:
            qs = (Datastore.objects.filter(type="v_PostGIS", created_by=request.user.username) |
                  Datastore.objects.filter(type="v_PostGIS", defaultuserdatastore__username=request.user.username)).order_by('name').distinct()
            
        qs_lg = (get_user_layergroups(request) | LayerGroup.objects.filter(name='__default__')).order_by('name').distinct()

        if layergroup_id:
            try:
                lyrgroup = LayerGroup.objects.get(id=layergroup_id)
                qs = qs.filter(workspace__server__id=lyrgroup.server_id)
                qs_lg = qs_lg.filter(id=layergroup_id)
            except:
                pass
            
        self.fields["datastore"] = forms.ModelChoiceField(
            label=_('Datastore'), required=True,
            queryset=qs,
            widget=forms.Select(attrs={'class':'form-control js-example-basic-single'})
        )
        
        self.fields["layer_group"] = forms.ModelChoiceField(
            label=_('Layer group'), required=True,
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
