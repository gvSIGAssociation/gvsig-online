from django.db import models

class ETLworkspaces(models.Model):

    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500, null=True, blank=True)
    workspace = models.TextField()
    username = models.CharField(max_length=250)
    parameters = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.name


class ETLstatus(models.Model):

    name = models.CharField(max_length=250)
    message = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    id_ws = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.name

class database_connections(models.Model):

    type = models.CharField(max_length=250)
    name = models.CharField(max_length=250, unique=True)
    connection_params = models.TextField()
    
    def __str__(self):
        return self.name


class segex_FechaFinGarantizada(models.Model):
    entity = models.CharField(max_length=250)
    type = models.IntegerField(null=False)
    fechafingarantizada = models.DateTimeField(auto_now_add=False, null=False)

    def __str__(self):
        return self.name