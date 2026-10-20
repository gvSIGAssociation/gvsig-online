from django.db import models

class SentiloConfiguration(models.Model):
    domain = models.CharField(max_length=200)
    sentilo_identity_key = models.CharField(max_length=200)
    tabla_de_datos = models.CharField(max_length=200)
    sentilo_sensors = models.TextField()  # Assuming this can be a long list
    intervalo_de_actualizacion = models.IntegerField()

    def __str__(self):
        return self.domain
