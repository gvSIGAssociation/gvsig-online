# -*- coding: utf-8 -*-
"""
Migracion de datos: database_connections -> Connection

Esta migracion copia todas las conexiones del modelo database_connections del plugin ETL
al modelo centralizado Connection de gvsigol_services.

Ademas, analiza los workspaces ETL existentes y asigna permisos ETL a los usuarios
que utilizan cada conexion en sus workspaces.

Despues de ejecutar esta migracion y verificar que todo funciona correctamente,
se puede eliminar el modelo database_connections y su migracion asociada.
"""
from django.db import migrations
import json
import re


def normalize_postgres_params(connection_params, conn_type):
    """
    Normaliza los parametros de conexion PostgreSQL/PostGIS.
    El ETL guardaba 'password' pero gvsigol_services espera 'passwd'.
    Tambien asegura que 'port' sea string.
    """
    if conn_type not in ('PostgreSQL', 'PostGIS'):
        return connection_params
    
    try:
        params = json.loads(connection_params) if isinstance(connection_params, str) else connection_params
    except (json.JSONDecodeError, TypeError):
        return connection_params
    
    # Convertir 'password' a 'passwd'
    if 'password' in params and 'passwd' not in params:
        params['passwd'] = params.pop('password')
    
    # Asegurar que port sea string
    if 'port' in params:
        params['port'] = str(params['port'])
    
    return json.dumps(params)


def extract_connection_names_from_workspace(workspace_json):
    """
    Extrae los nombres de conexiones usadas en un workspace ETL.
    Los campos que contienen nombres de conexiones son: 'db', 'api', 'db-option'
    """
    connection_names = set()
    
    if not workspace_json:
        return connection_names
    
    try:
        workspace = json.loads(workspace_json) if isinstance(workspace_json, str) else workspace_json
    except (json.JSONDecodeError, TypeError):
        return connection_names
    
    # El workspace es una lista de entidades/nodos
    if not isinstance(workspace, list):
        return connection_names
    
    for item in workspace:
        if not isinstance(item, dict):
            continue
        
        # Buscar en entities -> parameters
        entities = item.get('entities', [])
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            parameters = entity.get('parameters', {})
            if not isinstance(parameters, dict):
                continue
            
            # Campos que contienen nombres de conexiones
            for field in ['db', 'api', 'db-option']:
                value = parameters.get(field)
                if value and isinstance(value, str) and value.strip():
                    connection_names.add(value.strip())
    
    return connection_names


def migrate_database_connections_to_connection(apps, schema_editor):
    """
    Migra todas las conexiones de database_connections a Connection.
    Ademas asigna permisos ETL a los usuarios que usan cada conexion en sus workspaces.
    """
    try:
        # Obtener los modelos
        database_connections = apps.get_model('gvsigol_plugin_geoetl', 'database_connections')
        ETLworkspaces = apps.get_model('gvsigol_plugin_geoetl', 'ETLworkspaces')
        Connection = apps.get_model('gvsigol_services', 'Connection')
        ConnectionRole = apps.get_model('gvsigol_services', 'ConnectionRole')
        User = apps.get_model('auth', 'User')
        
        # Importar auth_backend para obtener el rol primario del usuario
        from gvsigol_auth import auth_backend
        
        # Mapeo de tipos: ETL usa PostgreSQL, Connection usa PostGIS
        type_mapping = {
            'PostgreSQL': 'PostGIS',
            'Oracle': 'Oracle',
            'SQLServer': 'SQLServer',
            'MySQL': 'MySQL',
            'indenova': 'indenova',
            'segex': 'segex',
            'sharepoint': 'sharepoint',
            'padron-atm': 'padron-atm',
        }
        
        # Paso 1: Analizar todos los workspaces ETL para saber que conexiones usa cada usuario
        # Estructura: {connection_name: set(usernames)}
        connection_users = {}
        
        for ws in ETLworkspaces.objects.all():
            try:
                if not ws.username:
                    continue
                
                # Extraer nombres de conexiones del workspace
                conn_names = extract_connection_names_from_workspace(ws.workspace)
                
                # Tambien revisar en parameters si hay referencias a conexiones
                if ws.parameters:
                    try:
                        params = json.loads(ws.parameters)
                        db_param = params.get('db', '')
                        if db_param:
                            conn_names.add(db_param)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Registrar el usuario para cada conexion usada
                for conn_name in conn_names:
                    if conn_name not in connection_users:
                        connection_users[conn_name] = set()
                    connection_users[conn_name].add(ws.username)
            except Exception as ws_error:
                print('    ERROR procesando workspace: %s' % str(ws_error))
        
        print('')
        print('=== Analisis de workspaces ETL ===')
        print('  Conexiones referenciadas: %d' % len(connection_users))
        for conn_name, users in connection_users.items():
            print('    - "%s": usado por %s' % (conn_name, list(users)))
        
        # Paso 2: Migrar las conexiones de database_connections a Connection
        migrated_count = 0
        skipped_count = 0
        connections_map = {}  # {nombre: Connection object}
        
        for db_conn in database_connections.objects.all():
            try:
                # Verificar si ya existe una Connection con este nombre
                existing = Connection.objects.filter(name=db_conn.name).first()
                if existing:
                    print('  Conexion "%s" ya existe en Connection, omitiendo creacion...' % db_conn.name)
                    connections_map[db_conn.name] = existing
                    skipped_count += 1
                    continue
                
                # Mapear el tipo
                new_type = type_mapping.get(db_conn.type, db_conn.type)
                
                # Normalizar parametros de PostgreSQL (password -> passwd, port como string)
                normalized_params = normalize_postgres_params(db_conn.connection_params, db_conn.type)
                
                # Crear la nueva Connection (sin permisos globales)
                new_conn = Connection.objects.create(
                    name=db_conn.name,
                    description='Conexion migrada automaticamente desde plugin ETL (tipo: %s)' % db_conn.type,
                    type=new_type,
                    connection_params=normalized_params,
                    created_by='etl_migration',
                    allow_all_etl=False,
                    allow_all_datastore=False,
                    allow_all_manage=False,
                )
                
                connections_map[db_conn.name] = new_conn
                print('  Migrada: "%s" (type: %s -> %s)' % (db_conn.name, db_conn.type, new_type))
                migrated_count += 1
            except Exception as conn_error:
                print('  ERROR migrando conexion "%s": %s' % (db_conn.name, str(conn_error)))
        
        print('')
        print('=== Migracion database_connections -> Connection completada ===')
        print('  Migradas: %d' % migrated_count)
        print('  Omitidas (ya existian): %d' % skipped_count)
        
        # Paso 3: Asignar permisos ETL a los usuarios que usan cada conexion
        permissions_created = 0
        
        for conn_name, usernames in connection_users.items():
            try:
                connection = connections_map.get(conn_name)
                if not connection:
                    # La conexion referenciada no existe en database_connections
                    # Intentar buscarla en Connection por si ya existia
                    connection = Connection.objects.filter(name=conn_name).first()
                    if not connection:
                        print('  Advertencia: Conexion "%s" no encontrada, omitiendo permisos' % conn_name)
                        continue
                
                for username in usernames:
                    try:
                        # Verificar si el usuario es staff (no superuser)
                        try:
                            user = User.objects.get(username=username)
                            if user.is_superuser:
                                # Superusuarios ya tienen acceso a todo, no necesitan permisos especificos
                                continue
                            if not user.is_staff:
                                continue
                        except User.DoesNotExist:
                            print('  Advertencia: Usuario "%s" no encontrado' % username)
                            continue
                        
                        # Obtener el rol primario del usuario (ug_username)
                        try:
                            user_role = auth_backend.get_primary_role(username)
                        except Exception:
                            user_role = "ug_%s" % username
                        
                        # Verificar si ya existe el permiso
                        existing_perm = ConnectionRole.objects.filter(
                            connection=connection,
                            role=user_role
                        ).first()
                        
                        if existing_perm:
                            # Actualizar para asegurar que tiene permiso ETL
                            if not existing_perm.can_use_etl:
                                existing_perm.can_use_etl = True
                                existing_perm.save()
                                print('  Actualizado permiso ETL: %s -> %s' % (user_role, conn_name))
                                permissions_created += 1
                        else:
                            # Crear nuevo permiso
                            ConnectionRole.objects.create(
                                connection=connection,
                                role=user_role,
                                can_use_etl=True,
                                can_use_datastore=False,
                                can_manage=False,
                            )
                            print('  Creado permiso ETL: %s -> %s' % (user_role, conn_name))
                            permissions_created += 1
                    except Exception as user_error:
                        print('  ERROR asignando permiso a usuario "%s": %s' % (username, str(user_error)))
            except Exception as perm_error:
                print('  ERROR procesando permisos para conexion "%s": %s' % (conn_name, str(perm_error)))
        
        print('')
        print('=== Asignacion de permisos ETL completada ===')
        print('  Permisos creados/actualizados: %d' % permissions_created)
    
    except Exception as e:
        print('  ERROR en migracion de conexiones ETL: %s' % str(e))
        raise


def reverse_migration(apps, schema_editor):
    """
    Revierte la migracion eliminando las conexiones y permisos creados.
    Solo elimina las que fueron creadas por esta migracion.
    """
    try:
        Connection = apps.get_model('gvsigol_services', 'Connection')
        ConnectionRole = apps.get_model('gvsigol_services', 'ConnectionRole')
        
        # Primero eliminar los ConnectionRoles asociados a conexiones de la migracion
        migrated_connections = Connection.objects.filter(created_by='etl_migration')
        roles_deleted = 0
        for conn in migrated_connections:
            roles_deleted += ConnectionRole.objects.filter(connection=conn).delete()[0]
        
        # Luego eliminar las conexiones
        deleted_count = migrated_connections.delete()[0]
        
        print('')
        print('=== Reversion completada ===')
        print('  Conexiones eliminadas: %d' % deleted_count)
        print('  Permisos eliminados: %d' % roles_deleted)
    
    except Exception as e:
        print('  ERROR revirtiendo migracion ETL: %s' % str(e))
        raise


class Migration(migrations.Migration):
    
    dependencies = [
        ('gvsigol_plugin_geoetl', '0028_auto_20251020_1744'),
        # Depende de que exista el modelo Connection y ConnectionRole
        ('gvsigol_services', '0089_auto_20260130_1637'),
        ('auth', '__first__'),
    ]
    
    operations = [
        migrations.RunPython(
            migrate_database_connections_to_connection,
            reverse_code=reverse_migration,
        ),
    ]
