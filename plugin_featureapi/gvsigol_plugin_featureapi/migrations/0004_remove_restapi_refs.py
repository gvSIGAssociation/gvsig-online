import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion

def apply(apps, schema_editor):
    try:
        sql = """
        SELECT
            tc.constraint_name
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name='gvsigol_plugin_restapi_featurechange'
        AND tc.table_schema='public'
        AND kcu.column_name = 'layer_id'
        AND ccu.table_name = 'gvsigol_services_layer'
        AND ccu.table_schema = 'public'
        """
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(sql)
            r = cursor.fetchall()
            if len(r) > 0:
                constraint_name = r[0][0]
                sql = """
                ALTER TABLE public.gvsigol_plugin_restapi_featurechange
                DROP CONSTRAINT "{}"
                """.format(constraint_name)
                schema_editor.execute(sql)
    except Exception as e:
        # Ignore errors since it is expected to fail if plugin_restapi
        # is not installed.
        # Rollback transaction to get a clean DB connection status
        # for Django migration system
        schema_editor.execute("ROLLBACK")

class Migration(migrations.Migration):
    """
    Remove foreign key to Layer in gvsigol_plugin_restapi_featurechange,
    since it will block any Layer deletion that is still referred from
    that table. Normally Django automatically handles this problem, but
    it will not do so when gvsigol_plugin_restapi is not installed.
    """
    dependencies = [
        ('gvsigol_plugin_featureapi', '0003_copy_data_v2'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop)
    ]
