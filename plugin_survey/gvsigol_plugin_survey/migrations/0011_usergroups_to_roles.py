from django.db import migrations
from django.apps import apps as global_apps

def groups_to_roles(apps, schema_editor):
    UserGroup = apps.get_model("gvsigol_auth", "UserGroup")
    Role = apps.get_model("gvsigol_auth", "Role")
    SurveyReadGroup = apps.get_model("gvsigol_plugin_survey", "SurveyReadGroup")
    SurveyWriteGroup = apps.get_model("gvsigol_plugin_survey", "SurveyWriteGroup")
    for g in SurveyReadGroup.objects.all():
        try:
            g.role = g.user_group.name
            g.save()
        except:
            print(str(e))

    for g in SurveyWriteGroup.objects.all():
        try:
            g.role = g.user_group.name
            g.save()
        except:
            print(str(e))


class Migration(migrations.Migration):
    dependencies = [
        ('gvsigol_plugin_survey', '0010_auto_20230822_1025'),
    ]
    operations = [
        migrations.RunPython(groups_to_roles, reverse_code=migrations.RunPython.noop),
    ]

