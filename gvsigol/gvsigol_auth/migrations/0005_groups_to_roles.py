# Generated by Django 2.2.27 on 2022-03-28 11:25

from django.db import migrations

def groups_to_roles(apps, schema_editor):
    UserGroup = apps.get_model("gvsigol_auth", "UserGroup")
    Role = apps.get_model("gvsigol_auth", "Role")
    for g in UserGroup.objects.all():
        try:
            if not Role.objects.filter(name=g.name).exists():
                role = Role(name=g.name, description=g.description)
                role.save()
        except Exception as e:
            print(str(e))
    try:
        from django.conf import settings
        User = apps.get_model(settings.AUTH_USER_MODEL)
        for user in User.objects.all().prefetch_related('usergroupuser_set'):
            for ugu in user.usergroupuser_set.all():
                role = Role.objects.get(name=ugu.user_group.name)
                user.role_set.add(role)
    except Exception as e:
        print(str(e))


class Migration(migrations.Migration):
    dependencies = [
        ('gvsigol_auth', '0004_role'),
    ]
    operations = [
        migrations.RunPython(groups_to_roles, reverse_code=migrations.RunPython.noop),
    ]
