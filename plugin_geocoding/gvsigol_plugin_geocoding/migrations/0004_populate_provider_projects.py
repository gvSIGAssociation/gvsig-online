from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_plugin_geocoding', '0003_provider_projects'),
    ]

    operations = [
        migrations.RunSQL(
            """
            INSERT INTO gvsigol_plugin_geocoding_provider_projects (provider_id, project_id)
            SELECT p.id, pr.id
            FROM gvsigol_plugin_geocoding_provider p
            CROSS JOIN gvsigol_core_project pr
            ON CONFLICT (provider_id, project_id) DO NOTHING;
            """,
            """
            DELETE FROM gvsigol_plugin_geocoding_provider_projects;
            """
        ),
    ] 