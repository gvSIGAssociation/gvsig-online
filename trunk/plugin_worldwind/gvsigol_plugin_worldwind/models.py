# -*- coding: utf-8 -*-

# from win32.lib.netbios import MAX_LANA


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
    TYPE_CHOICES = [
        ('url', 'Url'),
        ('mapserver', 'Mapserver')
    ]
    type = models.CharField(max_length=250, choices = TYPE_CHOICES, default="url", blank = False)
    path = models.CharField(max_length=250, default="", blank=True, null=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE)
    heightUrl = models.URLField(max_length=250, default="")
    layers = models.CharField(max_length=250, default="elevation", blank=True, null = True);
    
   # class Meta:
   #     unique_together = (("id", "project"),)
        
    def __str__(self):
        return self.name
