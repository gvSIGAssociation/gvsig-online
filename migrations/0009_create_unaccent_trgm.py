from django.db import migrations

class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("gvsigol_auth", "0008_usercache"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                BEGIN
                    CREATE EXTENSION IF NOT EXISTS pg_trgm;
                EXCEPTION
                    WHEN insufficient_privilege THEN
                        NULL;
                END;

                BEGIN
                    CREATE EXTENSION IF NOT EXISTS unaccent;
                EXCEPTION
                    WHEN insufficient_privilege THEN
                        NULL;
                END;
            END
            $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    BEGIN
                        DROP EXTENSION IF EXISTS pg_trgm;
                    EXCEPTION
                        WHEN insufficient_privilege THEN
                            NULL;
                    END;
                    BEGIN
                        DROP EXTENSION IF EXISTS unaccent;
                    EXCEPTION
                        WHEN insufficient_privilege THEN
                            NULL;
                    END;
                END
                $$;
            """,
        )
    ]