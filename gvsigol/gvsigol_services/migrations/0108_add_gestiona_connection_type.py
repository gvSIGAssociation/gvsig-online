# Generated manually for Gestiona API connection type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0107_layer_allow_calculated_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='connection',
            name='type',
            field=models.CharField(
                choices=[
                    ('PostGIS', 'PostgreSQL/PostGIS'),
                    ('Oracle', 'Oracle'),
                    ('SQLServer', 'SQL Server'),
                    ('indenova', 'InDenova'),
                    ('segex', 'SEGEX'),
                    ('sharepoint', 'SharePoint'),
                    ('padron-atm', 'Padrón ATM'),
                    ('sgarexws', 'SgaRexWS'),
                    ('gestiona', 'Gestiona'),
                ],
                default='PostGIS',
                max_length=50,
            ),
        ),
    ]
