# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def copy_widget_layers(apps, schema_editor):
    PanelWidget = apps.get_model('gvsigol_plugin_panels', 'PanelWidget')
    Layer = apps.get_model('gvsigol_services', 'Layer')
    valid_ids = set(Layer.objects.values_list('id', flat=True))
    for widget in PanelWidget.objects.all().iterator():
        config = widget.config if isinstance(widget.config, dict) else {}
        try:
            layer_id = int(config.get('layer_id'))
        except (TypeError, ValueError):
            continue
        if layer_id in valid_ids:
            widget.layer_id = layer_id
            widget.save(update_fields=['layer'])


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_panels', '0003_remove_panel_status'),
        ('gvsigol_services', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='panel',
            name='project',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='panels', to='gvsigol_core.project'),
        ),
        migrations.AddConstraint(
            model_name='panel',
            constraint=models.UniqueConstraint(
                condition=Q(project__isnull=True),
                fields=('slug',),
                name='unique_standalone_panel_slug',
            ),
        ),
        migrations.AlterField(
            model_name='paneldataset',
            name='project',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='panel_datasets', to='gvsigol_core.project'),
        ),
        migrations.AddField(
            model_name='paneldataset',
            name='panel',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='datasets', to='gvsigol_plugin_panels.panel'),
        ),
        migrations.AddConstraint(
            model_name='paneldataset',
            constraint=models.CheckConstraint(
                check=Q(project__isnull=False) | Q(panel__isnull=False),
                name='panel_dataset_has_scope',
            ),
        ),
        migrations.AddField(
            model_name='panelwidget',
            name='layer',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='panel_widgets', to='gvsigol_services.layer'),
        ),
        migrations.RunPython(copy_widget_layers, migrations.RunPython.noop),
    ]
