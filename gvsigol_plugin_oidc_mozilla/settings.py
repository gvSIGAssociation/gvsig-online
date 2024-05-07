# -*- coding: utf-8 -*-
from xmlrpc.client import boolean
import environ
import os
import logging


LOGGER = logging.getLogger('gvsigol')


LOGGER.info('Loading plugin  plugin_oidc_mozilla.')

#TODO: 
# OIDC_OP_BASE_URL="$BASE_URL/auth"
# DJANGO_AUTHENTICATION_BACKENDS
# DRF_DEFAULT_AUTHENTICATION_CLASSES ... ver configure.sh

env_plugin_oidc_mozilla = environ.Env(
    OIDC_OP_BASE_URL=(str, '/auth'), 
    OIDC_OP_REALM_NAME=(str,'master'),
    OIDC_OP_AUTHORIZATION_ENDPOINT=(str, None),
    OIDC_OP_TOKEN_ENDPOINT=(str, None),
    OIDC_OP_JWKS_ENDPOINT=(str, None),
    OIDC_OP_LOGOUT_ENDPOINT=(str, None),
    OIDC_OP_USER_ENDPOINT=(str, None),
    OIDC_RP_CLIENT_ID=(str),
    OIDC_RP_CLIENT_SECRET=(str),
    KEYCLOAK_ADMIN_CLIENT_ID=(str),
    KEYCLOAK_ADMIN_CLIENT_SECRET=(str),
    OIDC_RP_SCOPES=(str,'openid email username'),
    MANAGE_PASSWORD_URL=(str,''),
    OIDC_GVSIGOL_CONFIG_MODULE=(str,''),
    OIDC_GVSIGOL_EMAIL_LOGIN=(bool,True),
    ALLOW_LOGOUT_GET_METHOD=(bool,True),
    OIDC_RP_SIGN_ALGO=(str,'RS256'),
    GVSIGOL_SUPERUSER_ROLE=(str,'GVSIGOL_DJANGO_SUPERUSER'),
    GVSIGOL_STAFF_ROLE=(str, 'GVSIGOL_DJANGO_STAFF'),
    OIDC_STORE_ID_TOKEN=(bool, True),
    OIDC_STORE_ACCESS_TOKEN=(bool, True),
    OIDC_STORE_REFRESH_TOKEN=(bool, False),
    OIDC_MOBILE_CLIENT_ID=(str, 'OIDC_MOBILE_CLIENT_ID')
 )
OIDC_OP_BASE_URL = env_plugin_oidc_mozilla('OIDC_OP_BASE_URL')
OIDC_OP_REALM_NAME = env_plugin_oidc_mozilla('OIDC_OP_REALM_NAME')
OIDC_RP_CLIENT_ID = env_plugin_oidc_mozilla('OIDC_RP_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = env_plugin_oidc_mozilla('OIDC_RP_CLIENT_SECRET')
KEYCLOAK_ADMIN_CLIENT_ID = env_plugin_oidc_mozilla('KEYCLOAK_ADMIN_CLIENT_ID')
KEYCLOAK_ADMIN_CLIENT_SECRET = env_plugin_oidc_mozilla('KEYCLOAK_ADMIN_CLIENT_SECRET')
OIDC_OP_REALM_BASE_URL= env_plugin_oidc_mozilla('OIDC_OP_BASE_URL')+ '/realms/' + env_plugin_oidc_mozilla('OIDC_OP_REALM_NAME')
if env_plugin_oidc_mozilla('OIDC_OP_AUTHORIZATION_ENDPOINT'):
    OIDC_OP_AUTHORIZATION_ENDPOINT=env_plugin_oidc_mozilla('OIDC_OP_AUTHORIZATION_ENDPOINT')
else:
    OIDC_OP_AUTHORIZATION_ENDPOINT=OIDC_OP_REALM_BASE_URL + '/protocol/openid-connect/auth'
if env_plugin_oidc_mozilla('OIDC_OP_TOKEN_ENDPOINT'):
    OIDC_OP_TOKEN_ENDPOINT=env_plugin_oidc_mozilla('OIDC_OP_TOKEN_ENDPOINT')
else:
    OIDC_OP_TOKEN_ENDPOINT=OIDC_OP_REALM_BASE_URL+ '/protocol/openid-connect/token'
if env_plugin_oidc_mozilla('OIDC_OP_JWKS_ENDPOINT'):
    OIDC_OP_JWKS_ENDPOINT=env_plugin_oidc_mozilla('OIDC_OP_JWKS_ENDPOINT')
else:
    OIDC_OP_JWKS_ENDPOINT=OIDC_OP_REALM_BASE_URL+ '/protocol/openid-connect/certs'
if env_plugin_oidc_mozilla('OIDC_OP_LOGOUT_ENDPOINT'):
    OIDC_OP_LOGOUT_ENDPOINT=env_plugin_oidc_mozilla('OIDC_OP_LOGOUT_ENDPOINT')
else:
    OIDC_OP_LOGOUT_ENDPOINT=OIDC_OP_REALM_BASE_URL+ '/protocol/openid-connect/logout'
if env_plugin_oidc_mozilla('OIDC_OP_USER_ENDPOINT'):
    OIDC_OP_USER_ENDPOINT=env_plugin_oidc_mozilla('OIDC_OP_USER_ENDPOINT')
else:
    OIDC_OP_USER_ENDPOINT=OIDC_OP_REALM_BASE_URL+ '/protocol/openid-connect/userinfo'
#OIDC_OP_LOGOUT_ENDPOINT = ''
OIDC_OP_LOGOUT_URL_METHOD = "gvsigol_plugin_oidc_mozilla.provider_logout"
OIDC_RP_SIGN_ALGO = env_plugin_oidc_mozilla('OIDC_RP_SIGN_ALGO')
OIDC_STORE_ID_TOKEN = env_plugin_oidc_mozilla('OIDC_STORE_ID_TOKEN')
OIDC_STORE_ACCESS_TOKEN =  env_plugin_oidc_mozilla('OIDC_STORE_ACCESS_TOKEN')
OIDC_STORE_REFRESH_TOKEN = env_plugin_oidc_mozilla('OIDC_STORE_REFRESH_TOKEN')
OIDC_RP_SCOPES = env_plugin_oidc_mozilla('OIDC_RP_SCOPES') + " " + OIDC_RP_CLIENT_ID
MANAGE_PASSWORD_URL = env_plugin_oidc_mozilla('MANAGE_PASSWORD_URL')
OIDC_EXEMPT_URLS = ['gvsigol_authenticate_user', 'gvsigol_logout_user']
LOGIN_REDIRECT_URL_FAILURE = 'index'
OIDC_GVSIGOL_CONFIG_MODULE = env_plugin_oidc_mozilla('OIDC_GVSIGOL_CONFIG_MODULE')
OIDC_GVSIGOL_EMAIL_LOGIN = env_plugin_oidc_mozilla('OIDC_GVSIGOL_EMAIL_LOGIN')
ALLOW_LOGOUT_GET_METHOD = env_plugin_oidc_mozilla('ALLOW_LOGOUT_GET_METHOD')
#OIDC_AUTH_REQUEST_EXTRA_PARAMS= {"app": "LIBRA"}
OIDC_USE_PKCE = True
#DJANGO_AUTHENTICATION_BACKENDS="'gvsigol_plugin_oidc_mozilla.oidc.GvsigolOIDCAuthenticationBackend',"
GVSIGOL_SUPERUSER_ROLE = env_plugin_oidc_mozilla('GVSIGOL_SUPERUSER_ROLE')
GVSIGOL_STAFF_ROLE = env_plugin_oidc_mozilla('GVSIGOL_STAFF_ROLE')
OIDC_MOBILE_CLIENT_ID = env_plugin_oidc_mozilla('OIDC_MOBILE_CLIENT_ID')

LOGGER.info('OIDC_OP_BASE_URL=%s',OIDC_OP_BASE_URL)
LOGGER.info('OIDC_OP_REALM_NAME=%s', OIDC_OP_REALM_NAME)
LOGGER.info('OIDC_OP_REALM_BASE_URL=%s',  OIDC_OP_REALM_BASE_URL)
LOGGER.info('OIDC_OP_AUTHORIZATION_ENDPOINT=%s', OIDC_OP_AUTHORIZATION_ENDPOINT)
LOGGER.info('OIDC_OP_TOKEN_ENDPOINT=%s', OIDC_OP_TOKEN_ENDPOINT)
LOGGER.info('OIDC_OP_JWKS_ENDPOINT=%s', OIDC_OP_JWKS_ENDPOINT)
LOGGER.info('OIDC_OP_LOGOUT_ENDPOINT=%s', OIDC_OP_LOGOUT_ENDPOINT)
LOGGER.info('OIDC_OP_USER_ENDPOINT=%s', OIDC_OP_USER_ENDPOINT)
LOGGER.info('OIDC_OP_LOGOUT_ENDPOINT=%s', OIDC_OP_LOGOUT_ENDPOINT)
LOGGER.info('OIDC_OP_LOGOUT_URL_METHOD=%s', OIDC_OP_LOGOUT_URL_METHOD)
LOGGER.info('OIDC_RP_SIGN_ALGO=%s', OIDC_RP_SIGN_ALGO)
LOGGER.info('OIDC_OP_USER_ENDPOINT=%s', OIDC_OP_USER_ENDPOINT)
LOGGER.info('OIDC_RP_SCOPES=%s', OIDC_RP_SCOPES)
LOGGER.info('GVSIGOL_SUPERUSER_ROLE=%s', GVSIGOL_SUPERUSER_ROLE)
LOGGER.info('GVSIGOL_STAFF_ROLE=%s', GVSIGOL_STAFF_ROLE)
LOGGER.info('OIDC_MOBILE_CLIENT_ID=%s', OIDC_MOBILE_CLIENT_ID)

# TODO: show only in debug mode
LOGGER.info('OIDC_RP_CLIENT_ID=%s', OIDC_RP_CLIENT_ID)
LOGGER.info('KEYCLOAK_ADMIN_CLIENT_ID=%s', KEYCLOAK_ADMIN_CLIENT_ID)


