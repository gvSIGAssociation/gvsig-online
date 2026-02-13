# -*- coding: utf-8 -*-


from django.db import migrations

def fill_user_properties(apps, schema_editor):
    try:
        User = apps.get_model("auth", "User")
        UserProperties = apps.get_model("gvsigol_auth", "UserProperties")
        from django.conf import settings
        editable = (not settings.AUTH_READONLY_USERS)
        for user in User.objects.all():
            UserProperties.objects.get_or_create(user=user, editable=editable)
    except Exception as error:
        import logging
        logging.getLogger('gvsigol').error(f'Error filling user properties: {error}')
    
class Migration(migrations.Migration):
    """
    Create UserProperties for existing users.
    Editable flag is set based on the AUTH_READONLY_USERS setting.
    For most installations, where AUTH_READONLY_USERS is False, all existing users
    will be defind as editable.
    For selected installations where AUTH_READONLY_USERS is True, an ad-hoc
    update procedure may be needed to complement this migration.
    """
    dependencies = [
        ('gvsigol_auth', '0006_userproperties'),
    ]

    operations = [
        migrations.RunPython(fill_user_properties, reverse_code=migrations.RunPython.noop),
    ]
