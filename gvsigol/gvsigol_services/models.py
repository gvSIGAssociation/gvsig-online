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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from gvsigol.basetypes import CloneConf
import logging
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from .backend_postgis import Introspect
import os
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, ugettext
from gvsigol_services.triggers import CUSTOM_PROCEDURES
from django.utils.crypto import get_random_string
from gvsigol import settings
from django.db import models
from gvsigol_auth.models import UserGroup
import ast
import json

LOG_NAME = 'gvsigol'


class Server(models.Model):
    TYPE_CHOICES = (
        ('geoserver', 'geoserver'),
        ('mapserver', 'mapserver')
    )
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, default='geoserver')
    frontend_url = models.CharField(max_length=500)
    user = models.CharField(max_length=25)
    password = models.CharField(max_length=100)
    default = models.BooleanField(default=False)
    authz_service_conf = JSONField(default=None, null=True)

    def _get_relative_url(self, url):
        if url.startswith(settings.BASE_URL + '/'):
            return url[len(settings.BASE_URL):]
        return url

    def getWmsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        if workspace:
            return base_url + "/" + workspace + "/wms"
        return base_url + "/wms"

    def getWfsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        if workspace:
            return base_url + "/" + workspace + "/wfs"
        return base_url + "/wfs"

    def getWcsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        if workspace:
            return base_url + "/" + workspace + "/wcs"
        return base_url + "/wcs"

    def getWmtsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        return base_url + "/gwc/service/wmts"

    def getCacheEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        return base_url + "/gwc/service/wms"

    def getGWCRestEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        return base_url + "/gwc/rest"

    def __str__(self):
        return self.title_name

    @property
    def title_name(self):
        return "{title} [{name}]".format(title=self.title, name=self.name)


class Node(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    status = models.CharField(max_length=25)
    url = models.CharField(max_length=500)
    is_master = models.BooleanField(default=False)

    def getUrl(self):
        return self.url


def get_default_server():
    # note: using only() to avoid errors applying Server migrations on new deploys
    theServer = Server.objects.filter(default=True).only('id').first()
    return theServer.id


class Workspace(models.Model):
    server = models.ForeignKey(
        Server, default=get_default_server, on_delete=models.CASCADE)
    name = models.CharField(max_length=250, unique=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    uri = models.CharField(max_length=500)
    wms_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wfs_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wcs_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wmts_endpoint = models.CharField(max_length=500, null=True, blank=True)
    cache_endpoint = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Datastore(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    type = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500, null=True, blank=True)
    connection_params = models.TextField()
    created_by = models.CharField(max_length=100)

    def __str__(self):
        return self.workspace.name + ":" + self.name

    def get_schema_name(self):
        try:
            params = json.loads(self.connection_params)
            return params.get('schema', 'public')
        except:
            return 'public'

    def get_db_connection(self):
        params = json.loads(self.connection_params)
        host = params['host']
        port = params['port']
        dbname = params['database']
        user = params['user']
        passwd = params['passwd']
        i = Introspect(database=dbname, host=host,
                       port=port, user=user, password=passwd)
        return i, params


class DefaultUserDatastore(models.Model):
    username = models.TextField(unique=True)
    datastore = models.ForeignKey(Datastore, on_delete=models.CASCADE)


class LayerGroup(models.Model):
    server_id = models.IntegerField(null=True, default=get_default_server)
    name = models.CharField(max_length=150)
    title = models.CharField(max_length=500, null=True, blank=True)
    visible = models.BooleanField(default=False)
    cached = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def clone(self, target_datastore=None, clone_conf=None):
        if not clone_conf:
            clone_conf = CloneConf()
        old_id = self.pk
        old_name = self.name
        new_name = target_datastore.workspace.name + "_" + self.name
        i = 1
        salt = ''
        while LayerGroup.objects.filter(name=new_name, server_id=target_datastore.workspace.server.id).exists():
            new_name = new_name + '_' + str(i) + salt
            i = i + 1
            if (i % 1000) == 0:
                salt = '_' + get_random_string(3)
        self.pk = None
        self.name = new_name
        self.save()

        new_instance = LayerGroup.objects.get(id=self.pk)
        new_instance._cloned_from_name = old_name
        new_instance._cloned_from_instance = LayerGroup.objects.get(id=old_id)
        new_instance._cloned_lyr_instance_map = {}
        new_instance._cloned_lyr_name_map = {}
        if clone_conf.recursive:
            for lyr in new_instance._cloned_from_instance.layer_set.all():
                new_lyr = lyr.clone(target_datastore=target_datastore,
                                    layer_group=new_instance, clone_conf=clone_conf)
                try:
                    new_instance._cloned_lyr_instance_map[new_lyr._cloned_from_instance] = new_lyr
                    new_instance._cloned_lyr_name_map[new_lyr._cloned_from_name] = new_lyr.name
                except AttributeError:
                    pass  # raster layers are not cloned and can be safely ignored
                except:
                    logging.getLogger(LOG_NAME).exception(
                        f"Error cloning layer: {new_lyr.id} - {new_lyr.name}")
        return new_instance


def get_default_layer_thumbnail():
    return settings.STATIC_URL + 'img/no_thumbnail.jpg'


def as_dict(in_list, key):
    return {obj[key]: obj for obj in in_list}


class LayerConfig:
    def __init__(self, layer):
        self.layer = layer
        self._conf = None
        self._field_info_dict = None
        self._field_conf_dict = None
        self._control_fields_dict = None
        self._field_info = None
        self._geometry_columns = None
        self._pks = None

    def __query_db_fields(self):
        i, tablename, dsname = self.layer.get_db_connection()
        self._field_info = i.get_fields_info(tablename, dsname)
        self._geometry_columns = i.get_geometry_columns(tablename, dsname)
        self._pks = i.get_pk_columns(tablename, dsname)
        i.close()

    @property
    def conf(self):
        if self._conf is None:
            try:
                self._conf = ast.literal_eval(self.layer.conf)
            except:
                self._conf = {}
        return self._conf

    @conf.setter
    def conf(self, new_conf):
        self.layer.conf = new_conf
        self._conf = new_conf

    @property
    def field_info(self):
        if self._field_info is None:
            self.__query_db_fields()
        return self._field_info

    @property
    def geometry_columns(self):
        if self._geometry_columns is None:
            self.__query_db_fields()
        return self._geometry_columns

    @property
    def pks(self):
        if self._pks is None:
            self.__query_db_fields()
        return self._pks

    @property
    def field_info_dict(self):
        if self._field_info_dict is None:
            self._field_info_dict = as_dict(self._field_info, 'name')
        return self._field_info_dict

    @property
    def field_conf_dict(self):
        if self._field_conf_dict is None:
            self._field_conf_dict = as_dict(
                self.conf.get('fields', []), 'name')
        return self._field_conf_dict

    @property
    def control_fields_dict(self):
        if self._control_fields_dict is None:
            self._control_fields_dict = as_dict(
                settings.CONTROL_FIELDS, 'name')
        return self._control_fields_dict

    def init_field_conf(self, field_conf, field_info):
        field_conf['name'] = field_conf.get('name', field_info['name'])
        for id, language in settings.LANGUAGES:
            field_conf['title-' +
                       id] = field_conf.get('title-'+id, field_info['name'])
        field_conf['visible'] = field_conf.get('visible', True)
        if field_conf['name'] in self.pks:
            field_conf['editable'] = field_conf.get('editable', False)
            field_conf['editableactive'] = True
        elif field_conf.get('editable', True) and \
                Trigger.objects.filter(layer=self.layer, field=field_conf['name']).exists():
            field_conf['editable'] = False
            field_conf['editableactive'] = False
        else:
            field_conf['editable'] = field_conf.get('editable', True)
            field_conf['editableactive'] = True
        field_conf['infovisible'] = field_conf.get('infovisible', True)
        field_conf['nullable'] = (field_info.get('nullable') != 'NO')
        if not field_conf['nullable']:
            field_conf['mandatory'] = True
        else:
            field_conf['mandatory'] = field_conf.get('mandatory', False)

        if field_conf['name'] in self.control_fields_dict:
            control_field = self.control_fields_dict.get(field_conf['name'])
            field_conf['editableactive'] = control_field.get(
                'editableactive', False)
            field_conf['editable'] = control_field.get('editable', False)
            field_conf['visible'] = control_field.get(
                'visible', field_conf['visible'])
            field_conf['infovisible'] = control_field.get(
                'visible', field_conf['infovisible'])
            field_conf['nullable'] = control_field.get(
                'nullable', field_conf['nullable'])
            field_conf['mandatory'] = control_field.get(
                'mandatory', field_conf['mandatory'])

        field_conf['gvsigol_type'] = field_conf.get('gvsigol_type', '')  
        field_conf['type_params'] = field_conf.get('type_params', {})    

        if field_conf.get('gvsigol_type') == 'link':
            field_conf['editableactive'] = True
            field_conf['editable'] = False

        return field_conf

    def get_field_conf(self, include_pks=False):
        return self.conf.get('fields', [])

    def get_updated_field_conf(self, include_pks=False):
        fields = []
        for the_field_info in self.field_info:
            field_name = the_field_info['name']
            if (include_pks or not field_name in self.pks) and \
                    (not field_name in self.geometry_columns):
                the_field_conf = self.field_conf_dict.get(field_name, {})
                field = self.init_field_conf(the_field_conf, the_field_info)
                fields.append(field)
        
        # Agregar campos de tipo "link" que están en la configuración pero no en BBDD
        # existing_field_names = {field.get('name') for field in fields}
        # for field_conf in self.conf.get('fields', []):
        #     field_name = field_conf.get('name')
        #     if field_name not in existing_field_names and field_conf.get('gvsigol_type') == 'link':
        #         # Crear campo de tipo link con configuración básica
        #         link_field = {
        #             'name': field_name,
        #             'type': 'character varying', 
        #             'visible': field_conf.get('visible', True),
        #             'infovisible': field_conf.get('infovisible', True),
        #             'nullable': field_conf.get('nullable', True),
        #             'mandatory': field_conf.get('mandatory', False),
        #             'editable': False,  
        #             'editableactive': False,
        #             'gvsigol_type': 'link',
        #             'type_params': field_conf.get('type_params', {})
        #         }
                
        #         for id, language in settings.LANGUAGES:
        #             link_field['title-' + id] = field_conf.get('title-' + id, field_name)
                
        #         fields.append(link_field)
        
        return fields

    def refresh_field_conf(self, include_pks=False):
        fields = self.get_updated_field_conf(include_pks=include_pks)
        self.conf['fields'] = fields
        self.layer.conf = self.conf

    def get_field_viewconf(self, include_pks=False):
        fields = self.get_updated_field_conf(include_pks=include_pks)
        for field in fields:
            try:
                enum = LayerFieldEnumeration.objects.get(
                    layer=self.layer, field=field['name']).enumeration
                field['type'] = str(
                    ugettext('enumerated ({0})').format(enum.title))
            except:
                field['type'] = self.field_info_dict.get(
                    field['name'], {}).get('type', '')
            try:
                trigger = Trigger.objects.get(
                    layer=self.layer, field=field['name'])
                field['calculation'] = trigger.procedure.signature
                field['calculationLabel'] = str(
                    trigger.procedure.localized_label)
                field['editableactive'] = False
                field['editable'] = False
            except:
                field['calculation'] = ''
                field['calculationLabel'] = ''
        return fields


class Layer(models.Model):
    external = models.BooleanField(default=False)
    external_params = models.TextField(null=True, blank=True)
    datastore = models.ForeignKey(
        Datastore, null=True, on_delete=models.CASCADE)
    layer_group = models.ForeignKey(LayerGroup, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    abstract = models.CharField(max_length=5000, null=True, blank=True)
    type = models.CharField(max_length=150)
    # the layer can be read by anyone, even anonymous users
    public = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)
    queryable = models.BooleanField(default=True)
    cached = models.BooleanField(default=False)
    single_image = models.BooleanField(default=False)
    vector_tile = models.BooleanField(default=False)
    allow_download = models.BooleanField(default=False)
    time_enabled = models.BooleanField(default=False)
    time_enabled_field = models.CharField(
        max_length=150, null=True, blank=True)
    time_enabled_endfield = models.CharField(
        max_length=150, null=True, blank=True)
    time_presentation = models.CharField(max_length=150, null=True, blank=True)
    time_resolution_year = models.IntegerField(null=True, default=0)
    time_resolution_month = models.IntegerField(null=True, default=0)
    time_resolution_week = models.IntegerField(null=True, default=0)
    time_resolution_day = models.IntegerField(null=True, default=0)
    time_resolution_hour = models.IntegerField(null=True, default=0)
    time_resolution_minute = models.IntegerField(null=True, default=0)
    time_resolution_second = models.IntegerField(null=True, default=0)
    time_default_value_mode = models.CharField(
        max_length=150, null=True, blank=True)
    time_default_value = models.CharField(
        max_length=150, null=True, blank=True)
    time_resolution = models.CharField(max_length=150, null=True, blank=True)
    order = models.IntegerField(default=100)
    created_by = models.CharField(max_length=100)
    thumbnail = models.ImageField(
        upload_to='thumbnails', default=get_default_layer_thumbnail, null=True, blank=True)
    conf = models.TextField(null=True, blank=True)
    detailed_info_enabled = models.BooleanField(default=True)
    detailed_info_button_title = models.CharField(
        max_length=150, null=True, blank=True, default='Detailed info')
    detailed_info_html = models.TextField(null=True, blank=True)
    timeout = models.IntegerField(null=True, default=30000)
    native_srs = models.CharField(max_length=100, default='EPSG:4326')
    native_extent = models.CharField(max_length=250, default='-180,-90,180,90')
    latlong_extent = models.CharField(
        max_length=250, default='-180,-90,180,90')
    # table name for postgis layers, not defined for the rest
    source_name = models.TextField(null=True, blank=True)
    real_time = models.BooleanField(default=False)
    update_interval = models.IntegerField(null=True, default=1000)
    featureapi_endpoint = models.CharField(
        max_length=100, null=False, default='/api/v1')

    def __str__(self):
        return self.name

    def get_qualified_name(self):
        return self.datastore.workspace.name + ":" + self.name

    @property
    def full_qualified_name(self):
        if self.datastore is not None:
            return self.datastore.workspace.server.name + ":" + self.datastore.workspace.name + ":" + self.name
        else:
            return self.name

    def clone(self, target_datastore, recursive=True, layer_group=None, clone_conf=None):
        if not clone_conf:
            clone_conf = CloneConf()
        from gvsigol_services.utils import clone_layer
        return clone_layer(target_datastore, self, layer_group, clone_conf=clone_conf)

    def get_config_manager(self):
        return LayerConfig(self)

    def get_db_connection(self):
        i, params = self.datastore.get_db_connection()
        source_name = self.source_name if self.source_name else self.name
        return i, source_name, params.get('schema', 'public')


class LayerReadGroup(models.Model):
    """
    Deprecated, use LayerReadRole instead. To be removed in v4.0.
    """
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)


class LayerWriteGroup(models.Model):
    """
    Deprecated, use LayerReadRole instead. To be removed in v4.0.
    """
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)


class LayerReadRole(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    role = models.TextField()
    """
    Some limits have been aplied to the read permission for this role on this layer, such as
    - a CQL filter to limit the records available for read or write
    - some fields are hidden or read-only
    - ...
    """
    filtered = models.BooleanField(default=False)
    """
    This permission has been set using some high level or plugin-specific UI, so it
    should not be editable in the general layer permission UI.
    """
    external = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['layer', 'role'], name='unique_read_role_per_layer')
        ]


class LayerWriteRole(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    role = models.TextField()
    """
    Some limits have been aplied to the read permission for this role on this layer, such as
    - a CQL filter to limit the records available for read or write
    - some fields are hidden or read-only
    - ...
    """
    filtered = models.BooleanField(default=False)
    """
    This permission has been set using some high level or plugin-specific UI, so it
    should not be editable in the general layer permission UI.
    """
    external = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['layer', 'role'], name='unique_write_role_per_layer')
        ]


class LayerManageRole(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    role = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['layer', 'role'], name='unique_manage_role_per_layer')
        ]


class LayerGroupRole(models.Model):
    PERM_INCLUDEINPROJECTS = 'includeinprojects'
    PERM_MANAGE = 'manage'
    PERMISSION_CHOICES = [
        (PERM_MANAGE, PERM_MANAGE),
        (PERM_INCLUDEINPROJECTS, PERM_INCLUDEINPROJECTS),
    ]
    layergroup = models.ForeignKey(LayerGroup, on_delete=models.CASCADE)
    role = models.TextField()
    permission = models.TextField(
        choices=PERMISSION_CHOICES, default=PERM_MANAGE)

    class Meta:
        indexes = [
            models.Index(fields=['layergroup', 'permission', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(fields=[
                                    'layergroup', 'permission', 'role'], name='unique_permission_role_per_layergroup')
        ]

    def __str__(self):
        return '({}, {}, {})'.format(self.layergroup.name, self.role, self.permission)


class DataRule(models.Model):
    path = models.CharField(max_length=500)
    roles = models.CharField(max_length=500)


class LayerLock(models.Model):
    """locks created from geoportal"""
    GEOPORTAL_LOCK = 0
    """locks created from sync API"""
    SYNC_LOCK = 1
    """Valid lock types"""
    TYPE_CHOICES = (
        (GEOPORTAL_LOCK, 'Geoportal'),
        (SYNC_LOCK, 'Sync')
    )
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100)
    type = models.IntegerField(choices=TYPE_CHOICES, default=GEOPORTAL_LOCK)

    def __str__(self):
        return self.layer.name


class LayerResource(models.Model):
    """Stores resources (images, pdfs, etc) linked to specific features in a Layer"""

    """image files, stored in the file system"""
    EXTERNAL_IMAGE = 1
    """PDF files, stored in the file system"""
    EXTERNAL_PDF = 2
    """.ODT or .DOC files, stored in the file system"""
    EXTERNAL_DOC = 3
    """any kind of resource file"""
    EXTERNAL_FILE = 4
    """video files"""
    EXTERNAL_VIDEO = 5
    """alfresco directory"""
    EXTERNAL_ALFRESCO_DIR = 6
    """Valid resource types"""
    TYPE_CHOICES = (
        (EXTERNAL_IMAGE, 'Image'),
        (EXTERNAL_PDF, 'PDF'),
        (EXTERNAL_DOC, 'DOC'),
        (EXTERNAL_VIDEO, 'Video'),
        (EXTERNAL_FILE, 'File'),
    )
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    """The primary key of the feature. This makes mandatory for
    gvSIG Online layers to have a numeric, non-complex primary key"""
    feature = models.BigIntegerField()
    type = models.IntegerField(choices=TYPE_CHOICES)
    path = models.CharField(max_length=500)
    """The title of the resource (optional)"""
    title = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'feature']),
            models.Index(fields=['path']),
        ]

    def get_abspath(self):
        return os.path.join(settings.MEDIA_ROOT, self.path)

    def get_url(self):
        return reverse('layer_resource', args=[self.pk])


class Enumeration(models.Model):
    name = models.CharField(max_length=150)
    title = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class EnumerationItem(models.Model):
    enumeration = models.ForeignKey(Enumeration, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    selected = models.BooleanField(default=False)
    order = models.IntegerField(null=False, default=0)

    def __str__(self):
        return self.name


class LayerFieldEnumeration(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, null=True)
    enumeration = models.ForeignKey(Enumeration, on_delete=models.CASCADE)
    field = models.CharField(max_length=150)
    multiple = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'field']),
        ]


class ServiceUrl(models.Model):
    SERVICE_TYPE_CHOICES = (
        ('WMS', 'WMS'),
        ('WMTS', 'WMTS'),
        ('WFS', 'WFS'),
        ('CSW', 'CSW'),
    )
    title = models.CharField(max_length=500, null=True, blank=True)
    type = models.CharField(
        max_length=50, choices=SERVICE_TYPE_CHOICES, default='WMS')
    url = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def url_path(self):
        """
        Returns the URL excluding the query and fragment, which is equivalent to the
        URL part before the '?' character.
        """
        return self.url.split('?')[0]


class TriggerProcedure(models.Model):
    """
    The definition of a PostgreSQL function designed to be used in a trigger,
    which will be used for calculated fields.

    Our TriggerProcedure definition includes also parameters for the trigger creation,
    since these procedures make some assumptions based on the kind of trigger that will
    be applied (ROW OR STATEMENT orientation, BEFORE, AFTER OR INSTEAD OF activation, etc).

    If the definition is not static and has to be customized based on environment variables,
    field names, etc, a CustomFunctionDef subclass must be registered in triggers.CUSTOM_PROCEDURES
    dictionary.
    """
    signature = models.TextField(unique=True)
    func_name = models.CharField(max_length=150)
    func_schema = models.CharField(max_length=150)
    label = models.CharField(max_length=150)
    definition_tpl = models.TextField(blank=True, null=True)
    activation = models.CharField(max_length=10)
    event = models.CharField(max_length=100)
    orientation = models.CharField(max_length=10)
    """
    Condition is excluded for the moment since it is very complex to validate
    against SQL injection attacks.
    condition = models.TextField()
    """

    def get_definition(self):
        custom_procedure_cls = CUSTOM_PROCEDURES.get(self.signature)
        if custom_procedure_cls:
            return custom_procedure_cls().get_definition()
        else:
            return self.definition_tpl

    @property
    def localized_label(self):
        return _(self.label)


class Trigger(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, null=True)
    field = models.CharField(max_length=150)
    procedure = models.ForeignKey(TriggerProcedure, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'field']),
        ]

    def get_name(self):
        return self.procedure.func_name + "_" + self.field + "_trigger"

    def install(self):
        from gvsigol_services.utils import get_db_connect_from_layer
        trigger_name = self.get_name()
        i, target_table, target_schema = get_db_connect_from_layer(self.layer)
        i.install_trigger(trigger_name, target_schema, target_table,
                          self.procedure.activation, self.procedure.event, self.procedure.orientation, '', self.procedure.func_schema, self.procedure.func_name, [self.field])
        i.close()

    def drop(self):
        from gvsigol_services.utils import get_db_connect_from_layer
        trigger_name = self.get_name()
        i, target_table, target_schema = get_db_connect_from_layer(self.layer)
        i.drop_trigger(trigger_name, target_schema, target_table)
        i.close()


class SqlView(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['datastore', 'name'], name='unique_name_per_datastore')
        ]
    name = models.TextField()
    datastore = models.ForeignKey(Datastore, on_delete=models.CASCADE)
    """
    In order to avoid SQL injections, we only accept a particular type of views
    that fit in the following JSON schema:
     {
        "fields":  [
            {"table_alias": "t1", "name": "f1", "alias": "f1"},
            {"table_alias": "t2", "name": "f1", "alias": "ff1"},
            {"table_alias": "t1", "name": "f2", "alias": "f2"},
            {"table_alias": "t2", "name": "f2", "alias": "ff2"}
        ],
        "from": [
            {
                "schema": "sch1",
                "name": "table1",
                "alias": "t1"
            },
            {
                "schema": "sch1",
                "name": "table2",
                "alias": "t1",
                "join_type": "INNER",
                "join_field1": {
                    "table_alias": "t1",
                    "name": "f1"
                },
                "join_field2": {
                    "table_alias": "t2",
                    "name": "f1"
                }
            }
        ],
        "pks": ["f1"]
    }

    The main limitations of this schema are:
    - complex ON conditions are not allowed (i.e. ON t1.f1 = t2.t1_id AND t1.type = t2.type)
    - where clauses are not allowed (although the schema could be extended to accept WHERE clauses)
    """
    json_def = JSONField()
    created_by = models.CharField(max_length=100, default='')

    @property
    def tables_str(self):
        tables = [t.get('schema', '')+'.'+t.get('name', '')
                  for t in self.json_def.get('from', [])]
        return ", ".join(tables)


class Category(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return f"Category - {self.title} )"

class Marker(models.Model):
    idProj = models.IntegerField()
    title = models.CharField(max_length=255)
    position_lat = models.FloatField()
    position_lng = models.FloatField()
    zoom = models.FloatField()
    thumbnail = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='markers'
    )

    def __str__(self):
        return f"Marker - {self.title} (Proj {self.idProj})"

class LayerTopologyConfiguration(models.Model):
    """
    Modelo para almacenar la configuración de reglas topológicas de una capa.
    Una sola fila por capa con campos específicos para cada regla.
    """
    layer = models.OneToOneField(Layer, on_delete=models.CASCADE, related_name='topology_config')
    
    # Regla: No debe solapar
    no_overlap = models.BooleanField(default=False)
    
    # Regla: No debe haber huecos
    no_gaps = models.BooleanField(default=False)
    
    # Regla: Debe estar cubierto por
    must_be_covered_by = models.BooleanField(default=False)
    covered_by_layer = models.CharField(max_length=255, blank=True, null=True, 
                                      help_text="Capa que debe cubrir en formato schema.tabla")
    
    # Regla: No debe solapar con
    must_not_overlap_with = models.BooleanField(default=False)
    overlap_layers = JSONField(default=list, blank=True, 
                              help_text="Lista de capas con las que no debe solapar en formato schema.tabla")
    
    # Regla: Debe ser contiguo
    must_be_contiguous = models.BooleanField(default=False)
    contiguous_tolerance = models.FloatField(default=1.0, 
                                           help_text="Tolerancia en metros para la contigüidad")

    class Meta:
        verbose_name = 'Layer Topology Configuration'
        verbose_name_plural = 'Layer Topology Configurations'

    def __str__(self):
        return f"Topology config for {self.layer.name}"

    def get_active_rules_count(self):
        """
        Cuenta cuántas reglas están activas
        """
        active_count = 0
        if self.no_overlap:
            active_count += 1
        if self.no_gaps:
            active_count += 1
        if self.must_be_covered_by:
            active_count += 1
        if self.must_not_overlap_with:
            active_count += 1
        if self.must_be_contiguous:
            active_count += 1
        
        return active_count

    def get_rules_summary(self):
        """
        Devuelve un resumen legible de las reglas activas
        """
        summary = []
        
        if self.no_overlap:
            summary.append("No overlap")
        
        if self.no_gaps:
            summary.append("No gaps")
        
        if self.must_be_covered_by:
            if self.covered_by_layer:
                summary.append(f"Covered by: {self.covered_by_layer}")
            else:
                summary.append("Covered by (not configured)")
        
        if self.must_not_overlap_with:
            if self.overlap_layers:
                summary.append(f"No overlap with: {', '.join(self.overlap_layers)}")
            else:
                summary.append("No overlap with (not configured)")
        
        if self.must_be_contiguous:
            summary.append(f"Contiguous (tolerance: {self.contiguous_tolerance}m)")
        
        return '; '.join(summary) if summary else "No active rules"


class FavoriteFilter(models.Model):
    """
    Modelo para almacenar filtros favoritos guardados por los usuarios.
    Permite guardar y compartir filtros personalizados para capas específicas de proyectos específicos.
    """
    name = models.CharField(max_length=150, null=False)
    description = models.CharField(max_length=500, null=True, blank=True)
    share_filter = models.BooleanField(default=False)
    project = models.ForeignKey('gvsigol_core.Project', on_delete=models.CASCADE, null=False)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, null=False)
    filter_data = JSONField(help_text="Estructura JSON con la configuración del filtro")
    created_by = models.CharField(max_length=100, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Favorite Filter'
        verbose_name_plural = 'Favorite Filters'
        indexes = [
            models.Index(fields=['project', 'layer']),
            models.Index(fields=['created_by']),
            models.Index(fields=['share_filter']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'project', 'layer', 'created_by'], 
                name='unique_favorite_filter_per_user_layer'
            )
        ]

    def __str__(self):
        return f"Filter '{self.name}' for layer '{self.layer.name}' by {self.created_by}"

    def get_filter_summary(self):
        """
        Devuelve un resumen legible del filtro
        """
        if self.filter_data:
            filter_queries = self.filter_data.get('filterQueries', [])
            operator = self.filter_data.get('filterOperator', 'AND')
            
            if filter_queries:
                query_count = len(filter_queries)
                return f"{query_count} query{'s' if query_count > 1 else ''} with {operator} operator"
        
        return "No filter data"

    def is_accessible_by_user(self, user):
        """
        Verifica si un usuario puede acceder a este filtro
        """
        
        if self.created_by == user.username:
            return True
        
        # Si está compartido, cualquier usuario del proyecto puede acceder
        if self.share_filter:
            return self.project.userprojectrole_set.filter(user=user).exists()
        
        return False