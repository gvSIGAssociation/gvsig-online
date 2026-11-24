from django.db import migrations, models


def copy_project_selectable_groups(apps, schema_editor):
    """Los proyectos que tenían el interruptor global pasan a tener cada grupo seleccionable."""
    Project = apps.get_model('gvsigol_core', 'Project')
    ProjectLayerGroup = apps.get_model('gvsigol_core', 'ProjectLayerGroup')
    project_ids = list(
        Project.objects.filter(selectable_groups=True).values_list('pk', flat=True)
    )
    if not project_ids:
        return
    ProjectLayerGroup.objects.filter(
        project_id__in=project_ids,
        baselayer_group=False,
    ).update(selectable=True)


def restore_project_selectable_groups(apps, schema_editor):
    Project = apps.get_model('gvsigol_core', 'Project')
    ProjectLayerGroup = apps.get_model('gvsigol_core', 'ProjectLayerGroup')
    selectable_project_ids = set(
        ProjectLayerGroup.objects.filter(selectable=True).values_list('project_id', flat=True)
    )
    for project in Project.objects.all().only('id', 'selectable_groups'):
        flag = project.id in selectable_project_ids
        if project.selectable_groups != flag:
            project.selectable_groups = flag
            project.save(update_fields=['selectable_groups'])


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_core', '0056_docs_web_edits'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectlayergroup',
            name='selectable',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(copy_project_selectable_groups, restore_project_selectable_groups),
    ]
