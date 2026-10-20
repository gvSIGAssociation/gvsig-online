from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0102_layer_annotations'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='layer',
            name='annotations',
        ),
    ]
