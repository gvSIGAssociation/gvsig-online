# Generated manually for the panel administration and ACL.
from django.db import migrations, models
import django.db.models.deletion


def copy_project_roles(apps, schema_editor):
    Panel = apps.get_model('gvsigol_plugin_panels', 'Panel')
    PanelRole = apps.get_model('gvsigol_plugin_panels', 'PanelRole')
    ProjectRole = apps.get_model('gvsigol_core', 'ProjectRole')
    rows = []
    for panel in Panel.objects.all().iterator():
        panel.name = panel.slug or panel.title
        panel.save(update_fields=['name'])
        for project_role in ProjectRole.objects.filter(project_id=panel.project_id):
            rows.append(PanelRole(
                panel_id=panel.id,
                role=project_role.role,
                permission=project_role.permission,
            ))
    if rows:
        PanelRole.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_panels', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='panel',
            name='name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='panel',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='PanelRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.TextField()),
                ('permission', models.TextField(
                    choices=[('read', 'read'), ('manage', 'manage')],
                    default='read',
                )),
                ('panel', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='gvsigol_plugin_panels.panel',
                )),
            ],
        ),
        migrations.AddIndex(
            model_name='panelrole',
            index=models.Index(
                fields=['panel', 'permission', 'role'],
                name='gvsigol_plu_panel_i_b182b1_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='panelrole',
            constraint=models.UniqueConstraint(
                fields=('panel', 'permission', 'role'),
                name='unique_permission_role_and_panel',
            ),
        ),
        migrations.RunPython(copy_project_roles, migrations.RunPython.noop),
    ]
