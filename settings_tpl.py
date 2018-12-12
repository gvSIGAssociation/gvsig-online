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

import os
import ldap
import django.conf.locale
from django_auth_ldap.config import LDAPSearch
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage

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
            try:
                # available since Django 1.10.x
                from django.core.management.utils import get_random_secret_key
            except:
                from django.utils.crypto import get_random_string
                def get_random_secret_key():
                    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
                    return get_random_string(50, chars) 
            from django.core.management import utils
            import os
            SECRET_KEY = get_random_secret_key()
            secret = file(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
            os.chmod(SECRET_FILE, 0o400)
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % SECRET_FILE)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ##DEBUG##

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'gvsigol_auth',
    'gvsigol_services',
    'gvsigol_symbology',
    'gvsigol_filemanager',
    'gvsigol_core',
    ##GVSIGOL_PLUGINS##
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.PersistentRemoteUserMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'gvsigol_core.context_processors.global_settings',
                'django.contrib.messages.context_processors.messages',
                'django.core.context_processors.i18n',
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
    'ENABLED': True,
    'HOST':'##LDAP_HOST##',
    'PORT': '##LDAP_PORT##',
    'DOMAIN': '##LDAP_ROOT_DN##',
    'USERNAME': '##LDAP_BIND_USER##',
    'PASSWORD': '##LDAP_BIND_PASSWD##',
    'AD': '##LDAP_AD_SUFFIX##'
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.RemoteUserBackend',
    'django_auth_ldap.backend.LDAPBackend',
    #'django.contrib.auth.backends.ModelBackend',
)
AUTH_LDAP_SERVER_URI = "ldap://##LDAP_HOST##:##LDAP_PORT##"
AUTH_LDAP_ROOT_DN = "##LDAP_ROOT_DN##"
AUTH_LDAP_USER_SEARCH = LDAPSearch("##LDAP_ROOT_DN##", ldap.SCOPE_SUBTREE, "(uid=%(user)s)")


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
#LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

EXTRA_LANG_INFO = {
    'va': {
        'bidi': False,
        'code': u'va',
        'name': u'Valencian',
        'name_local': u'Valencian'
    },
}

# Add custom languages not provided by Django
LANG_INFO = dict(django.conf.locale.LANG_INFO.items() + EXTRA_LANG_INFO.items())
django.conf.locale.LANG_INFO = LANG_INFO

LANGUAGES = [ ##LANGUAGES## 
]

LOCALE_PATHS = (
    '##GVSIGOL_HOME##/gvsigol/gvsigol/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_core/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_services/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_symbology/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_auth/locale',
    '##GVSIGOL_HOME##/gvsigol/gvsigol_filemanager/locale',
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
LOGOUT_PAGE_URL = '##LOGOUT_PAGE_URL##'

# Email settings
EMAIL_BACKEND_ACTIVE = ##EMAIL_BACKEND_ACTIVE##
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'gvsigonline@scolab.es'
EMAIL_HOST_PASSWORD = '****'
EMAIL_PORT = 587
SITE_ID=1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
BASE_URL = '##BASE_URL##'
MEDIA_ROOT = '##MEDIA_ROOT##'
MEDIA_URL = '##BASE_URL##/##MEDIA_PATH##/'
STATIC_URL = '/##STATIC_PATH##/'
STATIC_ROOT = '##GVSIGOL_HOME##/gvsigol/assets'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'compressor.finders.CompressorFinder',
)

GVSIGOL_VERSION = '2.3.4'

GVSIGOL_USERS_CARTODB = {
    'dbhost': '##DB_HOST##',
    'dbport': '##DB_PORT##',
    'dbname': '##DB_NAME##',
    'dbuser': '##DB_USER##',
    'dbpassword': '##DB_PASSWD##'
}

PUBLIC_VIEWER = True

GEOSERVER_PATH = '/geoserver'
FRONTEND_URL = '##FRONTEND_URL##'
#FRONTEND_URL = 'https://intranet-pre.gva.es'

GVSIGOL_SERVICES = {
    'ENGINE':'geoserver',
    'URL': '##GEOSERVER_BASE_URL##',
    'USER': 'root',
    'PASSWORD': '##GEOSERVER_PASSWD##',
    'CLUSTER_NODES':[##GEOSERVER_CLUSTER_NODES##],
    'SUPPORTED_TYPES': (
                        ('v_PostGIS', _('PostGIS vector')),
                        #('v_SHP', _('Shapefile folder')),                        
                        ('c_GeoTIFF', _('GeoTiff')),
                        ('e_WMS', _('Cascading WMS')),
    ),
    # if MOSAIC_DB entry is omitted, mosaic indexes will be stored as SHPs
    'MOSAIC_DB': {
                  'host': '##DB_HOST##',
                  'port': '##DB_PORT##',
                  'database': '##DB_NAME##',
                  'schema': 'imagemosaic',
                  'user': '##DB_USER##',
                  'passwd': '##DB_PASSWD##'
    },
    # NOTE: we are migrating gdal_tools to the external library pygdaltools.
    # In the future we will only need GDALTOOLS_BASEPATH variable 
    # OGR path is only necessary if different from the one defined on gdal_tools.OGR2OGR_PATH
    'OGR2OGR_PATH': '##OGR2OGR_PATH##',
    'GDALTOOLS_BASEPATH': '##GDALTOOLS_BASEPATH##'
}
                     
TILE_SIZE = 256
MAX_ZOOM_LEVEL = 18

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

GVSIGOL_NAME = '##GVSIGOL_NAME##'
GVSIGOL_SURNAME = '##GVSIGOL_SURNAME##'
GVSIGOL_NAME_SHORT = '##GVSIGOL_NAME_SHORT##'
GVSIGOL_SURNAME_SHORT = '##GVSIGOL_SURNAME_SHORT##'

CSRF_TRUSTED_ORIGINS = ['##GVSIGOL_HOST##']

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

BASELAYER_SUPPORTED_TYPES = ['WMS', 'WMTS', 'XYZ', 'Bing', 'OSM']

WMTS_MAX_VERSION = '1.0.0'
WMS_MAX_VERSION = '1.3.0'
BING_LAYERS = ['Road','Aerial','AerialWithLabels']

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'gvsigol': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
