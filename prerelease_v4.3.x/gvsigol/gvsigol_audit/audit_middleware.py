# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2024 SCOLAB.

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

import time
import logging
from django.utils.deprecation import MiddlewareMixin
from gvsigol_audit import audit_settings as audit_settings
from gvsigol_audit.audit_logger import create_audit_log, write_audit_log
from gvsigol_audit.audit_registry import get_registered_patterns

logger = logging.getLogger('gvsigol_audit')


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware para auditar peticiones HTTP (APIs REST y vistas Django).
    
    Intercepta peticiones a endpoints registrados y genera logs estructurados
    en formato JSON compatibles con Grafana Loki.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.audit_enabled = getattr(audit_settings, 'AUDIT_ENABLED', True)
        self.audit_mode = getattr(audit_settings, 'AUDIT_MODE', 'basic')
        self.exclude_paths = getattr(audit_settings, 'AUDIT_EXCLUDE_PATHS', [])
        self.auto_detect = getattr(audit_settings, 'AUDIT_AUTO_DETECT', True)
        
        # Cachear prefijo de gvsigol y exclusiones estáticas una sola vez (optimización)
        if self.auto_detect:
            try:
                from django.conf import settings as django_settings
                gvsigol_path = getattr(django_settings, 'GVSIGOL_PATH', 'gvsigonline')
                self.gvsigol_prefix = f'/{gvsigol_path}/'
                # Cachear exclusiones de estáticos también
                self.static_exclusions = [
                    self.gvsigol_prefix + 'static/',
                    self.gvsigol_prefix + 'media/',
                    self.gvsigol_prefix + 'admin/',
                    self.gvsigol_prefix + 'jsi18n/',
                ]
            except:
                self.gvsigol_prefix = None
                self.static_exclusions = []
        else:
            self.gvsigol_prefix = None
            self.static_exclusions = []
        
        # Cachear patrones después de la inicialización (lazy loading)
        # Los patrones se registran en ready() de los plugins al inicio y no cambian después
        self._audit_patterns = None
        super().__init__(get_response)
    
    def _get_audit_patterns(self):
        """
        Obtiene los patrones de auditoría con cacheo.
        Los patrones se cachean después de la primera llamada ya que
        se registran en ready() de los plugins al inicio y no cambian después.
        
        Returns:
            list: Lista de patrones de endpoints
        """
        if self._audit_patterns is None:
            self._audit_patterns = get_registered_patterns()
        return self._audit_patterns
    
    def is_auditable_request(self, request):
        """
        Determina si una petición debe ser auditada.
        
        Utiliza detección automática optimizada si AUDIT_AUTO_DETECT está activado,
        o solo verifica patrones registrados explícitamente si está desactivado.
        
        Args:
            request: Objeto HttpRequest de Django
            
        Returns:
            bool: True si la petición debe ser auditada
        """
        path = request.path
        
        # Verificar si está en la lista de exclusión (rápido, lista pequeña)
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        # Obtener patrones registrados (cacheados después de la primera llamada)
        audit_patterns = self._get_audit_patterns()
        
        # Verificar si el path coincide con patrones registrados explícitamente
        if audit_patterns:
            for pattern in audit_patterns:
                if path.startswith(pattern):
                    return True
        
        # Si auto-detección está desactivada, parar aquí
        if not self.auto_detect:
            return False
        
        # Detección automática optimizada (todo O(1) o listas pequeñas)
        
        # 1. APIs REST: verificar /api/ (muy rápido, O(1))
        if path.startswith('/api/'):
            return True
        
        # 2. APIs REST: verificar headers (acceso a diccionario, O(1))
        content_type = request.META.get('CONTENT_TYPE', '')
        if content_type and ('application/json' in content_type or 'application/xml' in content_type):
            return True
        
        accept = request.META.get('HTTP_ACCEPT', '')
        if accept and ('application/json' in accept or 'application/xml' in accept):
            return True
        
        # 3. Vistas Django: usar prefijo cacheado (O(1))
        if self.gvsigol_prefix and path.startswith(self.gvsigol_prefix):
            # Verificar exclusiones de estáticos (lista pequeña, O(k))
            for exclusion in self.static_exclusions:
                if path.startswith(exclusion):
                    return False
            return True
        
        return False
    
    def process_request(self, request):
        """
        Procesa la petición entrante y registra el tiempo de inicio.
        """
        if not self.audit_enabled:
            return None
        
        if not self.is_auditable_request(request):
            return None
        
        # Guardar tiempo de inicio para calcular tiempo de respuesta
        request._audit_start_time = time.time()
        
        return None
    
    def process_response(self, request, response):
        """
        Procesa la respuesta y genera el log de auditoría.
        
        Args:
            request: Objeto HttpRequest de Django
            response: Objeto HttpResponse de Django
            
        Returns:
            HttpResponse: Respuesta sin modificar
        """
        if not self.audit_enabled:
            return response
        
        if not self.is_auditable_request(request):
            return response
        
        # Calcular tiempo de respuesta
        start_time = getattr(request, '_audit_start_time', None)
        if start_time:
            response_time_ms = (time.time() - start_time) * 1000
        else:
            response_time_ms = 0
        
        try:
            # Crear log de auditoría
            log_data = create_audit_log(
                request=request,
                response=response,
                response_time_ms=response_time_ms,
                mode=self.audit_mode
            )
            
            # Escribir log (verificar si debe usar stdout)
            log_path = getattr(audit_settings, 'AUDIT_LOG_PATH', None)
            use_stdout = bool(log_path and isinstance(log_path, str) and log_path.lower() == 'stdout')
            write_audit_log(log_data, use_stdout=use_stdout)
            
        except Exception as e:
            # No fallar la petición si hay error en el logging
            logger.error(f"Error in audit middleware: {str(e)}", exc_info=True)
        
        return response

