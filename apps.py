

from django.apps import AppConfig

class GvsigolAuthConfig(AppConfig):
    name = 'gvsigol_auth'

    def ready(self):
        from actstream import registry
        from django.contrib.auth import get_user_model
        registry.register(get_user_model())
        try:
            # ensure we have a proper environment
            from gvsigol_auth.utils import ensure_admin_group
            ensure_admin_group()
        except:
            # Don't fail when we are migrating applications!!
            pass
