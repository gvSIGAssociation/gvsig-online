# -*- coding: utf-8 -*-
"""Condiciones de activación y permisos del asistente.

Las decisiones puras no tocan la base de datos: las vistas les pasan los
booleanos que ya calcularon (can_edit, proveedor configurado, etc.).
"""

_PLACEHOLDER_KEYS = (
    '',
    'your_openai_api_key',
    'your_azure_openai_api_key',
)


def feature_enabled(flag, installed, provider_ready):
    """True solo si el flag, GeoCopilot y el proveedor están listos."""
    return bool(flag) and bool(installed) and bool(provider_ready)


def user_may_use(is_authenticated, is_staff, is_superuser):
    return bool(is_authenticated) and (bool(is_staff) or bool(is_superuser))


def workspace_edit_mode(can_edit, can_restricted):
    """'full', 'restricted' o 'forbidden'. Ignora cualquier flag del cliente."""
    if can_edit:
        return 'full'
    if can_restricted:
        return 'restricted'
    return 'forbidden'


def provider_is_ready(provider, enabled, api_key, endpoint=''):
    if not enabled:
        return False
    key = (api_key or '').strip()
    if key in _PLACEHOLDER_KEYS:
        return False
    if provider == 'azure_openai' and not (endpoint or '').strip():
        return False
    if provider not in ('openai', 'azure_openai'):
        return False
    return True


def assistant_feature_enabled():
    """Las tres condiciones de instalación. No mira al usuario."""
    from django.apps import apps
    from gvsigol_plugin_geoetl import settings as geoetl_settings

    if not geoetl_settings.ETL_ASSISTANT_ENABLED:
        return False
    if not apps.is_installed('gvsigol_plugin_geocopilot'):
        return False
    try:
        from gvsigol_plugin_geocopilot.settings import (
            GEOCOPILOT_SETTINGS,
            LANGCHAIN_SETTINGS,
        )
    except Exception:
        return False
    provider = (LANGCHAIN_SETTINGS.get('DEFAULT_LLM_PROVIDER') or '').lower()
    if provider == 'openai':
        block = LANGCHAIN_SETTINGS.get('OPENAI_SETTINGS') or {}
        return provider_is_ready(
            'openai',
            GEOCOPILOT_SETTINGS.get('ENABLE_OPENAI'),
            block.get('API_KEY'),
        )
    if provider == 'azure_openai':
        block = LANGCHAIN_SETTINGS.get('AZURE_OPENAI_SETTINGS') or {}
        return provider_is_ready(
            'azure_openai',
            GEOCOPILOT_SETTINGS.get('ENABLE_AZURE_OPENAI'),
            block.get('API_KEY'),
            block.get('ENDPOINT'),
        )
    return False


def assistant_available(request):
    """Feature activo y usuario staff o superusuario."""
    if not assistant_feature_enabled():
        return False
    user = getattr(request, 'user', None)
    if user is None:
        return False
    return user_may_use(
        getattr(user, 'is_authenticated', False),
        getattr(user, 'is_staff', False),
        getattr(user, 'is_superuser', False),
    )
