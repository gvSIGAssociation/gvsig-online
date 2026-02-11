# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0097_migrate_area_triggers'),
    ]

    operations = [
        migrations.AddField(
            model_name='connectiontrigger',
            name='language',
            field=models.CharField(
                choices=[
                    ('plpgsql', 'PL/pgSQL (database trigger)'),
                    ('python', 'Python (application-level)')
                ],
                default='plpgsql',
                help_text='Language of the trigger code: PL/pgSQL for database triggers, Python for application-level triggers',
                max_length=10
            ),
        ),
    ]


