# -*- coding: utf-8 -*-
"""
Migración para crear la conexión del sistema basada en GVSIGOL_USERS_CARTODB.

Esta conexión se usa para los datastores automáticos de usuarios (ds_<username>).
Se crea una sola vez y se reutiliza para todos los usuarios nuevos.

Solo superusuarios pueden gestionar esta conexión (created_by='system').
"""

import json

from django.db import migrations
from django.conf import settings


def create_system_connection(apps, schema_editor):
    """Crea la conexión del sistema si no existe."""
    
    Connection = apps.get_model('gvsigol_services', 'Connection')
    
    # Obtener parámetros de la configuración
    users_cartodb = getattr(settings, 'GVSIGOL_USERS_CARTODB', None)
    
    if not users_cartodb:
        print('  AVISO: GVSIGOL_USERS_CARTODB no está configurado. No se creará la conexión del sistema.')
        return
    
    dbhost = users_cartodb.get('dbhost', 'localhost')
    dbport = users_cartodb.get('dbport', '5432')
    dbname = users_cartodb.get('dbname', '')
    dbuser = users_cartodb.get('dbuser', '')
    dbpassword = users_cartodb.get('dbpassword', '')
    jndiname = users_cartodb.get('jndiname', '')
    
    if not dbname:
        print('  AVISO: GVSIGOL_USERS_CARTODB no tiene dbname configurado. No se creará la conexión del sistema.')
        return
    
    # Nombre de la conexión del sistema
    connection_name = f"con_system_{dbname}_{dbhost.replace('.', '_')}"
    
    # Verificar si ya existe
    if Connection.objects.filter(name=connection_name).exists():
        print(f'  La conexión del sistema "{connection_name}" ya existe.')
        return
    
    # Verificar si existe una conexión con los mismos parámetros (puede ser migrada)
    for conn in Connection.objects.filter(type='PostGIS'):
        try:
            params = json.loads(conn.connection_params) if conn.connection_params else {}
            if (params.get('host') == dbhost and 
                str(params.get('port')) == str(dbport) and 
                params.get('database') == dbname and 
                params.get('user') == dbuser):
                print(f'  Ya existe una conexión con los mismos parámetros: "{conn.name}". No se creará duplicado.')
                return
        except:
            continue
    
    # Crear la conexión del sistema
    connection_params = json.dumps({
        'host': dbhost,
        'port': dbport,
        'database': dbname,
        'user': dbuser,
        'passwd': dbpassword,
    })
    
    extra_params = json.dumps({
        'dbtype': 'postgis',
        'jndiReferenceName': jndiname
    })
    
    Connection.objects.create(
        name=connection_name,
        description='Conexión del sistema para datastores automáticos de usuarios',
        type='PostGIS',
        connection_params=connection_params,
        extra_params=extra_params,
        allow_all_datastore=False,
        allow_all_etl=False,
        allow_all_manage=False,
        created_by='system'
    )
    
    print(f'  ✓ Conexión del sistema creada: "{connection_name}"')


def reverse_system_connection(apps, schema_editor):
    """Elimina la conexión del sistema creada por esta migración."""
    
    Connection = apps.get_model('gvsigol_services', 'Connection')
    
    # Solo eliminar conexiones creadas por 'system' que empiecen con 'con_system_'
    deleted = Connection.objects.filter(
        created_by='system',
        name__startswith='con_system_'
    ).delete()
    
    print(f'  Eliminadas {deleted[0]} conexiones del sistema')


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0087_migrate_datastores_to_connections'),
    ]

    operations = [
        migrations.RunPython(create_system_connection, reverse_system_connection),
    ]









