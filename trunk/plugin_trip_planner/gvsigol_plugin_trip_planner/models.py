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
@author: José Badía <jbadia@scolab.es>
'''
from django.db import models
from gvsigol import settings
from django.utils.translation import ugettext as _
import json

class GTFSProvider(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, null=True, blank=True)
    url = models.URLField(null=False, blank=False, max_length=400)

    #params = models.TextField()

    #table_name = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    last_update = models.DateTimeField(auto_now_add=False, null=True, blank=True)


class APPMobileConfig(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, null=True, blank=True)
    params = models.TextField()


class GTFSstatus(models.Model):

    name = models.CharField(max_length=250)
    message = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return self.name


