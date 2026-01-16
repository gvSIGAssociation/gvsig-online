# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2024 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
@author: Signals para invalidación de caché de Mapbox GL
'''

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Style, StyleLayer, MapboxStyleCache
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Style)
def invalidate_mapbox_cache_on_style_save(sender, instance, **kwargs):
    """
    Invalida la caché de Mapbox GL cuando se guarda un Style.
    
    Busca todas las capas que usan este estilo y borra su caché,
    forzando la regeneración en la próxima petición.
    """
    try:
        # Buscar todas las capas que usan este estilo
        style_layers = StyleLayer.objects.filter(style=instance).select_related('layer')
        
        deleted_total = 0
        for sl in style_layers:
            # Borrar caché de la capa
            deleted_count, _ = MapboxStyleCache.objects.filter(layer=sl.layer).delete()
            if deleted_count > 0:
                deleted_total += deleted_count
                logger.info(
                    f"Invalidated Mapbox cache for layer {sl.layer.id} ({sl.layer.name}) "
                    f"due to style {instance.id} ({instance.name}) change"
                )
        
        if deleted_total > 0:
            logger.info(f"Total Mapbox caches invalidated: {deleted_total}")
            
    except Exception as e:
        logger.error(f"Error invalidating Mapbox cache: {e}", exc_info=True)


@receiver(post_delete, sender=Style)
def invalidate_mapbox_cache_on_style_delete(sender, instance, **kwargs):
    """
    Invalida la caché de Mapbox GL cuando se elimina un Style.
    """
    # Reutilizar la misma lógica que al guardar
    invalidate_mapbox_cache_on_style_save(sender, instance, **kwargs)


@receiver(post_save, sender=StyleLayer)
def invalidate_mapbox_cache_on_stylelayer_save(sender, instance, **kwargs):
    """
    Invalida la caché cuando se añade o modifica la relación Style-Layer.
    
    Esto cubre casos como añadir un nuevo estilo a una capa o cambiar
    la asociación entre estilos y capas.
    """
    try:
        deleted_count, _ = MapboxStyleCache.objects.filter(layer=instance.layer).delete()
        if deleted_count > 0:
            logger.info(
                f"Invalidated Mapbox cache for layer {instance.layer.id} ({instance.layer.name}) "
                f"due to StyleLayer change"
            )
    except Exception as e:
        logger.error(f"Error invalidating Mapbox cache on StyleLayer save: {e}", exc_info=True)


@receiver(post_delete, sender=StyleLayer)
def invalidate_mapbox_cache_on_stylelayer_delete(sender, instance, **kwargs):
    """
    Invalida la caché cuando se elimina la relación Style-Layer.
    """
    try:
        deleted_count, _ = MapboxStyleCache.objects.filter(layer=instance.layer).delete()
        if deleted_count > 0:
            logger.info(
                f"Invalidated Mapbox cache for layer {instance.layer.id} ({instance.layer.name}) "
                f"due to StyleLayer deletion"
            )
    except Exception as e:
        logger.error(f"Error invalidating Mapbox cache on StyleLayer delete: {e}", exc_info=True)

