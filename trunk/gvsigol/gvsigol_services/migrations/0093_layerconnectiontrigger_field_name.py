# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0092_auto_20260204_1716'),
    ]

    operations = [
        migrations.AddField(
            model_name='layerconnectiontrigger',
            name='field_name',
            field=models.CharField(
                blank=True, 
                null=True, 
                help_text='Name of the field that will be calculated by this trigger (only for calculated field triggers)', 
                max_length=150
            ),
        ),
        migrations.AddField(
            model_name='layerconnectiontrigger',
            name='created_by',
            field=models.CharField(default='', max_length=100),
        ),
        # Remove old constraint and add new one
        migrations.RemoveConstraint(
            model_name='layerconnectiontrigger',
            name='unique_conn_trigger_per_layer',
        ),
        migrations.AddConstraint(
            model_name='layerconnectiontrigger',
            constraint=models.UniqueConstraint(fields=['layer', 'trigger'], name='unique_trigger_per_layer'),
        ),
    ]

