from django.db import models

class exports_historical(models.Model):

    time = models.CharField(max_length=30)
    file = models.TextField()
    status = models.CharField(max_length=25, null=True, blank=True)
    message = models.TextField( null=True, blank=True)
    redirect = models.TextField(null=True, blank=True)
    username = models.TextField(default='')
    task_id = models.CharField(default='', max_length=250)
    
    def __str__(self):
        return self.name
