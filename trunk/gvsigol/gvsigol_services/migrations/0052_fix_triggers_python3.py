# -*- coding: utf-8 -*-


from django.db import migrations
from gvsigol_services.triggers import install_procedure
import ast, json
from gvsigol_services.backend_postgis import Introspect

def get_db_connect_from_datastore(datastore):
    params = json.loads(datastore.connection_params)
    host = params['host']
    port = params['port']
    dbname = params['database']
    user = params['user']
    passwd = params['passwd']
    i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
    return i, params.get('schema', 'public')

def has_field(layer, field_name):
    layer_conf = ast.literal_eval(layer.conf) if layer.conf else {}
    fields = layer_conf.get('fields', [])
    for field in fields:
        if field.get('name') == field_name:
            return True
    return False

def install(trigger):
    # model methods can't be used from migrations
    trigger_name = get_name(trigger)
    i, target_schema = get_db_connect_from_datastore(trigger.layer.datastore)
    target_table = trigger.layer.source_name if trigger.layer.source_name else trigger.layer.name
    i.install_trigger(trigger_name, target_schema, target_table,
                    trigger.procedure.activation, trigger.procedure.event, trigger.procedure.orientation, '', trigger.procedure.func_schema, trigger.procedure.func_name, [trigger.field])
    i.close()

def drop(trigger):
    trigger_name = get_name(trigger)
    i, target_schema = get_db_connect_from_datastore(trigger.layer.datastore)
    target_table = trigger.layer.source_name if trigger.layer.source_name else trigger.layer.name
    i.drop_trigger(trigger_name, target_schema, target_table)
    i.close()

def get_name(trigger):
    return trigger.procedure.func_name + "_" + trigger.field + "_trigger"

def insert_def(apps, schema_editor):
    try:
        from django.utils.translation import ugettext_noop as _
        TriggerProcedure = apps.get_model("gvsigol_services", "TriggerProcedure")
        for procedure in TriggerProcedure.objects.filter(func_name=''):
            if procedure.signature == 'public.gol_geocoder_inverso_cartociudad(text)':
                procedure.func_name = 'gol_geocoder_inverso_cartociudad'
            elif procedure.signature == 'public.gol_geocoder_inverso_icv_gva_es(text)':
                procedure.func_name = 'gol_geocoder_inverso_icv_gva_es'
            procedure.save()
            install_procedure(procedure.pk)
        Trigger = apps.get_model("gvsigol_services", "Trigger")
        for trigger in Trigger.objects.all():
            try:
                drop(trigger)
            except:
                pass
            install(trigger)
    except Exception as error:
        print(error)
    
class Migration(migrations.Migration):
    """
    Fixes triggers, they were broken by the migration script 2to3 during
    Python 3 migration.
    """
    dependencies = [
        ('gvsigol_services', '0051_layer_vector_tile'),
    ]

    operations = [
        migrations.RunPython(insert_def, reverse_code=migrations.RunPython.noop),
    ]
