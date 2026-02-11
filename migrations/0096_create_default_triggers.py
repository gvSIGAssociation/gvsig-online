# -*- coding: utf-8 -*-
from django.db import migrations
from django.conf import settings
import json


def create_default_triggers(apps, schema_editor):
    """
    Crea 6 triggers por defecto en la conexión del sistema:
    - Calcular área (coordenadas nativas)
    - Calcular área (geography)
    - Calcular longitud (coordenadas nativas)
    - Calcular longitud (geography)
    - Calcular perímetro (coordenadas nativas)
    - Calcular perímetro (geography)
    """
    Connection = apps.get_model('gvsigol_services', 'Connection')
    ConnectionTrigger = apps.get_model('gvsigol_services', 'ConnectionTrigger')
    
    # Obtener la conexión del sistema (basada en GVSIGOL_USERS_CARTODB)
    try:
        dbhost = settings.GVSIGOL_USERS_CARTODB['dbhost']
        dbport = settings.GVSIGOL_USERS_CARTODB['dbport']
        dbname = settings.GVSIGOL_USERS_CARTODB['dbname']
        dbuser = settings.GVSIGOL_USERS_CARTODB['dbuser']
    except (AttributeError, KeyError):
        print('  ⚠ GVSIGOL_USERS_CARTODB no configurado. No se crearán triggers por defecto.')
        return
    
    # Buscar la conexión del sistema
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
        except:
            continue
    
    if not system_connection:
        print('  ⚠ No se encontró la conexión del sistema. No se crearán triggers por defecto.')
        return
    
    print(f'  Creando triggers por defecto en conexión: {system_connection.name}')
    
    # Definir los 6 triggers
    default_triggers = [
        # === ÁREA ===
        {
            'name': 'calc_area_native',
            'description': 'Calcula el área de la geometría usando el sistema de coordenadas nativo de la capa. El resultado está en las unidades del SRS (metros² para proyecciones métricas, grados² para geográficas).',
            'timing': 'BEFORE',
            'event': 'INSERT,UPDATE',
            'scope': 'global',
            'is_calculated_field': True,
            'sql_code': '''BEGIN
    -- Calcular área en unidades nativas del SRS
    NEW.{target_field} := ST_Area(NEW.{geom});
    RETURN NEW;
END;''',
        },
        {
            'name': 'calc_area_geography',
            'description': 'Calcula el área de la geometría en metros cuadrados (m²) usando coordenadas geográficas (geography). Más preciso para grandes áreas o datos en EPSG:4326.',
            'timing': 'BEFORE',
            'event': 'INSERT,UPDATE',
            'scope': 'global',
            'is_calculated_field': True,
            'sql_code': '''BEGIN
    -- Calcular área en m² usando geography (más preciso para coordenadas geográficas)
    NEW.{target_field} := ST_Area(NEW.{geom}::geography);
    RETURN NEW;
END;''',
        },
        # === LONGITUD ===
        {
            'name': 'calc_length_native',
            'description': 'Calcula la longitud de la geometría (líneas) usando el sistema de coordenadas nativo de la capa. El resultado está en las unidades del SRS.',
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
            'description': 'Calcula la longitud de la geometría (líneas) en metros usando coordenadas geográficas (geography). Más preciso para datos en EPSG:4326.',
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
        # === PERÍMETRO ===
        {
            'name': 'calc_perimeter_native',
            'description': 'Calcula el perímetro de la geometría (polígonos) usando el sistema de coordenadas nativo de la capa. El resultado está en las unidades del SRS.',
            'timing': 'BEFORE',
            'event': 'INSERT,UPDATE',
            'scope': 'global',
            'is_calculated_field': True,
            'sql_code': '''BEGIN
    -- Calcular perímetro en unidades nativas del SRS
    NEW.{target_field} := ST_Perimeter(NEW.{geom});
    RETURN NEW;
END;''',
        },
        {
            'name': 'calc_perimeter_geography',
            'description': 'Calcula el perímetro de la geometría (polígonos) en metros usando coordenadas geográficas (geography). Más preciso para datos en EPSG:4326.',
            'timing': 'BEFORE',
            'event': 'INSERT,UPDATE',
            'scope': 'global',
            'is_calculated_field': True,
            'sql_code': '''BEGIN
    -- Calcular perímetro en metros usando geography
    NEW.{target_field} := ST_Perimeter(NEW.{geom}::geography);
    RETURN NEW;
END;''',
        },
    ]
    
    created_count = 0
    for trigger_data in default_triggers:
        # Verificar si ya existe
        if ConnectionTrigger.objects.filter(
            connection=system_connection, 
            name=trigger_data['name']
        ).exists():
            print(f'    - Trigger "{trigger_data["name"]}" ya existe, omitiendo.')
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
        print(f'    ✓ Trigger "{trigger_data["name"]}" creado.')
    
    print(f'  ✓ {created_count} triggers creados en la conexión del sistema.')


def reverse_default_triggers(apps, schema_editor):
    """Elimina los triggers por defecto creados por esta migración."""
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
    
    print(f'  ✓ {deleted_count} triggers por defecto eliminados.')


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


