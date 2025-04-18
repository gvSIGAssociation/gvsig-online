# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2020-10-20 14:47


from django.db import migrations
from gvsigol_services.triggers import install_procedure, drop_procedure

TRIGGER_FUNCTION_SCHEMA = "public"
TRIGGER_FUNCTION_NAME = "gol_geocoder_inverso_icv_gva_es"
TRIGGER_FUNCTION_SIGNATURE = "public.gol_geocoder_inverso_icv_gva_es(text)"

TRIGGER_FUNCTION_DEF = """CREATE OR REPLACE FUNCTION public.gol_geocoder_inverso_icv_gva_es() RETURNS trigger AS $$
        # TODO: comprobar que no es tipo punto
        import requests
        timeout = 10
        #https://descargas.icv.gva.es/server_api/geocodificador/geocoder.php?x=728414.6128043989&y=4356747.200758437
        geocoder_url = 'https://descargas.icv.gva.es/server_api/geocodificador/geocoder.php'
        try:
            column_name = TD["args"][0]
            plan = plpy.prepare("SELECT * FROM geometry_columns WHERE f_table_name = $1 AND f_table_schema = $2", ["text","text"])        
            rv = plpy.execute(plan,[TD["table_name"],TD["table_schema"]],1)
            geom_column = rv[0]["f_geometry_column"]
            
            plan = plpy.prepare("SELECT st_x(ST_GeometryN(ST_Transform($1,25830), 1)) as x, st_y(ST_GeometryN(ST_Transform($1,25830), 1)) as y", ["text"])
            rv = plpy.execute(plan,[TD["new"][geom_column]],1)
            x = rv[0]["x"]
            y = rv[0]["y"]
            
            _data = {'x': x, 'y': y}
            r = requests.get(geocoder_url, params=_data, timeout=timeout)
            response = r.json()
            address = response.get('dtipo_vial', '') + ' ' + response.get('nombre', '')
            if response.get('dtipo_porpk'):
                address += ' ' + response.get('dtipo_porpk')
            if response.get('numero'):
                address += ' ' + response.get('numero')
            if response.get('municipio'):
                address += ', ' + response.get('municipio') 
            TD["new"][column_name] = address 
        except plpy.SPIError as e:
            TD["new"][column_name] = ''
            plpy.log("ERROR geocoder_inverso_cartociudad: " + str(e))
        except Exception as e:
            TD["new"][column_name] = ''
            plpy.log(str(e))
        finally:
            return "MODIFY"
    $$ LANGUAGE plpython2u;
    """

def insert_def(apps, schema_editor):
    try:
        from django.utils.translation import ugettext_noop as _
        TriggerProcedure = apps.get_model("gvsigol_services", "TriggerProcedure")
        procedure = TriggerProcedure()
        procedure.signature = TRIGGER_FUNCTION_SIGNATURE
        procedure.func_name = TRIGGER_FUNCTION_NAME
        procedure.func_schema = TRIGGER_FUNCTION_SCHEMA
        procedure.label = _('Inverse Geocoder ICV')
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
        ('gvsigol_services', '0044_fill_layerresource_title'),
    ]

    operations = [
        migrations.RunPython(insert_def, reverse_code=remove_def),
    ]
