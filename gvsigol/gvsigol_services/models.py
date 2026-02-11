# -*- coding: utf-8 -*-


'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from gvsigol.basetypes import CloneConf
import logging
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from .backend_postgis import Introspect
import os
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, ugettext
from gvsigol_services.triggers import CUSTOM_PROCEDURES
from django.utils.crypto import get_random_string
from gvsigol import settings
from django.db import models
from gvsigol_auth.models import UserGroup
import ast
import json

LOG_NAME = 'gvsigol'


class Server(models.Model):
    TYPE_CHOICES = (
        ('geoserver', 'geoserver'),
        ('mapserver', 'mapserver')
    )
    name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, default='geoserver')
    frontend_url = models.CharField(max_length=500)
    user = models.CharField(max_length=25)
    password = models.CharField(max_length=100)
    default = models.BooleanField(default=False)
    authz_service_conf = JSONField(default=None, null=True)

    def _get_relative_url(self, url):
        if url.startswith(settings.BASE_URL + '/'):
            return url[len(settings.BASE_URL):]
        return url

    def getWmsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        if workspace:
            return base_url + "/" + workspace + "/wms"
        return base_url + "/wms"

    def getWfsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        if workspace:
            return base_url + "/" + workspace + "/wfs"
        return base_url + "/wfs"

    def getWcsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        if workspace:
            return base_url + "/" + workspace + "/wcs"
        return base_url + "/wcs"

    def getWmtsEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        return base_url + "/gwc/service/wmts"

    def getCacheEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        return base_url + "/gwc/service/wms"

    def getGWCRestEndpoint(self, workspace=None, relative=False):
        if relative:
            base_url = self._get_relative_url(self.frontend_url)
        else:
            base_url = self.frontend_url
        return base_url + "/gwc/rest"

    def __str__(self):
        return self.title_name

    @property
    def title_name(self):
        return "{title} [{name}]".format(title=self.title, name=self.name)


class Node(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    status = models.CharField(max_length=25)
    url = models.CharField(max_length=500)
    is_master = models.BooleanField(default=False)

    def getUrl(self):
        return self.url


def get_default_server():
    # note: using only() to avoid errors applying Server migrations on new deploys
    theServer = Server.objects.filter(default=True).only('id').first()
    return theServer.id


class Workspace(models.Model):
    server = models.ForeignKey(
        Server, default=get_default_server, on_delete=models.CASCADE)
    name = models.CharField(max_length=250, unique=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    uri = models.CharField(max_length=500)
    wms_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wfs_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wcs_endpoint = models.CharField(max_length=500, null=True, blank=True)
    wmts_endpoint = models.CharField(max_length=500, null=True, blank=True)
    cache_endpoint = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Connection(models.Model):
    """
    Modelo centralizado para gestionar conexiones a bases de datos y servicios externos.
    Los almacenes de datos (Datastore) referenciarán conexiones en lugar de almacenar
    credenciales directamente. También usado por el plugin ETL.
    """
    # Categorías de tipos de conexión
    TYPE_CATEGORY_DATABASE = 'database'
    TYPE_CATEGORY_API = 'api'
    
    # Opciones del primer desplegable (categoría)
    CATEGORY_CHOICES = (
        ('database', 'Base de datos'),
        ('api', 'API externa'),
    )
    
    # Tipos de bases de datos disponibles
    DATABASE_TYPE_CHOICES = (
        ('PostGIS', 'PostgreSQL/PostGIS'),
        ('Oracle', 'Oracle'),
        ('SQLServer', 'SQL Server'),
    )
    
    # Tipos de APIs externas disponibles
    API_TYPE_CHOICES = (
        ('indenova', 'InDenova'),
        ('segex', 'SEGEX'),
        ('sharepoint', 'SharePoint'),
        ('padron-atm', 'Padrón ATM'),
    )
    
    # Todos los tipos combinados para el campo del modelo
    TYPE_CHOICES = DATABASE_TYPE_CHOICES + API_TYPE_CHOICES
    
    # Listas para validación rápida
    DATABASE_TYPES = ('PostGIS', 'Oracle', 'SQLServer')
    API_TYPES = ('indenova', 'segex', 'sharepoint', 'padron-atm')
    
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='PostGIS')
    connection_params = models.TextField(help_text=_('JSON with connection parameters'))
    # Parámetros adicionales opcionales en formato JSON (ej: {"dbtype": "postgis", "jndiReferenceName": ""})
    extra_params = models.TextField(
        null=True, 
        blank=True,
        help_text=_('Optional additional parameters in JSON format')
    )
    
    # Permisos globales - determinan si TODOS los usuarios pueden usar esta conexión
    allow_all_datastore = models.BooleanField(
        default=False,
        help_text=_('Allow all users to create datastores with this connection')
    )
    allow_all_etl = models.BooleanField(
        default=False,
        help_text=_('Allow all users to use this connection in ETL')
    )
    allow_all_manage = models.BooleanField(
        default=False,
        help_text=_('Allow all users to manage this connection (edit, delete)')
    )
    
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Connection')
        verbose_name_plural = _('Connections')

    def __str__(self):
        return self.name

    def is_database_type(self):
        """Retorna True si la conexión es de tipo base de datos."""
        return self.type in self.DATABASE_TYPES
    
    def is_api_type(self):
        """Retorna True si la conexión es de tipo API externa."""
        return self.type in self.API_TYPES
    
    def can_be_used_for_datastore(self):
        """Retorna True si la conexión puede usarse para crear Datastores."""
        # Solo conexiones PostGIS pueden usarse para Datastores de GeoServer
        return self.type in ('PostGIS', 'PostgreSQL')
    
    def get_type_category(self):
        """Retorna la categoría del tipo: 'database' o 'api'."""
        if self.is_database_type():
            return self.TYPE_CATEGORY_DATABASE
        return self.TYPE_CATEGORY_API
    
    def get_etl_type(self):
        """
        Retorna el tipo de conexión compatible con el ETL.
        PostGIS -> PostgreSQL para compatibilidad con ETL.
        """
        if self.type == 'PostGIS':
            return 'PostgreSQL'
        return self.type

    @staticmethod
    def get_default_db_params():
        """
        Obtiene los parámetros por defecto de la base de datos de la aplicación.
        Útil para pre-rellenar formularios.
        """
        from django.conf import settings as django_settings
        db_config = django_settings.DATABASES.get('default', {})
        return {
            'host': db_config.get('HOST', 'localhost'),
            'port': str(db_config.get('PORT', '5432')),
            'database': db_config.get('NAME', ''),
            'user': db_config.get('USER', ''),
            # No incluimos password por seguridad
        }

    def get_connection_params(self):
        """Devuelve los parámetros de conexión como diccionario."""
        try:
            return json.loads(self.connection_params)
        except:
            return {}

    def get_extra_params(self):
        """Devuelve los parámetros adicionales como diccionario."""
        try:
            return json.loads(self.extra_params) if self.extra_params else {}
        except:
            return {}

    def get_all_params(self):
        """
        Devuelve todos los parámetros combinados (conexión + extras).
        Los extras sobrescriben los de conexión si hay conflicto.
        """
        params = self.get_connection_params()
        params.update(self.get_extra_params())
        return params

    def get_masked_params(self):
        """Devuelve los parámetros con contraseñas enmascaradas para visualización."""
        params = self.get_connection_params()
        if 'passwd' in params:
            params['passwd'] = '****'
        if 'password' in params:
            params['password'] = '****'
        return params

    def get_db_connection(self):
        """Obtiene una conexión de introspección a la base de datos."""
        params = self.get_connection_params()
        if self.type in ('PostGIS', 'PostgreSQL'):
            host = params.get('host', 'localhost')
            port = params.get('port', '5432')
            dbname = params.get('database', '')
            user = params.get('user', '')
            passwd = params.get('passwd', params.get('password', ''))
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            return i, params
        return None, params

    def test_connection(self):
        """Prueba la conexión y devuelve True si es exitosa, False en caso contrario."""
        try:
            if self.type in ('PostGIS', 'PostgreSQL'):
                i, _ = self.get_db_connection()
                if i:
                    i.close()
                    return True
            # Para otros tipos de bases de datos, retornar False por ahora
            # (se puede extender para Oracle, SQLServer, etc.)
            return False
        except Exception as e:
            logging.getLogger(LOG_NAME).error(f"Connection test failed for {self.name}: {e}")
            return False

    def get_schemas(self):
        """Obtiene la lista de esquemas disponibles en la conexión."""
        try:
            if self.type in ('PostGIS', 'PostgreSQL'):
                i, _ = self.get_db_connection()
                if i:
                    schemas = i.get_schemas()
                    i.close()
                    return schemas
            return []
        except Exception as e:
            logging.getLogger(LOG_NAME).error(f"Error getting schemas for {self.name}: {e}")
            return []

    def create_schema_if_not_exists(self, schema_name):
        """
        Crea un esquema en la base de datos si no existe.
        Retorna True si se creó, False si ya existía.
        Lanza excepción si hay error.
        """
        try:
            if self.type in ('PostGIS', 'PostgreSQL'):
                i, _ = self.get_db_connection()
                if i:
                    created = i.create_schema(schema_name)
                    i.close()
                    if created:
                        logging.getLogger(LOG_NAME).info(f"Schema '{schema_name}' created in connection '{self.name}'")
                    return created
            return False
        except Exception as e:
            logging.getLogger(LOG_NAME).error(f"Error creating schema '{schema_name}' in {self.name}: {e}")
            raise


class ConnectionRole(models.Model):
    """
    Permisos de acceso a conexiones por rol.
    Permite compartir conexiones con roles específicos.
    Cada rol puede tener permisos separados para:
    - Usar la conexión en datastores
    - Usar la conexión en ETL  
    - Gestionar la conexión (editar, eliminar)
    """
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='roles')
    role = models.TextField()
    # Permisos separados para mayor flexibilidad
    can_use_datastore = models.BooleanField(
        default=False,
        help_text=_('This role can create datastores with this connection')
    )
    can_use_etl = models.BooleanField(
        default=False,
        help_text=_('This role can use this connection in ETL')
    )
    can_manage = models.BooleanField(
        default=False,
        help_text=_('This role can manage this connection (edit, delete)')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['connection', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['connection', 'role'], name='unique_role_per_connection')
        ]
        verbose_name = _('Connection Role')
        verbose_name_plural = _('Connection Roles')

    def __str__(self):
        perms = []
        if self.can_use_datastore:
            perms.append('datastore')
        if self.can_use_etl:
            perms.append('etl')
        if self.can_manage:
            perms.append('manage')
        return f"{self.connection.name} - {self.role} ({', '.join(perms) if perms else 'no perms'})"


class ConnectionTrigger(models.Model):
    """
    Trigger SQL asociado a una conexión PostGIS.
    Los triggers se pueden asignar a capas para ejecutar código SQL
    en operaciones INSERT, UPDATE o DELETE.
    """
    # Tipos de eventos que pueden activar el trigger
    EVENT_INSERT = 'INSERT'
    EVENT_UPDATE = 'UPDATE'
    EVENT_DELETE = 'DELETE'
    EVENT_CHOICES = [
        (EVENT_INSERT, _('Insert')),
        (EVENT_UPDATE, _('Update')),
        (EVENT_DELETE, _('Delete')),
    ]
    
    # Momento de ejecución del trigger
    TIMING_BEFORE = 'BEFORE'
    TIMING_AFTER = 'AFTER'
    TIMING_CHOICES = [
        (TIMING_BEFORE, _('Before')),
        (TIMING_AFTER, _('After')),
    ]
    
    # Ámbito del trigger
    SCOPE_GLOBAL = 'global'
    SCOPE_SCHEMAS = 'schemas'
    SCOPE_CHOICES = [
        (SCOPE_GLOBAL, _('Global (all schemas)')),
        (SCOPE_SCHEMAS, _('Specific schemas')),
    ]
    
    # Lenguaje del trigger
    LANGUAGE_PLPGSQL = 'plpgsql'
    LANGUAGE_PYTHON = 'python'
    LANGUAGE_CHOICES = [
        (LANGUAGE_PLPGSQL, _('PL/pgSQL (database trigger)')),
        (LANGUAGE_PYTHON, _('Python (application-level)')),
    ]
    
    connection = models.ForeignKey(
        Connection, 
        on_delete=models.CASCADE, 
        related_name='connection_triggers',
        limit_choices_to={'type': 'PostGIS'},
        help_text=_('Connection where this trigger will be executed')
    )
    name = models.CharField(
        max_length=150,
        help_text=_('Unique name for this trigger')
    )
    description = models.TextField(
        blank=True, 
        null=True,
        help_text=_('Description of what this trigger does')
    )
    # Almacena eventos como string separado por comas: "INSERT,UPDATE" o "INSERT,UPDATE,DELETE"
    event = models.CharField(
        max_length=30,
        help_text=_('Events that activate this trigger (comma-separated: INSERT,UPDATE,DELETE)')
    )
    timing = models.CharField(
        max_length=10,
        choices=TIMING_CHOICES,
        default=TIMING_AFTER,
        help_text=_('When the trigger executes relative to the event')
    )
    sql_code = models.TextField(
        help_text=_('SQL code to execute. Use NEW for inserted/updated row, OLD for deleted/updated row.')
    )
    # Ámbito: global o esquemas específicos
    scope = models.CharField(
        max_length=10,
        choices=SCOPE_CHOICES,
        default=SCOPE_GLOBAL,
        help_text=_('Whether the trigger applies to all schemas or specific ones')
    )
    # Lista de esquemas (JSON array) si scope='schemas'
    schemas = models.TextField(
        blank=True,
        null=True,
        help_text=_('JSON array of schema names if scope is "schemas"')
    )
    # Si puede usarse como campo calculado
    is_calculated_field = models.BooleanField(
        default=False,
        help_text=_('If enabled, this trigger can be used as a calculated field in layers')
    )
    # Lenguaje: plpgsql (trigger nativo de PostgreSQL) o python (código ejecutado a nivel de aplicación)
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default=LANGUAGE_PLPGSQL,
        help_text=_('Language of the trigger code: PL/pgSQL for database triggers, Python for application-level triggers')
    )
    # Permisos globales - si True, todos los staff pueden usar este trigger
    allow_all = models.BooleanField(
        default=False,
        help_text=_('Allow all staff users to use this trigger in their layers')
    )
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Connection Trigger')
        verbose_name_plural = _('Connection Triggers')
        ordering = ['connection', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['connection', 'name'], 
                name='unique_conn_trigger_name_per_connection'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.timing} {self.event}) - {self.connection.name}"
    
    def get_schemas_list(self):
        """Devuelve la lista de esquemas si scope='schemas', o lista vacía si es global."""
        if self.scope == self.SCOPE_SCHEMAS and self.schemas:
            try:
                return json.loads(self.schemas)
            except:
                return []
        return []
    
    def set_schemas_list(self, schemas_list):
        """Establece la lista de esquemas como JSON."""
        self.schemas = json.dumps(schemas_list) if schemas_list else None
    
    def get_events_list(self):
        """Devuelve la lista de eventos (INSERT, UPDATE, DELETE)."""
        if self.event:
            return [e.strip() for e in self.event.split(',') if e.strip()]
        return []
    
    def set_events_list(self, events_list):
        """Establece los eventos como string separado por comas."""
        self.event = ','.join(events_list) if events_list else ''
    
    def get_events_display(self):
        """Devuelve los eventos formateados para mostrar."""
        return ', '.join(self.get_events_list())
    
    def get_compatible_datastores(self):
        """
        Obtiene los datastores compatibles con este trigger.
        Si scope='global', devuelve todos los datastores de la conexión.
        Si scope='schemas', solo los que coincidan con los esquemas especificados.
        """
        from gvsigol_services.models import Datastore
        
        datastores = Datastore.objects.filter(connection=self.connection)
        
        if self.scope == self.SCOPE_SCHEMAS:
            schemas = self.get_schemas_list()
            if schemas:
                datastores = datastores.filter(name__in=schemas)
        
        return datastores
    
    def get_full_trigger_name(self, layer_name):
        """
        Genera el nombre completo del trigger para una capa específica.
        Formato: tg_{trigger_name}_{layer_name}_{timing}_{events}
        Los eventos se unen con guión bajo: insert_update_delete
        """
        # Convertir "INSERT,UPDATE" a "insert_update"
        events_part = '_'.join([e.strip().lower() for e in self.event.split(',') if e.strip()])
        return f"tg_{self.name}_{layer_name}_{self.timing.lower()}_{events_part}"
    
    def get_function_name(self, schema, table):
        """
        Genera el nombre de la función PL/pgSQL para este trigger.
        Formato: fn_tg_{trigger_name}_{schema}_{table}
        """
        safe_name = f"{self.name}_{schema}_{table}".replace('.', '_').replace('-', '_')
        return f"fn_tg_{safe_name}"
    
    def generate_function_sql(self, schema, table, target_field=None, geom_field=None, pk_field=None):
        """
        Genera el SQL para crear la función que ejecutará el trigger.
        El código SQL del usuario se usa directamente tal cual - debe incluir
        DECLARE (opcional), BEGIN, RETURN y END.
        
        Variables de plantilla soportadas:
        - {target_field}: El campo seleccionado por el usuario al asignar el trigger
        - {current_schema}: El esquema donde está la capa
        - {current_table}: La tabla de la capa
        - {geom}: El nombre del campo de geometría de la capa
        - {pk_field}: El campo de clave primaria de la capa
        """
        function_name = self.get_function_name(schema, table)
        
        # Reemplazar variables de plantilla en el código SQL
        processed_sql = self.sql_code
        processed_sql = processed_sql.replace('{current_schema}', schema)
        processed_sql = processed_sql.replace('{current_table}', table)
        if target_field:
            processed_sql = processed_sql.replace('{target_field}', target_field)
        if geom_field:
            processed_sql = processed_sql.replace('{geom}', geom_field)
        if pk_field:
            processed_sql = processed_sql.replace('{pk_field}', pk_field)
        
        sql = f"""
CREATE OR REPLACE FUNCTION {schema}.{function_name}()
RETURNS TRIGGER AS $$
{processed_sql}
$$ LANGUAGE plpgsql;
"""
        return sql
    
    def generate_trigger_sql(self, schema, table):
        """
        Genera el SQL para crear el trigger en la tabla especificada.
        Soporta múltiples eventos (INSERT OR UPDATE OR DELETE).
        """
        trigger_name = self.get_full_trigger_name(table)
        function_name = self.get_function_name(schema, table)
        full_table_name = f"{schema}.{table}"
        events = self.get_events_list()
        events_clause = ' OR '.join(events)  # "INSERT OR UPDATE" o "INSERT OR UPDATE OR DELETE"
        
        sql = f"""
CREATE TRIGGER {trigger_name}
{self.timing} {events_clause} ON {full_table_name}
FOR EACH ROW
EXECUTE FUNCTION {schema}.{function_name}();
"""
        return sql
    
    def generate_drop_trigger_sql(self, schema, table):
        """
        Genera el SQL para eliminar el trigger.
        """
        trigger_name = self.get_full_trigger_name(table)
        full_table_name = f"{schema}.{table}"
        
        sql = f"DROP TRIGGER IF EXISTS {trigger_name} ON {full_table_name};"
        return sql
    
    def generate_drop_function_sql(self, schema, table):
        """
        Genera el SQL para eliminar la función del trigger.
        """
        function_name = self.get_function_name(schema, table)
        
        sql = f"DROP FUNCTION IF EXISTS {schema}.{function_name}();"
        return sql
    
    def can_use(self, user):
        """
        Verifica si un usuario puede usar este trigger.
        - Superusers siempre pueden
        - Si allow_all=True, todos los staff pueden
        - Si no, se verifica si el usuario tiene algún rol con permiso
        """
        if user.is_superuser:
            return True
        
        if self.allow_all:
            return True
        
        # Verificar permisos por rol
        from gvsigol_auth import auth_backend
        user_roles = auth_backend.get_roles(user)
        
        return self.trigger_roles.filter(role__in=user_roles).exists()
    
    def get_allowed_roles(self):
        """Devuelve la lista de roles que tienen permiso para usar este trigger."""
        return list(self.trigger_roles.values_list('role', flat=True))


class ConnectionTriggerRole(models.Model):
    """
    Permisos de acceso a triggers por rol.
    Permite compartir triggers con roles específicos de staff.
    """
    trigger = models.ForeignKey(
        ConnectionTrigger, 
        on_delete=models.CASCADE, 
        related_name='trigger_roles'
    )
    role = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['trigger', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['trigger', 'role'], 
                name='unique_role_per_trigger'
            )
        ]
    
    def __str__(self):
        return f"{self.trigger.name} - {self.role}"


class Datastore(models.Model):
    """
    Almacén de datos que puede usar el modelo legacy (connection_params directo)
    o el nuevo modelo (referencia a Connection + schema).
    """
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    type = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500, null=True, blank=True)
    # Campo legacy - se mantiene para compatibilidad hacia atrás
    connection_params = models.TextField(null=True, blank=True)
    created_by = models.CharField(max_length=100)
    
    # Nuevos campos para el modelo de conexiones centralizadas
    connection = models.ForeignKey(
        Connection, 
        on_delete=models.PROTECT,  # Proteger conexión si hay datastores usándola
        null=True, 
        blank=True,
        related_name='datastores',
        help_text=_('Reference to centralized connection')
    )
    schema = models.CharField(
        max_length=150, 
        null=True, 
        blank=True,
        help_text=_('Database schema for this datastore')
    )
    legacy_mode = models.BooleanField(
        default=True,
        help_text=_('True if using connection_params directly, False if using Connection reference')
    )

    def __str__(self):
        return self.workspace.name + ":" + self.name

    def is_using_connection(self):
        """Indica si el datastore usa el nuevo modelo de conexiones."""
        return not self.legacy_mode and self.connection is not None

    def get_schema_name(self):
        """Obtiene el nombre del esquema, soportando ambos modos."""
        # Nuevo modelo: usar campo schema directamente
        if self.is_using_connection() and self.schema:
            return self.schema
        
        # Modo legacy: extraer del connection_params
        try:
            params = json.loads(self.connection_params) if self.connection_params else {}
            return params.get('schema', 'public')
        except:
            return 'public'

    def get_connection_params_dict(self):
        """
        Obtiene los parámetros de conexión como diccionario,
        independientemente del modo (legacy o nuevo).
        """
        if self.is_using_connection():
            # Nuevo modelo: obtener de la Connection y añadir schema
            params = self.connection.get_connection_params()
            params['schema'] = self.schema or 'public'
            return params
        else:
            # Modo legacy: parsear connection_params
            try:
                return json.loads(self.connection_params) if self.connection_params else {}
            except:
                return {}

    def get_db_connection(self):
        """
        Obtiene una conexión de introspección a la base de datos.
        Soporta tanto el modo legacy como el nuevo modelo de conexiones.
        """
        params = self.get_connection_params_dict()
        
        host = params.get('host', 'localhost')
        port = params.get('port', '5432')
        dbname = params.get('database', '')
        user = params.get('user', '')
        passwd = params.get('passwd', params.get('password', ''))
        
        i = Introspect(database=dbname, host=host,
                       port=port, user=user, password=passwd)
        return i, params

    def migrate_to_connection(self, connection, schema=None):
        """
        Migra este datastore del modo legacy al nuevo modelo de conexiones.
        
        Args:
            connection: Instancia de Connection a usar
            schema: Esquema a usar (si no se proporciona, se extrae del connection_params actual)
        """
        if schema is None:
            schema = self.get_schema_name()
        
        self.connection = connection
        self.schema = schema
        self.legacy_mode = False
        # Preservamos connection_params como backup
        self.save()

    def get_masked_connection_params(self):
        """Devuelve los parámetros de conexión con contraseñas enmascaradas."""
        params = self.get_connection_params_dict()
        if 'passwd' in params:
            params['passwd'] = '****'
        if 'password' in params:
            params['password'] = '****'
        return params


class DefaultUserDatastore(models.Model):
    username = models.TextField(unique=True)
    datastore = models.ForeignKey(Datastore, on_delete=models.CASCADE)


class LayerGroup(models.Model):
    server_id = models.IntegerField(null=True, default=get_default_server)
    name = models.CharField(max_length=150)
    title = models.CharField(max_length=500, null=True, blank=True)
    visible = models.BooleanField(default=False)
    cached = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def clone(self, target_datastore=None, clone_conf=None):
        if not clone_conf:
            clone_conf = CloneConf()
        old_id = self.pk
        old_name = self.name
        new_name = target_datastore.workspace.name + "_" + self.name
        i = 1
        salt = ''
        while LayerGroup.objects.filter(name=new_name, server_id=target_datastore.workspace.server.id).exists():
            new_name = new_name + '_' + str(i) + salt
            i = i + 1
            if (i % 1000) == 0:
                salt = '_' + get_random_string(3)
        self.pk = None
        self.name = new_name
        self.save()

        new_instance = LayerGroup.objects.get(id=self.pk)
        new_instance._cloned_from_name = old_name
        new_instance._cloned_from_instance = LayerGroup.objects.get(id=old_id)
        new_instance._cloned_lyr_instance_map = {}
        new_instance._cloned_lyr_name_map = {}
        if clone_conf.recursive:
            for lyr in new_instance._cloned_from_instance.layer_set.all():
                new_lyr = lyr.clone(target_datastore=target_datastore,
                                    layer_group=new_instance, clone_conf=clone_conf)
                try:
                    new_instance._cloned_lyr_instance_map[new_lyr._cloned_from_instance] = new_lyr
                    new_instance._cloned_lyr_name_map[new_lyr._cloned_from_name] = new_lyr.name
                except AttributeError:
                    pass  # raster layers are not cloned and can be safely ignored
                except:
                    logging.getLogger(LOG_NAME).exception(
                        f"Error cloning layer: {new_lyr.id} - {new_lyr.name}")
        return new_instance


def get_default_layer_thumbnail():
    return settings.STATIC_URL + 'img/no_thumbnail.jpg'


def as_dict(in_list, key):
    return {obj[key]: obj for obj in in_list}


class LayerConfig:
    def __init__(self, layer):
        self.layer = layer
        self._conf = None
        self._field_info_dict = None
        self._field_conf_dict = None
        self._control_fields_dict = None
        self._field_info = None
        self._geometry_columns = None
        self._pks = None

    def __query_db_fields(self):
        i, tablename, dsname = self.layer.get_db_connection()
        self._field_info = i.get_fields_info(tablename, dsname)
        self._geometry_columns = i.get_geometry_columns(tablename, dsname)
        self._pks = i.get_pk_columns(tablename, dsname)
        i.close()

    @property
    def conf(self):
        if self._conf is None:
            try:
                self._conf = ast.literal_eval(self.layer.conf)
            except:
                self._conf = {}
        return self._conf

    @conf.setter
    def conf(self, new_conf):
        self.layer.conf = new_conf
        self._conf = new_conf

    @property
    def field_info(self):
        if self._field_info is None:
            self.__query_db_fields()
        return self._field_info

    @property
    def geometry_columns(self):
        if self._geometry_columns is None:
            self.__query_db_fields()
        return self._geometry_columns

    @property
    def pks(self):
        if self._pks is None:
            self.__query_db_fields()
        return self._pks

    @property
    def field_info_dict(self):
        if self._field_info_dict is None:
            self._field_info_dict = as_dict(self._field_info, 'name')
        return self._field_info_dict

    @property
    def field_conf_dict(self):
        if self._field_conf_dict is None:
            self._field_conf_dict = as_dict(
                self.conf.get('fields', []), 'name')
        return self._field_conf_dict

    @property
    def control_fields_dict(self):
        if self._control_fields_dict is None:
            self._control_fields_dict = as_dict(
                settings.CONTROL_FIELDS, 'name')
        return self._control_fields_dict

    def init_field_conf(self, field_conf, field_info):
        field_conf['name'] = field_conf.get('name', field_info['name'])
        for id, language in settings.LANGUAGES:
            field_conf['title-' +
                       id] = field_conf.get('title-'+id, field_info['name'])
        field_conf['visible'] = field_conf.get('visible', True)
        if field_conf['name'] in self.pks:
            field_conf['editable'] = field_conf.get('editable', False)
            field_conf['editableactive'] = True
        elif field_conf.get('editable', True) and \
                Trigger.objects.filter(layer=self.layer, field=field_conf['name']).exists():
            field_conf['editable'] = False
            field_conf['editableactive'] = False
        elif field_conf.get('editable', True) and \
                LayerConnectionTrigger.objects.filter(
                    layer=self.layer, 
                    field_name=field_conf['name'],
                    trigger__is_calculated_field=True
                ).exists():
            # Campo calculado por un ConnectionTrigger
            field_conf['editable'] = False
            field_conf['editableactive'] = False
        else:
            field_conf['editable'] = field_conf.get('editable', True)
            field_conf['editableactive'] = True
        field_conf['infovisible'] = field_conf.get('infovisible', True)
        field_conf['nullable'] = (field_info.get('nullable') != 'NO')
        if not field_conf['nullable']:
            field_conf['mandatory'] = True
        else:
            field_conf['mandatory'] = field_conf.get('mandatory', False)

        if field_conf['name'] in self.control_fields_dict:
            control_field = self.control_fields_dict.get(field_conf['name'])
            field_conf['editableactive'] = control_field.get(
                'editableactive', False)
            field_conf['editable'] = control_field.get('editable', False)
            field_conf['visible'] = control_field.get(
                'visible', field_conf['visible'])
            field_conf['infovisible'] = control_field.get(
                'visible', field_conf['infovisible'])
            field_conf['nullable'] = control_field.get(
                'nullable', field_conf['nullable'])
            field_conf['mandatory'] = control_field.get(
                'mandatory', field_conf['mandatory'])

        field_conf['gvsigol_type'] = field_conf.get('gvsigol_type', '')  
        field_conf['type_params'] = field_conf.get('type_params', {})    
        field_conf['field_format'] = field_conf.get('field_format', {})   

        if field_conf.get('gvsigol_type') == 'link':
            field_conf['editableactive'] = True
            field_conf['editable'] = False

        return field_conf

    def get_field_conf(self, include_pks=False):
        return self.conf.get('fields', [])

    def get_updated_field_conf(self, include_pks=False):
        fields = []
        for the_field_info in self.field_info:
            field_name = the_field_info['name']
            if (include_pks or not field_name in self.pks) and \
                    (not field_name in self.geometry_columns):
                the_field_conf = self.field_conf_dict.get(field_name, {})
                field = self.init_field_conf(the_field_conf, the_field_info)
                fields.append(field)
        
        return fields

    def refresh_field_conf(self, include_pks=False):
        fields = self.get_updated_field_conf(include_pks=include_pks)
        self.conf['fields'] = fields
        self.layer.conf = self.conf

    def get_field_viewconf(self, include_pks=False):
        fields = self.get_updated_field_conf(include_pks=include_pks)
        for field in fields:
            try:
                enum = LayerFieldEnumeration.objects.get(
                    layer=self.layer, field=field['name']).enumeration
                field['type'] = str(
                    ugettext('enumerated ({0})').format(enum.title))
            except:
                field['type'] = self.field_info_dict.get(
                    field['name'], {}).get('type', '')
            try:
                trigger = Trigger.objects.get(
                    layer=self.layer, field=field['name'])
                field['calculation'] = trigger.procedure.signature
                field['calculationLabel'] = str(
                    trigger.procedure.localized_label)
                field['editableactive'] = False
                field['editable'] = False
            except:
                # Verificar si hay un ConnectionTrigger calculado para este campo
                try:
                    layer_conn_trigger = LayerConnectionTrigger.objects.get(
                        layer=self.layer, 
                        field_name=field['name'],
                        trigger__is_calculated_field=True
                    )
                    field['calculation'] = layer_conn_trigger.trigger.name
                    field['calculationLabel'] = layer_conn_trigger.trigger.name
                    field['editableactive'] = False
                    field['editable'] = False
                except LayerConnectionTrigger.DoesNotExist:
                    field['calculation'] = ''
                    field['calculationLabel'] = ''
        return fields


class Layer(models.Model):
    external = models.BooleanField(default=False)
    external_params = models.TextField(null=True, blank=True)
    datastore = models.ForeignKey(
        Datastore, null=True, on_delete=models.CASCADE)
    layer_group = models.ForeignKey(LayerGroup, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    abstract = models.CharField(max_length=5000, null=True, blank=True)
    type = models.CharField(max_length=150)
    # the layer can be read by anyone, even anonymous users
    public = models.BooleanField(default=False)
    visible = models.BooleanField(default=False)
    queryable = models.BooleanField(default=True)
    cached = models.BooleanField(default=False)
    single_image = models.BooleanField(default=False)
    vector_tile = models.BooleanField(default=False)
    allow_download = models.BooleanField(default=False)
    time_enabled = models.BooleanField(default=False)
    time_enabled_field = models.CharField(
        max_length=150, null=True, blank=True)
    time_enabled_endfield = models.CharField(
        max_length=150, null=True, blank=True)
    time_presentation = models.CharField(max_length=150, null=True, blank=True)
    time_resolution_year = models.IntegerField(null=True, default=0)
    time_resolution_month = models.IntegerField(null=True, default=0)
    time_resolution_week = models.IntegerField(null=True, default=0)
    time_resolution_day = models.IntegerField(null=True, default=0)
    time_resolution_hour = models.IntegerField(null=True, default=0)
    time_resolution_minute = models.IntegerField(null=True, default=0)
    time_resolution_second = models.IntegerField(null=True, default=0)
    time_default_value_mode = models.CharField(
        max_length=150, null=True, blank=True)
    time_default_value = models.CharField(
        max_length=150, null=True, blank=True)
    time_resolution = models.CharField(max_length=150, null=True, blank=True)
    order = models.IntegerField(default=100)
    created_by = models.CharField(max_length=100)
    thumbnail = models.ImageField(
        upload_to='thumbnails', default=get_default_layer_thumbnail, null=True, blank=True)
    conf = models.TextField(null=True, blank=True)
    detailed_info_enabled = models.BooleanField(default=True)
    detailed_info_button_title = models.CharField(
        max_length=150, null=True, blank=True, default='Detailed info')
    detailed_info_html = models.TextField(null=True, blank=True)
    timeout = models.IntegerField(null=True, default=30000)
    native_srs = models.CharField(max_length=100, default='EPSG:4326')
    native_extent = models.CharField(max_length=250, default='-180,-90,180,90')
    latlong_extent = models.CharField(
        max_length=250, default='-180,-90,180,90')
    # table name for postgis layers, not defined for the rest
    source_name = models.TextField(null=True, blank=True)
    real_time = models.BooleanField(default=False)
    update_interval = models.IntegerField(null=True, default=1000)
    featureapi_endpoint = models.CharField(
        max_length=100, null=False, default='/api/v1')

    def __str__(self):
        return self.name

    def get_qualified_name(self):
        return self.datastore.workspace.name + ":" + self.name

    @property
    def full_qualified_name(self):
        if self.datastore is not None:
            return self.datastore.workspace.server.name + ":" + self.datastore.workspace.name + ":" + self.name
        else:
            return self.name

    def clone(self, target_datastore, recursive=True, layer_group=None, clone_conf=None):
        if not clone_conf:
            clone_conf = CloneConf()
        from gvsigol_services.utils import clone_layer
        return clone_layer(target_datastore, self, layer_group, clone_conf=clone_conf)

    def get_config_manager(self):
        return LayerConfig(self)

    def get_db_connection(self):
        i, params = self.datastore.get_db_connection()
        source_name = self.source_name if self.source_name else self.name
        return i, source_name, params.get('schema', 'public')
    
    @property
    def thumbnail_relurl(self):
        if self.thumbnail:
            if self.thumbnail.name == get_default_layer_thumbnail():
                return self.thumbnail.url
            return self.thumbnail.url.replace(settings.BASE_URL, '')
        return get_default_layer_thumbnail()


class LayerReadGroup(models.Model):
    """
    Deprecated, use LayerReadRole instead. To be removed in v4.0.
    """
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)


class LayerWriteGroup(models.Model):
    """
    Deprecated, use LayerReadRole instead. To be removed in v4.0.
    """
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)


class LayerReadRole(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    role = models.TextField()
    """
    Some limits have been aplied to the read permission for this role on this layer, such as
    - a CQL filter to limit the records available for read or write
    - some fields are hidden or read-only
    - ...
    """
    filtered = models.BooleanField(default=False)
    """
    This permission has been set using some high level or plugin-specific UI, so it
    should not be editable in the general layer permission UI.
    """
    external = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['layer', 'role'], name='unique_read_role_per_layer')
        ]


class LayerWriteRole(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    role = models.TextField()
    """
    Some limits have been aplied to the read permission for this role on this layer, such as
    - a CQL filter to limit the records available for read or write
    - some fields are hidden or read-only
    - ...
    """
    filtered = models.BooleanField(default=False)
    """
    This permission has been set using some high level or plugin-specific UI, so it
    should not be editable in the general layer permission UI.
    """
    external = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['layer', 'role'], name='unique_write_role_per_layer')
        ]


class LayerManageRole(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    role = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['layer', 'role'], name='unique_manage_role_per_layer')
        ]


class LayerConnectionTrigger(models.Model):
    """
    Vincula un ConnectionTrigger con un campo de una Layer.
    Cuando se asigna, se crea el trigger nativo en PostgreSQL.
    """
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name='layer_connection_triggers')
    trigger = models.ForeignKey(ConnectionTrigger, on_delete=models.CASCADE, related_name='layer_connection_triggers')
    field_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text=_('Name of the field that will be calculated by this trigger (only for calculated field triggers)')
    )
    is_installed = models.BooleanField(
        default=False,
        help_text=_('Whether the trigger is currently installed in the database')
    )
    installed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Layer Connection Trigger')
        verbose_name_plural = _('Layer Connection Triggers')
        constraints = [
            # Un trigger solo puede asignarse una vez por capa
            models.UniqueConstraint(
                fields=['layer', 'trigger'],
                name='unique_trigger_per_layer'
            )
        ]
    
    def __str__(self):
        return f"{self.layer.name} - {self.trigger.name}"
    
    def get_schema_and_table(self):
        """
        Obtiene el schema y nombre de tabla de la capa.
        El schema se obtiene de los connection_params del datastore.
        """
        # Obtener el schema de los connection_params del datastore
        schema = 'public'  # Valor por defecto
        
        if self.layer.datastore.connection_params:
            try:
                if isinstance(self.layer.datastore.connection_params, str):
                    params = json.loads(self.layer.datastore.connection_params)
                else:
                    params = self.layer.datastore.connection_params
                schema = params.get('schema', 'public')
            except:
                schema = 'public'
        
        # Si no hay schema en connection_params, usar el nombre del datastore
        if not schema or schema == 'public':
            # Intentar obtener el schema del método get_schema_name si existe
            if hasattr(self.layer.datastore, 'get_schema_name'):
                schema = self.layer.datastore.get_schema_name() or self.layer.datastore.name
            else:
                schema = self.layer.datastore.name
        
        table = self.layer.source_name if self.layer.source_name else self.layer.name
        
        return schema, table
    
    def get_geometry_field(self, introspect, table, schema):
        """
        Obtiene el nombre del campo de geometría de la capa.
        """
        try:
            geom_columns = introspect.get_geometry_columns(table, schema)
            if geom_columns and len(geom_columns) > 0:
                return geom_columns[0]  # Primer campo de geometría
        except Exception:
            pass
        return 'wkb_geometry'  # Valor por defecto común
    
    def get_pk_field(self, introspect, table, schema):
        """
        Obtiene el nombre del campo de clave primaria de la capa.
        """
        try:
            pk_columns = introspect.get_pk_columns(table, schema)
            if pk_columns and len(pk_columns) > 0:
                return pk_columns[0]  # Primera clave primaria
        except Exception:
            pass
        return 'ogc_fid'  # Valor por defecto común
    
    def install(self):
        """
        Instala el trigger en la base de datos PostgreSQL.
        
        Variables de plantilla que se reemplazan:
        - {target_field}: El campo seleccionado (self.field_name)
        - {current_schema}: El esquema de la capa
        - {current_table}: La tabla de la capa
        - {geom}: El campo de geometría de la capa
        - {pk_field}: El campo de clave primaria de la capa
        """
        from django.utils import timezone
        
        if self.layer.datastore.connection is None:
            return False, _('Layer datastore has no associated connection')
        
        if self.layer.datastore.connection.type != 'PostGIS':
            return False, _('Trigger installation is only supported for PostGIS connections')
        
        schema, table = self.get_schema_and_table()
        
        try:
            # Obtener conexión a la base de datos
            i, params = self.layer.datastore.connection.get_db_connection()
            
            if i is None:
                return False, _('Could not connect to database')
            
            # Obtener el nombre del campo de geometría y clave primaria
            geom_field = self.get_geometry_field(i, table, schema)
            pk_field = self.get_pk_field(i, table, schema)
            
            # Primero eliminar si existe
            drop_trigger_sql = self.trigger.generate_drop_trigger_sql(schema, table)
            drop_function_sql = self.trigger.generate_drop_function_sql(schema, table)
            
            i.cursor.execute(drop_trigger_sql)
            i.cursor.execute(drop_function_sql)
            
            # Crear función y trigger con variables de plantilla reemplazadas
            function_sql = self.trigger.generate_function_sql(
                schema, 
                table, 
                target_field=self.field_name,
                geom_field=geom_field,
                pk_field=pk_field
            )
            trigger_sql = self.trigger.generate_trigger_sql(schema, table)
            
            i.cursor.execute(function_sql)
            i.cursor.execute(trigger_sql)
            i.conn.commit()
            
            i.close()
            
            # Marcar como instalado
            self.is_installed = True
            self.installed_at = timezone.now()
            self.save()
            
            return True, _('Trigger installed successfully')
            
        except Exception as e:
            logging.getLogger('gvsigol').error(f"Error installing trigger: {e}")
            return False, str(e)
    
    def uninstall(self):
        """
        Desinstala el trigger de la base de datos PostgreSQL.
        """
        if not self.is_installed:
            return True, _('Trigger was not installed')
        
        if self.layer.datastore.connection is None:
            return False, _('Layer datastore has no associated connection')
        
        schema, table = self.get_schema_and_table()
        
        try:
            i, params = self.layer.datastore.connection.get_db_connection()
            
            if i is None:
                return False, _('Could not connect to database')
            
            drop_trigger_sql = self.trigger.generate_drop_trigger_sql(schema, table)
            drop_function_sql = self.trigger.generate_drop_function_sql(schema, table)
            
            i.cursor.execute(drop_trigger_sql)
            i.cursor.execute(drop_function_sql)
            i.conn.commit()
            
            i.close()
            
            # Marcar como no instalado
            self.is_installed = False
            self.installed_at = None
            self.save()
            
            return True, _('Trigger uninstalled successfully')
            
        except Exception as e:
            logging.getLogger('gvsigol').error(f"Error uninstalling trigger: {e}")
            return False, str(e)


class LayerGroupRole(models.Model):
    PERM_INCLUDEINPROJECTS = 'includeinprojects'
    PERM_MANAGE = 'manage'
    PERMISSION_CHOICES = [
        (PERM_MANAGE, PERM_MANAGE),
        (PERM_INCLUDEINPROJECTS, PERM_INCLUDEINPROJECTS),
    ]
    layergroup = models.ForeignKey(LayerGroup, on_delete=models.CASCADE)
    role = models.TextField()
    permission = models.TextField(
        choices=PERMISSION_CHOICES, default=PERM_MANAGE)

    class Meta:
        indexes = [
            models.Index(fields=['layergroup', 'permission', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(fields=[
                                    'layergroup', 'permission', 'role'], name='unique_permission_role_per_layergroup')
        ]

    def __str__(self):
        return '({}, {}, {})'.format(self.layergroup.name, self.role, self.permission)


class DataRule(models.Model):
    path = models.CharField(max_length=500)
    roles = models.CharField(max_length=500)


class LayerLock(models.Model):
    """locks created from geoportal"""
    GEOPORTAL_LOCK = 0
    """locks created from sync API"""
    SYNC_LOCK = 1
    """Valid lock types"""
    TYPE_CHOICES = (
        (GEOPORTAL_LOCK, 'Geoportal'),
        (SYNC_LOCK, 'Sync')
    )
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100)
    type = models.IntegerField(choices=TYPE_CHOICES, default=GEOPORTAL_LOCK)

    def __str__(self):
        return self.layer.name


class LayerResource(models.Model):
    """Stores resources (images, pdfs, etc) linked to specific features in a Layer"""

    """image files, stored in the file system"""
    EXTERNAL_IMAGE = 1
    """PDF files, stored in the file system"""
    EXTERNAL_PDF = 2
    """.ODT or .DOC files, stored in the file system"""
    EXTERNAL_DOC = 3
    """any kind of resource file"""
    EXTERNAL_FILE = 4
    """video files"""
    EXTERNAL_VIDEO = 5
    """alfresco directory"""
    EXTERNAL_ALFRESCO_DIR = 6
    """Valid resource types"""
    TYPE_CHOICES = (
        (EXTERNAL_IMAGE, 'Image'),
        (EXTERNAL_PDF, 'PDF'),
        (EXTERNAL_DOC, 'DOC'),
        (EXTERNAL_VIDEO, 'Video'),
        (EXTERNAL_FILE, 'File'),
    )
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    """The primary key of the feature. This makes mandatory for
    gvSIG Online layers to have a numeric, non-complex primary key"""
    feature = models.BigIntegerField()
    type = models.IntegerField(choices=TYPE_CHOICES)
    path = models.CharField(max_length=500)
    """The title of the resource (optional)"""
    title = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'feature']),
            models.Index(fields=['path']),
        ]

    def get_abspath(self):
        return os.path.join(settings.MEDIA_ROOT, self.path)

    def get_url(self):
        return reverse('layer_resource', args=[self.pk])


class Enumeration(models.Model):
    ALPHABETICAL='alphabetical'
    ALPHABETICAL_TITLE=_('Alphabetical')
    MANUAL ='manual'
    MANUAL_TITLE=_('Manual')
    ORDER_TYPE_CHOICES = [
        (ALPHABETICAL, ALPHABETICAL_TITLE),
        (MANUAL, MANUAL_TITLE),
    ]
    name = models.CharField(max_length=150)
    title = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.CharField(max_length=100)
    order_type = models.TextField(choices=ORDER_TYPE_CHOICES, blank=True, default=MANUAL)
    show_first_value = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class EnumerationItem(models.Model):
    enumeration = models.ForeignKey(Enumeration, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    selected = models.BooleanField(default=False)
    order = models.IntegerField(null=False, default=0)

    def __str__(self):
        return self.name


class LayerFieldEnumeration(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, null=True)
    enumeration = models.ForeignKey(Enumeration, on_delete=models.CASCADE)
    field = models.CharField(max_length=150)
    multiple = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'field']),
        ]


class ServiceUrl(models.Model):
    SERVICE_TYPE_CHOICES = (
        ('WMS', 'WMS'),
        ('WMTS', 'WMTS'),
        ('WFS', 'WFS'),
        ('CSW', 'CSW'),
    )
    title = models.CharField(max_length=500, null=True, blank=True)
    type = models.CharField(
        max_length=50, choices=SERVICE_TYPE_CHOICES, default='WMS')
    url = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def url_path(self):
        """
        Returns the URL excluding the query and fragment, which is equivalent to the
        URL part before the '?' character.
        """
        return self.url.split('?')[0]


class TriggerProcedure(models.Model):
    """
    The definition of a PostgreSQL function designed to be used in a trigger,
    which will be used for calculated fields.

    Our TriggerProcedure definition includes also parameters for the trigger creation,
    since these procedures make some assumptions based on the kind of trigger that will
    be applied (ROW OR STATEMENT orientation, BEFORE, AFTER OR INSTEAD OF activation, etc).

    If the definition is not static and has to be customized based on environment variables,
    field names, etc, a CustomFunctionDef subclass must be registered in triggers.CUSTOM_PROCEDURES
    dictionary.
    """
    signature = models.TextField(unique=True)
    func_name = models.CharField(max_length=150)
    func_schema = models.CharField(max_length=150)
    label = models.CharField(max_length=150)
    definition_tpl = models.TextField(blank=True, null=True)
    activation = models.CharField(max_length=10)
    event = models.CharField(max_length=100)
    orientation = models.CharField(max_length=10)
    """
    Condition is excluded for the moment since it is very complex to validate
    against SQL injection attacks.
    condition = models.TextField()
    """

    def get_definition(self):
        custom_procedure_cls = CUSTOM_PROCEDURES.get(self.signature)
        if custom_procedure_cls:
            return custom_procedure_cls().get_definition()
        else:
            return self.definition_tpl

    @property
    def localized_label(self):
        return _(self.label)


class Trigger(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, null=True)
    field = models.CharField(max_length=150)
    procedure = models.ForeignKey(TriggerProcedure, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=['layer', 'field']),
        ]

    def get_name(self):
        return self.procedure.func_name + "_" + self.field + "_trigger"

    def install(self):
        from gvsigol_services.utils import get_db_connect_from_layer
        trigger_name = self.get_name()
        i, target_table, target_schema = get_db_connect_from_layer(self.layer)
        i.install_trigger(trigger_name, target_schema, target_table,
                          self.procedure.activation, self.procedure.event, self.procedure.orientation, '', self.procedure.func_schema, self.procedure.func_name, [self.field])
        i.close()

    def drop(self):
        from gvsigol_services.utils import get_db_connect_from_layer
        trigger_name = self.get_name()
        i, target_table, target_schema = get_db_connect_from_layer(self.layer)
        i.drop_trigger(trigger_name, target_schema, target_table)
        i.close()


class SqlView(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['datastore', 'name'], name='unique_name_per_datastore')
        ]
    name = models.TextField()
    datastore = models.ForeignKey(Datastore, on_delete=models.CASCADE)
    """
    In order to avoid SQL injections, we only accept a particular type of views
    that fit in the following JSON schema:
     {
        "fields":  [
            {"table_alias": "t1", "name": "f1", "alias": "f1"},
            {"table_alias": "t2", "name": "f1", "alias": "ff1"},
            {"table_alias": "t1", "name": "f2", "alias": "f2"},
            {"table_alias": "t2", "name": "f2", "alias": "ff2"}
        ],
        "from": [
            {
                "schema": "sch1",
                "name": "table1",
                "alias": "t1"
            },
            {
                "schema": "sch1",
                "name": "table2",
                "alias": "t1",
                "join_type": "INNER",
                "join_field1": {
                    "table_alias": "t1",
                    "name": "f1"
                },
                "join_field2": {
                    "table_alias": "t2",
                    "name": "f1"
                }
            }
        ],
        "pks": ["f1"]
    }

    The main limitations of this schema are:
    - complex ON conditions are not allowed (i.e. ON t1.f1 = t2.t1_id AND t1.type = t2.type)
    - where clauses are not allowed (although the schema could be extended to accept WHERE clauses)
    """
    json_def = JSONField()
    created_by = models.CharField(max_length=100, default='')

    @property
    def tables_str(self):
        tables = [t.get('schema', '')+'.'+t.get('name', '')
                  for t in self.json_def.get('from', [])]
        return ", ".join(tables)


class Category(models.Model):
    title = models.CharField(max_length=255)
    project = models.ForeignKey('gvsigol_core.Project', on_delete=models.CASCADE, related_name='categories')

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        constraints = [
            models.UniqueConstraint(
                fields=['title', 'project'], 
                name='unique_category_title_per_project'
            )
        ]

    def __str__(self):
        return f"{self.title} (Project: {self.project.name})"

class Marker(models.Model):
    idProj = models.IntegerField()
    title = models.CharField(max_length=255)
    position_lat = models.FloatField()
    position_lng = models.FloatField()
    zoom = models.FloatField()
    thumbnail = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='markers'
    )

    def __str__(self):
        return f"Marker - {self.title} (Proj {self.idProj})"

class LayerTopologyConfiguration(models.Model):
    """
    Modelo para almacenar la configuración de reglas topológicas de una capa.
    Una sola fila por capa con campos específicos para cada regla.
    """
    layer = models.OneToOneField(Layer, on_delete=models.CASCADE, related_name='topology_config')
    
    # Regla: No debe solapar
    no_overlap = models.BooleanField(default=False)
    
    # Regla: No debe haber huecos
    no_gaps = models.BooleanField(default=False)
    
    # Regla: Debe estar cubierto por
    must_be_covered_by = models.BooleanField(default=False)
    covered_by_layer = models.CharField(max_length=255, blank=True, null=True, 
                                      help_text="Capa que debe cubrir en formato schema.tabla")
    
    # Regla: No debe solapar con
    must_not_overlap_with = models.BooleanField(default=False)
    overlap_layers = JSONField(default=list, blank=True, 
                              help_text="Lista de capas con las que no debe solapar en formato schema.tabla")
    
    # Regla: Debe ser contiguo
    must_be_contiguous = models.BooleanField(default=False)
    contiguous_tolerance = models.FloatField(default=1.0, 
                                           help_text="Tolerancia en metros para la contigüidad")

    class Meta:
        verbose_name = 'Layer Topology Configuration'
        verbose_name_plural = 'Layer Topology Configurations'

    def __str__(self):
        return f"Topology config for {self.layer.name}"

    def get_active_rules_count(self):
        """
        Cuenta cuántas reglas están activas
        """
        active_count = 0
        if self.no_overlap:
            active_count += 1
        if self.no_gaps:
            active_count += 1
        if self.must_be_covered_by:
            active_count += 1
        if self.must_not_overlap_with:
            active_count += 1
        if self.must_be_contiguous:
            active_count += 1
        
        return active_count

    def get_rules_summary(self):
        """
        Devuelve un resumen legible de las reglas activas
        """
        summary = []
        
        if self.no_overlap:
            summary.append("No overlap")
        
        if self.no_gaps:
            summary.append("No gaps")
        
        if self.must_be_covered_by:
            if self.covered_by_layer:
                summary.append(f"Covered by: {self.covered_by_layer}")
            else:
                summary.append("Covered by (not configured)")
        
        if self.must_not_overlap_with:
            if self.overlap_layers:
                summary.append(f"No overlap with: {', '.join(self.overlap_layers)}")
            else:
                summary.append("No overlap with (not configured)")
        
        if self.must_be_contiguous:
            summary.append(f"Contiguous (tolerance: {self.contiguous_tolerance}m)")
        
        return '; '.join(summary) if summary else "No active rules"


class FavoriteFilter(models.Model):
    """
    Modelo para almacenar filtros favoritos guardados por los usuarios.
    Permite guardar y compartir filtros personalizados para capas específicas de proyectos específicos.
    """
    name = models.CharField(max_length=150, null=False)
    description = models.CharField(max_length=500, null=True, blank=True)
    share_filter = models.BooleanField(default=False)
    project = models.ForeignKey('gvsigol_core.Project', on_delete=models.CASCADE, null=False)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, null=False)
    filter_data = JSONField(help_text="Estructura JSON con la configuración del filtro")
    created_by = models.CharField(max_length=100, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Favorite Filter'
        verbose_name_plural = 'Favorite Filters'
        indexes = [
            models.Index(fields=['project', 'layer']),
            models.Index(fields=['created_by']),
            models.Index(fields=['share_filter']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'project', 'layer', 'created_by'], 
                name='unique_favorite_filter_per_user_layer'
            )
        ]

    def __str__(self):
        return f"Filter '{self.name}' for layer '{self.layer.name}' by {self.created_by}"

    def get_filter_summary(self):
        """
        Devuelve un resumen legible del filtro
        """
        if self.filter_data:
            filter_queries = self.filter_data.get('filterQueries', [])
            operator = self.filter_data.get('filterOperator', 'AND')
            
            if filter_queries:
                query_count = len(filter_queries)
                return f"{query_count} query{'s' if query_count > 1 else ''} with {operator} operator"
        
        return "No filter data"

    def is_accessible_by_user(self, user):
        """
        Verifica si un usuario puede acceder a este filtro
        """
        
        if self.created_by == user.username:
            return True
        
        # Si está compartido, cualquier usuario del proyecto puede acceder
        if self.share_filter:
            return self.project.userprojectrole_set.filter(user=user).exists()
        
        return False