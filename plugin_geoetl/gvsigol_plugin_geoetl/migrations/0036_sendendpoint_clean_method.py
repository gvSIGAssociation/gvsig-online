from django.db import migrations

METHODS = ('GET', 'POST', 'PUT', 'DELETE')


def clean_methods(apps, schema_editor):
    SendEndpoint = apps.get_model('gvsigol_plugin_geoetl', 'SendEndpoint')
    for row in SendEndpoint.objects.exclude(method__in=METHODS):
        text = (row.method or '').upper()
        row.method = next((m for m in METHODS if m in text), 'POST')
        row.save(update_fields=['method'])


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geoetl', '0035_etlstatus_celery_task_id'),
    ]

    operations = [
        migrations.RunPython(clean_methods, migrations.RunPython.noop),
    ]
