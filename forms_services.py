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
from xml.dom import ValidationErr
from .models import Workspace, Datastore, Layer, LayerGroup, Server, ServiceUrl, SqlView, Connection, ConnectionRole
from django.utils.translation import ugettext as _, ugettext_lazy
from gvsigol_services import geographic_servers
from django import forms
from django.db import models as db_models
import string
import random
import json
from django.conf import settings as django_settings
from gvsigol.settings import EXTERNAL_LAYER_SUPPORTED_TYPES
from django.core.exceptions import ValidationError
from gvsigol_services.utils import get_user_layergroups, can_manage_layergroup
from gvsigol_core import utils as core_utils


EXTERNAL_LAYER_LABELS = {
    'MVT': 'Vector tiles (MVT)'
}

external_layer_supported_types = tuple(
    (x, EXTERNAL_LAYER_LABELS.get(x, x)) for x in EXTERNAL_LAYER_SUPPORTED_TYPES
)
layers = (('---', _('No se han podido obtener las capas')), ('1.3.0', 'version 1.3.0'))
version = (('1.1.1', _('1.1.1')), ('1.3.0', _('1.3.0')), ('1.0.0', _('1.0.0')))
blank = (('', '---------'),)
servers = (('geoserver', 'geoserver'),)

supported_srs = tuple((x['code'],x['code']+' - '+x['title']) for x in core_utils.get_supported_crs_array())
supported_srs_with_other = supported_srs + (('__other__', ugettext_lazy('Other')),)

if getattr(django_settings, 'SUPPORTED_FORMATS_CHOICES', None):
    img_formats = django_settings.SUPPORTED_FORMATS_CHOICES
else:
    img_formats = (('image/png', 'image/png'), ('image/jpeg', 'image/jpeg'), ('vector-tiles', 'vector tiles'))

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
    """
    Formulario para crear almacenes de datos.
    - Para v_PostGIS: SIEMPRE requiere seleccionar una conexión centralizada existente
    - Para otros tipos (GeoTIFF, WMS, ImageMosaic): usa connection_params directamente
    """
    workspace = forms.ModelChoiceField(label=_('Workspace'), required=True, queryset=Workspace.objects.all().order_by('name'), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    type = forms.ChoiceField(label=_('Type'), choices=supported_types, required=True, widget=forms.Select(attrs={'class':'form-control'}))
    file = forms.CharField(label=_('File'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    
    # connection_params: solo para tipos que NO son v_PostGIS (GeoTIFF, WMS, ImageMosaic)
    connection_params = forms.CharField(label=_('Connection params'), required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))
    
    # Campos para v_PostGIS: OBLIGATORIOS para este tipo
    connection = forms.ModelChoiceField(
        label=_('Connection'),
        required=False,
        queryset=Connection.objects.filter(type='PostGIS').order_by('name'),
        widget=forms.Select(attrs={'class': 'form-control js-example-basic-single', 'id': 'id_connection'}),
        empty_label='---------'
    )
    schema = forms.CharField(
        label=_('Schema'),
        required=False,
        max_length=150,
        widget=forms.Select(attrs={
            'class': 'form-control', 
            'id': 'id_schema'
        }),
        help_text=_('Select an existing schema or type a new name to create it')
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(DatastoreForm, self).__init__(*args, **kwargs)
        
        # Filtrar conexiones según permisos del usuario
        if user:
            if user.is_superuser:
                self.fields['connection'].queryset = Connection.objects.filter(
                    type='PostGIS'
                ).order_by('name')
            else:
                # Usuario staff puede usar conexiones para crear datastores si:
                # 1. allow_all_datastore está activado (permiso global)
                # 2. Las creó él mismo
                # 3. Tienen un ConnectionRole con alguno de sus roles con can_use_datastore=True
                # 4. Tienen un ConnectionRole con su username con can_use_datastore=True (migración automática)
                # 5. Tienen datastores que él creó (para compatibilidad con migración)
                from gvsigol_auth import auth_backend
                user_roles = auth_backend.get_roles(user)
                # Incluir el username del usuario en la lista de roles para buscar
                all_user_roles = list(user_roles) + [user.username]
                # Obtener IDs de conexiones donde el rol tiene permiso de datastore
                role_connection_ids = ConnectionRole.objects.filter(
                    role__in=all_user_roles,
                    can_use_datastore=True
                ).values_list('connection_id', flat=True)
                self.fields['connection'].queryset = Connection.objects.filter(
                    type='PostGIS'
                ).filter(
                    db_models.Q(allow_all_datastore=True) |
                    db_models.Q(created_by=user.username) |
                    db_models.Q(id__in=role_connection_ids) |
                    db_models.Q(datastores__created_by=user.username)  # Conexiones con datastores creados por este usuario
                ).distinct().order_by('name')

    def clean(self):
        cleaned_data = super(DatastoreForm, self).clean()
        workspace = cleaned_data.get("workspace")
        name = cleaned_data.get("name")
        ds_type = cleaned_data.get("type")
        connection = cleaned_data.get("connection")
        schema = cleaned_data.get("schema")
        connection_params = cleaned_data.get("connection_params")

        if name and workspace:
            gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
            if gs.datastore_exists(workspace.name, name):
                self.add_error('name', _("Datastore already exists"))

        # Validación según tipo de almacén
        if ds_type == 'v_PostGIS':
            # PostGIS: SIEMPRE requiere conexión centralizada y esquema
            if not connection:
                self.add_error('connection', _("Please select a connection"))
            if not schema:
                self.add_error('schema', _("Please select a schema"))
        else:
            # Otros tipos (GeoTIFF, WMS, ImageMosaic): requiere connection_params
            if connection_params:
                try:
                    json.loads(connection_params)
                except:
                    self.add_error('connection_params', _("Error: Invalid JSON format"))
        
        return cleaned_data

class DatastoreUpdateForm(forms.ModelForm):
    """
    Formulario para actualizar almacenes de datos.
    - Si legacy_mode=False: muestra la conexión (solo lectura) y permite editar descripción
    - Si legacy_mode=True: muestra connection_params editables (flujo antiguo)
    """
    class Meta:
        model = Datastore
        fields = ['type', 'name', 'description', 'connection_params']
    
    type = forms.CharField(label=_('Type'), required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'}))
    description = forms.CharField(label=_('Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class':'form-control', 'tabindex': '1'}))
    connection_params = forms.CharField(label=_('Connection params'), required=False, widget=forms.Textarea(attrs={'class':'form-control connection_params', 'tabindex': '2'}))
    
    # Campos informativos para datastores que usan conexión (solo lectura)
    connection_name = forms.CharField(
        label=_('Connection'), 
        required=False, 
        widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'})
    )
    schema_name = forms.CharField(
        label=_('Schema'), 
        required=False, 
        widget=forms.TextInput(attrs={'class':'form-control', 'readonly': 'true'})
    )

    def __init__(self, *args, **kwargs):
        super(DatastoreUpdateForm, self).__init__(*args, **kwargs)
        
        # Si hay una instancia, determinar si usa conexión o es legacy
        if self.instance and self.instance.pk:
            if not self.instance.legacy_mode and self.instance.connection:
                # Modo conexión: rellenar campos informativos
                self.fields['connection_name'].initial = self.instance.connection.name
                self.fields['schema_name'].initial = self.instance.schema or 'public'
                # connection_params no es requerido en este modo
                self.fields['connection_params'].required = False
            else:
                # Modo legacy: connection_params es requerido
                self.fields['connection_params'].required = True

    def clean(self):
        cleaned_data = super(DatastoreUpdateForm, self).clean()
        connection_params = cleaned_data.get("connection_params")

        # Solo validar connection_params si es modo legacy
        if self.instance and self.instance.legacy_mode:
            if connection_params:
                try:
                    cleaned_data['connection_params_json'] = json.loads(connection_params)
                except:
                    self.add_error('connection_params', _("Error: Invalid JSON format"))
            else:
                self.add_error('connection_params', _("Connection params are required"))
        
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
    datastore = forms.CharField(label=_('Datastore'), required=True, max_length=200, widget=forms.TextInput(attrs={'class' : 'form-control', 'readonly': 'true'}))
    name = forms.CharField(label=_('Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control', 'readonly': 'true'}))
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=None, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
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

    def __init__(self, request, *args, **kwargs):
        layergroup_id = kwargs.pop('layergroup_id')
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        if instance and not can_manage_layergroup(request, instance.layer_group):
            self.fields['layer_group'].widget = forms.Select(attrs={'class' : 'form-control js-example-basic-single', 'readonly': 'true', 'disabled': 'true'})
            self.fields['layer_group'].queryset = LayerGroup.objects.filter(id=instance.layer_group_id)
            return
        if request.user.is_superuser:
            self.fields['layer_group'].queryset = LayerGroup.objects.all().order_by('name')
        else:
            self.fields['layer_group'].queryset = (get_user_layergroups(request) | LayerGroup.objects.filter(name='__default__')).order_by('name').distinct()
        if layergroup_id and LayerGroup.objects.filter(id=layergroup_id).exists():
            lyrgroup_field = self.fields['layer_group']
            lyrgroup_field.widget = forms.Select(attrs={'class' : 'form-control js-example-basic-single', 'readonly': 'true', 'disabled': 'true'})
            lyrgroup_field.queryset = lyrgroup_field.queryset.filter(id=layergroup_id)

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
    layer_group = forms.ModelChoiceField(label=_('Layer group'), required=True, queryset=LayerGroup.objects.none(), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))

    type = forms.ChoiceField(label=_('Type'), choices=external_layer_supported_types, required=True, widget=forms.Select(attrs={'class' : 'form-control'}))
    version = forms.ChoiceField(label=_('Version'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control'}))

    url = forms.CharField(label=_('URL'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    layers = forms.ChoiceField(label=_('Layers'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))

    format = forms.ChoiceField(label=_('Format'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    infoformat = forms.ChoiceField(label=_('Featureinfo format'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    matrixset = forms.ChoiceField(label=_('Matrixset'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    tilematrix = forms.ChoiceField(label=_('Tilematrix'), required=False, choices=blank, widget=forms.Select(attrs={'class':'form-control  js-example-basic-single'}))
    key = forms.CharField(label=_('Apikey'), required=False, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    
    style_url = forms.CharField(label=_('Mapbox style URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/style.json'}))
    style_file = forms.FileField(label=_('Or upload your Mapbox style (.json)'), required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.json'}))
    
    srs = forms.ChoiceField(label=_('SRS'), required=True, choices=supported_srs_with_other, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    custom_srs = forms.CharField(label=_('Custom SRS'), required=False, max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EPSG:XXXX'}))

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['layer_group'].queryset = get_user_layergroups(request).order_by('name').distinct()

class ServiceUrlForm(forms.ModelForm):
    class Meta:
        model = ServiceUrl
        fields = ['title', 'type', 'url']
    title = forms.CharField(label=_('Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
    type = forms.ChoiceField(label=_('Type'), required=False, choices=service_types, widget=forms.Select(attrs={'class':'form-control', 'tabindex': '2'}))
    url = forms.CharField(label=_('URL'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))


class SqlViewForm(forms.ModelForm):
    class Meta:
        model = SqlView
        fields = ['datastore', 'name', 'from_tables', 'fields']
    datastore = forms.ModelChoiceField(label=_('Datastore'), required=True, queryset=None, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    name = forms.CharField(label=_('Name'), required=True, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    from_tables = forms.CharField(label=_('Tables'), required=True, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    fields = forms.CharField(label=_('Fields'), required=True, widget=forms.TextInput(attrs={'class' : 'form-control'}))

    def clean_from_tables(self):
        from_tables = json.loads(self.cleaned_data.get('from_tables', []))
        if len(from_tables) == 0:
            raise ValidationError(ugettext_lazy('At least one table must be selected'), code='from_table')

        table_aliases = []
        for idx, table in enumerate(from_tables, start=1):
            alias = table.get('alias')
            if not table.get('name') or not alias \
                or not table.get('datastore_id') \
                or not table.get('datastore_name'):
                raise ValidationError(ugettext_lazy('Invalid table definition'), code='from_table')
            join_field = table.get('join_field')
            if idx > 1:
                join_field1 = table.get('join_field1')
                if not join_field1 or not join_field1.get('name'):
                    raise ValidationError(ugettext_lazy('Invalid table definition. Join field 1 is missing'), code='from_table_join_field1')
                join_field2 = table.get('join_field2')
                if not join_field2 or not join_field2.get('name'):
                    raise ValidationError(ugettext_lazy('Invalid table definition. Join field 2 is missing'), code='from_table_join_field2')
            if alias in table_aliases:
                raise ValidationError(ugettext_lazy('Duplicated alias'), code='from_table_alias')
            table_aliases.append(alias)
        return from_tables

    def clean_fields(self):
        fields = json.loads(self.cleaned_data.get('fields', []))
        if len(fields) == 0:
            raise ValidationError(ugettext_lazy('At least one field must be selected'), code='view_fields')
        field_aliases = []
        for field in fields:
            if not field.get('name') or not field.get('alias') or not field.get('table_alias'):
                raise ValidationError(ugettext_lazy('Invalid field definition'), code='view_fields')
            if field.get('alias') in field_aliases:
                raise ValidationError(ugettext_lazy('Duplicated alias'), code='view_field_alias')
            field_aliases.append(field.get('alias'))
        return fields

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user.is_superuser:
            self.fields['datastore'].queryset = Datastore.objects.filter(type__startswith='v_').order_by('name')
        else:
            self.fields['datastore'].queryset = (Datastore.objects.filter( type__startswith='v_', created_by=user.username) |
                  Datastore.objects.filter( type__startswith='v_', defaultuserdatastore__username=user.username)).order_by('name').distinct()


# ============================================================================
# Connection Forms
# ============================================================================

# Categorías de conexión (primer desplegable)
connection_categories = (
    ('database', 'Base de datos'),
    ('api', 'API externa'),
)

# Tipos de bases de datos (segundo desplegable cuando category=database)
database_connection_types = (
    ('PostGIS', 'PostgreSQL/PostGIS'),
    ('Oracle', 'Oracle'),
    ('SQLServer', 'SQL Server'),
)

# Tipos de APIs externas (segundo desplegable cuando category=api)
api_connection_types = (
    ('indenova', 'InDenova'),
    ('segex', 'SEGEX'),
    ('sharepoint', 'SharePoint'),
    ('padron-atm', 'Padrón ATM'),
)

# Todos los tipos combinados
connection_types = database_connection_types + api_connection_types

# Listas para validación
DATABASE_TYPE_LIST = ('PostGIS', 'Oracle', 'SQLServer')
API_TYPE_LIST = ('indenova', 'segex', 'sharepoint', 'padron-atm')

class ConnectionForm(forms.ModelForm):
    """
    Formulario para crear conexiones.
    Soporta dos categorías: bases de datos y APIs externas.
    Los campos dinámicos se muestran/ocultan según la selección.
    """
    class Meta:
        model = Connection
        fields = ['name', 'description', 'type']
    
    # Campos básicos
    name = forms.CharField(
        label=_('Name'), 
        required=True, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '1'})
    )
    description = forms.CharField(
        label=_('Description'), 
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '2', 'rows': '3'})
    )
    
    # Primer desplegable: categoría (database o api)
    category = forms.ChoiceField(
        label=_('Category'), 
        choices=[('', '---')] + list(connection_categories), 
        required=True, 
        widget=forms.Select(attrs={'class': 'form-control', 'tabindex': '3', 'id': 'id_category'})
    )
    
    # Segundo desplegable: tipo específico (se rellena dinámicamente según categoría)
    type = forms.ChoiceField(
        label=_('Type'), 
        choices=[('', '---')] + list(connection_types), 
        required=True, 
        widget=forms.Select(attrs={'class': 'form-control', 'tabindex': '4', 'id': 'id_type'})
    )
    
    # ==================== CAMPOS PARA POSTGRESQL/POSTGIS ====================
    host = forms.CharField(
        label=_('Host'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field', 'tabindex': '5'})
    )
    port = forms.CharField(
        label=_('Port'), 
        required=False, 
        max_length=10, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field', 'tabindex': '6'})
    )
    database = forms.CharField(
        label=_('Database'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field', 'tabindex': '7'})
    )
    user = forms.CharField(
        label=_('User'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field', 'tabindex': '8'})
    )
    password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control db-postgis-field', 'tabindex': '9'})
    )
    extra_params = forms.CharField(
        label=_('Additional parameters (JSON)'), 
        required=False, 
        widget=forms.Textarea(attrs={
            'class': 'form-control db-postgis-field', 
            'tabindex': '10', 
            'rows': '3',
            'placeholder': '{"dbtype": "postgis", "jndiReferenceName": ""}'
        }),
        help_text=_('Optional parameters in JSON format')
    )
    
    # ==================== CAMPOS PARA ORACLE ====================
    oracle_user = forms.CharField(
        label=_('User name'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-oracle-field'})
    )
    oracle_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control db-oracle-field'})
    )
    # DSN dividido en componentes para facilitar la entrada
    oracle_host = forms.CharField(
        label=_('Host'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control db-oracle-field',
            'placeholder': 'oract-scan.ejemplo.es'
        })
    )
    oracle_port = forms.CharField(
        label=_('Port'), 
        required=False, 
        max_length=10, 
        initial='1521',
        widget=forms.TextInput(attrs={
            'class': 'form-control db-oracle-field',
            'placeholder': '1521'
        })
    )
    oracle_service = forms.CharField(
        label=_('Service name'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control db-oracle-field',
            'placeholder': 'servicio.ejemplo.es'
        })
    )
    
    # ==================== CAMPOS PARA SQL SERVER ====================
    sqlserver_server = forms.CharField(
        label=_('Server'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-sqlserver-field'})
    )
    sqlserver_user = forms.CharField(
        label=_('User name'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-sqlserver-field'})
    )
    sqlserver_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control db-sqlserver-field'})
    )
    sqlserver_database = forms.CharField(
        label=_('Database'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-sqlserver-field'})
    )
    sqlserver_tds_version = forms.ChoiceField(
        label=_('TDS Version'), 
        required=False, 
        choices=[
            ('4.2', '4.2'), ('5.0', '5.0'), ('7.0', '7.0'), 
            ('7.1', '7.1'), ('7.2', '7.2'), ('7.3', '7.3'), 
            ('7.4', '7.4'), ('8.0', '8.0')
        ],
        initial='7.0',
        widget=forms.Select(attrs={'class': 'form-control db-sqlserver-field'})
    )
    
    # ==================== CAMPOS PARA INDENOVA ====================
    indenova_domain = forms.CharField(
        label=_('Domain'), 
        required=False, 
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control api-indenova-field'})
    )
    indenova_api_key = forms.CharField(
        label=_('API Key'), 
        required=False, 
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control api-indenova-field'})
    )
    indenova_client_id = forms.CharField(
        label=_('Client ID'), 
        required=False, 
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control api-indenova-field'})
    )
    indenova_secret = forms.CharField(
        label=_('Secret'), 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control api-indenova-field'})
    )
    
    # ==================== CAMPOS PARA SEGEX ====================
    segex_domain = forms.ChoiceField(
        label=_('Domain'), 
        required=False, 
        choices=[
            ('PRO', 'https://sedipualba.es/apisegex/ (Producción)'),
            ('PRE', 'https://pre.sedipualba.es/apisegex/ (Preproducción)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control api-segex-field'})
    )
    segex_entity = forms.CharField(
        label=_('Entity'), 
        required=False, 
        max_length=250,
        widget=forms.TextInput(attrs={'class': 'form-control api-segex-field'}),
        help_text=_('Entity code from SEDIPUALB@')
    )
    segex_user = forms.CharField(
        label=_('User (wsSegUser)'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control api-segex-field'})
    )
    segex_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control api-segex-field'})
    )
    
    # ==================== CAMPOS PARA SHAREPOINT ====================
    sharepoint_tenant_id = forms.CharField(
        label=_('Tenant ID'), 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
        })
    )
    sharepoint_client_id = forms.CharField(
        label=_('Client ID'), 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
        })
    )
    sharepoint_client_secret = forms.CharField(
        label=_('Client Secret'), 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control api-sharepoint-field'})
    )
    sharepoint_host = forms.CharField(
        label=_('SharePoint Host'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': 'example.sharepoint.com'
        })
    )
    sharepoint_site_path = forms.CharField(
        label=_('Site Path'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': '/sites/MySite'
        })
    )
    
    # ==================== CAMPOS PARA PADRÓN ATM ====================
    padron_atm_email = forms.EmailField(
        label=_('E-mail'), 
        required=False, 
        widget=forms.EmailInput(attrs={'class': 'form-control api-padron-atm-field'})
    )
    padron_atm_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control api-padron-atm-field'})
    )
    padron_atm_id_acceso = forms.CharField(
        label=_('Id Acceso'), 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control api-padron-atm-field'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-rellenar con valores por defecto de la BBDD de la aplicación
        if not self.data:  # Solo si no hay datos POST
            default_params = Connection.get_default_db_params()
            self.fields['host'].initial = default_params.get('host', 'localhost')
            self.fields['port'].initial = default_params.get('port', '5432')
            self.fields['database'].initial = default_params.get('database', '')
            self.fields['user'].initial = default_params.get('user', '')
            self.fields['extra_params'].initial = '{"dbtype": "postgis", "jndiReferenceName": ""}'

    def clean_extra_params(self):
        """Valida que extra_params sea un JSON válido."""
        extra_params = self.cleaned_data.get('extra_params', '')
        if extra_params:
            try:
                json.loads(extra_params)
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON format'))
        return extra_params

    def clean(self):
        cleaned_data = super().clean()
        conn_type = cleaned_data.get('type')
        
        # Validar campos requeridos según el tipo de conexión
        if conn_type == 'PostGIS':
            required = {'host': _('Host'), 'port': _('Port'), 'database': _('Database'), 'user': _('User')}
            for field, label in required.items():
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required'))
        
        elif conn_type == 'Oracle':
            required = {'oracle_user': _('User'), 'oracle_host': _('Host'), 
                       'oracle_port': _('Port'), 'oracle_service': _('Service name')}
            for field, label in required.items():
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required'))
        
        elif conn_type == 'SQLServer':
            required = {'sqlserver_server': _('Server'), 'sqlserver_user': _('User'), 
                       'sqlserver_database': _('Database')}
            for field, label in required.items():
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required'))
        
        elif conn_type == 'indenova':
            required = {'indenova_domain': _('Domain'), 'indenova_api_key': _('API Key'),
                       'indenova_client_id': _('Client ID'), 'indenova_secret': _('Secret')}
            for field, label in required.items():
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required'))
        
        elif conn_type == 'segex':
            required = {'segex_user': _('User'), 'segex_password': _('Password')}
            for field, label in required.items():
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required'))
        
        elif conn_type == 'sharepoint':
            required = {'sharepoint_tenant_id': _('Tenant ID'), 'sharepoint_client_id': _('Client ID'),
                       'sharepoint_client_secret': _('Client Secret'), 'sharepoint_host': _('Host')}
            for field, label in required.items():
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required'))
        
        elif conn_type == 'padron-atm':
            required = {'padron_atm_email': _('E-mail'), 'padron_atm_password': _('Password'),
                       'padron_atm_id_acceso': _('Id Acceso')}
            for field, label in required.items():
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required'))
        
        return cleaned_data

    def get_connection_params(self):
        """Construye el JSON de parámetros de conexión según el tipo."""
        conn_type = self.cleaned_data.get('type')
        
        if conn_type == 'PostGIS':
            return json.dumps({
                'host': self.cleaned_data.get('host', ''),
                'port': self.cleaned_data.get('port', ''),
                'database': self.cleaned_data.get('database', ''),
                'user': self.cleaned_data.get('user', ''),
                'passwd': self.cleaned_data.get('password', ''),
            })
        
        elif conn_type == 'Oracle':
            # Componer DSN desde host:port/service
            oracle_host = self.cleaned_data.get('oracle_host', '')
            oracle_port = self.cleaned_data.get('oracle_port', '1521')
            oracle_service = self.cleaned_data.get('oracle_service', '')
            dsn = f"{oracle_host}:{oracle_port}/{oracle_service}"
            # Usar 'username' como en el ETL original
            return json.dumps({
                'username': self.cleaned_data.get('oracle_user', ''),
                'password': self.cleaned_data.get('oracle_password', ''),
                'dsn': dsn,
            })
        
        elif conn_type == 'SQLServer':
            # Usar nombres con guiones como en el ETL original
            return json.dumps({
                'server-sql-server': self.cleaned_data.get('sqlserver_server', ''),
                'username-sql-server': self.cleaned_data.get('sqlserver_user', ''),
                'password-sql-server': self.cleaned_data.get('sqlserver_password', ''),
                'db-sql-server': self.cleaned_data.get('sqlserver_database', ''),
                'tds-version-sql-server': self.cleaned_data.get('sqlserver_tds_version', '7.0'),
            })
        
        elif conn_type == 'indenova':
            # Usar nombres con guiones como en el ETL original
            return json.dumps({
                'domain': self.cleaned_data.get('indenova_domain', ''),
                'api-key': self.cleaned_data.get('indenova_api_key', ''),
                'client-id': self.cleaned_data.get('indenova_client_id', ''),
                'secret': self.cleaned_data.get('indenova_secret', ''),
            })
        
        elif conn_type == 'segex':
            entity = self.cleaned_data.get('segex_entity', '')
            return json.dumps({
                'domain': self.cleaned_data.get('segex_domain', 'PRO'),
                'entity': entity,
                # Mantener compatibilidad con ETL que espera entities-list como array [codigo, descripcion]
                'entities-list': [entity, entity] if entity else [],
                'user': self.cleaned_data.get('segex_user', ''),
                'password': self.cleaned_data.get('segex_password', ''),
            })
        
        elif conn_type == 'sharepoint':
            # Usar nombres con guiones como en el ETL original
            return json.dumps({
                'tenant-id': self.cleaned_data.get('sharepoint_tenant_id', ''),
                'client-id': self.cleaned_data.get('sharepoint_client_id', ''),
                'client-secret': self.cleaned_data.get('sharepoint_client_secret', ''),
                'sharepoint-host': self.cleaned_data.get('sharepoint_host', ''),
                'site-path': self.cleaned_data.get('sharepoint_site_path', ''),
            })
        
        elif conn_type == 'padron-atm':
            return json.dumps({
                'email': self.cleaned_data.get('padron_atm_email', ''),
                'password': self.cleaned_data.get('padron_atm_password', ''),
                'idacceso': self.cleaned_data.get('padron_atm_id_acceso', ''),
            })
        
        return '{}'

    def get_extra_params(self):
        """Devuelve los parámetros extra como string JSON (o None si vacío)."""
        conn_type = self.cleaned_data.get('type')
        # Solo PostGIS usa extra_params
        if conn_type == 'PostGIS':
            extra = self.cleaned_data.get('extra_params', '')
            return extra if extra else None
        return None


class ConnectionUpdateForm(forms.ModelForm):
    """
    Formulario para actualizar conexiones existentes.
    El tipo no se puede cambiar, pero los parámetros sí.
    """
    class Meta:
        model = Connection
        fields = ['name', 'description', 'type']
    
    # Campos básicos
    name = forms.CharField(
        label=_('Name'), 
        required=True, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'true'})
    )
    description = forms.CharField(
        label=_('Description'), 
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '3'})
    )
    type = forms.ChoiceField(
        label=_('Type'), 
        choices=connection_types, 
        required=True, 
        widget=forms.Select(attrs={'class': 'form-control', 'disabled': 'true'})
    )
    
    # ==================== CAMPOS PARA POSTGRESQL/POSTGIS ====================
    host = forms.CharField(
        label=_('Host'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field'})
    )
    port = forms.CharField(
        label=_('Port'), 
        required=False, 
        max_length=10, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field'})
    )
    database = forms.CharField(
        label=_('Database'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field'})
    )
    user = forms.CharField(
        label=_('User'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-postgis-field'})
    )
    password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control db-postgis-field', 
            'placeholder': _('Leave empty to keep current password')
        })
    )
    extra_params = forms.CharField(
        label=_('Additional parameters (JSON)'), 
        required=False, 
        widget=forms.Textarea(attrs={
            'class': 'form-control db-postgis-field', 
            'rows': '3',
            'placeholder': '{"dbtype": "postgis", "jndiReferenceName": ""}'
        }),
        help_text=_('Optional parameters in JSON format')
    )
    
    # ==================== CAMPOS PARA ORACLE ====================
    oracle_user = forms.CharField(
        label=_('User name'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-oracle-field'})
    )
    oracle_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control db-oracle-field',
            'placeholder': _('Leave empty to keep current password')
        })
    )
    # DSN dividido en componentes
    oracle_host = forms.CharField(
        label=_('Host'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control db-oracle-field',
            'placeholder': 'oract-scan.ejemplo.es'
        })
    )
    oracle_port = forms.CharField(
        label=_('Port'), 
        required=False, 
        max_length=10, 
        widget=forms.TextInput(attrs={
            'class': 'form-control db-oracle-field',
            'placeholder': '1521'
        })
    )
    oracle_service = forms.CharField(
        label=_('Service name'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control db-oracle-field',
            'placeholder': 'servicio.ejemplo.es'
        })
    )
    
    # ==================== CAMPOS PARA SQL SERVER ====================
    sqlserver_server = forms.CharField(
        label=_('Server'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-sqlserver-field'})
    )
    sqlserver_user = forms.CharField(
        label=_('User name'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-sqlserver-field'})
    )
    sqlserver_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control db-sqlserver-field',
            'placeholder': _('Leave empty to keep current password')
        })
    )
    sqlserver_database = forms.CharField(
        label=_('Database'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control db-sqlserver-field'})
    )
    sqlserver_tds_version = forms.ChoiceField(
        label=_('TDS Version'), 
        required=False, 
        choices=[
            ('4.2', '4.2'), ('5.0', '5.0'), ('7.0', '7.0'), 
            ('7.1', '7.1'), ('7.2', '7.2'), ('7.3', '7.3'), 
            ('7.4', '7.4'), ('8.0', '8.0')
        ],
        initial='7.0',
        widget=forms.Select(attrs={'class': 'form-control db-sqlserver-field'})
    )
    
    # ==================== CAMPOS PARA INDENOVA ====================
    indenova_domain = forms.CharField(
        label=_('Domain'), 
        required=False, 
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control api-indenova-field'})
    )
    indenova_api_key = forms.CharField(
        label=_('API Key'), 
        required=False, 
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control api-indenova-field'})
    )
    indenova_client_id = forms.CharField(
        label=_('Client ID'), 
        required=False, 
        max_length=500, 
        widget=forms.TextInput(attrs={'class': 'form-control api-indenova-field'})
    )
    indenova_secret = forms.CharField(
        label=_('Secret'), 
        required=False, 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control api-indenova-field',
            'placeholder': _('Leave empty to keep current secret')
        })
    )
    
    # ==================== CAMPOS PARA SEGEX ====================
    segex_domain = forms.ChoiceField(
        label=_('Domain'), 
        required=False, 
        choices=[
            ('PRO', 'https://sedipualba.es/apisegex/ (Producción)'),
            ('PRE', 'https://pre.sedipualba.es/apisegex/ (Preproducción)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control api-segex-field'})
    )
    segex_entity = forms.CharField(
        label=_('Entity'), 
        required=False, 
        max_length=250,
        widget=forms.TextInput(attrs={'class': 'form-control api-segex-field'}),
        help_text=_('Entity code from SEDIPUALB@')
    )
    segex_user = forms.CharField(
        label=_('User (wsSegUser)'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={'class': 'form-control api-segex-field'})
    )
    segex_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control api-segex-field',
            'placeholder': _('Leave empty to keep current password')
        })
    )
    
    # ==================== CAMPOS PARA SHAREPOINT ====================
    sharepoint_tenant_id = forms.CharField(
        label=_('Tenant ID'), 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
        })
    )
    sharepoint_client_id = forms.CharField(
        label=_('Client ID'), 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
        })
    )
    sharepoint_client_secret = forms.CharField(
        label=_('Client Secret'), 
        required=False, 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': _('Leave empty to keep current secret')
        })
    )
    sharepoint_host = forms.CharField(
        label=_('SharePoint Host'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': 'example.sharepoint.com'
        })
    )
    sharepoint_site_path = forms.CharField(
        label=_('Site Path'), 
        required=False, 
        max_length=250, 
        widget=forms.TextInput(attrs={
            'class': 'form-control api-sharepoint-field',
            'placeholder': '/sites/MySite'
        })
    )
    
    # ==================== CAMPOS PARA PADRÓN ATM ====================
    padron_atm_email = forms.EmailField(
        label=_('E-mail'), 
        required=False, 
        widget=forms.EmailInput(attrs={'class': 'form-control api-padron-atm-field'})
    )
    padron_atm_password = forms.CharField(
        label=_('Password'), 
        required=False, 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control api-padron-atm-field',
            'placeholder': _('Leave empty to keep current password')
        })
    )
    padron_atm_id_acceso = forms.CharField(
        label=_('Id Acceso'), 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control api-padron-atm-field'})
    )

    def clean_extra_params(self):
        """Valida que extra_params sea un JSON válido."""
        extra_params = self.cleaned_data.get('extra_params', '')
        if extra_params:
            try:
                json.loads(extra_params)
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON format'))
        return extra_params

    def get_connection_params(self, current_params=None):
        """Construye el JSON de parámetros de conexión, preservando contraseñas si no se proporciona una nueva."""
        conn_type = self.cleaned_data.get('type')
        
        if conn_type == 'PostGIS':
            password = self.cleaned_data.get('password', '')
            if not password and current_params:
                password = current_params.get('passwd', current_params.get('password', ''))
            return json.dumps({
                'host': self.cleaned_data.get('host', ''),
                'port': self.cleaned_data.get('port', ''),
                'database': self.cleaned_data.get('database', ''),
                'user': self.cleaned_data.get('user', ''),
                'passwd': password,
            })
        
        elif conn_type == 'Oracle':
            password = self.cleaned_data.get('oracle_password', '')
            if not password and current_params:
                password = current_params.get('password', '')
            # Componer DSN desde host:port/service
            oracle_host = self.cleaned_data.get('oracle_host', '')
            oracle_port = self.cleaned_data.get('oracle_port', '1521')
            oracle_service = self.cleaned_data.get('oracle_service', '')
            dsn = f"{oracle_host}:{oracle_port}/{oracle_service}"
            # Usar 'username' como en el ETL original
            return json.dumps({
                'username': self.cleaned_data.get('oracle_user', ''),
                'password': password,
                'dsn': dsn,
            })
        
        elif conn_type == 'SQLServer':
            password = self.cleaned_data.get('sqlserver_password', '')
            if not password and current_params:
                password = current_params.get('password-sql-server', current_params.get('password', ''))
            # Usar nombres con guiones como en el ETL original
            return json.dumps({
                'server-sql-server': self.cleaned_data.get('sqlserver_server', ''),
                'username-sql-server': self.cleaned_data.get('sqlserver_user', ''),
                'password-sql-server': password,
                'db-sql-server': self.cleaned_data.get('sqlserver_database', ''),
                'tds-version-sql-server': self.cleaned_data.get('sqlserver_tds_version', '7.0'),
            })
        
        elif conn_type == 'indenova':
            secret = self.cleaned_data.get('indenova_secret', '')
            if not secret and current_params:
                secret = current_params.get('secret', '')
            # Usar nombres con guiones como en el ETL original
            return json.dumps({
                'domain': self.cleaned_data.get('indenova_domain', ''),
                'api-key': self.cleaned_data.get('indenova_api_key', ''),
                'client-id': self.cleaned_data.get('indenova_client_id', ''),
                'secret': secret,
            })
        
        elif conn_type == 'segex':
            password = self.cleaned_data.get('segex_password', '')
            if not password and current_params:
                password = current_params.get('password', '')
            entity = self.cleaned_data.get('segex_entity', '')
            return json.dumps({
                'domain': self.cleaned_data.get('segex_domain', 'PRO'),
                'entity': entity,
                # Mantener compatibilidad con ETL que espera entities-list como array [codigo, descripcion]
                'entities-list': [entity, entity] if entity else [],
                'user': self.cleaned_data.get('segex_user', ''),
                'password': password,
            })
        
        elif conn_type == 'sharepoint':
            secret = self.cleaned_data.get('sharepoint_client_secret', '')
            if not secret and current_params:
                secret = current_params.get('client-secret', current_params.get('client_secret', ''))
            # Usar nombres con guiones como en el ETL original
            return json.dumps({
                'tenant-id': self.cleaned_data.get('sharepoint_tenant_id', ''),
                'client-id': self.cleaned_data.get('sharepoint_client_id', ''),
                'client-secret': secret,
                'sharepoint-host': self.cleaned_data.get('sharepoint_host', ''),
                'site-path': self.cleaned_data.get('sharepoint_site_path', ''),
            })
        
        elif conn_type == 'padron-atm':
            password = self.cleaned_data.get('padron_atm_password', '')
            if not password and current_params:
                password = current_params.get('password', '')
            return json.dumps({
                'email': self.cleaned_data.get('padron_atm_email', ''),
                'password': password,
                'idacceso': self.cleaned_data.get('padron_atm_id_acceso', ''),
            })
        
        return '{}'

    def get_extra_params(self):
        """Devuelve los parámetros extra como string JSON (o None si vacío)."""
        conn_type = self.cleaned_data.get('type')
        if conn_type == 'PostGIS':
            extra = self.cleaned_data.get('extra_params', '')
            return extra if extra else None
        return None