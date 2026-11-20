# -*- coding: utf-8 -*-
"""Permisos del usuario para un turno del asistente, sin depender del request.

Las herramientas necesitan saber qué conexiones y qué carpetas del gestor de
ficheros puede usar el usuario. En el proceso web se sacan del request, como
siempre. Un worker de Celery no tiene request, y los roles con Keycloak salen
de la sesión del usuario: si el worker los pidiera por otra vía podrían no
coincidir. Por eso los calcula siempre el proceso web y viajan al worker ya
resueltos (to_payload / from_payload).

Con request (from_request) las comprobaciones de carpetas siguen llamando a
can_manage_path / can_browse_path en el momento de usarlas, igual que antes.
"""

import logging
import os

LOGGER = logging.getLogger('gvsigol')

PAYLOAD_VERSION = 1


def _publish_targets_needed():
    """Solo se calculan para el worker si el asistente puede preguntar por ellos."""
    from gvsigol_plugin_geoetl import settings as geoetl_settings
    return bool(getattr(geoetl_settings, 'ETL_ASSISTANT_QUESTIONS', False)
                or getattr(geoetl_settings, 'ETL_ASSISTANT_ALTERNATIVES', False))


def _filemanager_root():
    from django.conf import settings
    return os.path.abspath(getattr(settings, 'FILEMANAGER_DIRECTORY', '') or '')


class AssistantContext(object):

    def __init__(self, user_id=None, username='', is_superuser=False, is_staff=False,
                 connections=None, restricted=False, language=None, file_dirs=None, request=None,
                 publish_targets=None, datastores=None):
        self.user_id = user_id
        self.username = username or ''
        self.is_superuser = bool(is_superuser)
        self.is_staff = bool(is_staff)
        self.connections = [dict(item) for item in (connections or []) if isinstance(item, dict)]
        self.restricted = bool(restricted)
        self.language = language
        # Carpetas de primer nivel del gestor de ficheros que puede usar (sin
        # request). None para el superusuario: todas.
        self.file_dirs = None if file_dirs is None else [str(d) for d in file_dirs]
        self._request = request
        # Workspaces y grupos de capas donde puede publicar (None: sin calcular)
        self._publish_targets = publish_targets
        # Almacenes PostGIS donde puede crear una tabla (None: sin calcular)
        self._datastores = datastores

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    @classmethod
    def from_request(cls, request, connections, restricted, language=None):
        user = getattr(request, 'user', None)
        if language is None:
            try:
                from django.utils import translation
                language = translation.get_language()
            except Exception:
                language = None
        return cls(
            user_id=getattr(user, 'id', None),
            username=getattr(user, 'username', '') or '',
            is_superuser=getattr(user, 'is_superuser', False),
            is_staff=getattr(user, 'is_staff', False),
            connections=connections,
            restricted=restricted,
            language=language,
            request=request,
        )

    def to_payload(self):
        """Diccionario serializable (JSON) con todo resuelto, para el worker."""
        return {
            'version': PAYLOAD_VERSION,
            'user_id': self.user_id,
            'username': self.username,
            'is_superuser': self.is_superuser,
            'is_staff': self.is_staff,
            'connections': self.connections,
            'restricted': self.restricted,
            'language': self.language,
            'file_dirs': None if self.is_superuser else self._resolved_file_dirs(),
            'publish_targets': self.publish_targets() if _publish_targets_needed() else {},
            'datastores': self.datastores() if _publish_targets_needed() else [],
        }

    @classmethod
    def from_payload(cls, payload):
        payload = payload or {}
        return cls(
            user_id=payload.get('user_id'),
            username=payload.get('username') or '',
            is_superuser=payload.get('is_superuser'),
            is_staff=payload.get('is_staff'),
            connections=payload.get('connections'),
            restricted=payload.get('restricted'),
            language=payload.get('language'),
            file_dirs=payload.get('file_dirs') or [],
            publish_targets=payload.get('publish_targets') or {},
            datastores=payload.get('datastores') or [],
        )

    # ------------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------------

    def find_connection(self, name):
        for item in self.connections:
            if item.get('name') == name:
                return item
        return None

    def publish_targets(self):
        """{'workspaces': [...], 'layer_groups': [...]} donde el usuario puede publicar."""
        if self._publish_targets is None:
            self._publish_targets = {}
            if self._request is not None:
                try:
                    from gvsigol_plugin_geoetl.etl_raster_publish import publish_targets
                    self._publish_targets = publish_targets(self._request.user)
                except Exception:
                    LOGGER.exception('etl_assistant: no se pudieron leer los workspaces del usuario')
        return self._publish_targets

    def datastores(self):
        """Almacenes PostGIS que el usuario puede usar y cuya conexión tiene permiso ETL."""
        if self._datastores is None:
            self._datastores = []
            if self._request is not None:
                try:
                    self._datastores = usable_datastores(self._request, self.connections)
                except Exception:
                    LOGGER.exception('etl_assistant: no se pudieron leer los almacenes del usuario')
        return self._datastores

    # ------------------------------------------------------------------
    # Gestor de ficheros (mismas reglas que gvsigol_filemanager.views)
    # ------------------------------------------------------------------

    def can_manage_dir(self, name):
        """Carpeta de primer nivel del gestor de ficheros."""
        if self._request is not None:
            from gvsigol_filemanager.views import can_manage_path
            return bool(can_manage_path(self._request, name))
        if self.is_superuser:
            return True
        return name in (self.file_dirs or [])

    def can_browse(self, folder):
        """folder relativo a la raíz, ya validado (sin '..')."""
        if self._request is not None:
            from gvsigol_filemanager.views import can_browse_path
            return bool(can_browse_path(self._request, folder))
        if folder == '' and (self.is_superuser or self.is_staff):
            return True
        if self.is_superuser:
            return True
        if not self.is_staff:
            return False
        first = folder.split('/')[0]
        return os.path.isdir(os.path.join(_filemanager_root(), first)) and first in (self.file_dirs or [])

    def _resolved_file_dirs(self):
        if self._request is None:
            return list(self.file_dirs or [])
        root = _filemanager_root()
        if not root or not os.path.isdir(root):
            return []
        try:
            names = sorted(os.listdir(root))
        except OSError:
            return []
        return [name for name in names
                if not name.startswith('.') and os.path.isdir(os.path.join(root, name))
                and self.can_manage_dir(name)]


def usable_datastores(request, connections, candidates=None):
    """Datos de los almacenes PostGIS que se pueden ofrecer como destino.

    Hacen falta los dos permisos, que son independientes: usar el almacén y usar
    su conexión en ETL (connections ya viene filtrada por ese permiso). Los
    almacenes antiguos sin conexión o sin esquema no se pueden traducir a los
    parámetros del nodo y no se ofrecen.
    """
    from gvsigol_services.utils import can_use_datastore

    if candidates is None:
        from gvsigol_services.models import Datastore
        candidates = (Datastore.objects.filter(type='v_PostGIS', connection__isnull=False)
                      .exclude(schema__isnull=True).exclude(schema='')
                      .select_related('workspace', 'connection').order_by('name'))
    allowed = {item.get('name') for item in connections if item.get('type') in ('PostGIS', 'PostgreSQL')}
    return [{'name': ds.name, 'description': ds.description or '', 'workspace': ds.workspace.name,
             'connection': ds.connection.name, 'schema': ds.schema}
            for ds in candidates if ds.connection.name in allowed and can_use_datastore(request, ds)]


def as_context(request_or_context, connections, restricted):
    """Acepta el request de siempre o un AssistantContext ya construido."""
    if isinstance(request_or_context, AssistantContext):
        return request_or_context
    return AssistantContext.from_request(request_or_context, connections, restricted)
