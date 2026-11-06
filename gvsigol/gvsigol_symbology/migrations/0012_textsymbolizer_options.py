# Escrita a mano en el formato de Django 2.2 (compatible con Django 2.x y 4.x).
# Campo nuevo opcional: las etiquetas existentes quedan con options = NULL y se
# siguen generando exactamente igual que antes.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_symbology', '0011_mapboxstylecache'),
    ]

    operations = [
        migrations.AddField(
            model_name='textsymbolizer',
            name='options',
            field=models.TextField(blank=True, null=True),
        ),
    ]
