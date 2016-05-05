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
    UNIQUE_SYMBOL = 'SU'
    UNIQUE_VALUES = 'VU'
    INTERVALS = 'IN'
    EXPRESSIONS = 'EX'
    COLOR_TABLES = 'TC'
    CHARTS = 'CH'
    LEGEND_TYPES = (
        (UNIQUE_SYMBOL, _('Unique symbol')),
        (UNIQUE_VALUES, _('Unique values')),
        (INTERVALS, _('Intervals')),
        (EXPRESSIONS, _('Expressions')),
        (COLOR_TABLES, _('Color table')),
        (CHARTS, _('Graphics')),
    )
    title = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=150) 
    type = models.CharField(max_length=2, choices=LEGEND_TYPES, default=UNIQUE_SYMBOL)
    
    def __unicode__(self):
        return self.name


class LayerStyle(models.Model):
    style = models.ForeignKey(Style)
    layer = models.ForeignKey(Layer)
    name = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    order = models.IntegerField(null=False, default=0)
    
    def __unicode__(self):
        return self.layer.name + ' - ' + self.style.name
   
    
class Rule(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    filter = models.CharField(max_length=5000, blank=True, null=True) 
    order = models.IntegerField(null=False, default=0)
    minscale = models.FloatField(null=True, blank=True)
    maxscale = models.FloatField(null=True, blank=True)
    style = models.ForeignKey(Style)


class Symbol(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=150, blank=True, null=True)
    sld_code = models.CharField(max_length=5000, blank=True, null=True) 

    def __unicode__(self):
        return self.name

   
class Library(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.name

  
class LibrarySymbol(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=150, blank=True, null=True)
    sld_code = models.CharField(max_length=5000, blank=True, null=True) 
    library = models.ForeignKey(Library)
    type = models.CharField(max_length=20, blank=False, null=False, default='PointSymbolizer')
    is_public = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.name

   
class RuleSymbol(models.Model):
    rule = models.ForeignKey(Rule)
    symbol = models.ForeignKey(Symbol)
    
    def __unicode__(self):
        return self.rule.name + ' - ' + self.symbol.name

