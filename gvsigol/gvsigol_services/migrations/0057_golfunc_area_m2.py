# -*- coding: utf-8 -*-

from django.db import migrations
from gvsigol_services.triggers import install_procedure, drop_procedure

TRIGGER_FUNCTION_SCHEMA = "public"
TRIGGER_FUNCTION_NAME = "gol_area_m2"
TRIGGER_FUNCTION_SIGNATURE = "public.gol_area_m2(text)"

TRIGGER_FUNCTION_DEF = """CREATE OR REPLACE FUNCTION public.gol_area_m2() RETURNS trigger AS $$
        try:
            column_name = TD["args"][0]
            plan = plpy.prepare("SELECT * FROM geometry_columns WHERE f_table_name = $1 AND f_table_schema = $2", ["text","text"])        
            rv = plpy.execute(plan,[TD["table_name"],TD["table_schema"]],1)
            geom_column = rv[0]["f_geometry_column"]
            
            plan = plpy.prepare("SELECT ST_Area($1) as aream2", ["text"])
            rv = plpy.execute(plan,[TD["new"][geom_column]],1)
            TD["new"][column_name] = rv[0]["aream2"]
        except plpy.SPIError as e:
            TD["new"][column_name] = ''
            plpy.log("ERROR gol_area_m2: " + str(e))
        except Exception as e:
            TD["new"][column_name] = ''
            plpy.log(str(e))
        finally:
            return "MODIFY"
    $$ LANGUAGE plpython3u;
    """

def insert_def(apps, schema_editor):
    try:
        from django.utils.translation import ugettext_noop as _
        TriggerProcedure = apps.get_model("gvsigol_services", "TriggerProcedure")
        procedure = TriggerProcedure()
        procedure.signature = TRIGGER_FUNCTION_SIGNATURE
        procedure.func_name = TRIGGER_FUNCTION_NAME
        procedure.func_schema = TRIGGER_FUNCTION_SCHEMA
        procedure.label = _('Area (m2)')
        procedure.definition_tpl = TRIGGER_FUNCTION_DEF
        procedure.activation = 'BEFORE'
        procedure.event = 'INSERT OR UPDATE'
        procedure.orientation = 'ROW'
        procedure.save()
        
        install_procedure(procedure.pk)

    except Exception as error:
        print(error)

def remove_def(apps, schema_editor):
    try:
        drop_procedure(TRIGGER_FUNCTION_SIGNATURE)
        TriggerProcedure = apps.get_model("gvsigol_services", "TriggerProcedure")
        TriggerProcedure.objects.filter(signature=TRIGGER_FUNCTION_SIGNATURE).delete()
    except Exception as error:
        print(error)
        
class Migration(migrations.Migration):
    dependencies = [
        ('gvsigol_services', '0056_layerreadwriteroles'),
    ]

    operations = [
        migrations.RunPython(insert_def, reverse_code=remove_def),
    ]
