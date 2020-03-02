# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
@author: José Badía <jbadia@scolab.es>
'''
from django.db import models
from gvsigol_services.models import Layer
from django.utils.translation import ugettext as _


__WELL_KNOWN_LABELS = ( # just needed for triggering xgettext makemessages detection
    ('Circle', _('Circle')),
    ('Square', _('Square')),
    ('Triangle', _('Triangle')),
    ('star', _('star')),
    ('cross', _('Cross')),
    )

WELL_KNOWN_NAMES = (
    ('circle', 'Círculo'),
    ('square', 'Cuadrado'),
    ('triangle', 'Triángulo'),
    ('star', 'Estrella'),
    ('cross', 'Cruz'),
)

UNIQUE_SYMBOL = 'US'
UNIQUE_VALUES = 'UV'
INTERVALS = 'IN'
EXPRESSIONS = 'EX'
COLOR_TABLES = 'CT'
CLUSTERED_POINTS = 'CP'
CHARTS = 'CH'
LEGEND_TYPES = (
    (UNIQUE_SYMBOL, 'Unique symbol'),
    (UNIQUE_VALUES, 'Unique values'),
    (INTERVALS, 'Intervals'),
    (EXPRESSIONS, 'Expressions'),
    (CLUSTERED_POINTS, 'Clustered Points'),
    (COLOR_TABLES, 'Color table'),
    (CHARTS, 'Graphics'),
)

class Style(models.Model):   
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True, null=True)   
    is_default = models.BooleanField(default=False)
    type = models.CharField(max_length=2, choices=LEGEND_TYPES, default=UNIQUE_SYMBOL)
    minscale = models.FloatField(null=True, blank=True, default=-1)
    maxscale = models.FloatField(null=True, blank=True, default=-1)
    order = models.IntegerField(null=False, default=0)
    has_custom_legend = models.BooleanField(default=False)
    custom_legend_url = models.CharField(max_length=250, blank=True, null=True)
    sld = models.TextField(null=True, blank=True)
    
    def __unicode__(self):
        return self.name

class StyleLayer(models.Model):
    style = models.ForeignKey(Style)
    layer = models.ForeignKey(Layer)  
    
    def __unicode__(self):
        return self.layer.name + ' - ' + self.style.name
      
class Rule(models.Model):
    style = models.ForeignKey(Style)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=500, blank=True, null=True)
    abstract = models.CharField(max_length=500, blank=True, null=True)
    filter = models.CharField(max_length=5000, blank=True, null=True)    
    minscale = models.FloatField(null=True, blank=True, default=-1)
    maxscale = models.FloatField(null=True, blank=True, default=-1)
    order = models.IntegerField(null=False, default=0)
    
class Symbolizer(models.Model):
    rule = models.ForeignKey(Rule) 
    order = models.IntegerField(null=False, default=0)
    
class MarkSymbolizer(Symbolizer):
    opacity = models.IntegerField(default=1)
    size = models.IntegerField(default=8)
    rotation = models.IntegerField(default=0)
    well_known_name = models.CharField(max_length=25, choices=WELL_KNOWN_NAMES, default='circle')
    fill = models.CharField(max_length=100)
    fill_opacity = models.FloatField(default=1.0)
    stroke = models.CharField(max_length=100)
    stroke_width = models.IntegerField(default=1)
    stroke_opacity = models.FloatField(default=1.0)
    stroke_dash_array = models.CharField(max_length=100)
    
class ExternalGraphicSymbolizer(Symbolizer):
    opacity = models.IntegerField(default=1)
    size = models.IntegerField(default=8)
    rotation = models.IntegerField(default=0)
    online_resource = models.CharField(max_length=1000)
    format = models.CharField(max_length=100)
    
class LineSymbolizer(Symbolizer):
    stroke = models.CharField(max_length=100)
    stroke_width = models.IntegerField(default=1)
    stroke_opacity = models.FloatField(default=1.0)
    stroke_dash_array = models.CharField(max_length=100)
    
class PolygonSymbolizer(Symbolizer):
    fill = models.CharField(max_length=100)
    fill_opacity = models.FloatField(default=1.0)
    stroke = models.CharField(max_length=100)
    stroke_width = models.IntegerField(default=1)
    stroke_opacity = models.FloatField(default=1.0)
    stroke_dash_array = models.CharField(max_length=100)
    
class TextSymbolizer(Symbolizer):
    is_actived = models.BooleanField(default=False)
    label = models.CharField(max_length=100)
    font_family = models.CharField(max_length=100)
    font_size = models.IntegerField(default=12)
    font_style = models.CharField(max_length=100)
    font_weight = models.CharField(max_length=100)
    fill = models.CharField(max_length=100)
    fill_opacity = models.FloatField(default=1.0)
    halo_radius = models.IntegerField(default=12)
    halo_fill = models.CharField(max_length=100)
    halo_fill_opacity = models.FloatField(default=1.0)
    anchor_point_x = models.FloatField(default=0.5)
    anchor_point_y = models.FloatField(default=-1.5)

class ColorMap(models.Model):
    type = models.CharField(max_length=100)
    extended = models.BooleanField(default=False)
    
class ColorMapEntry(models.Model):
    order = models.IntegerField(null=False, default=0)
    color_map = models.ForeignKey(ColorMap, on_delete=models.CASCADE)
    color = models.CharField(max_length=100)
    quantity = models.FloatField()
    label = models.CharField(max_length=100)
    opacity = models.FloatField(default=1.0)
    
class RasterSymbolizer(Symbolizer):
    opacity = models.FloatField(default=1.0)
    color_map = models.OneToOneField(ColorMap, null=True, on_delete=models.CASCADE)
   
class Library(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=500, blank=True, null=True)
    
    def __unicode__(self):
        return self.name
 
class LibraryRule(models.Model):
    library = models.ForeignKey(Library)
    rule = models.ForeignKey(Rule)
    
    def __unicode__(self):
        return self.library.name + ' - ' + self.rule.name

class ColorRampLibrary(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=500, blank=True, null=True)
    
    def __unicode__(self):
        return self.name
    
class ColorRampFolder(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=500, blank=True, null=True)
    color_ramp_library = models.ForeignKey(ColorRampLibrary)
    
    def __unicode__(self):
        return self.name
   
class ColorRamp(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    definition = models.TextField()
    color_ramp_folder = models.ForeignKey(ColorRampFolder)
    
    def __unicode__(self):
        return self.name