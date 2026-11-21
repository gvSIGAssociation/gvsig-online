# Escrita a mano en el formato de Django 2.2 (compatible con Django 2.x y 4.x).
#
# - options (opcional) en marcas, líneas y polígonos: los existentes quedan con NULL y se
#   siguen generando exactamente igual que antes (ver symbol_options.py).
# - Grosores, tamaño y opacidad de las marcas pasan de entero a decimal (0.5 px...).
#   IntegralFloatField lee como int los valores sin decimales, así que lo ya guardado
#   se sigue viendo y exportando igual ("1", no "1.0"). PostgreSQL convierte la columna
#   integer -> double precision sin pérdida.

from django.db import migrations, models

import gvsigol_symbology.models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_symbology', '0012_textsymbolizer_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='marksymbolizer',
            name='options',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='linesymbolizer',
            name='options',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='polygonsymbolizer',
            name='options',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='marksymbolizer',
            name='opacity',
            field=gvsigol_symbology.models.IntegralFloatField(default=1),
        ),
        migrations.AlterField(
            model_name='marksymbolizer',
            name='size',
            field=gvsigol_symbology.models.IntegralFloatField(default=8),
        ),
        migrations.AlterField(
            model_name='marksymbolizer',
            name='stroke_width',
            field=gvsigol_symbology.models.IntegralFloatField(default=1),
        ),
        migrations.AlterField(
            model_name='linesymbolizer',
            name='stroke_width',
            field=gvsigol_symbology.models.IntegralFloatField(default=1),
        ),
        migrations.AlterField(
            model_name='polygonsymbolizer',
            name='stroke_width',
            field=gvsigol_symbology.models.IntegralFloatField(default=1),
        ),
    ]
