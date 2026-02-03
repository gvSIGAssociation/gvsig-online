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

"""
Sistema de registro centralizado de patrones de endpoints para auditoría.

Este es el sistema base independiente que puede ser usado tanto por el core
como por plugins. No tiene dependencias de plugins.
"""

# Registro global de patrones de endpoints
_AUDIT_PATTERNS = set()

# Patrones por defecto (para compatibilidad hacia atrás)
_DEFAULT_PATTERNS = []


def register_audit_pattern(pattern):
    """
    Registra un patrón de endpoint para auditoría.
    
    Args:
        pattern: String con el patrón de path (ej: '/api/v1/layers/', '/gvsigonline/core/')
                 El patrón debe comenzar con '/' y se usa startswith() para la coincidencia.
    
    Ejemplo:
        from gvsigol_audit.audit_registry import register_audit_pattern
        
        register_audit_pattern('/api/v1/layers/')
        register_audit_pattern('/gvsigonline/core/')
    """
    if not isinstance(pattern, str):
        raise ValueError("El patrón debe ser un string")
    
    if not pattern.startswith('/'):
        raise ValueError("El patrón debe comenzar con '/'")
    
    _AUDIT_PATTERNS.add(pattern)


def register_audit_patterns(patterns):
    """
    Registra múltiples patrones de endpoints para auditoría.
    
    Args:
        patterns: Lista o tupla de strings con patrones de path
    
    Ejemplo:
        from gvsigol_audit.audit_registry import register_audit_patterns
        
        register_audit_patterns([
            '/api/v1/layers/',
            '/gvsigonline/core/',
        ])
    """
    for pattern in patterns:
        register_audit_pattern(pattern)


def get_registered_patterns():
    """
    Obtiene todos los patrones registrados para auditoría.
    
    Returns:
        list: Lista de patrones registrados (incluye patrones por defecto)
    """
    return _DEFAULT_PATTERNS + list(_AUDIT_PATTERNS)


def clear_registry():
    """
    Limpia el registro (útil para tests).
    """
    global _AUDIT_PATTERNS
    _AUDIT_PATTERNS.clear()

