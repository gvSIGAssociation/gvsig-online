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
from django.db import models
from gvsigol_auth.models import UserGroup
from gvsigol import settings
from django.utils.crypto import get_random_string
from gvsigol_services.triggers import CUSTOM_PROCEDURES
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
import os

CLONE_PERMISSION_CLONE = "clone"
CLONE_PERMISSION_SKIP = "skip"

class Server(models.Model):
    TYPE_CHOICES = (
        ('geoserver', 'geoserver'),
        ('mapserver', 'mapserver')
    )
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='geoserver')
    frontend_url = models.CharField(max_length=500)
    user = models.CharField(max_length=25)
    password = models.CharField(max_length=100)
    default = models.BooleanField(default=False)
    
    def getWmsEndpoint(self, workspace=None):
        if workspace:
            return self.frontend_url + "/" + workspace + "/wms"
        else:
            return self.frontend_url + "/wms"
    
    def getWfsEndpoint(self, workspace=None):
        if workspace:
            return self.frontend_url + "/" + workspace + "/wfs"
        else:
            return self.frontend_url + "/wfs"
    
    def getWcsEndpoint(self, workspace=None):
        if workspace:
            return self.frontend_url + "/" + workspace + "/wcs"
        else:
            return self.frontend_url + "/wcs"
    
    def getWmtsEndpoint(self, workspace=None):
        return self.frontend_url + "/gwc/service/wmts"
    
    def getCacheEndpoint(self, workspace=None):
        return self.frontend_url + "/gwc/service/wms"
    
    def getGWCRestEndpoint(self, workspace=None):
        return self.frontend_url + "/gwc/rest"
    
    def __str__(self):
        return self.name
    
class Node(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    status = models.CharField(max_length=25)
    url = models.CharField(max_length=500)
    is_master = models.BooleanField(default=False)
    
    def getUrl(self):
        return self.url

def get_default_server():
    theServer = Server.objects.get(default=True)
    return theServer.id

class Workspace(models.Model):
    server = models.ForeignKey(Server, default=get_default_server, on_delete=models.CASCADE)
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

class LayerGroup(models.Model):
    server_id = models.IntegerField(null=True, default=get_default_server)
    name = models.CharField(max_length=150) 
    title = models.CharField(max_length=500, null=True, blank=True) 
    visible = models.BooleanField(default=False)
    cached = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
    def clone(self, recursive=True, target_datastore=None, copy_layer_data=True, permissions=CLONE_PERMISSION_CLONE):
        old_id = self.pk
        new_name = target_datastore.workspace.name + "_" + self.name
        i = 1
        salt = ''
        while LayerGroup.objects.filter(name=new_name, server_id=target_datastore.workspace.server.id).exists():
            new_name = new_name + '_' + str(i) + salt
            i = i + 1
            if (i%1000) == 0:
                salt = '_' + get_random_string(3)
        self.pk = None
        self.name = new_name
        self.save()
        
        new_instance =  LayerGroup.objects.get(id=self.pk)
        if recursive:
            for lyr in LayerGroup.objects.get(id=old_id).layer_set.all():
                lyr.clone(target_datastore=target_datastore, layer_group=new_instance, copy_data=copy_layer_data, permissions=permissions)
        return new_instance

def get_default_layer_thumbnail():
    return settings.STATIC_URL + 'img/no_thumbnail.jpg'

class Layer(models.Model):
    external = models.BooleanField(default=False)
    external_params = models.TextField(null=True, blank=True)
    datastore = models.ForeignKey(Datastore, null=True, on_delete=models.CASCADE)
    layer_group = models.ForeignKey(LayerGroup, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    abstract = models.CharField(max_length=5000, null=True, blank=True)
    type = models.CharField(max_length=150)
    public = models.BooleanField(default=False) # the layer can be read by anyone, even anonymous users
    visible = models.BooleanField(default=True)
    queryable = models.BooleanField(default=True)
    cached = models.BooleanField(default=False)
    single_image = models.BooleanField(default=False)
    allow_download = models.BooleanField(default=True)
    time_enabled = models.BooleanField(default=False)
    time_enabled_field = models.CharField(max_length=150, null=True, blank=True) 
    time_enabled_endfield = models.CharField(max_length=150, null=True, blank=True) 
    time_presentation = models.CharField(max_length=150, null=True, blank=True) 
    time_resolution_year = models.IntegerField(null=True, default=0)
    time_resolution_month = models.IntegerField(null=True, default=0)
    time_resolution_week = models.IntegerField(null=True, default=0)
    time_resolution_day = models.IntegerField(null=True, default=0)
    time_resolution_hour = models.IntegerField(null=True, default=0)
    time_resolution_minute = models.IntegerField(null=True, default=0)
    time_resolution_second = models.IntegerField(null=True, default=0)
    time_default_value_mode = models.CharField(max_length=150, null=True, blank=True) 
    time_default_value = models.CharField(max_length=150, null=True, blank=True)
    time_resolution = models.CharField(max_length=150, null=True, blank=True)
    order = models.IntegerField(default=100)
    created_by = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to='thumbnails', default=get_default_layer_thumbnail, null=True, blank=True)
    conf = models.TextField(null=True, blank=True)
    detailed_info_enabled = models.BooleanField(default=True)
    detailed_info_button_title = models.CharField(max_length=150, null=True, blank=True, default='Detailed info')
    detailed_info_html = models.TextField(null=True, blank=True)
    timeout = models.IntegerField(null=True, default=30000)
    native_srs = models.CharField(max_length=100, default='EPSG:4326')
    native_extent = models.CharField(max_length=250, default='-180,-90,180,90')
    latlong_extent = models.CharField(max_length=250, default='-180,-90,180,90')
    source_name = models.TextField(null=True, blank=True) # table name for postgis layers, not defined for the rest
    real_time = models.BooleanField(default=False)
    update_interval = models.IntegerField(null=True, default=1000)
    
    def __str__(self):
        return self.name
    
    def get_qualified_name(self):
        return self.datastore.workspace.name + ":" + self.name
    
    def clone(self, target_datastore, recursive=True, layer_group=None, copy_data=True, permissions=CLONE_PERMISSION_CLONE):
        from gvsigol_services.utils import clone_layer
        return clone_layer(target_datastore, self, layer_group, copy_data=copy_data, permissions=permissions)

class LayerReadGroup(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)
    
    
class LayerWriteGroup(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)
    
    
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
    feature = models.IntegerField()
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
        return reverse('get_layer_resource', args=[self.pk])
    
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
    type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES, default='WMS')
    url = models.CharField(max_length=500, null=True, blank=True)
    
    def __str__(self):
        return self.title

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
    definition_tpl =  models.TextField(blank=True, null=True)
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
        return self.procedure.__name__ + "_" + self.field + "_trigger"
    
    def install(self):
        from gvsigol_services.utils import get_db_connect_from_layer
        trigger_name = self.get_name()
        i, target_table, target_schema = get_db_connect_from_layer(self.layer)
        i.install_trigger(trigger_name, target_schema, target_table,
                        self.procedure.activation, self.procedure.event, self.procedure.orientation, '', self.procedure.func_schema, self.procedure.__name__, [self.field])
        i.close()

    def drop(self):
        from gvsigol_services.utils import get_db_connect_from_layer
        trigger_name = self.get_name()
        i, target_table, target_schema = get_db_connect_from_layer(self.layer)
        i.drop_trigger(trigger_name, target_schema, target_table)
        i.close()