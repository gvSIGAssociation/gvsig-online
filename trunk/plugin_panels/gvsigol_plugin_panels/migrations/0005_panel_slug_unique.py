# -*- coding: utf-8 -*-
from django.db import migrations, models


def deduplicate_slugs(apps, schema_editor):
    """Los paneles con proyecto podían repetir slug entre proyectos distintos.

    Ahora el slug es la URL pública del panel, así que hay que resolver los
    choques antes de crear el índice único.
    """
    Panel = apps.get_model('gvsigol_plugin_panels', 'Panel')
    seen = set()
    for panel in Panel.objects.order_by('id'):
        slug = panel.slug
        if slug not in seen:
            seen.add(slug)
            continue
        n = 2
        candidate = '%s-%s' % (slug[:150], n)
        while candidate in seen or Panel.objects.filter(slug=candidate).exclude(pk=panel.pk).exists():
            n += 1
            candidate = '%s-%s' % (slug[:150], n)
        panel.slug = candidate
        panel.save(update_fields=['slug'])
        seen.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_panels', '0004_global_panels'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='panel',
            name='unique_standalone_panel_slug',
        ),
        migrations.AlterUniqueTogether(
            name='panel',
            unique_together=set(),
        ),
        migrations.RunPython(deduplicate_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='panel',
            name='slug',
            field=models.SlugField(max_length=160, unique=True),
        ),
    ]
