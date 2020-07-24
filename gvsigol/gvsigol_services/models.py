from __future__ import unicode_literals
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
    
    def __unicode__(self):
        return self.name
    
class Node(models.Model):
    server = models.ForeignKey(Server)
    status = models.CharField(max_length=25)
    url = models.CharField(max_length=500)
    is_master = models.BooleanField(default=False)
    
    def getUrl(self):
        return self.url

def get_default_server():
    theServer = Server.objects.get(default=True)
    return theServer.id

class Workspace(models.Model):
    server = models.ForeignKey(Server, default=get_default_server)
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
    
    def __unicode__(self):
        return self.name
    
    
class Datastore(models.Model):
    workspace = models.ForeignKey(Workspace)
    type = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500, null=True, blank=True)
    connection_params = models.TextField()
    created_by = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.workspace.name + ":" + self.name
 
    
class LayerGroup(models.Model):
    server_id = models.IntegerField(null=True, default=get_default_server)
    name = models.CharField(max_length=150) 
    title = models.CharField(max_length=500, null=True, blank=True) 
    visible = models.BooleanField(default=False)
    cached = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name

def get_default_layer_thumbnail():
    return settings.STATIC_URL + 'img/no_thumbnail.jpg'

class Layer(models.Model):
    external = models.BooleanField(default=False)
    external_params = models.TextField(null=True, blank=True)
    datastore = models.ForeignKey(Datastore, null=True)
    layer_group = models.ForeignKey(LayerGroup)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    abstract = models.CharField(max_length=5000, null=True, blank=True)
    type = models.CharField(max_length=150)
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
    
    def __unicode__(self):
        return self.name
    
    def get_qualified_name(self):
        return self.datastore.workspace.name + ":" + self.name

class LayerReadGroup(models.Model):
    layer = models.ForeignKey(Layer)
    group = models.ForeignKey(UserGroup)
    
    
class LayerWriteGroup(models.Model):
    layer = models.ForeignKey(Layer)
    group = models.ForeignKey(UserGroup)
    
    
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
    
    def __unicode__(self):
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
    
class Enumeration(models.Model):
    name = models.CharField(max_length=150) 
    title = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name
    
class EnumerationItem(models.Model):
    enumeration = models.ForeignKey(Enumeration, on_delete=models.CASCADE)
    name = models.CharField(max_length=150) 
    selected = models.BooleanField(default=False)
    order = models.IntegerField(null=False, default=0)
    
    def __unicode__(self):
        return self.name
    
class LayerFieldEnumeration(models.Model):
    enumeration = models.ForeignKey(Enumeration, on_delete=models.CASCADE)
    layername = models.CharField(max_length=150)
    schema = models.CharField(max_length=150)
    field = models.CharField(max_length=150) 
    multiple = models.BooleanField(default=False)
    
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
    
    def __unicode__(self):
        return self.title
    
