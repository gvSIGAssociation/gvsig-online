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
@author: José Badía <jbadia@scolab.es>
'''
from django.db import models
from gvsigol_services.models import Layer
from django.utils.translation import ugettext as _

class Style(models.Model):
    UNIQUE_SYMBOL = 'US'
    UNIQUE_VALUES = 'UV'
    INTERVALS = 'IN'
    EXPRESSIONS = 'EX'
    COLOR_TABLES = 'CT'
    CHARTS = 'CH'
    LEGEND_TYPES = (
        (UNIQUE_SYMBOL, _('Unique symbol')),
        (UNIQUE_VALUES, _('Unique values')),
        (INTERVALS, _('Intervals')),
        (EXPRESSIONS, _('Expressions')),
        (COLOR_TABLES, _('Color table')),
        (CHARTS, _('Graphics')),
    )
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True, null=True)   
    is_default = models.BooleanField(default=False)
    type = models.CharField(max_length=2, choices=LEGEND_TYPES, default=UNIQUE_SYMBOL)
    order = models.IntegerField(null=False, default=0)
    
    def __unicode__(self):
        return self.name

class StyleLayer(models.Model):
    style = models.ForeignKey(Style)
    layer = models.ForeignKey(Layer)  
    
    def __unicode__(self):
        return self.layer.name + ' - ' + self.style.name
      
class Rule(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=25)
    filter = models.CharField(max_length=5000, blank=True, null=True)    
    minscale = models.FloatField(null=True, blank=True)
    maxscale = models.FloatField(null=True, blank=True)
    order = models.IntegerField(null=False, default=0)
    
class Symbolizer(models.Model):
    rule = models.ForeignKey(Rule)
    type = models.CharField(max_length=25) 
    sld = models.CharField(max_length=5000, blank=True, null=True)
    json = models.CharField(max_length=5000, blank=True, null=True)
    order = models.IntegerField(null=False, default=0)
    
class StyleRule(models.Model):
    rule = models.ForeignKey(Rule)
    style = models.ForeignKey(Style)
   
class Library(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=500, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.name
 
class LibraryRule(models.Model):
    library = models.ForeignKey(Library)
    rule = models.ForeignKey(Rule)
    
    def __unicode__(self):
        return self.library.name + ' - ' + self.rule.name