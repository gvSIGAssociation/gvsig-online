from gvsigol.celery import app as celery_app
import logging
from gvsigol_auth import auth_backend
LOGGER = 'gvsigol'

@celery_app.task(bind=True)
def update_user_cache(self):
    """
    Updates the user cache to allow complex search on Keycloak based installations
    """
    from gvsigol_auth.models import UserCache, User
    from django.conf import settings
    from gvsigol_auth.settings import USE_USER_CACHE
    if not USE_USER_CACHE:
        return
    logging.getLogger(LOGGER).info("starting update_user_cache")
    """
    Use users from auth_backend  (Keycloak, GVLOGIN, Django User model, etc.) to populate the cache,
    then use local users from Django User model to set editable flag.
    """
    logging.getLogger(LOGGER).info(f'USE_USER_CACHE: {USE_USER_CACHE}')
    for user in auth_backend.get_users_details():
        try:
            user_cache = UserCache.objects.get(username=user.get('username'))
        except UserCache.DoesNotExist:
            user_cache = UserCache(username=user.get('username'))
        user_cache.user_id = user.get('id')
        user_cache.email = user.get('email')
        user_cache.first_name = user.get('first_name')
        user_cache.last_name = user.get('last_name')
        user_cache.is_superuser = user.get('is_superuser')
        user_cache.is_staff = user.get('is_staff')
        user_cache.roles = ";".join(user.get('roles'))
        try:
            user = User.objects.get(username=user.get('username'))
            user_cache.editable = user.userproperties.editable
        except:
            user_cache.editable = True
        user_cache.save()
        user_cache.update_searchable_data()

    for user in User.objects.all():
        try:
            user_cache = UserCache.objects.get(username=user.username)
            try:
                user_cache.editable = user.userproperties.editable
            except:
                user_cache.editable = True
            user_cache.save()
        except UserCache.DoesNotExist:
            user_cache = UserCache(username=user.username)
            user_cache.user_id = user.id
            user_cache.email = user.email
            #logging.getLogger(LOGGER).info(f"User.user_cache.email: {user_cache.email}")
            user_cache.first_name = user.first_name
            user_cache.last_name = user.last_name
            user_cache.roles = ";".join([role.name for role in user.roles_set.all()])
            user_cache.is_superuser = user.is_superuser
            user_cache.is_staff = user.is_staff
            try:
                user_cache.editable = user.userproperties.editable
            except:
                user_cache.editable = True
            user_cache.save()
        user_cache.update_searchable_data()
