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

import os
from django.conf import settings

"""
Configuración de Auditoría del Sistema

Este módulo centraliza la configuración del sistema de auditoría que puede ser
usado tanto por el core como por plugins.
"""

# Habilitar/deshabilitar auditoría
# Se puede configurar mediante variable de entorno AUDIT_ENABLED o en settings.py
try:
    import environ
    env = environ.Env()
    AUDIT_ENABLED = env('AUDIT_ENABLED', default=False)
except (ImportError, AttributeError):
    AUDIT_ENABLED = getattr(settings, 'AUDIT_ENABLED', False)

# Modo de logging: 'basic', 'full', o 'compact'
# - basic: información mínima (método, path, usuario, status, tiempo)
# - full: información completa incluyendo geometrías
# - compact: información completa pero sin geometrías (para ahorrar espacio)
# Se puede configurar mediante variable de entorno AUDIT_MODE o en settings.py
try:
    AUDIT_MODE = env('AUDIT_MODE', default='compact')
except (NameError, AttributeError):
    AUDIT_MODE = getattr(settings, 'AUDIT_MODE', 'compact')

# Ruta donde escribir los logs de auditoría
# Se puede configurar mediante variable de entorno AUDIT_LOG_PATH o en settings.py
# Si se establece a 'stdout', los logs se escribirán a stdout (útil para Docker)
# Por defecto, si no se especifica, se usa stdout
try:
    log_path = env('AUDIT_LOG_PATH', default=None)
    if log_path:
        if log_path.lower() == 'stdout':
            AUDIT_LOG_PATH = 'stdout'
        else:
            AUDIT_LOG_PATH = log_path
    else:
        # Por defecto, usar stdout (recomendado para Docker y contenedores)
        AUDIT_LOG_PATH = 'stdout'
except (NameError, AttributeError):
    # Si no se puede usar environ, verificar en settings.py
    # Si no está en settings.py, usar stdout por defecto
    AUDIT_LOG_PATH = getattr(settings, 'AUDIT_LOG_PATH', 'stdout')
    # Asegurar que si es None, se establece a stdout
    if not AUDIT_LOG_PATH or AUDIT_LOG_PATH.lower() == 'stdout':
        AUDIT_LOG_PATH = 'stdout'

# Lista de campos sensibles adicionales a filtrar (además de los por defecto)
# Se puede configurar en settings.py como lista
AUDIT_SENSITIVE_FIELDS = getattr(settings, 'AUDIT_SENSITIVE_FIELDS', [])

# Rutas a excluir de la auditoría (patrones de path)
# Se puede configurar en settings.py como lista
AUDIT_EXCLUDE_PATHS = getattr(settings, 'AUDIT_EXCLUDE_PATHS', [
    '/api/v1/swagger/',
    '/api/v1/redoc/',
    '/api/v1/swagger.json',
    '/api/v1/swagger.yaml',
])

# Habilitar detección automática de APIs REST y vistas Django
# Si es True (por defecto), se auditarán automáticamente:
# - Todas las peticiones a /api/*
# - Peticiones con headers JSON/XML
# - Vistas Django bajo el prefijo de gvsigol (ej: /gvsigonline/*)
# Si es False, solo se auditarán los endpoints registrados explícitamente
# Se puede configurar mediante variable de entorno AUDIT_AUTO_DETECT o en settings.py
try:
    AUDIT_AUTO_DETECT = env('AUDIT_AUTO_DETECT', default=True)
except (NameError, AttributeError):
    AUDIT_AUTO_DETECT = getattr(settings, 'AUDIT_AUTO_DETECT', True)

