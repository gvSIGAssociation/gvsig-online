

from django.apps import AppConfig

class GvsigolAuthConfig(AppConfig):
    name = 'gvsigol_auth'

    def ready(self):
        from actstream import registry
        from django.contrib.auth import get_user_model
        registry.register(get_user_model())
        try:
            # ensure we have a proper environment
            self._ensure_admin_group()
        except:
            # Don't fail when we are migrating applications!!
            pass
    
    def _ensure_admin_group(self):
        from gvsigol_auth.models import UserGroup, UserGroupUser
        from gvsigol_auth.utils import is_superuser
        from django.contrib.auth.models import User 
        try:
            group = UserGroup.objects.get(name='admin')
        except UserGroup.DoesNotExist:
            group = UserGroup()
            group.name = 'admin'
            group.description = 'admin group'
            group.save()
        
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            if UserGroupUser.objects.filter(user=user, user_group=group).count()==0:
                ugu = UserGroupUser()
                ugu.user = user
                ugu.user_group = group
                ugu.save()
