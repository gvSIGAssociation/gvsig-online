from django.contrib.gis.db import models

class Poi(models.Model):
    name = models.CharField(max_length=100, null=True)
    description = models.TextField(null=True, blank=True)
    geometry = models.PointField(srid=4326, null=True)