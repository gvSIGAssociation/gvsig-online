# -*- coding: utf-8 -*-

from django.db import models
from gvsigol_core.models import Layer, Project

class MediaDisplayConfig(models.Model):
    """
    Configuración del plugin MediaDisplay por proyecto
    """
    project = models.OneToOneField(Project, on_delete=models.CASCADE, verbose_name="Proyecto")
    enabled_layers = models.ManyToManyField(Layer, blank=True, verbose_name="Capas habilitadas para multimedia")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración Media Display"
        verbose_name_plural = "Configuraciones Media Display"

    def __str__(self):
        return f"Media Display - {self.project.name}"

    def get_enabled_layer_names(self):
        """Retorna los nombres de las capas habilitadas"""
        return list(self.enabled_layers.values_list('name', flat=True))