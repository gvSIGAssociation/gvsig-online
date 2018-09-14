from __future__ import unicode_literals

from django.db import models
from gvsigol_services.models import Layer

class LayerMetadata(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    metadata_uuid = models.CharField(max_length=100, null=True, blank=True)
    metadata_id = models.IntegerField(null=True, blank=True)