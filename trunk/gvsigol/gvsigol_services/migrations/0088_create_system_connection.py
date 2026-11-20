# -*- coding: utf-8 -*-
"""
Migracion para crear la conexion del sistema basada en GVSIGOL_USERS_CARTODB.

Esta conexion se usa para los datastores automaticos de usuarios (ds_<username>).
Se crea una sola vez y se reutiliza para todos los usuarios nuevos.

Solo superusuarios pueden gestionar esta conexion (created_by='system').
"""

import json

from django.db import migrations
from django.conf import settings


def create_system_connection(apps, schema_editor):
    """Crea la conexion del sistema si no existe."""
    
    try:
        Connection = apps.get_model('gvsigol_services', 'Connection')
        
        # Obtener parametros de la configuracion
        users_cartodb = getattr(settings, 'GVSIGOL_USERS_CARTODB', None)
        
        if not users_cartodb:
            print('  AVISO: GVSIGOL_USERS_CARTODB no esta configurado. No se creara la conexion del sistema.')
            return
        
        dbhost = users_cartodb.get('dbhost', 'localhost')
        dbport = users_cartodb.get('dbport', '5432')
        dbname = users_cartodb.get('dbname', '')
        dbuser = users_cartodb.get('dbuser', '')
        dbpassword = users_cartodb.get('dbpassword', '')
        jndiname = users_cartodb.get('jndiname', '')
        
        if not dbname:
            print('  AVISO: GVSIGOL_USERS_CARTODB no tiene dbname configurado. No se creara la conexion del sistema.')
            return
        
        # Nombre de la conexion del sistema
        connection_name = "con_system_%s_%s" % (dbname, dbhost.replace('.', '_'))
        
        # Verificar si ya existe
        if Connection.objects.filter(name=connection_name).exists():
            print('  La conexion del sistema "%s" ya existe.' % connection_name)
            return
        
        # Verificar si existe una conexion con los mismos parametros (puede ser migrada)
        for conn in Connection.objects.filter(type='PostGIS'):
            try:
                params = json.loads(conn.connection_params) if conn.connection_params else {}
                if (params.get('host') == dbhost and 
                    str(params.get('port')) == str(dbport) and 
                    params.get('database') == dbname and 
                    params.get('user') == dbuser):
                    print('  Ya existe una conexion con los mismos parametros: "%s". No se creara duplicado.' % conn.name)
                    return
            except Exception:
                continue
        
        # Crear la conexion del sistema
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
            description='Conexion del sistema para datastores automaticos de usuarios',
            type='PostGIS',
            connection_params=connection_params,
            extra_params=extra_params,
            allow_all_datastore=False,
            allow_all_etl=False,
            allow_all_manage=False,
            created_by='system'
        )
        
        print('  Conexion del sistema creada: "%s"' % connection_name)
    
    except Exception as e:
        print('  ERROR creando conexion del sistema: %s' % str(e))
        raise


def reverse_system_connection(apps, schema_editor):
    """Elimina la conexion del sistema creada por esta migracion."""
    
    try:
        Connection = apps.get_model('gvsigol_services', 'Connection')
        
        # Solo eliminar conexiones creadas por 'system' que empiecen con 'con_system_'
        deleted = Connection.objects.filter(
            created_by='system',
            name__startswith='con_system_'
        ).delete()
        
        print('  Eliminadas %d conexiones del sistema' % deleted[0])
    
    except Exception as e:
        print('  ERROR eliminando conexion del sistema: %s' % str(e))
        raise


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0087_migrate_datastores_to_connections'),
    ]

    operations = [
        migrations.RunPython(create_system_connection, reverse_system_connection),
    ]
