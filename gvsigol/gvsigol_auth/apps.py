from __future__ import unicode_literals

from django.apps import AppConfig

class GvsigolAuthConfig(AppConfig):
    name = 'gvsigol_auth'

    def ready(self):
        from actstream import registry
        from django.contrib.auth import get_user_model
        registry.register(get_user_model())
