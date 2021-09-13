# -*- coding: utf-8 -*-


from django.db import migrations

def fix_admin_usergroup(apps, schema_editor):
    try:
        UserGroupUser = apps.get_model("gvsigol_auth", "UserGroupUser")
        UserGroup = apps.get_model("gvsigol_auth", "UserGroup")
        UserGroupUser.objects.filter(user_group__name='admin')[1:].delete()
        UserGroup.objects.filter(name='admin')[1:].delete()
    except Exception as error:
        print(error)
    
class Migration(migrations.Migration):
    """
    Fixes UserGroup where admin group has been created more than once.
    """
    dependencies = [
        ('gvsigol_auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_admin_usergroup, reverse_code=migrations.RunPython.noop),
    ]
