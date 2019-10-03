from django.db import models

class SampleDashboard(models.Model):
    name = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=250, null=True, blank=True)
    
    def __unicode__(self):
        return self.name