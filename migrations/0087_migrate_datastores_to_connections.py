# -*- coding: utf-8 -*-
"""
Data migration para migrar almacenes de datos existentes al nuevo sistema de conexiones centralizadas.

Esta migración:
1. Busca todos los datastores de tipo v_PostGIS que están en legacy_mode=True (o sin conexión asignada)
2. Agrupa los datastores por sus parámetros de conexión (host, port, database, user)
3. Crea una Connection para cada grupo único de parámetros
4. Actualiza los datastores para que apunten a la nueva conexión centralizada
5. Asigna permisos según el siguiente criterio:
   - Si el datastore tiene nombre ds_<username> (creado automáticamente): NO se asignan permisos
   - Si el datastore tiene otro nombre (creado manualmente): SÍ se asignan permisos al rol ug_<username>
"""

import json
from collections import defaultdict

from django.db import migrations

# Importar funciones de utilidad (no dependen del ORM, son funciones puras)
from gvsigol_services.utils import get_datastore_name
from gvsigol_auth import auth_backend


def migrate_datastores_to_connections(apps, schema_editor):
    """Migra los almacenes de datos legacy al sistema de conexiones centralizadas."""
    
    try:
        Datastore = apps.get_model('gvsigol_services', 'Datastore')
        Connection = apps.get_model('gvsigol_services', 'Connection')
        ConnectionRole = apps.get_model('gvsigol_services', 'ConnectionRole')
        Role = apps.get_model('gvsigol_auth', 'Role')
        
        # Buscar datastores PostGIS que necesitan migración
        legacy_datastores = Datastore.objects.filter(
            type='v_PostGIS',
            legacy_mode=True,
            connection__isnull=True
        )
        
        total_datastores = legacy_datastores.count()
        
        if total_datastores == 0:
            print('  No hay almacenes de datos que necesiten migracion.')
            return
        
        print('  Encontrados %d almacenes de datos para migrar.' % total_datastores)
        
        # Agrupar datastores por parámetros de conexión únicos
        connection_groups = defaultdict(list)
        
        for ds in legacy_datastores:
            try:
                params = json.loads(ds.connection_params) if ds.connection_params else {}
            except json.JSONDecodeError:
                print('  AVISO: Datastore "%s" tiene connection_params invalidos, se omitira.' % ds.name)
                continue
            
            # Crear una clave única basada en los parámetros de conexión (sin schema)
            host = params.get('host', 'localhost')
            port = params.get('port', '5432')
            database = params.get('database', '')
            user = params.get('user', '')
            passwd = params.get('passwd', params.get('password', ''))
            
            connection_key = (host, port, database, user, passwd)
            connection_groups[connection_key].append({
                'datastore': ds,
                'params': params,
                'schema': params.get('schema', 'public'),
                'created_by': ds.created_by
            })
        
        print('  Se crearan %d conexiones unicas.' % len(connection_groups))
        
        # Procesar cada grupo de conexión
        connections_created = 0
        datastores_migrated = 0
        
        for conn_key, datastores_info in connection_groups.items():
            try:
                host, port, database, user, passwd = conn_key
                
                # Determinar nombre para la conexión
                connection_name = "con_%s_%s" % (database, host.replace('.', '_'))
                
                # Asegurar nombre único
                base_name = connection_name
                counter = 1
                while Connection.objects.filter(name=connection_name).exists():
                    connection_name = "%s_%d" % (base_name, counter)
                    counter += 1
                
                # Crear la conexión
                connection_params = json.dumps({
                    'host': host,
                    'port': port,
                    'database': database,
                    'user': user,
                    'passwd': passwd,
                })
                
                # Detectar extra_params del primer datastore (como dbtype)
                first_params = datastores_info[0]['params']
                extra_params = {}
                if 'dbtype' in first_params:
                    extra_params['dbtype'] = first_params['dbtype']
                # Añadir jndiReferenceName por defecto si no existe
                if 'jndiReferenceName' not in extra_params:
                    extra_params['jndiReferenceName'] = ''
                
                # Crear la conexión sin permisos globales (se gestionan por roles)
                connection = Connection.objects.create(
                    name=connection_name,
                    description='Conexion migrada automaticamente desde datastores existentes',
                    type='PostGIS',
                    connection_params=connection_params,
                    extra_params=json.dumps(extra_params) if extra_params else None,
                    allow_all_datastore=False,  # Sin permisos globales
                    allow_all_etl=False,         # Sin permisos globales
                    allow_all_manage=False,      # Sin permisos globales
                    created_by='system_migration'
                )
                
                connections_created += 1
                
                # Recopilar usuarios que crearon datastores manualmente (no automáticos)
                # Un datastore es automático si su nombre es ds_<username>
                users_with_manual_datastores = set()
                
                for info in datastores_info:
                    ds = info['datastore']
                    creator = info['created_by']
                    
                    if creator:
                        # Calcular el nombre automático que tendría el datastore para este usuario
                        auto_datastore_name = get_datastore_name(creator)
                        
                        # Si el nombre del datastore NO coincide con el automático, es manual
                        if ds.name != auto_datastore_name:
                            users_with_manual_datastores.add(creator)
                
                # Crear permisos para usuarios que crearon datastores manualmente
                roles_created = 0
                for creator_username in users_with_manual_datastores:
                    try:
                        # Obtener el rol primario del usuario (ug_<username>)
                        user_role_name = auth_backend.get_primary_role(creator_username)
                        
                        # Verificar que el rol existe en el sistema
                        Role.objects.get(name=user_role_name)
                        
                        role_obj, created = ConnectionRole.objects.get_or_create(
                            connection=connection,
                            role=user_role_name,
                            defaults={
                                'can_use_datastore': True,  # Puede crear más datastores
                                'can_use_etl': False,       # ETL se asignará en migración posterior
                                'can_manage': True          # Puede gestionar la conexión
                            }
                        )
                        if created:
                            roles_created += 1
                            print('    Rol "%s" (usuario "%s"): can_use_datastore=True, can_manage=True' % (user_role_name, creator_username))
                    except Role.DoesNotExist:
                        print('    AVISO: Rol "%s" no encontrado para usuario "%s", omitiendo' % (user_role_name, creator_username))
                    except Exception as role_error:
                        print('    ERROR asignando rol para usuario "%s": %s' % (creator_username, str(role_error)))
                
                # Actualizar cada datastore para usar la nueva conexión
                for info in datastores_info:
                    ds = info['datastore']
                    schema = info['schema']
                    
                    ds.connection = connection
                    ds.schema = schema
                    ds.legacy_mode = False
                    ds.save()
                    
                    datastores_migrated += 1
                
                manual_count = len(users_with_manual_datastores)
                print('  Conexion "%s": %d datastores migrados, %d roles creados (%d usuarios con datastores manuales)' % (
                    connection_name, len(datastores_info), roles_created, manual_count))
            
            except Exception as conn_error:
                print('  ERROR migrando grupo de conexion: %s' % str(conn_error))
                continue
        
        print('  RESUMEN: %d conexiones creadas, %d datastores migrados' % (connections_created, datastores_migrated))
        print('  NOTA: Solo se asignaron permisos a usuarios que crearon datastores manualmente (no ds_<username>)')
    
    except Exception as e:
        print('  ERROR en migracion de datastores: %s' % str(e))
        raise


def reverse_migration(apps, schema_editor):
    """Revierte la migración: desvincula los datastores de las conexiones y elimina las conexiones migradas."""
    
    try:
        Datastore = apps.get_model('gvsigol_services', 'Datastore')
        Connection = apps.get_model('gvsigol_services', 'Connection')
        
        # Buscar conexiones creadas por esta migración
        migrated_connections = Connection.objects.filter(created_by='system_migration')
        
        # Desvincular todos los datastores de estas conexiones
        for connection in migrated_connections:
            datastores = Datastore.objects.filter(connection=connection)
            for ds in datastores:
                ds.connection = None
                ds.schema = None
                ds.legacy_mode = True
                ds.save()
        
        # Eliminar las conexiones migradas
        count = migrated_connections.count()
        migrated_connections.delete()
        
        print('  Revertida migracion: %d conexiones eliminadas' % count)
    
    except Exception as e:
        print('  ERROR revirtiendo migracion: %s' % str(e))
        raise


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_services', '0086_auto_20260130_1139'),
    ]

    operations = [
        migrations.RunPython(migrate_datastores_to_connections, reverse_migration),
    ]
