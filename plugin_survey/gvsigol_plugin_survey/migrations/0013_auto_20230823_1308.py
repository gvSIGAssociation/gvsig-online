# Generated by Django 2.2.28 on 2023-08-23 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_survey', '0012_auto_20230822_1159'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='surveyreadgroup',
            index=models.Index(fields=['survey', 'role'], name='gvsigol_plu_survey__22f61e_idx'),
        ),
        migrations.AddIndex(
            model_name='surveywritegroup',
            index=models.Index(fields=['survey', 'role'], name='gvsigol_plu_survey__b3f4b3_idx'),
        ),
        migrations.AddConstraint(
            model_name='surveyreadgroup',
            constraint=models.UniqueConstraint(fields=('survey', 'role'), name='unique_read_permission_per_role_and_survey'),
        ),
        migrations.AddConstraint(
            model_name='surveywritegroup',
            constraint=models.UniqueConstraint(fields=('survey', 'role'), name='unique_write_permission_per_role_and_survey'),
        ),
    ]
