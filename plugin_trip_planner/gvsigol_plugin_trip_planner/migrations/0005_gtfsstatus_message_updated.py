from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_trip_planner', '0004_remove_gtfsstatus_id_ws'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gtfsstatus',
            name='message',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='gtfsstatus',
            name='updated',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
