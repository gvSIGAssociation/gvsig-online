# Generated manually for calculated attributes feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0106_add_new_connection_type_choice'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='allow_calculated_fields',
            field=models.BooleanField(default=False),
        ),
    ]
