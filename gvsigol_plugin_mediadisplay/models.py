# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.postgres.fields import JSONField
from gvsigol_core.models import Project

class MediaDisplayConfig(models.Model):
    """
    Configuración del plugin MediaDisplay por proyecto
    """
    project = models.OneToOneField(Project, on_delete=models.CASCADE, verbose_name="Proyecto")
    layer_configs = JSONField(default=dict, blank=True, verbose_name="Configuración de capas")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración Media Display"
        verbose_name_plural = "Configuraciones Media Display"
    
    def __str__(self):
        return f"Media Display - {self.project.name}"
    
    def get_enabled_layer_names(self):
        """Obtener nombres de las capas habilitadas desde layer_configs"""
        return list(self.layer_configs.keys())
    
    def get_layer_config(self, layer_id):
        """Obtener configuración de una capa específica"""
        return self.layer_configs.get(str(layer_id), {})