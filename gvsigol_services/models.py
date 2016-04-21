from __future__ import unicode_literals
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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from django.db import models
from gvsigol_auth.models import UserGroup

class Workspace(models.Model):
    name = models.CharField(max_length=250, unique=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    uri = models.CharField(max_length=500)
    wms_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wfs_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wcs_endpoint = models.CharField(max_length=500, null=True, blank=True)
    cache_endpoint = models.CharField(max_length=500, null=True, blank=True)
    
    def __unicode__(self):
        return self.name
    
    
class Datastore(models.Model):
    workspace = models.ForeignKey(Workspace)
    type = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500, null=True, blank=True)
    connection_params = models.TextField()
    
    def __unicode__(self):
        return self.workspace.name + ":" + self.name
 
    
class LayerGroup(models.Model):
    name = models.CharField(max_length=150) 
    title = models.CharField(max_length=500, null=True, blank=True) 
    cached = models.BooleanField(default=False) 
    order = models.IntegerField(null=False, default=0) 
    
    def __unicode__(self):
        return self.name


class Layer(models.Model):
    datastore = models.ForeignKey(Datastore)
    layer_group = models.ForeignKey(LayerGroup)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    abstract = models.CharField(max_length=5000)
    type = models.CharField(max_length=150)
    metadata_uuid = models.CharField(max_length=100, null=True, blank=True)
    visible = models.BooleanField(default=True)
    queryable = models.BooleanField(default=True)
    cached = models.BooleanField(default=True)
    single_image = models.BooleanField(default=False)
    order = models.IntegerField(null=False, default=0)
    
    def __unicode__(self):
        return self.name


class LayerReadGroup(models.Model):
    layer = models.ForeignKey(Layer)
    group = models.ForeignKey(UserGroup)
    
    
class LayerWriteGroup(models.Model):
    layer = models.ForeignKey(Layer)
    group = models.ForeignKey(UserGroup)    
    
    
class DataRule(models.Model):
    path = models.CharField(max_length=500)
    roles = models.CharField(max_length=500)
