# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.postgres.fields import JSONField
from gvsigol_core.models import Project

class SimpleDownloadConfig(models.Model):
    """
    Configuración del plugin Simple Download por proyecto
    """
    project = models.OneToOneField(Project, on_delete=models.CASCADE, verbose_name="Proyecto")
    file_configs = JSONField(default=dict, blank=True, verbose_name="Configuración de archivos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración Simple Download"
        verbose_name_plural = "Configuraciones Simple Download"
    
    def __str__(self):
        return f"Simple Download - {self.project.name}"
    
    
    def get_file_config(self, file_id):
        """Obtener configuración de un archivo específico"""
        return self.file_configs.get(str(file_id), {})

    def add_file_config(self, title, file_url, **extra):
        """Añadir un nuevo archivo"""
        existing_ids = [int(k) for k in self.file_configs.keys() if k.isdigit()]
        new_id = str(max(existing_ids) + 1) if existing_ids else "1"
        self.file_configs[new_id] = {
            "title": title,
            "file_url": file_url,
            **extra  # Permite añadir campos adicionales
        }
        self.save()
        return new_id

    def update_file_config(self, file_id, **kwargs):
        """Actualizar configuración de un archivo"""
        if str(file_id) in self.file_configs:
            self.file_configs[str(file_id)].update(kwargs)
            self.save()
            return True
        return False

    def delete_file_config(self, file_id):
        """Eliminar un archivo"""
        if str(file_id) in self.file_configs:
            del self.file_configs[str(file_id)]
            self.save()
            return True
        return False

    def get_all_files(self):
        """Obtener todos los archivos ordenados por ID"""
        return sorted(self.file_configs.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)