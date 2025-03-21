from django.db import models

from gvsigol_services.models import Layer

class Chart(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    type = models.CharField(max_length=25, default='barchart')
    title = models.CharField(max_length=150)
    description = models.CharField(null=True, blank=True, max_length=500)
    conf = models.TextField()


def translations_placeholder():
    # do not remove
    test = _("gvsigol_plugin_charts manual title")
    test = _("gvsigol_plugin_charts manual desc")