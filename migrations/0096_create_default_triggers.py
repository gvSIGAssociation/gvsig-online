# -*- coding: utf-8 -*-
from django.db import migrations
from django.conf import settings
import json


def create_default_triggers(apps, schema_editor):
    """
    Crea 6 triggers por defecto en la conexion del sistema:
    - Calcular area (coordenadas nativas)
    - Calcular area (geography)
    - Calcular longitud (coordenadas nativas)
    - Calcular longitud (geography)
    - Calcular perimetro (coordenadas nativas)
    - Calcular perimetro (geography)
    """
    try:
        Connection = apps.get_model('gvsigol_services', 'Connection')
        ConnectionTrigger = apps.get_model('gvsigol_services', 'ConnectionTrigger')
        
        # Obtener la conexion del sistema (basada en GVSIGOL_USERS_CARTODB)
        try:
            dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
            dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
            dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
            dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
        except (AttributeError, KeyError):
            print('  AVISO: GVSIGOL_USERS_CARTODB no configurado. No se crearan triggers por defecto.')
            return
        
        # Buscar la conexion del sistema
        system_connection = None
        for conn in Connection.objects.filter(type='PostGIS'):
            try:
                params = json.loads(conn.connection_params) if conn.connection_params else {}
                if (params.get('host') == dbhost and 
                    str(params.get('port')) == str(dbport) and 
                    params.get('database') == dbname and 
                    params.get('user') == dbuser):
                    system_connection = conn
                    break
            except Exception:
                continue
        
        if not system_connection:
            print('  AVISO: No se encontro la conexion del sistema. No se crearan triggers por defecto.')
            return
        
        print('  Creando triggers por defecto en conexion: %s' % system_connection.name)
        
        # Definir los 6 triggers
        default_triggers = [
            # === AREA ===
            {
                'name': 'calc_area_native',
                'description': 'Calcula el area de la geometria usando el sistema de coordenadas nativo de la capa. El resultado esta en las unidades del SRS (metros2 para proyecciones metricas, grados2 para geograficas).',
                'timing': 'BEFORE',
                'event': 'INSERT,UPDATE',
                'scope': 'global',
                'is_calculated_field': True,
                'sql_code': '''BEGIN
    -- Calcular area en unidades nativas del SRS
    NEW.{target_field} := ST_Area(NEW.{geom});
    RETURN NEW;
END;''',
            },
            {
                'name': 'calc_area_geography',
                'description': 'Calcula el area de la geometria en metros cuadrados (m2) usando coordenadas geograficas (geography). Mas preciso para grandes areas o datos en EPSG:4326.',
                'timing': 'BEFORE',
                'event': 'INSERT,UPDATE',
                'scope': 'global',
                'is_calculated_field': True,
                'sql_code': '''BEGIN
    -- Calcular area en m2 usando geography (mas preciso para coordenadas geograficas)
    NEW.{target_field} := ST_Area(NEW.{geom}::geography);
    RETURN NEW;
END;''',
            },
            # === LONGITUD ===
            {
                'name': 'calc_length_native',
                'description': 'Calcula la longitud de la geometria (lineas) usando el sistema de coordenadas nativo de la capa. El resultado esta en las unidades del SRS.',
                'timing': 'BEFORE',
                'event': 'INSERT,UPDATE',
                'scope': 'global',
                'is_calculated_field': True,
                'sql_code': '''BEGIN
    -- Calcular longitud en unidades nativas del SRS
    NEW.{target_field} := ST_Length(NEW.{geom});
    RETURN NEW;
END;''',
            },
            {
                'name': 'calc_length_geography',
                'description': 'Calcula la longitud de la geometria (lineas) en metros usando coordenadas geograficas (geography). Mas preciso para datos en EPSG:4326.',
                'timing': 'BEFORE',
                'event': 'INSERT,UPDATE',
                'scope': 'global',
                'is_calculated_field': True,
                'sql_code': '''BEGIN
    -- Calcular longitud en metros usando geography
    NEW.{target_field} := ST_Length(NEW.{geom}::geography);
    RETURN NEW;
END;''',
            },
            # === PERIMETRO ===
            {
                'name': 'calc_perimeter_native',
                'description': 'Calcula el perimetro de la geometria (poligonos) usando el sistema de coordenadas nativo de la capa. El resultado esta en las unidades del SRS.',
                'timing': 'BEFORE',
                'event': 'INSERT,UPDATE',
                'scope': 'global',
                'is_calculated_field': True,
                'sql_code': '''BEGIN
    -- Calcular perimetro en unidades nativas del SRS
    NEW.{target_field} := ST_Perimeter(NEW.{geom});
    RETURN NEW;
END;''',
            },
            {
                'name': 'calc_perimeter_geography',
                'description': 'Calcula el perimetro de la geometria (poligonos) en metros usando coordenadas geograficas (geography). Mas preciso para datos en EPSG:4326.',
                'timing': 'BEFORE',
                'event': 'INSERT,UPDATE',
                'scope': 'global',
                'is_calculated_field': True,
                'sql_code': '''BEGIN
    -- Calcular perimetro en metros usando geography
    NEW.{target_field} := ST_Perimeter(NEW.{geom}::geography);
    RETURN NEW;
END;''',
            },
        ]
        
        created_count = 0
        for trigger_data in default_triggers:
            try:
                # Verificar si ya existe
                if ConnectionTrigger.objects.filter(
                    connection=system_connection, 
                    name=trigger_data['name']
                ).exists():
                    print('    Trigger "%s" ya existe, omitiendo.' % trigger_data['name'])
                    continue
                
                ConnectionTrigger.objects.create(
                    connection=system_connection,
                    name=trigger_data['name'],
                    description=trigger_data['description'],
                    timing=trigger_data['timing'],
                    event=trigger_data['event'],
                    scope=trigger_data['scope'],
                    schemas='[]',
                    is_calculated_field=trigger_data['is_calculated_field'],
                    sql_code=trigger_data['sql_code'],
                    allow_all=True,  # Disponible para todos los usuarios
                    created_by='system',
                )
                created_count += 1
                print('    Trigger "%s" creado.' % trigger_data['name'])
            except Exception as trigger_error:
                print('    ERROR creando trigger "%s": %s' % (trigger_data['name'], str(trigger_error)))
        
        print('  %d triggers creados en la conexion del sistema.' % created_count)
    
    except Exception as e:
        print('  ERROR en creacion de triggers por defecto: %s' % str(e))
        raise


def reverse_default_triggers(apps, schema_editor):
    """Elimina los triggers por defecto creados por esta migracion."""
    try:
        ConnectionTrigger = apps.get_model('gvsigol_services', 'ConnectionTrigger')
        
        trigger_names = [
            'calc_area_native',
            'calc_area_geography',
            'calc_length_native',
            'calc_length_geography',
            'calc_perimeter_native',
            'calc_perimeter_geography',
        ]
        
        deleted_count = ConnectionTrigger.objects.filter(
            name__in=trigger_names,
            created_by='system'
        ).delete()[0]
        
        print('  %d triggers por defecto eliminados.' % deleted_count)
    
    except Exception as e:
        print('  ERROR eliminando triggers por defecto: %s' % str(e))
        raise


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0095_connectiontrigger_permissions'),
    ]

    operations = [
        migrations.RunPython(
            create_default_triggers,
            reverse_default_triggers
        ),
    ]
