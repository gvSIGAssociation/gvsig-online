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

import json
import logging
import copy
from datetime import datetime
from django.conf import settings

logger = logging.getLogger('gvsigol_audit')

# Campos sensibles por defecto que deben ser filtrados
DEFAULT_SENSITIVE_FIELDS = [
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'access_token', 'refresh_token', 'authorization', 'auth', 'credentials',
    'private_key', 'secret_key', 'session_key'
]

# Campos que contienen geometrías GeoJSON
GEOMETRY_FIELDS = [
    'geometry', 'wkb_geometry', 'geom', 'geojson', 'coordinates'
]


def is_geojson_geometry(obj):
    """
    Detecta si un objeto es una geometría GeoJSON.
    
    Args:
        obj: Objeto a verificar
        
    Returns:
        bool: True si es una geometría GeoJSON válida
    """
    if not isinstance(obj, dict):
        return False
    
    # Verificar si tiene el campo 'type' típico de GeoJSON
    if 'type' in obj and obj['type'] in ['Point', 'LineString', 'Polygon', 
                                         'MultiPoint', 'MultiLineString', 
                                         'MultiPolygon', 'GeometryCollection']:
        # Verificar si tiene 'coordinates' o 'geometries'
        if 'coordinates' in obj or 'geometries' in obj:
            return True
    
    return False


def filter_sensitive_data(data, sensitive_fields=None):
    """
    Filtra campos sensibles de un diccionario de forma recursiva.
    
    Args:
        data: Diccionario o estructura de datos a filtrar
        sensitive_fields: Lista de nombres de campos sensibles (default: DEFAULT_SENSITIVE_FIELDS)
        
    Returns:
        Diccionario con campos sensibles reemplazados por "[FILTERED]"
    """
    if sensitive_fields is None:
        sensitive_fields = DEFAULT_SENSITIVE_FIELDS
    
    if not isinstance(data, dict):
        return data
    
    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Verificar si el campo es sensible
        is_sensitive = any(sensitive_field.lower() in key_lower 
                          for sensitive_field in sensitive_fields)
        
        if is_sensitive:
            filtered[key] = "[FILTERED]"
        elif isinstance(value, dict):
            filtered[key] = filter_sensitive_data(value, sensitive_fields)
        elif isinstance(value, list):
            filtered[key] = [
                filter_sensitive_data(item, sensitive_fields) 
                if isinstance(item, dict) else item
                for item in value
            ]
        else:
            filtered[key] = value
    
    return filtered


def filter_geometries(data):
    """
    Filtra geometrías GeoJSON de un diccionario de forma recursiva.
    
    Args:
        data: Diccionario o estructura de datos a filtrar
        
    Returns:
        Diccionario con geometrías reemplazadas por "[GEOMETRY_FILTERED]"
    """
    if not isinstance(data, dict):
        return data
    
    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Verificar si el campo es una geometría
        is_geometry_field = any(geom_field.lower() in key_lower 
                                for geom_field in GEOMETRY_FIELDS)
        
        if is_geometry_field and is_geojson_geometry(value):
            filtered[key] = "[GEOMETRY_FILTERED]"
        elif isinstance(value, dict):
            # Verificar si el objeto completo es una geometría GeoJSON
            if is_geojson_geometry(value):
                filtered[key] = "[GEOMETRY_FILTERED]"
            else:
                filtered[key] = filter_geometries(value)
        elif isinstance(value, list):
            filtered[key] = [
                "[GEOMETRY_FILTERED]" if is_geojson_geometry(item) 
                else (filter_geometries(item) if isinstance(item, dict) else item)
                for item in value
            ]
        else:
            filtered[key] = value
    
    return filtered


def get_client_ip(request):
    """
    Obtiene la IP real del cliente, considerando proxies.
    
    Args:
        request: Objeto HttpRequest de Django
        
    Returns:
        str: IP del cliente
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


def get_request_body(request):
    """
    Obtiene el cuerpo de la petición como diccionario.
    
    Args:
        request: Objeto HttpRequest de Django
        
    Returns:
        dict: Cuerpo de la petición parseado, o None si no se puede parsear
    """
    try:
        if hasattr(request, 'body') and request.body:
            # Intentar parsear como JSON
            try:
                return json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Si no es JSON, devolver como string truncado
                body_str = request.body.decode('utf-8', errors='ignore')
                if len(body_str) > 1000:
                    return {"_raw": body_str[:1000] + "...[TRUNCATED]"}
                return {"_raw": body_str}
    except Exception as e:
        logger.warning(f"Error parsing request body: {str(e)}")
    
    return None


def create_audit_log(request, response, response_time_ms, mode='basic'):
    """
    Crea un log de auditoría en formato JSON compatible con Loki.
    
    Args:
        request: Objeto HttpRequest de Django
        response: Objeto HttpResponse de Django
        response_time_ms: Tiempo de respuesta en milisegundos
        mode: Modo de logging ('basic', 'full', o 'compact')
        
    Returns:
        dict: Log estructurado en formato JSON
    """
    # Información básica siempre presente
    log_data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'level': 'info',
        'method': request.method,
        'path': request.path,
        'user': request.user.username if request.user.is_authenticated else 'anonymous',
        'user_id': request.user.id if request.user.is_authenticated else None,
        'status_code': response.status_code,
        'response_time_ms': round(response_time_ms, 2),
        'ip_address': get_client_ip(request)
    }
    
    # Modo básico: solo información esencial
    if mode == 'basic':
        return log_data
    
    # Modos full y compact: información adicional
    log_data['query_params'] = dict(request.GET)
    log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
    
    # Filtrar headers sensibles
    headers = {}
    sensitive_headers = ['authorization', 'cookie', 'x-api-key']
    for key, value in request.META.items():
        if key.startswith('HTTP_'):
            header_name = key[5:].replace('_', '-').title()
            if any(sensitive.lower() in header_name.lower() 
                   for sensitive in sensitive_headers):
                headers[header_name] = "[FILTERED]"
            else:
                headers[header_name] = value
    
    log_data['headers'] = headers
    
    # Obtener y filtrar request_body
    request_body = get_request_body(request)
    if request_body:
        # Filtrar datos sensibles
        filtered_body = filter_sensitive_data(request_body)
        
        # En modo compact, también filtrar geometrías
        if mode == 'compact':
            filtered_body = filter_geometries(filtered_body)
        
        log_data['request_body'] = filtered_body
    
    return log_data


def write_audit_log(log_data, log_path=None, use_stdout=False):
    """
    Escribe un log de auditoría en formato JSON a un archivo o stdout.
    
    Args:
        log_data: Diccionario con los datos del log
        log_path: Ruta del archivo de log (default: desde settings)
        use_stdout: Si es True, escribir a stdout en lugar de archivo (útil para Docker)
    """
    try:
        # Si use_stdout está activado, escribir directamente a stdout (Docker capturará los logs)
        if use_stdout:
            import sys
            json.dump(log_data, sys.stdout, ensure_ascii=False)
            sys.stdout.write('\n')
            sys.stdout.flush()
            return
        
        if log_path is None:
            # Obtener path desde settings de auditoría
            try:
                from gvsigol_audit import audit_settings as audit_settings
                log_path = getattr(audit_settings, 'AUDIT_LOG_PATH', 'stdout')
            except (ImportError, AttributeError):
                log_path = 'stdout'
        
        # Si el path es 'stdout', escribir directamente a stdout
        if log_path and log_path.lower() == 'stdout':
            import sys
            json.dump(log_data, sys.stdout, ensure_ascii=False)
            sys.stdout.write('\n')
            sys.stdout.flush()
            return
        
        # Crear directorio si no existe
        import os
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                # Si no se puede crear el directorio, escribir a stdout
                logger.warning(f"No se pudo crear directorio de logs {log_dir}: {str(e)}. Escribiendo a stdout.")
                import sys
                json.dump(log_data, sys.stdout, ensure_ascii=False)
                sys.stdout.write('\n')
                sys.stdout.flush()
                return
        
        # Escribir log en formato JSON (una línea por log, compatible con Loki)
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False)
                f.write('\n')
        except (OSError, PermissionError) as e:
            # Si no se puede escribir al archivo, escribir a stdout
            logger.warning(f"No se pudo escribir a {log_path}: {str(e)}. Escribiendo a stdout.")
            import sys
            json.dump(log_data, sys.stdout, ensure_ascii=False)
            sys.stdout.write('\n')
            sys.stdout.flush()
    
    except Exception as e:
        logger.error(f"Error writing audit log: {str(e)}")
        # Como último recurso, intentar escribir a stdout
        try:
            import sys
            json.dump(log_data, sys.stdout, ensure_ascii=False)
            sys.stdout.write('\n')
            sys.stdout.flush()
        except:
            pass

