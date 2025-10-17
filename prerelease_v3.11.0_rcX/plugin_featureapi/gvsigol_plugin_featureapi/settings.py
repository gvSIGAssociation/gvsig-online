# -*- coding: utf-8 -*-

#Es mejor acordar un nombre para el campo al principio y no cambiarlo nunca.
NUM_MAX_FEAT = 100
GVSIGOL_PATH = 'gvsigonline'
TIME_ZONE = 'UTC'
USE_TZ = True
"""
SETTINGS para el settings general de gvsigol
"""
# REST_FRAMEWORK = {
#     'DEFAULT_PERMISSION_CLASSES': (
#         'rest_framework.permissions.IsAuthenticated',
#     ),
#     'DEFAULT_AUTHENTICATION_CLASSES': (
#         'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
#         'rest_framework.authentication.SessionAuthentication'
#     ),
# }
# 
# SWAGGER_SETTINGS = {
#     "api_key": '',
#     "is_authenticated": False, 
#     "is_superuser": False,  
#     'SECURITY_DEFINITIONS': {
#         'api_key': {
#             'type': 'apiKey',
#             'in': 'header',
#             'name': 'Authorization'
#         }
#     },
#     'USE_SESSION_AUTH': False,
#     'JSON_EDITOR': True,
#     'enabled_methods': [
#         'get',
#         'post',
#         'put',
#         'patch',
#         'delete'
#     ]
# }