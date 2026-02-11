# -*- coding: utf-8 -*-
from django.db import migrations
from django.conf import settings
import json


def get_introspect_from_connection(connection):
    """
    Crea una instancia de Introspect desde un modelo Connection histórico.
    Retorna (introspect, params) o (None, None) si falla.
    """
    try:
        from gvsigol_services.backend_postgis import Introspect
        
        # Obtener parámetros de conexión
        if connection.connection_params:
            if isinstance(connection.connection_params, str):
                params = json.loads(connection.connection_params)
            else:
                params = connection.connection_params
        else:
            params = {}
        
        host = params.get('host', 'localhost')
        port = params.get('port', '5432')
        dbname = params.get('database', '')
        user = params.get('user', '')
        passwd = params.get('passwd', params.get('password', ''))
        
        i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
        return i, params
    except Exception as e:
        print(f'        Error conectando a la base de datos: {e}')
        return None, None


def get_schema_and_table_from_layer(layer):
    """
    Obtiene el esquema y la tabla de una capa.
    """
    # El source_name contiene el nombre de la tabla (puede incluir esquema)
    source_name = layer.source_name if layer.source_name else layer.name
    
    # El esquema se puede obtener del datastore
    if layer.datastore:
        if layer.datastore.connection_params:
            if isinstance(layer.datastore.connection_params, str):
                params = json.loads(layer.datastore.connection_params)
            else:
                params = layer.datastore.connection_params
            schema = params.get('schema', 'public')
        else:
            schema = 'public'
    else:
        schema = 'public'
    
    return schema, source_name


def get_geometry_field(introspect, table, schema):
    """Obtiene el nombre del campo de geometría de una tabla."""
    try:
        geom_columns = introspect.get_geometry_columns(table, schema)
        if geom_columns and len(geom_columns) > 0:
            return geom_columns[0]
    except Exception:
        pass
    return 'wkb_geometry'


def get_pk_field(introspect, table, schema):
    """Obtiene el nombre del campo de clave primaria de una tabla."""
    try:
        pk_columns = introspect.get_pk_columns(table, schema)
        if pk_columns and len(pk_columns) > 0:
            return pk_columns[0]
    except Exception:
        pass
    return 'ogc_fid'


def migrate_area_triggers(apps, schema_editor):
    """
    Migra las capas que usan el trigger antiguo gol_area_m2 al nuevo sistema
    de ConnectionTrigger (calc_area_native).
    
    Pasos:
    1. Buscar todas las capas que usan el trigger gol_area_m2
    2. Para cada capa:
       a. Verificar si la conexión del datastore tiene calc_area_native
       b. Si no lo tiene, duplicarlo desde la conexión del sistema
       c. Crear LayerConnectionTrigger para vincular la capa
       d. Eliminar el trigger antiguo de la base de datos
       e. Instalar el nuevo trigger en la base de datos
       f. Eliminar el Trigger antiguo del modelo
    """
    Trigger = apps.get_model('gvsigol_services', 'Trigger')
    TriggerProcedure = apps.get_model('gvsigol_services', 'TriggerProcedure')
    Layer = apps.get_model('gvsigol_services', 'Layer')
    Connection = apps.get_model('gvsigol_services', 'Connection')
    ConnectionTrigger = apps.get_model('gvsigol_services', 'ConnectionTrigger')
    LayerConnectionTrigger = apps.get_model('gvsigol_services', 'LayerConnectionTrigger')
    
    # Buscar el TriggerProcedure de área
    AREA_SIGNATURE = "public.gol_area_m2(text)"
    try:
        area_procedure = TriggerProcedure.objects.get(signature=AREA_SIGNATURE)
    except TriggerProcedure.DoesNotExist:
        print('  ⚠ TriggerProcedure gol_area_m2 no encontrado. Nada que migrar.')
        return
    
    # Buscar triggers que usan este procedimiento
    old_triggers = Trigger.objects.filter(procedure=area_procedure)
    if not old_triggers.exists():
        print('  ℹ No hay capas usando el trigger gol_area_m2. Nada que migrar.')
        return
    
    print(f'  Encontrados {old_triggers.count()} triggers antiguos de área para migrar.')
    
    # Definición del trigger calc_area_native para duplicar
    CALC_AREA_NATIVE_DEF = {
        'name': 'calc_area_native',
        'description': 'Calcula el área de la geometría usando el sistema de coordenadas nativo de la capa. El resultado está en las unidades del SRS (metros² para proyecciones métricas, grados² para geográficas).',
        'timing': 'BEFORE',
        'event': 'INSERT,UPDATE',
        'scope': 'global',
        'schemas': '[]',
        'is_calculated_field': True,
        'sql_code': '''BEGIN
    -- Calcular área en unidades nativas del SRS
    NEW.{target_field} := ST_Area(NEW.{geom});
    RETURN NEW;
END;''',
        'allow_all': True,
        'created_by': 'migration',
    }
    
    migrated_count = 0
    error_count = 0
    
    for old_trigger in old_triggers:
        layer = old_trigger.layer
        field_name = old_trigger.field
        
        print(f'    Migrando: capa "{layer.name}", campo "{field_name}"')
        
        # Verificar que la capa tiene datastore y conexión
        if not layer.datastore:
            print(f'      ⚠ La capa no tiene datastore. Omitiendo.')
            error_count += 1
            continue
        
        connection = layer.datastore.connection
        if not connection:
            print(f'      ⚠ El datastore no tiene conexión asociada. Omitiendo.')
            error_count += 1
            continue
        
        # Verificar si la conexión ya tiene calc_area_native
        conn_trigger = ConnectionTrigger.objects.filter(
            connection=connection, 
            name='calc_area_native'
        ).first()
        
        if not conn_trigger:
            # Crear el trigger en esta conexión
            print(f'      → Creando calc_area_native en conexión "{connection.name}"')
            conn_trigger = ConnectionTrigger.objects.create(
                connection=connection,
                **CALC_AREA_NATIVE_DEF
            )
        
        # Verificar si ya existe un LayerConnectionTrigger para esta capa/campo
        if LayerConnectionTrigger.objects.filter(
            layer=layer,
            trigger=conn_trigger,
            field_name=field_name
        ).exists():
            print(f'      ℹ Ya existe LayerConnectionTrigger. Omitiendo.')
            # Eliminar el trigger antiguo de todas formas
            old_trigger.delete()
            continue
        
        # Obtener conexión a la base de datos para instalar el nuevo trigger
        introspect, params = get_introspect_from_connection(connection)
        if introspect is None:
            print(f'      ⚠ No se pudo conectar a la base de datos. Omitiendo.')
            error_count += 1
            continue
        
        # Crear el LayerConnectionTrigger
        try:
            schema, table = get_schema_and_table_from_layer(layer)
            
            # Obtener campos de geometría y clave primaria
            geom_field = get_geometry_field(introspect, table, schema)
            pk_field = get_pk_field(introspect, table, schema)
            
            # 1. Eliminar el trigger antiguo de la base de datos
            old_trigger_name = f"gol_area_m2_{field_name}_trigger"
            drop_old_trigger_sql = f"DROP TRIGGER IF EXISTS {old_trigger_name} ON {schema}.{table};"
            print(f'      → Eliminando trigger antiguo: {old_trigger_name}')
            try:
                introspect.cursor.execute(drop_old_trigger_sql)
            except Exception as e:
                print(f'        ⚠ Error eliminando trigger antiguo (puede que no exista): {e}')
            
            # 2. Generar el nombre del nuevo trigger y función
            # Usar el mismo formato que el modelo ConnectionTrigger:
            # - Trigger: tg_{trigger_name}_{layer_name}_{timing}_{events}
            # - Función: fn_tg_{trigger_name}_{schema}_{table}
            events_part = '_'.join([e.strip().lower() for e in conn_trigger.event.split(',') if e.strip()])
            new_trigger_name = f"tg_{conn_trigger.name}_{table}_{conn_trigger.timing.lower()}_{events_part}"
            safe_name = f"{conn_trigger.name}_{schema}_{table}".replace('.', '_').replace('-', '_')
            new_function_name = f"fn_tg_{safe_name}"
            
            # 3. Eliminar función y trigger nuevo si existieran (por si acaso)
            drop_new_trigger_sql = f"DROP TRIGGER IF EXISTS {new_trigger_name} ON {schema}.{table};"
            drop_new_function_sql = f"DROP FUNCTION IF EXISTS {schema}.{new_function_name}();"
            try:
                introspect.cursor.execute(drop_new_trigger_sql)
                introspect.cursor.execute(drop_new_function_sql)
            except Exception as e:
                print(f'        ⚠ Error eliminando trigger/función previa: {e}')
            
            # 4. Procesar el SQL del trigger con las variables de plantilla
            processed_sql = conn_trigger.sql_code
            processed_sql = processed_sql.replace('{current_schema}', schema)
            processed_sql = processed_sql.replace('{current_table}', table)
            processed_sql = processed_sql.replace('{target_field}', field_name)
            processed_sql = processed_sql.replace('{geom}', geom_field)
            processed_sql = processed_sql.replace('{pk_field}', pk_field)
            
            # 5. Crear la nueva función
            create_function_sql = f"""
CREATE OR REPLACE FUNCTION {schema}.{new_function_name}()
RETURNS TRIGGER AS $$
{processed_sql}
$$ LANGUAGE plpgsql;
"""
            print(f'      → Creando función: {schema}.{new_function_name}()')
            introspect.cursor.execute(create_function_sql)
            
            # 6. Crear el nuevo trigger
            events = conn_trigger.event.split(',')
            events_clause = ' OR '.join(events)  # "INSERT OR UPDATE"
            
            create_trigger_sql = f"""
CREATE TRIGGER {new_trigger_name}
{conn_trigger.timing} {events_clause} ON {schema}.{table}
FOR EACH ROW
EXECUTE FUNCTION {schema}.{new_function_name}();
"""
            print(f'      → Creando trigger: {new_trigger_name}')
            introspect.cursor.execute(create_trigger_sql)
            
            # 7. Commit
            introspect.conn.commit()
            
            # 8. Crear el LayerConnectionTrigger
            layer_trigger = LayerConnectionTrigger.objects.create(
                layer=layer,
                trigger=conn_trigger,
                field_name=field_name,
                is_installed=True,
                created_by='migration'
            )
            print(f'      ✓ LayerConnectionTrigger creado e instalado.')
            
            # 9. Eliminar el trigger antiguo del modelo
            old_trigger.delete()
            migrated_count += 1
            
            introspect.close()
            
        except Exception as e:
            print(f'      ✗ Error migrando trigger: {e}')
            error_count += 1
            try:
                introspect.conn.rollback()
                introspect.close()
            except:
                pass
    
    print(f'  ✓ Migración completada: {migrated_count} triggers migrados, {error_count} errores.')


def reverse_area_triggers(apps, schema_editor):
    """
    Revierte la migración: elimina los LayerConnectionTrigger creados.
    Nota: No podemos recrear los Trigger antiguos automáticamente.
    """
    LayerConnectionTrigger = apps.get_model('gvsigol_services', 'LayerConnectionTrigger')
    
    deleted_count = LayerConnectionTrigger.objects.filter(
        trigger__name='calc_area_native',
        created_by='migration'
    ).delete()[0]
    
    print(f'  ✓ {deleted_count} LayerConnectionTrigger eliminados.')
    print('  ⚠ Los Trigger antiguos no se pueden restaurar automáticamente.')


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0096_create_default_triggers'),
    ]

    operations = [
        migrations.RunPython(
            migrate_area_triggers,
            reverse_area_triggers
        ),
    ]

