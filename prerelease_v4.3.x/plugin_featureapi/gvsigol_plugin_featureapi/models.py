'''
    gvSIG Online.
    Copyright (C) 2010-2019 SCOLAB.

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

@author: Nacho Brodin <nbrodin@scolab.es>
'''
from django.contrib.gis.db import models as models_geom
from django.db import models

from gvsigol_services.models import Layer


class FeatureVersions(models.Model):
    version = models.IntegerField(default=1)
    wkb_geometry = models_geom.GeometryField()
    fields = models.TextField()
    date = models.DateTimeField(null=True, blank=True)
    usr = models.CharField(max_length=150, default='')
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    feat_id = models.BigIntegerField(default=0)
    operation = models.IntegerField(default=1) #1-CREATE 2-UPDATE 3-DELETE
    resource = models.CharField(max_length=500, null=True)
    