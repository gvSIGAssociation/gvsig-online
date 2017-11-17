from __future__ import unicode_literals

from django.db import models
from gvsigol import settings
from gvsigol_auth.models import UserGroup
from gvsigol_services.models import LayerGroup

class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=250, null=True, blank=True)
    image = models.ImageField(upload_to='images', default=settings.STATIC_URL + 'img/no_project.png', null=True, blank=True)
    center_lat = models.CharField(max_length=100)
    center_lon = models.CharField(max_length=100)
    zoom = models.IntegerField(null=False, default=10)
    extent = models.CharField(max_length=250)
    toc_mode = models.TextField(max_length=50, default='toc_hidden')
    toc_order = models.TextField(null=True, blank=True)
    created_by = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.name + ' - ' + self.description
    
    
class ProjectUserGroup(models.Model):
    project = models.ForeignKey(Project, default=None)
    user_group = models.ForeignKey(UserGroup, default=None)
    
    def __unicode__(self):
        return self.project.name + ' - ' + self.user_group.name  
 
    
class ProjectLayerGroup(models.Model):
    project = models.ForeignKey(Project, default=None)
    layer_group = models.ForeignKey(LayerGroup, default=None)
    
    def __unicode__(self):
        return self.project.name + ' - ' + self.layer_group.name
    
    
class BaseLayer(models.Model):
    name = models.CharField(max_length=150, null=True, blank=True) 
    title = models.CharField(max_length=150) 
    type = models.CharField(max_length=50, null=True, blank=True)
    type_params = models.TextField(null=True, blank=True)
    
    def __unicode__(self):
        return self.name
    
class BaseLayerProject(models.Model):
    baselayer = models.ForeignKey(BaseLayer)
    project = models.ForeignKey(Project)
    order = models.IntegerField(null=False, default=0)
    is_default = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.baselayer.name +"-"+self.project.id