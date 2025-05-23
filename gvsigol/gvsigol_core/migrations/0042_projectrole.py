# Generated by Django 2.2.27 on 2022-03-31 11:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0041_auto_20220401_0707'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.TextField()),
                ('project', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_core.Project')),
            ],
        ),
        migrations.AddIndex(
            model_name='projectrole',
            index=models.Index(fields=['project', 'role'], name='gvsigol_cor_project_0d1a20_idx'),
        ),
    ]
