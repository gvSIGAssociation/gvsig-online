# -*- coding: utf-8 -*-
from __future__ import unicode_literals


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
@author: jbadia <jbadia@scolab.es>
'''


from django.db import models
from gvsigol_core.models import Project
from gvsigol_services.models import Layer

class Survey(models.Model):
    name = models.CharField(max_length=150) 
    title = models.CharField(max_length=150) 
    project = models.ForeignKey(Project, null=True, blank=True)
    
    def __unicode__(self):
        return self.name
    
class SurveySection(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    name = models.CharField(max_length=200) 
    title = models.CharField(max_length=200) 
    srs = models.CharField(max_length=100, null=True, blank=True) 
    layer = models.ForeignKey(Layer, null=True)
    
    order = models.IntegerField(null=False, default=0)
    
    def __unicode__(self):
        return self.survey+'-'+self.name
