from django.db import models

class exports_historical(models.Model):

    time = models.CharField(max_length=30)
    file = models.CharField(max_length=250)
    status = models.CharField(max_length=25, null=True, blank=True)
    message = models.CharField(max_length=500, null=True, blank=True)
    redirect = models.CharField(max_length=500, null=True, blank=True)
    username = models.CharField(default='', max_length=30)
    
    def __str__(self):
        return self.name
