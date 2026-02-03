# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.postgres.fields import JSONField
from gvsigol_core.models import Project

class SimpleDownloadConfig(models.Model):
    """
    Configuración del plugin Simple Download por proyecto
    """
    project = models.OneToOneField(Project, on_delete=models.CASCADE, verbose_name="Proyecto")
    file_configs = JSONField(default=list, blank=True, verbose_name="Configuración de archivos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración Simple Download"
        verbose_name_plural = "Configuraciones Simple Download"
    
    def __str__(self):
        return f"Simple Download - {self.project.name}"
    
    
    def get_file_config(self, file_id):
        """Obtener configuración de un archivo específico"""
        if isinstance(self.file_configs, list):
            for file_config in self.file_configs:
                if file_config.get('id') == file_id:
                    return file_config
            return {}
        return self.file_configs.get(str(file_id), {})

    def get_all_files(self):
        """Obtener todos los archivos ordenados por ID"""
        if isinstance(self.file_configs, list):
            return sorted(self.file_configs, key=lambda x: x.get('id', 0))
        return sorted(self.file_configs.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)