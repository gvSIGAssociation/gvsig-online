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
from django.utils.translation import gettext as _
import json

class GTFSProvider(models.Model):
    SOURCE_URL = 'url'
    SOURCE_FILE = 'file'
    SOURCE_CHOICES = [(SOURCE_URL, 'URL'), (SOURCE_FILE, 'File')]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, null=True, blank=True)
    # url: feed downloaded periodically. file: GTFS uploaded by hand (stored in sources/<id>.zip)
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_URL)
    url = models.URLField(blank=True, default='', max_length=400)
    is_active = models.BooleanField(default=True)

    # when the provider's GTFS file last changed (downloaded or uploaded)
    last_update = models.DateTimeField(auto_now_add=False, null=True, blank=True)

    @property
    def is_file(self):
        return self.source_type == self.SOURCE_FILE


class APPMobileConfig(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, null=True, blank=True)
    params = models.TextField()


class GTFSstatus(models.Model):
    # status: '' | Running | Success (graph rebuilt) | Unchanged | NoProviders | Error
    name = models.CharField(max_length=250)
    message = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    # fingerprint of the active GTFS files used in the last successful graph build
    last_build_signature = models.CharField(max_length=64, null=True, blank=True)
    
    def __str__(self):
        return self.name


