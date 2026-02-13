# -*- coding: utf-8 -*-
from django.dispatch import Signal

role_added = Signal(providing_args=["role"])
role_deleted = Signal(providing_args=["role"])

user_updated = Signal(providing_args=["username", "user_obj", "user_dict", "roles"])
user_roles_updated = Signal(providing_args=["username", "roles"])
user_deleted = Signal(providing_args=["username"])
