# -*- coding: utf-8 -*-
from django.dispatch import Signal

layer_created = Signal(providing_args=["layer"])
layer_updated = Signal(providing_args=["layer"])
layer_deleted = Signal(providing_args=["layer"])