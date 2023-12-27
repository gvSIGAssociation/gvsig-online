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

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

import os
import ldap
import django.conf.locale
from django.conf import settings
from django_auth_ldap.config import LDAPSearch
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
import datetime
from gvsigol.utils import import_settings
import environ


print ("INFO: Ejecutando settings.py !!...........................................")

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
if '__file__' in globals():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
else:
    BASE_DIR = os.path.join(os.path.abspath(os.getcwd()), "gvsigol")

if os.environ.get("UWSGI_ENABLED") and os.environ.get("UWSGI_ENABLED")=='True': 
    default_static_dir="/opt/gvsigonline/static"
    default_static_url="/static/"
else:
    default_static_dir=str(os.path.join(BASE_DIR, 'assets'))
    default_static_url="/gvsigonline/static/"


# Define default environment 
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),    
    BASE_URL=(str,'https://localhost'),
    STATIC_ROOT=(str,default_static_dir),
    STATIC_URL=(str,default_static_url),
    MEDIA_ROOT=(str,'/opt/gvsigol_data/'),
    MEDIA_URL=(str,'/media/'),
    ALLOWED_HOST_NAMES=(list,['http://localhost:8000']),
    GVSIGOL_PLUGINS=(list),
    GVSIGOL_SKIN=(str,'skin-blue'),
    DB_HOST=(str,'localhost'),
    DB_PORT=(str,'5432'),
    DB_USER=(str,'gvsigonline'),
    DB_PASS=(str,'gvsigonline'),
    DB_NAME=(str,'gvsigonline'),
    # Auth
    DJANGO_AUTHENTICATION_BACKENDS=(tuple,()),
    GVSIGOL_AUTH_BACKEND=(str,'gvsigol_auth'),
    GVSIGOL_AUTH_MIDDLEWARE=(str,''),
    OIDC_VERIFY_SSL=(bool, True),
    # Setup support for proxy headers
    USE_X_FORWARDED_HOST=(bool,True),
    SECURE_PROXY_SSL_HEADER=(tuple,('HTTP_X_FORWARDED_PROTO', 'https')),
    AUTH_DASHBOARD_UI=(bool,True),
    AUTH_READONLY_USERS=(bool,False),
    # UI
    IFRAME_MODE_UI=(bool,False),
    MANAGE_PERMISSION_UI=(bool,True),
    #csrf
    CSRF_TRUSTED_ORIGINS = (list,['localhost']),
    #cors
    CORS_ALLOWED_ORIGINS = (list,['http://localhost:8000']),    
    CORS_ALLOW_CREDENTIALS = (bool,True),
    CORS_ORIGIN_ALLOW_ALL = (bool,False),
    # frontend SPA
    USE_SPA_PROJECT_LINKS = (bool,False),
    FRONTEND_BASE_URL = (str,'/gvsigonline'),
    FRONTEND_REDIRECT_URL = (str,'/gvsigonline'),
    #Log level
    LOG_LEVEL=(str,"DEBUG"),
    # LDAP
    LDAP_ENABLED=(bool,False),
    LDAP_HOST=(str,'localhost'),
    LDAP_PORT=(str,'389'),
    LDAP_ROOT_DN=(str,'dc=local,dc=gvsigonline,dc=com'),
    LDAP_BIND_USER=(str,'gvsigonline'),
    LDAP_BIND_PASSWD=(str,'gvsigonline'),
    LDAP_AD_SUFFIX=(str,''),
    #CELERY
    #TODO: split string host, pass, etc
    CELERY_BROKER_URL=(str,'pyamqp://gvsigol:12345678@localhost:5672/gvsigol'),

)
ENVIRON_FILE = os.path.join(BASE_DIR, '.env')
environ.Env.read_env(ENVIRON_FILE)

# Eliminando warnings molestos  
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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
            SECRET_KEY = get_random_secret_key()
            secret = open(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
            os.chmod(SECRET_FILE, 0o400)
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % SECRET_FILE)

#
# TODO: Revisar si va a ser necesario con Docker ya que existe un .env que debe añadirse al .svnignore/.gitignore
#
try:
    from gvsigol import settings_passwords
except:
    # Store your passwords for local development in 'settings_passwds.py'
    # Do not write any password here!!!!
    pw_file = open(os.path.join(BASE_DIR, 'gvsigol', 'settings_passwords.py'), 'w')
    pw_file.write("BING_KEY_DEVEL='yourbingkey'\n")
    pw_file.write("DB_USER_DEVEL='postgres'\n")
    pw_file.write("DB_PW_DEVEL='postgres'\n")
    pw_file.write("LDAP_USER_DEVEL='yourldapuser'\n")
    pw_file.write("LDAP_PW_DEVEL='yourldapkey'\n")
    pw_file.write("GEOSERVER_USER_DEVEL='admin'\n")
    pw_file.write("GEOSERVER_PW_DEVEL='geoserver'\n")
    pw_file.write("EMAIL_USER_DEVEL='example@youremaildomain.org'\n")
    pw_file.write("EMAIL_PASSWORD_DEVEL=''\n")
    pw_file.close()
    from gvsigol import settings_passwords
finally:
    # Store your passwords for local development in 'settings_passwords.py'
    # Do not write any password here!!!!
    try:
        BING_KEY_DEVEL = settings_passwords.BING_KEY_DEVEL
    except:
        BING_KEY_DEVEL = ''
    try:
        DB_USER_DEVEL = settings_passwords.DB_USER_DEVEL
    except:
        DB_USER_DEVEL = 'postgres'
    try:
        DB_PW_DEVEL = settings_passwords.DB_PW_DEVEL
    except:
        DB_PW_DEVEL = 'postgres'
    try:
        LDAP_USER_DEVEL = settings_passwords.LDAP_USER_DEVEL
    except:
        LDAP_USER_DEVEL = ''
    try:
        LDAP_PW_DEVEL = settings_passwords.LDAP_PW_DEVEL
    except:
        LDAP_PW_DEVEL = ''
    try:
        GEOSERVER_USER_DEVEL = settings_passwords.GEOSERVER_USER_DEVEL
    except:
        GEOSERVER_USER_DEVEL = 'admin'
    try:
        GEOSERVER_PW_DEVEL = settings_passwords.GEOSERVER_PW_DEVEL
    except:
        GEOSERVER_PW_DEVEL = 'geoserver'
    try:
        EMAIL_USER_DEVEL = settings_passwords.EMAIL_USER_DEVEL
    except:
        EMAIL_USER_DEVEL = ''
    try:
        EMAIL_PASSWORD_DEVEL = settings_passwords.EMAIL_PASSWORD_DEVEL
    except:
        EMAIL_PASSWORD_DEVEL = ''


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = ['*']
USE_X_FORWARDED_HOST = env('USE_X_FORWARDED_HOST')
SECURE_PROXY_SSL_HEADER = env('SECURE_PROXY_SSL_HEADER')

#GEOS_LIBRARY_PATH = 'C:\\Python27\\Lib\\site-packages\\osgeo\\geos_c.dll'
#GDAL_LIBRARY_PATH = '/usr/local/lib/libgdal.so'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'mozilla_django_oidc',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.sites',
    'django_extensions',
    'rest_framework',

    ############# CORE ################
    'gvsigol_statistics',
    'gvsigol_auth',
    'gvsigol_services',
    'gvsigol_symbology',
    'gvsigol_filemanager',
    'gvsigol_core',

    'actstream',
    #### DEPENDENCIES ######,
    'django_celery_beat'    
]

# environment
#from dotenv import load_dotenv
#load_dotenv()

# default environment

#Load plugins
#plugins = envos.getenv("GVSIGOL_PLUGINS").split(",")
for i in env('GVSIGOL_PLUGINS'):
    print("INFO: Loading plugin " + i)
    INSTALLED_APPS.append(i)


# corsheader
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
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',   
    'django.contrib.auth.middleware.PersistentRemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.CommonMiddleware',
]


try:
    __import__('corsheaders')
    MIDDLEWARE.append('corsheaders.middleware.CorsMiddleware')
except ImportError:
    print('ERROR: No ha instalado la libreria corsheaders')

CORS_ORIGIN_ALLOW_ALL = env('CORS_ORIGIN_ALLOW_ALL')
CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = env('CORS_ALLOW_CREDENTIALS')

CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')

CRONTAB_ACTIVE = True
ROOT_URLCONF = 'gvsigol.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'gvsigol_statistics/templates'),
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
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'gvsigol.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        #'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'), # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
        'PASSWORD': env('DB_PASS'), # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}
POSTGIS_VERSION = (2, 3, 3)

AUTH_WITH_REMOTE_USER = False

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

GVSIGOL_LDAP = {
    'ENABLED': env('LDAP_ENABLED'),
    'HOST': env('LDAP_HOST'),
    'PORT': env('LDAP_PORT'),
    'DOMAIN': env('LDAP_ROOT_DN'),
    'USERNAME': env('LDAP_BIND_USER'),
    'PASSWORD': env('LDAP_BIND_PASSWD'),
    'AD': env('LDAP_AD_SUFFIX')
}    

AUTHENTICATION_BACKENDS = (
    #'django.contrib.auth.backends.RemoteUserBackend',
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)

#Load auth backends
AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS + env('DJANGO_AUTHENTICATION_BACKENDS')
print ("INFO: Additional AUTHENTICATION_BACKENDS = " + str(env('DJANGO_AUTHENTICATION_BACKENDS')))

LOGIN_URL = 'gvsigol_authenticate_user'
#GVSIGOL_AUTH_BACKEND = 'gvsigol_plugin_oidc_mozilla'
GVSIGOL_AUTH_BACKEND = env('GVSIGOL_AUTH_BACKEND')
LOGIN_REDIRECT_URL = "home"
#LOGIN_REDIRECT_URL = "https://localhost/gvsigonline"
LOGOUT_REDIRECT_URL = "index"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
if GVSIGOL_AUTH_BACKEND != 'gvsigol_auth':
    import_settings(GVSIGOL_AUTH_BACKEND+".settings", globals())
GVSIGOL_AUTH_MIDDLEWARE = env('GVSIGOL_AUTH_MIDDLEWARE')
AUTH_LDAP_SERVER_URI = "ldap://" + env('LDAP_HOST') + ":" + env('LDAP_PORT')
AUTH_LDAP_ROOT_DN = env('LDAP_ROOT_DN')
AUTH_LDAP_USER_SEARCH = LDAPSearch(env('LDAP_ROOT_DN'), ldap.SCOPE_SUBTREE, "(uid=%(user)s)")
AUTH_DASHBOARD_UI = env('AUTH_DASHBOARD_UI')
AUTH_READONLY_USERS = env('AUTH_READONLY_USERS')
OIDC_VERIFY_SSL = env('OIDC_VERIFY_SSL')

if GVSIGOL_AUTH_BACKEND == 'gvsigol_plugin_oidc_mozilla' :
    MIDDLEWARE.insert(6, 'mozilla_django_oidc.middleware.SessionRefresh')

# Internationalization
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

EXTRA_LANG_INFO = {
    'ca-es@valencia': {
        'bidi': False,
        'code': 'ca-es@valencia',
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



LANGUAGES = (
    ('es', _('Spanish')),
    #('ca-es@valencia', _('Valencian')),
    #('ca', _('Catalan')),
    ('en', _('English')),
    #('pt', _('Portuguese')),
    #('de', _('German')),
    #('pt-br', _('Brazilian Portuguese')),
)


LOCALE_PATHS =  [
    os.path.join(BASE_DIR, 'gvsigol/locale'),
    os.path.join(BASE_DIR, 'gvsigol_core/locale'),
    os.path.join(BASE_DIR, 'gvsigol_auth/locale'),
    os.path.join(BASE_DIR, 'gvsigol_services/locale'),
    os.path.join(BASE_DIR, 'gvsigol_statistics/locale'),
    os.path.join(BASE_DIR, 'gvsigol_symbology/locale'),
    os.path.join(BASE_DIR, 'gvsigol_filemanager/locale')
]
for app in INSTALLED_APPS:
    if app.startswith('gvsigol_app_') or app.startswith('gvsigol_plugin_'):
        LOCALE_PATHS.append(os.path.join(BASE_DIR, app, 'locale'))

# Email settings
EMAIL_BACKEND_ACTIVE = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
#EMAIL_HOST = ''
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = EMAIL_USER_DEVEL
EMAIL_HOST_PASSWORD = EMAIL_PASSWORD_DEVEL
EMAIL_PORT = 587
SITE_ID=1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
#BASE_URL = 'https://localhost'
#MEDIA_ROOT = '/usr/local/var/www/media/'
#MEDIA_URL = 'https://localhost/media/'
BASE_URL = env('BASE_URL') 
MEDIA_ROOT = env('MEDIA_ROOT')
MEDIA_URL = env('MEDIA_URL')
STATIC_ROOT = env('STATIC_ROOT')
STATIC_URL = env('STATIC_URL')

#STATICFILES_DIRS = (
#    os.path.join(BASE_DIR, 'gvsigol_core/static'),
#    os.path.join(BASE_DIR, 'gvsigol_auth/static'),
#    os.path.join(BASE_DIR, 'gvsigol_services/static'),
#    os.path.join(BASE_DIR, 'gvsigol_symbology/static'),
#    os.path.join(BASE_DIR, 'gvsigol_filemanager/static'),
#    os.path.join(BASE_DIR, 'gvsigol_statistics/static'),
#    os.path.join(BASE_DIR, 'gvsigol_app_librapicassa/static'),
#    os.path.join(BASE_DIR, 'gvsigol_plugin_picassa/static'),
#)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'compressor.finders.CompressorFinder',
)

GVSIGOL_VERSION = '3.x.x-dev'

GVSIGOL_USERS_CARTODB = {
    'dbhost': env('DB_HOST'),
    'dbport': env('DB_PORT'),
    'dbname': env('DB_NAME'),
    'dbuser': env('DB_USER'), 
    'dbpassword': env('DB_PASS') 
}

MOSAIC_DB = {
    'host': env('DB_HOST'),
    'port': env('DB_PORT'),
    'database': env('DB_NAME'),
    'schema': 'imagemosaic',
    'user': env('DB_USER'), 
    'passwd': env('DB_PASS')
}

#GDALTOOLS_BASEPATH = '/usr/bin'
#GDALTOOLS_BASEPATH = '/usr/local/bin'
#OGR2OGR_PATH = GDALTOOLS_BASEPATH + '/ogr2ogr'

TILE_SIZE = 256
MAX_ZOOM_LEVEL = 20 

# Must be a valid iconv encoding name. Use iconv --list on Linux to see valid names 
SUPPORTED_ENCODINGS = [ "LATIN1", "UTF-8", "ISO-8859-15", "WINDOWS-1252"]
USE_DEFAULT_SUPPORTED_CRS = True
SUPPORTED_CRS = {
    '3857': {
        'code': 'EPSG:3857',
        'title': 'WGS 84 / Pseudo-Mercator',
        'definition': '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs',
        'units': 'meters'
    },
    '900913': {
        'code': 'EPSG:900913',
        'title': 'Google Maps Global Mercator -- Spherical Mercator',
        'definition': '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs',
        'units': 'meters'
    },
    '4326': {
        'code': 'EPSG:4326',
        'title': 'WGS84',
        'definition': '+proj=longlat +datum=WGS84 +no_defs +axis=neu',
        'units': 'degrees'
    },
    '4258': {
        'code': 'EPSG:4258',
        'title': 'ETRS89',
        'definition': '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs +axis=neu',
        'units': 'degrees'
    },
    '25830': {
        'code': 'EPSG:25830',
        'title': 'ETRS89 / UTM zone 30N',
        'definition': '+proj=utm +zone=30 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs',
        'units': 'meters'
    },
    '25829': {
        'code': 'EPSG:25829',
        'title': 'ETRS89 / UTM zone 29N',
        'definition': '+proj=utm +zone=30 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs',
        'units': 'meters'
    },
    '102033': {
        'code': 'EPSG:102033',
        'title': 'South America Albers Equal Area Conic',
        'definition': '+proj=aea +lat_1=-5 +lat_2=-42 +lat_0=-32 +lon_0=-60 +x_0=0 +y_0=0 +ellps=aust_SA +units=m +no_defs',
        'units': 'meters'
    },
    '32721': {
        'code': 'EPSG:32721',
        'title': 'WGS 84 / UTM zone 21S',
        'definition': '+proj=utm +zone=21 +south +datum=WGS84 +units=m +no_defs',
        'units': 'meters'
    },
    '4674': {
        'code': 'EPSG:4674',
        'title': 'SIRGAS 2000 Geographic2D',
        'definition': '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs',
        'units': 'degrees'
    }
}

GVSIGOL_TOOLS = {
    'get_feature_info_control': {
        'private_fields_prefix': '_'
    },
    'attribute_table': {
        'private_fields_prefix': '_',
        'show_search': True
    }
}

GVSIGOL_ENABLE_ENUMERATIONS = True

GVSIGOL_BASE_LAYERS = {
    'bing': {
        'active': False,
        'key': BING_KEY_DEVEL # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
    }
}


GVSIGOL_SKIN = env('GVSIGOL_SKIN')

GVSIGOL_PATH = 'gvsigonline'
GVSIGOL_NAME = 'gvsig'
GVSIGOL_SURNAME = 'OL'
GVSIGOL_NAME_SHORT = 'g'
GVSIGOL_SURNAME_SHORT = 'OL'

FILEMANAGER_DIRECTORY = os.path.join(MEDIA_ROOT, 'data')
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

# REST framework
default_auth_classes_list = [
    'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework.authentication.BasicAuthentication'
]
if GVSIGOL_AUTH_BACKEND == 'gvsigol_plugin_oidc_mozilla' :
    default_auth_classes_list.insert(0,'mozilla_django_oidc.contrib.drf.OIDCAuthentication')


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': tuple (default_auth_classes_list)
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
            'level': env('LOG_LEVEL'),
            'propagate': False
        },
    },
}

TEMPORAL_ADVANCED_PARAMETERS = False

LEGACY_GVSIGOL_SERVICES = {
    'ENGINE':'geoserver',
    'URL': 'https://localhost/geoserver',
    'USER': GEOSERVER_USER_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
    'PASSWORD': GEOSERVER_PW_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
}


CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_TASK_ACKS_LATE = True
CELERYBEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_ALWAYS_EAGER  = True

CACHE_OPTIONS = {
    'GRID_SUBSETS': ['EPSG:3857', 'EPSG:4326'],
    'FORMATS': ['image/png'],
    'OPERATION_MODE': 'ONLY_MASTER'
}

PROXIES = {
    "http"  : None,
    "https" : None,
    "ftp"   : None
}

# use development backend if not using Apache/xsendfile
SENDFILE_BACKEND = 'django_sendfile.backends.development'
#SENDFILE_BACKEND = 'django_sendfile.backends.xsendfile'
SENDFILE_ROOT = '/'
SHARED_VIEW_EXPIRATION_TIME = 1

VERSION_FIELD = 'feat_version_gvol'
DATE_FIELD = 'feat_date_gvol'

PUSH_NOTIFICATIONS_SETTINGS = {
    "FCM_API_KEY": "[your api key]",
    "GCM_API_KEY": "[your api key]",
    "APNS_CERTIFICATE": "/path/to/your/certificate.pem",
    "APNS_TOPIC": "com.example.push_test",
    "WNS_PACKAGE_SECURITY_ID": "[your package security id, e.g: 'ms-app://e-3-4-6234...']",
    "WNS_SECRET_KEY": "[your app secret key, e.g.: 'KDiejnLKDUWodsjmewuSZkk']",
    "WP_PRIVATE_KEY": "/path/to/your/private.pem",
    "WP_CLAIMS": {'sub': "mailto: development@example.com"}
}

RELOAD_NODES_DELAY = 5 #EN SEGUNDOS

LAYERS_ROOT = 'layer_downloads'
#ALLOWED_HOST_NAMES = ['http://localhost']


ALLOWED_HOST_NAMES = [env('BASE_URL')]
for i in env('ALLOWED_HOST_NAMES'):
    print("INFO: Adding allowed host name: " + i)
    ALLOWED_HOST_NAMES.append(i)
print ("INFO: ALLOWED_HOST_NAMES = " + str(ALLOWED_HOST_NAMES))

JWT_AUTH = {
    #'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=5),
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=2),
    'JWT_ALLOW_REFRESH': True,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),
}

CHECK_TILELOAD_ERROR = False

GRAPH_MODELS = {
    'all_applications': False,
    'group_models': True,
    'app_labels': ['gvsigol_app_tocantins','gvsigol_plugin_print','gvsigol_plugin_edition','gvsigol_plugin_catalog','gvsigol_plugin_importvector','gvsigol_plugin_importfromservice','gvsigol_plugin_draw','gvsigol_plugin_geocoding','gvsigol_plugin_charts']
    }

GEOETL_DB = {
    'host': env('DB_HOST'),
    'port': env('DB_PORT'),
    'database': env('DB_NAME'),
    'user': env('DB_USER'),
    'password': env('DB_PASS'),
    'schema': 'ds_plugin_geoetl'
}

PRJ_LABELS = ['mobile', 'field_work', 'generic', 'main', 'citizen_app', 'public', 'viewer', 'management', 'government' , 'admin', 'infrastructures', 'data_collection', 'info', 'pois']
DATA_UPLOAD_MAX_NUMBER_FIELDS = 4096

# Frontend SPA
USE_SPA_PROJECT_LINKS = env('USE_SPA_PROJECT_LINKS')
FRONTEND_BASE_URL = env('FRONTEND_BASE_URL')
FRONTEND_REDIRECT_URL = env('FRONTEND_REDIRECT_URL')

# prueba para el gtfseditor y el problema con POST
#APPEND_SLASH=True

# UI iframe mode 
IFRAME_MODE_UI=env('IFRAME_MODE_UI')

# Allow users to manage permissions 
MANAGE_PERMISSION_UI=env('MANAGE_PERMISSION_UI')
