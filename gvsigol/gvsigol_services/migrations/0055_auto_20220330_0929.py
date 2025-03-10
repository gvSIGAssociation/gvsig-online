# Generated by Django 2.2.27 on 2022-03-30 09:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0054_auto_20220211_1145'),
    ]

    operations = [
        migrations.CreateModel(
            name='LayerWriteRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.TextField()),
                ('layer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_services.Layer')),
            ],
        ),
        migrations.CreateModel(
            name='LayerReadRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.TextField()),
                ('layer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_services.Layer')),
            ],
        ),
        migrations.AddIndex(
            model_name='layerwriterole',
            index=models.Index(fields=['layer', 'role'], name='gvsigol_ser_layer_i_6ecf45_idx'),
        ),
        migrations.AddIndex(
            model_name='layerreadrole',
            index=models.Index(fields=['layer', 'role'], name='gvsigol_ser_layer_i_0182f1_idx'),
        ),
    ]
