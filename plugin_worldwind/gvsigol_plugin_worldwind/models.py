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
@author: jvhigon <jvhigon@scolab.es>
'''


from django.db import models
from gvsigol_core.models import Project


class WorldwindProvider(models.Model):
    #name = models.CharField(max_length=100, unique=True, default="")
    path = models.CharField(max_length=250, default="")
    project = models.OneToOneField(Project)
    
   # class Meta:
   #     unique_together = (("id", "project"),)
        
    def __unicode__(self):
        return self.name