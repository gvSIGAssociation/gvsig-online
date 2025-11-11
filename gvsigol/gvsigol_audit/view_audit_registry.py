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
Registro centralizado de patrones de vistas Django del core de gvsigol para auditoría.

Permite que cada módulo del core registre sus propias vistas que deben ser auditadas.
Este módulo usa el sistema de registro centralizado de auditoría.
"""

from gvsigol_audit.audit_registry import register_audit_pattern, register_audit_patterns


def register_core_view_pattern(pattern):
    """
    Registra un patrón de vista Django del core para auditoría.
    
    Args:
        pattern: String con el patrón de path (ej: '/gvsigonline/core/', '/gvsigonline/auth/')
                 El patrón debe comenzar con '/' y se usa startswith() para la coincidencia.
    
    Ejemplo:
        from gvsigol_audit.view_audit_registry import register_core_view_pattern
        
        register_core_view_pattern('/gvsigonline/core/')
    """
    register_audit_pattern(pattern)


def register_core_view_patterns(patterns):
    """
    Registra múltiples patrones de vistas Django del core para auditoría.
    
    Args:
        patterns: Lista o tupla de strings con patrones de path
    
    Ejemplo:
        from gvsigol_audit.view_audit_registry import register_core_view_patterns
        
        register_core_view_patterns([
            '/gvsigonline/core/',
            '/gvsigonline/auth/',
        ])
    """
    register_audit_patterns(patterns)


def register_core_modules(gvsigol_path_prefix='/gvsigonline/'):
    """
    Registra automáticamente los patrones de los módulos del core de gvsigol.
    
    Args:
        gvsigol_path_prefix: Prefijo de las URLs de gvsigol (default: '/gvsigonline/')
                            Debe incluir las barras inicial y final.
    
    Ejemplo:
        from gvsigol_audit.view_audit_registry import register_core_modules
        register_core_modules('/gvsigonline/')
    """
    # Módulos del core de gvsigol que deben ser auditados
    core_modules = [
        'core/',
        'auth/',
        'services/',
        'symbology/',
        'filemanager/',
        'statistics/',
    ]
    
    # Asegurar que el prefijo termine con /
    if not gvsigol_path_prefix.endswith('/'):
        gvsigol_path_prefix += '/'
    
    # Asegurar que el prefijo comience con /
    if not gvsigol_path_prefix.startswith('/'):
        gvsigol_path_prefix = '/' + gvsigol_path_prefix
    
    patterns = [gvsigol_path_prefix + module for module in core_modules]
    register_core_view_patterns(patterns)

