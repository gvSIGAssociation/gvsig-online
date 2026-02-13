from django.db import migrations

class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("gvsigol_auth", "0009_create_unaccent_trgm"),
    ]

    def forwards(apps, schema_editor):
        try:
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
                )
                has_trgm = cursor.fetchone() is not None

            if has_trgm:
                schema_editor.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS
                        usercache_searchable_data_trgm_idx
                    ON gvsigol_auth_usercache
                    USING gin (searchable_data gin_trgm_ops);
                """)
            else:
                schema_editor.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS
                        usercache_searchable_data_btree_idx
                    ON gvsigol_auth_usercache (searchable_data);
                """)
        except:
            import logging
            logging.getLogger('gvsigol').exception("Error creating UserCache indexes")

    operations = [
        migrations.RunPython(forwards, reverse_code=migrations.RunPython.noop),
    ]