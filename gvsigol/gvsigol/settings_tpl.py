# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

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
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
import datetime
import os
import ldap
import django.conf.locale
from django_auth_ldap.config import LDAPSearch
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.views import debug
import re
from gvsigol.utils import import_settings

debug.HIDDEN_SETTINGS = re.compile(
    # exclude these variables from debug output
    debug.HIDDEN_SETTINGS.pattern + '|CELERY_BROKER_URL|USERNAME|HOST_USER|DBUSER|^USER$',
    flags=re.IGNORECASE,
)

GVSIGOL_VERSION = '3.10.0-dev'
print("INFO: gvSIG Online version: " + GVSIGOL_VERSION)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
if '__file__' in globals():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
else:
    BASE_DIR = os.path.join(os.path.abspath(os.getcwd()), "gvsigol")

# Eliminando warnings molestos
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '##SECRET_KEY##'
if len(SECRET_KEY) == 14:
    # It has not been replaced by deployment scripts
    # Generate a random one
    SECRET_FILE = os.path.join(BASE_DIR, 'gvsigol', 'secret.txt')
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:
        try:
            from django.core.management.utils import get_random_secret_key
            import os
            SECRET_KEY = get_random_secret_key()
            secret = open(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
            os.chmod(SECRET_FILE, 0o400)
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % SECRET_FILE)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ##DEBUG##

ALLOWED_HOSTS = ['*']
ALLOWED_HOST_NAMES = [##ALLOWED_HOST_NAMES##
]
CSRF_TRUSTED_ORIGINS = [##CSRF_TRUSTED_ORIGINS##
]
CORS_ALLOWED_ORIGINS = [##CORS_ALLOWED_ORIGINS##
]
CORS_ALLOW_CREDENTIALS = True
USE_X_FORWARDED_HOST = ##USE_X_FORWARDED_HOST##
SECURE_PROXY_SSL_HEADER = ##SECURE_PROXY_SSL_HEADER##
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2048
DATA_UPLOAD_MAX_MEMORY_SIZE = int('##DATA_UPLOAD_MAX_MEMORY_SIZE##') #Tamaño máximo para la memoria del getcapabilities default 2621440 (2.5M) es muy poco y no se pueden añadir capas externas cuando el servidor tiene muchas capas
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o774

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.sites',
    'django_celery_beat',
    'rest_framework',
    'gvsigol_statistics',
    'gvsigol_auth',
    'gvsigol_services',
    'gvsigol_symbology',
    'gvsigol_filemanager',
    'gvsigol_core',
    ##GVSIGOL_PLUGINS##
]
INSTALLED_APPS.append('actstream')

try:
    __import__('corsheaders')
    INSTALLED_APPS.append('corsheaders')
except ImportError:
    print('ERROR: No ha instalado la libreria corsheaders')
    
try:
    __import__('drf_yasg')
    INSTALLED_APPS.append('drf_yasg')
except ImportError:
    print('ERROR: No ha instalado la libreria drf_yasg')

ACTSTREAM_SETTINGS = {
    'FETCH_RELATIONS': True,
    'USE_JSONFIELD': True,
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'django.middleware.locale.LocaleMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.PersistentRemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware'
]

try:
    __import__('corsheaders')
    MIDDLEWARE.append('corsheaders.middleware.CorsMiddleware')
except ImportError:
    print('ERROR: No ha instalado la libreria corsheaders')

CRONTAB_ACTIVE = ##CRONTAB_ACTIVE##
ROOT_URLCONF = 'gvsigol.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'gvsigol_auth/templates'),
            os.path.join(BASE_DIR, 'gvsigol_core/templates'),
            os.path.join(BASE_DIR, 'gvsigol_services/templates'),
            os.path.join(BASE_DIR, 'gvsigol_symbology/templates'),
            os.path.join(BASE_DIR, 'gvsigol_filemanager/templates'),
            os.path.join(BASE_DIR, 'gvsigol_statistics/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'gvsigol_core.context_processors.global_settings',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                ##CONTEXT_PROCESSORS##
            ],
        },
    },
]

WSGI_APPLICATION = 'gvsigol.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '##DB_NAME##',
        'USER': '##DB_USER##',
        'PASSWORD': '##DB_PASSWD##',
        'HOST': '##DB_HOST##',
        'PORT': '##DB_PORT##',
        'OPTIONS' : {
            'options': '-c search_path=##DB_SCHEMA##'
        }
    }
}
POSTGIS_VERSION = (2, 1, 2)

AUTH_WITH_REMOTE_USER = ##AUTH_WITH_REMOTE_USER##


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

GVSIGOL_LDAP = {
    'ENABLED': ##LDAP_ENABLED##,
    'HOST':'##LDAP_HOST##',
    'PORT': '##LDAP_PORT##',
    'DOMAIN': '##LDAP_ROOT_DN##',
    'USERNAME': '##LDAP_BIND_USER##',
    'PASSWORD': '##LDAP_BIND_PASSWD##',
    'AD': '##LDAP_AD_SUFFIX##'
}

AUTHENTICATION_BACKENDS = (
    ##DJANGO_AUTHENTICATION_BACKENDS##
)
AUTH_LDAP_SERVER_URI = "ldap://##LDAP_HOST##:##LDAP_PORT##"
AUTH_LDAP_ROOT_DN = "##LDAP_ROOT_DN##"
AUTH_LDAP_USER_SEARCH = LDAPSearch("##LDAP_ROOT_DN##", ldap.SCOPE_SUBTREE, "(uid=%(user)s)")

LOGIN_URL = 'gvsigol_authenticate_user'
GVSIGOL_AUTH_BACKEND = '##GVSIGOL_AUTH_BACKEND##'
"""
GVSIGOL_AUTH_BACKEND is deprecated, use GVSIGOL_AUTH_PROVIDER and GVSIGOL_ROLE_PROVIDER instead
"""
GVSIGOL_AUTH_PROVIDER = GVSIGOL_AUTH_BACKEND
GVSIGOL_ROLE_PROVIDER = GVSIGOL_AUTH_BACKEND
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "##LOGOUT_REDIRECT_URL##"
if GVSIGOL_AUTH_BACKEND != 'gvsigol_auth':
    import_settings(GVSIGOL_AUTH_BACKEND+".settings", globals())
GVSIGOL_AUTH_MIDDLEWARE = '##GVSIGOL_AUTH_MIDDLEWARE##'
AUTH_DASHBOARD_UI = ("##AUTH_DASHBOARD_UI##" != 'False')
AUTH_READONLY_USERS = ("##AUTH_READONLY_USERS##" != 'False')
if GVSIGOL_AUTH_BACKEND == 'gvsigol_plugin_oidc_mozilla' :
    _insert_at = MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1
    MIDDLEWARE.insert(_insert_at, 'gvsigol_plugin_oidc_mozilla.middleware.GvsigolSessionRefresh')

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = '##LANGUAGE_CODE##'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

EXTRA_LANG_INFO = {
    'ca-es-valencia': {
        'bidi': False,
        'code': 'ca-es-valencia',
        'name': 'Valencian',
        'name_local': 'Valencià'
    },
    'va': {
        'bidi': False,
        'code': 'va',
        'name': 'Valencian',
        'name_local': 'Valencian'
    },
}

# Add custom languages not provided by Django
LANG_INFO = dict(list(django.conf.locale.LANG_INFO.items()) + list(EXTRA_LANG_INFO.items()))
django.conf.locale.LANG_INFO = LANG_INFO

LANGUAGES = [ ##LANGUAGES##
]

LOCALE_PATHS = [
    '##GVSIGOL_HOME##/gvsigol/gvsigol/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_core/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_services/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_symbology/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_auth/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_filemanager/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_statistics/locale',
]
for app in INSTALLED_APPS:
    if app.startswith('gvsigol_app_'):
        LOCALE_PATHS.insert(0, os.path.join('##GVSIGOL_HOME##/gvsigol/', app, 'locale'))

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Email settings
EMAIL_BACKEND_ACTIVE = ##EMAIL_BACKEND_ACTIVE##
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = ##EMAIL_USE_TLS##
EMAIL_HOST = '##EMAIL_HOST##'
EMAIL_HOST_USER = '##EMAIL_HOST_USER##'
EMAIL_HOST_PASSWORD = '##EMAIL_HOST_PASSWORD##'
EMAIL_PORT = ##EMAIL_PORT##
EMAIL_TIMEOUT = ##EMAIL_TIMEOUT##
DEFAULT_FROM_EMAIL = 'noreply@##GVSIGOL_HOST##'
SITE_ID=1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
BASE_URL = '##BASE_URL##'
MEDIA_ROOT = '##MEDIA_ROOT##'
MEDIA_URL = '##BASE_URL##/##MEDIA_PATH##/'
STATIC_URL = '/##STATIC_PATH##/'
STATIC_ROOT = '##GVSIGOL_HOME##/gvsigol/assets'
DOCS_URL = '##GVSIGOL_DOCS_URL##'
TEMP_ROOT = '##TEMP_ROOT##'
LAYERS_ROOT = 'layer_downloads'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'compressor.finders.CompressorFinder',
)

GVSIGOL_USERS_CARTODB = {
    'dbhost': '##DB_HOST##',
    'dbport': '##DB_PORT##',
    'dbname': '##DB_NAME##',
    'dbuser': '##DB_USER##',
    'dbpassword': '##DB_PASSWD##',
    'jndiname': '##DB_JNDI_NAME##'
}

# if MOSAIC_DB entry is omitted, mosaic indexes will be stored as SHPs
MOSAIC_DB = {
    'host': '##DB_HOST##',
    'port': '##DB_PORT##',
    'database': '##DB_NAME##',
    'schema': 'mosaic',
    'user': '##DB_USER##',
    'passwd': '##DB_PASSWD##'
}

# NOTE: we are migrating gdal_tools to the external library pygdaltools.
# In the future we will only need GDALTOOLS_BASEPATH variable
# OGR path is only necessary if different from the one defined on gdal_tools.OGR2OGR_PATH
GDALTOOLS_BASEPATH = '##GDALTOOLS_BASEPATH##'
GDAL_LIBRARY_PATH = '##GDAL_LIBRARY_PATH##'
OGR2OGR_PATH = GDALTOOLS_BASEPATH + '/ogr2ogr'

TILE_SIZE = 256
MAX_ZOOM_LEVEL = ##MAX_ZOOM_LEVELS##

# Must be a valid iconv encoding name. Use iconv --list on Linux to see valid names
SUPPORTED_ENCODINGS = [ "LATIN1", "UTF-8", "ISO-8859-15", "WINDOWS-1252"]
USE_DEFAULT_SUPPORTED_CRS = ##CRS_FROM_SETTINGS##
SUPPORTED_CRS = {
    '3857': {
        'code': 'EPSG:3857',
        'title': 'WGS 84 / Pseudo-Mercator',
        'definition': '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs',
        'units': 'meters'
    },
    '4326': {
        'code': 'EPSG:4326',
        'title': 'WGS84 / LatLon',
        'definition': '+proj=longlat +datum=WGS84 +no_defs +axis=neu',
        'units': 'degrees'
    },
    ##SUPPORTED_CRS##
}

GVSIGOL_TOOLS = {
    ##GVSIGOL_TOOLS##
    'get_feature_info_control': {
        'private_fields_prefix': '_'
    },
    'attribute_table': {
        'private_fields_prefix': '_',
        'show_search': True
    }
}

GVSIGOL_ENABLE_ENUMERATIONS = ##GVSIGOL_ENABLE_ENUMERATIONS##


#skin-blue
#skin-blue-light
#skin-red
#skin-red-light
#skin-black
#skin-black-light
#skin-green
#skin-green-light
#skin-purple
#skin-purple-light
#skin-yellow
#skin-yellow-light
GVSIGOL_SKIN = '##GVSIGOL_SKIN##'

GVSIGOL_PATH = '##GVSIGOL_PATH##'
GVSIGOL_NAME = '##GVSIGOL_NAME##'
GVSIGOL_SURNAME = '##GVSIGOL_SURNAME##'
GVSIGOL_NAME_SHORT = '##GVSIGOL_NAME_SHORT##'
GVSIGOL_SURNAME_SHORT = '##GVSIGOL_SURNAME_SHORT##'
GVSIGOL_CUSTOMER_NAME = '##GVSIGOL_CUSTOMER_NAME##'

FILEMANAGER_DIRECTORY = '##FILEMANAGER_DIR##'
FILEMANAGER_MEDIA_ROOT = os.path.join(MEDIA_ROOT, FILEMANAGER_DIRECTORY)
FILEMANAGER_MEDIA_URL = os.path.join(MEDIA_URL, FILEMANAGER_DIRECTORY)
FILEMANAGER_STORAGE = FileSystemStorage(location=FILEMANAGER_MEDIA_ROOT, base_url=FILEMANAGER_MEDIA_URL, file_permissions_mode=0o666)

CONTROL_FIELDS = [{
                'name': 'modified_by',
                'type': 'character_varying'
                },{
                'name': 'last_modification',
                'type': 'date'
                }]
VERSION_FIELD = 'feat_version_gvol'
DATE_FIELD = 'feat_date_gvol'
if 'gvsigol_plugin_restapi' in INSTALLED_APPS or 'gvsigol_plugin_featureapi' in INSTALLED_APPS:
    CONTROL_FIELDS.extend([{
        'name': DATE_FIELD,
        'type': 'timestamp_with_time_zone',
        'visible': False,
        'nullable': False,
        'default':  'now()'
        },{
        'name': VERSION_FIELD,
        'type': 'integer',
        'visible': False,
        'nullable': False,
        'default':  '1'
        }])

EXTERNAL_LAYER_SUPPORTED_TYPES = ['WMS', 'WMTS', 'XYZ', 'Bing', 'OSM']

WMTS_MAX_VERSION = '1.0.0'
WMS_MAX_VERSION = '1.3.0'
BING_LAYERS = ['Road','Aerial','AerialWithLabels']

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        ##DRF_DEFAULT_AUTHENTICATION_CLASSES##,
    ),
}

SWAGGER_SETTINGS = {
    "api_key": '',
    "is_authenticated": False, 
    "is_superuser": False,  
    'SECURITY_DEFINITIONS': {
        'api_key': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    },
    'USE_SESSION_AUTH': False
}

JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=2),
    'JWT_ALLOW_REFRESH': True,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'gvsigol.format': {
            'format' : '[%(asctime)s]%(levelname)s:%(name)s: %(message)s',
            'datefmt' : '%Y/%m/%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'gvsigol.format',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False
        },
        'gvsigol': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
    },
}

TEMPORAL_ADVANCED_PARAMETERS = ##TEMPORAL_ADVANCED_PARAMETERS##

LEGACY_GVSIGOL_SERVICES = { ## We introduce this variable for providing a default Server value when migrating from 2.3.x or earlier versions
    'ENGINE':'geoserver',
    'URL': '##GEOSERVER_BASE_URL##',
    'USER': 'root',
    'PASSWORD': '##GEOSERVER_PASSWD##',
}

SHARED_VIEW_EXPIRATION_TIME=1 #EN DIAS

CACHE_OPTIONS = {
    'GRID_SUBSETS': ['EPSG:3857', 'EPSG:4326'],
    'FORMATS': ['image/png','image/jpeg'],
    'OPERATION_MODE': '##CACHE_OPERATION_MODE##'
}
try:
    print(("Proxy HTTP:"  + os.environ['HTTP_PROXY']))
    print(("Proxy HTTPS:"  + os.environ['HTTPS_PROXY']))
    PROXIES = {
        "http"  : os.environ['HTTP_PROXY'],
        "https" : os.environ['HTTPS_PROXY'],
        "ftp"   : None
        }
except:
    print("No proxies defined.")
    PROXIES = {
        "http"  : None,
        "https" : None,
        "ftp"   : None
    }
    
CELERY_BROKER_URL = '##CELERY_BROKER_URL##'
SENDFILE_BACKEND = 'django_sendfile.backends.xsendfile'
SENDFILE_ROOT = '/' # note we are limitting access in Apache using XSendFilePath, so no need to limit here

OSM_TILING_1 = '##OSM_TILING_1##'
OSM_TILING_2 = '##OSM_TILING_2##'
OSM_TILING_3 = '##OSM_TILING_3##'

RELOAD_NODES_DELAY = 5 #EN SEGUNDOS

CHECK_TILELOAD_ERROR = ##CHECK_TILELOAD_ERROR##

GEOETL_DB = {
    'host': '##DB_HOST##',
    'port': '##DB_PORT##',
    'database': '##DB_NAME##',
    'user': '##DB_USER##',
    'password': '##DB_PASSWD##',
    'schema': 'ds_plugin_geoetl'
}

PRJ_LABELS = ['mobile', 'field_work', 'generic', 'main', 'citizen_app', 'public', 'viewer', 'management', 'government' , 'admin', 'infrastructures', 'data_collection', 'info', 'pois']
SHP_DOWNLOAD_DEFAULT_ENCODING = '##SHP_DOWNLOAD_DEFAULT_ENCODING##'

FRONTEND_BASE_URL = '##FRONTEND_BASE_URL##'
FRONTEND_REDIRECT_URL = '##FRONTEND_REDIRECT_URL##'
USE_SPA_PROJECT_LINKS = '##USE_SPA_PROJECT_LINKS##'

# UI iframe mode (hide html elements)
IFRAME_MODE_UI = False
# Show/hide permissions tab
MANAGE_PERMISSION_UI = True

VIEWER_DEFAULT_CRS = '##VIEWER_DEFAULT_CRS##'
