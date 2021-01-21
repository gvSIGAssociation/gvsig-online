# -*- coding: utf-8 -*-
from django.dispatch import Signal

layer_created = Signal(providing_args=["layer"])
layer_updated = Signal(providing_args=["layer"])
layer_deleted = Signal(providing_args=["layer"])
layerresource_created = Signal(providing_args=["layer", "featid", "resource_id", 'path', 'user'])
layerresource_deleted = Signal(providing_args=["layer", "featid", "resource_id", "historical_path", 'user'])