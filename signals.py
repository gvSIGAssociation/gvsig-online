# -*- coding: utf-8 -*-
from django.dispatch import Signal

role_added = Signal(providing_args=["role"])
role_deleted = Signal(providing_args=["role"])
