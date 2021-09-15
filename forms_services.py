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
from .models import Workspace, Datastore, Layer, LayerGroup, Server, ServiceUrl
from django.utils.translation import ugettext as _
from gvsigol_services import geographic_servers
from django import forms
import string
import random
import json
from gvsigol.settings import EXTERNAL_LAYER_SUPPORTED_TYPES


external_layer_supported_types = tuple((x,x) for x in EXTERNAL_LAYER_SUPPORTED_TYPES)
layers = (('---', _('No se han podido obtener las capas')), ('1.3.0', 'version 1.3.0'))
version = (('1.1.1', _('1.1.1')), ('1.3.0', _('1.3.0')), ('1.0.0', _('1.0.0')))
blank = (('', '---------'),)
servers = (('geoserver', 'geoserver'),)

img_formats = (('image/png', 'image/png'), ('image/jpeg', 'image/jpeg'))

time_presentation_op = (
    ('CONTINUOUS_INTERVAL', _('continuous interval')),
)
#time_presentation_op = (('CONTINUOUS_INTERVAL', _('continuous interval')), ('DISCRETE_INTERVAL', _('interval and resolution')), ('LIST', _('list')))
time_default_value_mode_op = (
    ('MINIMUM', _('smallest domain value')), 
    ('MAXIMUM', _('biggest domain value')), 
    ('NEAREST', _('nearest to the reference value')), 
    ('FIXED', _('reference value'))
)
#time_default_value_mode_op = (('MINIMUM', _('smallest domain value')), ('MAXIMUM', _('biggest domain value')))
time_resolution = (
    ('second', _('seconds')),
    ('minute', _('minutes')),
    ('hour', _('hours')),
    ('day', _('days')),
    ('month', _('months')),
    ('year', _('years')),
)

supported_types = (
    ('v_PostGIS', _('PostGIS vector')),
    ('c_GeoTIFF', _('GeoTiff')),
    ('e_WMS', _('Cascading WMS')),
    ('c_ImageMosaic', _('ImageMosaic')), 
)

service_types = (
    ('WMS', 'WMS'),
    ('WMTS', 'WMTS'),
    ('WFS', 'WFS'),
    ('CSW', 'CSW'),
)

def random_id():
    return 'server_' + ''.join(random.choice(string.ascii_uppercase) for i in range(6))
    

class ServerForm(forms.Form):
    name = forms.CharField(label=_('Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1', 'readonly': 'true'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '2'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    type = forms.ChoiceField(label=_('Type'), required=False, choices=servers, widget=forms.Select(attrs={'class':'form-control', 'tabindex': '4'}))
    frontend_url = forms.CharField(label=_('Frontend URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '5'}))
    user = forms.CharField(label=_('User'), required=False, max_length=25, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '7'}))
    password = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'class' : 'form-control', 'tabindex': '8'}))
    default = forms.BooleanField(label=_('Default'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'style' : 'margin-left: 10px'}))

class WorkspaceForm(forms.Form):  
    server = forms.ModelChoiceField(label=_('Server'), required=True, queryset=Server.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'})) 
    name = forms.CharField(label=_('Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '2'}))
    uri = forms.CharField(required=True, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    wms_endpoint = forms.CharField(label=_('WMS URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '4'}))
    wfs_endpoint = forms.CharField(label=_('WFS URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '5'}))
    wcs_endpoint = forms.CharField(label=_('WCS URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '6'}))
    wmts_endpoint = forms.CharField(label=_('WMTS URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '7'}))
    cache_endpoint = forms.CharField(label=_('Cache URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '8'}))
    is_public = forms.BooleanField(label=_('Is public?'), required=False, initial=False, widget=forms.CheckboxInput(attrs={'style' : 'margin-left: 10px'}))
    
class DatastoreForm(forms.Form):
    workspace = forms.ModelChoiceField(label=_('Workspace'), required=True, queryset=Workspace.objects.all().order_by('name'), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    type = forms.ChoiceField(label=_('Type'), choices=supported_types, required=True, widget=forms.Select(attrs={'class':'form-control'}))
    file = forms.CharField(label=_('File'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))  
    name = forms.CharField(label=_('Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    connection_params = forms.CharField(label=_('Connection params'), required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))

    def __init__(self, *args, **kwargs):
        super(DatastoreForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(DatastoreForm, self).clean()
        workspace = cleaned_data.get("workspace")
        name = cleaned_data.get("name")
        connection_params = cleaned_data.get("connection_params")

        if name and workspace:
            gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
            if gs.datastore_exists(workspace.name, name):
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
    type = forms.CharField(label=_('Type'), required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))   
    description = forms.CharField(label=_('Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class':'form-control', 'tabindex': '1'}))
    connection_params = forms.CharField(label=_('Connection params'), required=True, widget=forms.Textarea(attrs={'class':'form-control connection_params', 'tabindex': '2'}))
    
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
        fields = ['datastore', 'name', 'title', 'layer_group', 'format','visible', 'queryable', 'time_enabled', 'time_enabled_endfield', 'time_resolution', 'time_presentation', 'time_default_value_mode', 'time_default_value']
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=True, queryset=Datastore.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    name = forms.CharField(label=_('Name'), required=True, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    format = forms.ChoiceField(label=_('Format'), required=False, choices=img_formats, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    #visible = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #queryable = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    time_enabled_field = forms.CharField(label=_('Field'), required=False, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_enabled_endfield = forms.CharField(label=_('End field'), required=False, widget=forms.Select(attrs={'class' : 'form-control'}))
    
    time_resolution = forms.ChoiceField(label=_('Resolution'), required=False, choices=time_resolution, widget=forms.Select(attrs={'class' : 'form-control'}))
    
    time_presentation = forms.ChoiceField(label=_('Presentation'), required=False, choices=time_presentation_op, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_resolution_year = forms.IntegerField(label=_('Resolution year'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_month = forms.IntegerField(label=_('Resolution month'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_week = forms.IntegerField(label=_('Resolution week'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_day = forms.IntegerField(label=_('Resolution day'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_hour = forms.IntegerField(label=_('Resolution hour'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_minute = forms.IntegerField(label=_('Resolution minute'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_second = forms.IntegerField(label=_('Resolution second'), required=False, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_default_value_mode = forms.ChoiceField(label=_('Default mode'), required=False, choices=time_default_value_mode_op, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_default_value = forms.DateTimeField(label=_('Default date value'), required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control datetime-input'}))
    
class LayerUpdateForm(forms.ModelForm):
    class Meta:
        model = Layer
        fields = ['datastore', 'name', 'title', 'layer_group', 'visible', 'queryable', 'time_enabled', 'time_enabled_endfield', 'time_resolution', 'time_presentation', 'time_default_value_mode', 'time_default_value']
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=True, queryset=Datastore.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single', 'readonly': 'true'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control', 'readonly': 'true'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    format = forms.ChoiceField(label=_('Format'), required=False, choices=img_formats, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    #visible = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #queryable = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    #cached = forms.BooleanField(initial=True, widget=forms.CheckboxInput(attrs={'class' : 'validate filled-in'}))
    
    time_resolution = forms.ChoiceField(label=_('Resolution'), required=False, choices=time_resolution, widget=forms.Select(attrs={'class' : 'form-control'}))
  
    time_enabled_field = forms.ChoiceField(label=_('Field'), required=False, choices=blank, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_enabled_endfield = forms.ChoiceField(label=_('End field'), required=False, choices=blank, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_presentation = forms.ChoiceField(label=_('Presentation'), required=False, choices=time_presentation_op, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_resolution_year = forms.CharField(label=_('Resolution year'), required=False, max_length=4, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_month = forms.CharField(label=_('Resolution month'), required=False, max_length=2, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_week = forms.CharField(label=_('Resolution week'), required=False, max_length=2, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_day = forms.CharField(label=_('Resolution day'), required=False, max_length=2, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_hour = forms.CharField(label=_('Resolution hour'), required=False, max_length=2, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_minute = forms.CharField(label=_('Resolution minute'), required=False, max_length=2, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_resolution_second = forms.CharField(label=_('Resolution second'), required=False, max_length=2, widget=forms.NumberInput(attrs={'class' : 'form-control time_resolution_field', 'min': 0}))
    time_default_value_mode = forms.ChoiceField(label=_('Default mode'), required=False, choices=time_default_value_mode_op, widget=forms.Select(attrs={'class' : 'form-control'}))
    time_default_value = forms.DateTimeField(label=_('Default date value'), required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control datetime-input'}))
    
class LayerUploadTypeForm(forms.ModelForm):
    class Meta:
        model = Datastore
        fields = ['type']
    type = forms.ModelChoiceField(required=True, queryset=Workspace.objects.all())

class ExternalLayerForm(forms.ModelForm):
    class Meta:
        model = Layer
        fields = ['title', 'layer_group', 'type', 'version', 'url', 'layers', 'format', 'key']
        
    #name = forms.CharField(label=_(u'Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    
    type = forms.ChoiceField(label=_('Type'), choices=external_layer_supported_types, required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
    version = forms.ChoiceField(label=_('Version'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control'}))
   
    url = forms.CharField(label=_('URL'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    layers = forms.ChoiceField(label=_('Layers'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))

    format = forms.ChoiceField(label=_('Format'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    infoformat = forms.ChoiceField(label=_('Featureinfo format'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    matrixset = forms.ChoiceField(label=_('Matrixset'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    key = forms.CharField(label=_('Apikey'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
 
class ServiceUrlForm(forms.ModelForm):
    class Meta:
        model = ServiceUrl
        fields = ['title', 'type', 'url']
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
    type = forms.ChoiceField(label=_('Type'), required=False, choices=service_types, widget=forms.Select(attrs={'class':'form-control', 'tabindex': '2'}))
    url = forms.CharField(label=_('URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))   
