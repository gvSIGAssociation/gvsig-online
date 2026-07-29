# -*- coding: utf-8 -*-
"""Obtain OIDC access tokens for GeoNetwork API (bearer) authentication."""
from __future__ import unicode_literals

import logging
import threading
import time

import requests
from gvsigol import settings as gvsigol_settings

from gvsigol_plugin_catalog import settings as catalog_settings

logger = logging.getLogger('gvsigol')

_lock = threading.Lock()
_cached_token = None
_cached_expiry = 0


def _default_token_url():
    configured = getattr(catalog_settings, 'GEONETWORK_OIDC_TOKEN_URL', '') or ''
    if configured:
        return configured.rstrip('/')
    base = getattr(gvsigol_settings, 'OIDC_OP_BASE_URL', None) or ''
    realm = getattr(gvsigol_settings, 'OIDC_OP_REALM_NAME', None) or 'gvsigonline'
    if base:
        return '{}/realms/{}/protocol/openid-connect/token'.format(
            base.rstrip('/'), realm
        )
    return ''


def clear_token_cache():
    global _cached_token, _cached_expiry
    with _lock:
        _cached_token = None
        _cached_expiry = 0


def get_access_token(force_refresh=False):
    """
    Return a Keycloak access token using the Resource Owner Password grant
    against the GeoNetwork OIDC client.

    Tokens are cached in-process until near expiry.
    """
    global _cached_token, _cached_expiry
    now = time.time()
    with _lock:
        if (
            not force_refresh
            and _cached_token
            and _cached_expiry > now + 30
        ):
            return _cached_token

    token_url = _default_token_url()
    client_id = catalog_settings.GEONETWORK_OIDC_CLIENT_ID
    client_secret = catalog_settings.GEONETWORK_OIDC_CLIENT_SECRET
    username = catalog_settings.CATALOG_USER
    password = catalog_settings.CATALOG_PASSWORD
    scope = catalog_settings.GEONETWORK_OIDC_SCOPE

    if not token_url:
        raise RuntimeError(
            'GEONETWORK_OIDC_TOKEN_URL (or OIDC_OP_BASE_URL) is not configured'
        )
    if not client_id or not client_secret:
        raise RuntimeError(
            'GEONETWORK_OIDC_CLIENT_ID / GEONETWORK_OIDC_CLIENT_SECRET are required for bearer auth'
        )
    if not username or not password:
        raise RuntimeError(
            'GEONETWORK_USER / GEONETWORK_PASS are required for bearer auth'
        )

    data = {
        'grant_type': 'password',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password,
        'scope': scope,
    }
    verify = getattr(gvsigol_settings, 'OIDC_VERIFY_SSL', True)
    response = requests.post(
        token_url,
        data=data,
        timeout=getattr(catalog_settings, 'CATALOG_TIMEOUT', 10),
        verify=verify,
        proxies=getattr(gvsigol_settings, 'PROXIES', None),
    )
    if response.status_code != 200:
        logger.error(
            'Failed to obtain GeoNetwork OIDC token: %s %s',
            response.status_code,
            response.text[:500],
        )
        response.raise_for_status()

    payload = response.json()
    access_token = payload.get('access_token')
    if not access_token:
        raise RuntimeError('OIDC token response did not include access_token')

    expires_in = int(payload.get('expires_in') or 300)
    with _lock:
        _cached_token = access_token
        _cached_expiry = now + expires_in
    return access_token
