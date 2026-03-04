# Data migration: fill ApplicationOrder with default list (username=null, order=0)

from django.db import migrations


def fill_default_application_order(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    ApplicationOrder = apps.get_model('gvsigol_core', 'ApplicationOrder')
    Application = apps.get_model('gvsigol_core', 'Application')
    Project = apps.get_model('gvsigol_core', 'Project')
    for app in Application.objects.using(db_alias).all():
        ApplicationOrder.objects.using(db_alias).create(
            username=None, order=0, application=app, project=None
        )
    for project in Project.objects.using(db_alias).all():
        ApplicationOrder.objects.using(db_alias).create(
            username=None, order=0, application=None, project=project
        )


def reverse_fill(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    ApplicationOrder = apps.get_model('gvsigol_core', 'ApplicationOrder')
    ApplicationOrder.objects.using(db_alias).filter(username__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0052_applicationorder'),
    ]

    operations = [
        migrations.RunPython(fill_default_application_order, reverse_fill),
    ]
